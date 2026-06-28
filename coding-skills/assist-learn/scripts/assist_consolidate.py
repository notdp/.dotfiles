#!/usr/bin/env python3
"""Explicit Phase2 consolidation for raw memory candidates.

This is a deterministic write path for `/assist-consolidate`: it consumes
candidate JSON files, applies safety/promotion gates, accepts a structured
ADD/UPDATE/SKIP/DELETE/INVALIDATE decision, and writes tracked memory only after
the shared fail-closed redact gate passes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


try:
    from scripts.hooks.memory_score import parse_frontmatter, problem_type_weight, score_note, split_frontmatter
    from scripts.hooks.redact import SecretFoundError, assert_no_secrets
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from scripts.hooks.memory_score import parse_frontmatter, problem_type_weight, score_note, split_frontmatter
    from scripts.hooks.redact import SecretFoundError, assert_no_secrets


CATEGORY_TO_PROBLEM_TYPE = {
    "decision": "decision",
    "correction": "correction",
    "preference": "preference",
    "failure-mode": "failure-mode",
    "failure_mode": "failure-mode",
    "fact": "knowledge",
    "knowledge": "knowledge",
    "pattern": "pattern",
    "bug": "bug",
}
ACTIVE_STATUSES = {"", "active"}
TODAY = dt.date.today().isoformat()

ANTI_SELF_POISONING_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "negative_tool_claim",
        re.compile(r"(?i)\b(?:cannot|can't|can not|unable to|does not work|doesn't work|broken|unusable|不能用|坏了)\b"),
    ),
    (
        "transient_environment_failure",
        re.compile(
            r"(?i)\b(?:command not found|no such file|missing binary|missing credential|credential.*missing|permission denied|PATH (?:not set|not configured)|not configured|缺二进制|缺凭证|未配置凭证|PATH 未配置)\b"
        ),
    ),
    ("one_time_task_narration", re.compile(r"(?i)\b(?:this session|one[- ]time|temporary todo|一次性任务|本轮任务)\b")),
)


class ConsolidationError(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    id: str
    summary: str
    evidence: str
    implication: str
    problem_type: str
    origin_session: str
    raw: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConsolidationError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConsolidationError(f"{path}: top-level JSON must be an object")
    return data


def iter_candidates(raw_dir: Path) -> list[Candidate]:
    candidates: list[Candidate] = []
    if not raw_dir.exists():
        return candidates
    for path in sorted(raw_dir.glob("*.json")):
        data = load_json(path)
        candidates.append(parse_candidate(data, path))
    return candidates


def parse_candidate(data: dict[str, Any], path: Path) -> Candidate:
    for field in ("summary", "evidence", "implication", "origin_session"):
        if not str(data.get(field, "")).strip():
            raise ConsolidationError(f"{path}: missing required field {field}")
    category = str(data.get("category") or data.get("problem_type") or "").strip().lower()
    if category not in CATEGORY_TO_PROBLEM_TYPE:
        raise ConsolidationError(f"{path}: unsupported category/problem_type {category!r}")
    candidate_id = str(data.get("id") or path.stem).strip() or path.stem
    return Candidate(
        id=candidate_id,
        summary=str(data["summary"]).strip(),
        evidence=str(data["evidence"]).strip(),
        implication=str(data["implication"]).strip(),
        problem_type=CATEGORY_TO_PROBLEM_TYPE[category],
        origin_session=str(data["origin_session"]).strip(),
        raw=data,
    )


def candidate_text(candidate: Candidate) -> str:
    return "\n".join([candidate.summary, candidate.evidence, candidate.implication])


def anti_self_poisoning_reason(candidate: Candidate) -> str | None:
    text = candidate_text(candidate)
    for reason, pattern in ANTI_SELF_POISONING_RULES:
        if pattern.search(text):
            return reason
    return None


def promoted(candidate: Candidate, action: str) -> tuple[bool, str]:
    raw = candidate.raw
    if bool(raw.get("user_marked")):
        return True, "user_marked"
    if candidate.problem_type == "decision" and str(raw.get("why") or "").strip() and candidate.evidence:
        return True, "decision_with_why"
    if int(raw.get("occurrences") or 0) >= 2:
        return True, "recurring"
    if str(raw.get("scope") or "").lower() == "vault" and raw.get("commit") and raw.get("verify_json"):
        return True, "vault_evidence"
    if action in {"ADD", "UPDATE", "DELETE", "INVALIDATE"}:
        return True, f"llm_action_{candidate.problem_type}"
    return False, "not_promoted"


def keywords_for(candidate: Candidate) -> list[str]:
    raw_keywords = candidate.raw.get("keywords") or candidate.raw.get("tags") or []
    if isinstance(raw_keywords, str):
        items = [item.strip() for item in re.split(r"[,\s]+", raw_keywords) if item.strip()]
    elif isinstance(raw_keywords, list):
        items = [str(item).strip() for item in raw_keywords if str(item).strip()]
    else:
        items = []
    for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", candidate.summary.lower()):
        if word not in items:
            items.append(word)
    return items[:8]


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", fallback.lower()).strip("-") or "memory-note"
    return slug[:80]


def frontmatter_value(value: str) -> str:
    # Emit a YAML-safe double-quoted scalar so titles/values containing ':',
    # '#', quotes, etc. cannot break downstream frontmatter parsers (a malformed
    # title silently dropped the whole note in agentsview's strict YAML syncer).
    s = str(value).replace("\n", " ").strip()
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def render_user_note(candidate: Candidate) -> str:
    keywords = keywords_for(candidate)
    keywords_text = "[" + ", ".join(keywords) + "]" if keywords else "[]"
    title = frontmatter_value(candidate.summary)
    return (
        "---\n"
        f"title: {title}\n"
        f"date: {TODAY}\n"
        f"problem_type: {candidate.problem_type}\n"
        "type: semantic\n"
        f"created: {TODAY}\n"
        f"last_accessed: {TODAY}\n"
        "status: active\n"
        f"valid_from: {TODAY}\n"
        "valid_to:\n"
        "superseded_by:\n"
        "trust: \"0.8\"\n"
        f"keywords: {keywords_text}\n"
        "related: []\n"
        f"origin_session: {frontmatter_value(candidate.origin_session)}\n"
        "verify:\n"
        f"applies_to: {frontmatter_value(str(candidate.raw.get('applies_to') or 'user'))}\n"
        "---\n\n"
        f"Evidence: {candidate.evidence}\n\n"
        f"Implication: {candidate.implication}\n"
    )


def render_project_note(candidate: Candidate) -> str:
    tags = "[" + ", ".join(keywords_for(candidate)) + "]"
    return (
        "---\n"
        f"title: {frontmatter_value(candidate.summary)}\n"
        f"date: {TODAY}\n"
        f"problem_type: {candidate.problem_type}\n"
        "module: memory\n"
        "component: assist-consolidate\n"
        f"tags: {tags}\n"
        "---\n\n"
        f"## Context\n\n- Evidence: {candidate.evidence}\n\n"
        f"## Reusable Pattern\n\n- Implication: {candidate.implication}\n"
    )


def safe_write(path: Path, text: str) -> None:
    assert_no_secrets(text, source=str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def unique_path(directory: Path, basename: str) -> Path:
    path = directory / f"{basename}.md"
    index = 2
    while path.exists():
        path = directory / f"{basename}-{index}.md"
        index += 1
    return path


def rebuild_index(root: Path) -> None:
    script = root / "scripts" / "build_memory_index.py"
    if not script.exists():
        script = Path(__file__).resolve().parents[3] / "scripts" / "build_memory_index.py"
    result = subprocess.run(["python3", str(script), "--root", str(root)], text=True, capture_output=True)
    if result.returncode != 0:
        raise ConsolidationError(result.stderr or result.stdout)


def load_decisions(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        raise ConsolidationError("--decision-file is required; tests may pass a fixture provider, production must provide a structured decision")
    decision = load_json(path)
    if "action" in decision:
        return {"*": decision}
    if not decision or not all(isinstance(value, dict) and "action" in value for value in decision.values()):
        raise ConsolidationError(f"{path}: missing decision action")
    return decision


def decision_for(decisions: dict[str, dict[str, Any]], candidate: Candidate) -> dict[str, Any]:
    if candidate.id in decisions:
        return decisions[candidate.id]
    if "*" in decisions:
        return decisions["*"]
    raise ConsolidationError(f"candidate {candidate.id}: missing per-candidate decision")


def query_terms(candidate: Candidate) -> list[str]:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", candidate_text(candidate).lower())
    seen: set[str] = set()
    unique = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            unique.append(term)
    return unique[:20]


def related_notes(root: Path, candidate: Candidate, top: int = 5) -> list[tuple[float, Path]]:
    user_dir = root / "memory" / "user"
    if not user_dir.exists():
        return []
    terms = query_terms(candidate)
    hits: list[tuple[float, Path]] = []
    for path in sorted(user_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = split_frontmatter(text)
        meta = parse_frontmatter(frontmatter)
        if meta.get("status", "active").lower() not in ACTIVE_STATUSES:
            continue
        score = score_note(frontmatter, body, terms) * problem_type_weight(meta.get("problem_type", ""))
        if score > 0:
            hits.append((score, path))
    hits.sort(key=lambda item: (-item[0], item[1].name))
    return hits[:top]


def emit_context(root: Path, candidate: Candidate) -> None:
    notes = related_notes(root, candidate)
    print("decision_context related=" + ",".join(path.name for _score, path in notes))


def replace_frontmatter_line(text: str, key: str, value: str) -> str:
    frontmatter, body = split_frontmatter(text)
    if not frontmatter:
        raise ConsolidationError("target note is missing frontmatter")
    lines = frontmatter.splitlines()
    replaced = False
    for idx, line in enumerate(lines):
        if line.split(":", 1)[0].strip() == key:
            lines[idx] = f"{key}: {value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(lines) + "\n---\n\n" + body.rstrip() + "\n"


def soft_invalidate(path: Path, *, superseded_by: str, invalid_at: str | None = None) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_frontmatter_line(text, "status", "archived")
    text = replace_frontmatter_line(text, "valid_to", TODAY)
    text = replace_frontmatter_line(text, "superseded_by", superseded_by or "invalidated")
    if invalid_at:
        text = text.rstrip() + f"\n\ninvalid_at: {invalid_at}\n"
    safe_write(path, text)


def add_user_note(root: Path, candidate: Candidate) -> Path:
    user_dir = root / "memory" / "user"
    path = unique_path(user_dir, slugify(candidate.summary, candidate.id))
    safe_write(path, render_user_note(candidate))
    return path


def add_project_note(root: Path, candidate: Candidate) -> Path:
    target_dir = root / "docs" / "learnings" / candidate.problem_type
    path = unique_path(target_dir, slugify(candidate.summary, candidate.id))
    safe_write(path, render_project_note(candidate))
    return path


def project_repo_gate(candidate: Candidate, repo_nature: str, approved: bool) -> tuple[bool, str]:
    nature = (repo_nature or "internal").lower()
    if nature in {"client", "oss"} and bool(candidate.raw.get("cross_project")) and not approved:
        return False, "repo_nature_gate"
    return True, "ok"


def process_candidate(root: Path, candidate: Candidate, decision: dict[str, Any], args: argparse.Namespace) -> str:
    try:
        assert_no_secrets(candidate_text(candidate), source=f"candidate:{candidate.id}")
    except SecretFoundError as exc:
        raise ConsolidationError(f"redact gate rejected candidate {candidate.id}: {exc}") from exc

    blacklist_reason = anti_self_poisoning_reason(candidate)
    if blacklist_reason:
        return f"skip {candidate.id} anti_self_poisoning:{blacklist_reason}"

    action = str(decision.get("action") or "ADD").upper()

    if args.emit_decision_context:
        emit_context(root, candidate)

    if action == "SKIP":
        return f"skip {candidate.id} decision_skip:{decision.get('reason', '')}"

    ok, reason = promoted(candidate, action)
    if not ok:
        return f"skip {candidate.id} {reason}"

    if args.store == "project":
        allowed, gate_reason = project_repo_gate(candidate, args.repo_nature, args.approve_cross_project)
        if not allowed:
            return f"skip {candidate.id} {gate_reason}"
        return f"write {candidate.id} {add_project_note(root, candidate).relative_to(root)}"

    note_id = str(decision.get("note_id") or "").strip()
    if action in {"UPDATE", "DELETE", "INVALIDATE"} and note_id:
        target = root / "memory" / "user" / note_id
        if target.exists():
            replacement = add_user_note(root, candidate) if action == "UPDATE" else None
            soft_invalidate(
                target,
                superseded_by=replacement.name if replacement else str(decision.get("superseded_by") or "invalidated"),
                invalid_at=str(decision.get("invalid_at") or decision.get("reason") or action.lower()),
            )
            if replacement:
                return f"update {candidate.id} {note_id} -> {replacement.relative_to(root)}"
            return f"soft_invalidate {candidate.id} {note_id}"
        if action == "UPDATE":
            path = add_user_note(root, candidate)
            return f"write {candidate.id} fallback_add {path.relative_to(root)}"
    if action in {"DELETE", "INVALIDATE"}:
        return f"skip {candidate.id} missing_target"
    path = add_user_note(root, candidate)
    return f"write {candidate.id} {path.relative_to(root)}"


def verify_assertion_failed(root: Path, assertion: str) -> bool:
    assertion = assertion.strip()
    if not assertion:
        return False
    if assertion.startswith(("/", "~")) or ".." in Path(assertion).parts:
        return True
    return not (root / assertion).exists()


def invalidate_failed_verify_notes(root: Path) -> list[str]:
    user_dir = root / "memory" / "user"
    if not user_dir.exists():
        return []
    results = []
    for path in sorted(user_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, _body = split_frontmatter(text)
        meta = parse_frontmatter(frontmatter)
        if meta.get("status", "active").lower() not in ACTIVE_STATUSES:
            continue
        assertion = meta.get("verify", "")
        if verify_assertion_failed(root, assertion):
            soft_invalidate(path, superseded_by="verify-failed", invalid_at="verify-failed")
            results.append(f"invalidated {path.name} verify-failed")
    if results:
        rebuild_index(root)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate raw memory candidates into tracked stores.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--store", choices=("user", "project"), default="user")
    parser.add_argument("--decision-file", type=Path)
    parser.add_argument("--repo-nature", choices=("internal", "client", "oss"), default="internal")
    parser.add_argument("--approve-cross-project", action="store_true")
    parser.add_argument("--emit-decision-context", action="store_true")
    parser.add_argument("--invalidate-failed-verify", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.invalidate_failed_verify:
        try:
            results = invalidate_failed_verify_notes(root)
        except ConsolidationError as exc:
            print(f"assist_consolidate failed: {exc}", file=sys.stderr)
            return 1
        for line in results:
            print(line)
        if not results:
            print("no failed verify assertions")
        return 0

    try:
        decisions = load_decisions(args.decision_file)
        results = []
        errors = []
        needs_index_rebuild = False
        for candidate in iter_candidates(root / args.raw_dir):
            try:
                result = process_candidate(root, candidate, decision_for(decisions, candidate), args)
                results.append(result)
                if args.store == "user" and (result.startswith("write ") or result.startswith("update ") or result.startswith("soft_invalidate ")):
                    needs_index_rebuild = True
            except ConsolidationError as exc:
                errors.append(str(exc))
        if needs_index_rebuild:
            rebuild_index(root)
    except ConsolidationError as exc:
        print(f"assist_consolidate failed: {exc}", file=sys.stderr)
        return 1
    for line in results:
        print(line)
    for error in errors:
        print(f"assist_consolidate failed: {error}", file=sys.stderr)
    if not results:
        print("no candidates")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

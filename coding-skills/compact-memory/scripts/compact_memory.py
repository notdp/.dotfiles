#!/usr/bin/env python3
"""Deterministic `/compact-memory` reflection write path."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


try:
    from scripts.hooks.memory_score import parse_frontmatter, score_note, split_frontmatter
    from scripts.hooks.context_capsule import index_search_text, inactive_memory_status, parse_index_rows
    from scripts.hooks.redact import SecretFoundError, assert_no_secrets
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from scripts.hooks.memory_score import parse_frontmatter, score_note, split_frontmatter
    from scripts.hooks.context_capsule import index_search_text, inactive_memory_status, parse_index_rows
    from scripts.hooks.redact import SecretFoundError, assert_no_secrets


TODAY = dt.date.today().isoformat()
# A synthesized topic note is denser than an atomic note, and the INDEX must
# accommodate a real cross-agent memory (hundreds of notes) — synthesis then
# SHRINKS it by folding atomics and marking sources stale. The old 6k/40k caps
# blocked every cycle once the pool grew past a few dozen notes.
DEFAULT_MAX_NOTE_CHARS = 20000
DEFAULT_MAX_INDEX_CHARS = 120000
ACTIVE_STATUS = {"", "active"}
BECAUSE_RE = re.compile(r"\(because of ([^)]+)\)")


class CompactMemoryError(ValueError):
    pass


@dataclass(frozen=True)
class SourceNote:
    path: Path
    note_id: str
    meta: dict[str, str]
    frontmatter: str
    body: str


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CompactMemoryError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CompactMemoryError(f"{path}: top-level JSON must be an object")
    return data


def memory_user_dir(root: Path) -> Path:
    return root / "memory" / "user"


def read_source_notes(root: Path) -> list[SourceNote]:
    user_dir = memory_user_dir(root)
    notes: list[SourceNote] = []
    if not user_dir.exists():
        return notes
    for path in sorted(user_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = split_frontmatter(text)
        meta = parse_frontmatter(frontmatter)
        note_id = meta.get("id") or path.stem
        notes.append(SourceNote(path=path, note_id=note_id, meta=meta, frontmatter=frontmatter, body=body))
    return notes


def query_terms(topic: str) -> list[str]:
    seen: set[str] = set()
    terms = []
    for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", topic.lower()):
        if term not in seen:
            seen.add(term)
            terms.append(term)
    return terms[:20]


def decision_source_ids(decision: dict[str, Any]) -> list[str]:
    raw = decision.get("source_ids") or []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def select_sources(notes: list[SourceNote], topic: str, source_ids: list[str]) -> list[SourceNote]:
    ids = set(source_ids)
    terms = query_terms(topic)
    selected = []
    for note in notes:
        if note.meta.get("status", "active").strip().lower() not in ACTIVE_STATUS:
            continue
        # An explicitly requested source is honored regardless of type: the auto
        # synthesize worker clusters atomic notes (type:semantic from consolidate)
        # and names them by id. The episodic-only filter below applies only to the
        # topic-term fallback used by the manual /compact-memory skill.
        if note.note_id in ids or note.path.stem in ids:
            selected.append(note)
            continue
        if note.meta.get("type", "").strip().lower() != "episodic":
            continue
        if terms and score_note(note.frontmatter, note.body, terms) > 0:
            selected.append(note)
    return selected


def cited_ids(insight: str) -> list[str]:
    return [match.strip() for match in BECAUSE_RE.findall(insight)]


def validate_decision(decision: dict[str, Any], selected: list[SourceNote]) -> tuple[str, list[str]]:
    reflection_id = str(decision.get("id") or "reflection").strip() or "reflection"
    if str(decision.get("action") or "ADD").upper() == "SKIP":
        return reflection_id, []
    title = str(decision.get("title") or "").strip()
    insight = str(decision.get("insight") or "").strip()
    if not title:
        raise CompactMemoryError(f"decision {reflection_id}: missing title")
    if not insight:
        raise CompactMemoryError(f"decision {reflection_id}: missing insight")
    citations = cited_ids(insight)
    if not citations:
        raise CompactMemoryError(f"decision {reflection_id}: missing because-of citation")
    selected_ids = {note.note_id for note in selected} | {note.path.stem for note in selected}
    unknown = sorted(set(citations) - selected_ids)
    if unknown:
        raise CompactMemoryError(f"decision {reflection_id}: unknown_source {', '.join(unknown)}")
    if len(set(citations)) < 2:
        raise CompactMemoryError(f"decision {reflection_id}: under_supported citations={len(set(citations))}")
    return reflection_id, citations


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or fallback or "reflection")[:80]


def frontmatter_value(value: str) -> str:
    return str(value).replace("\n", " ").replace('"', "'").strip()


def keywords_text(decision: dict[str, Any], selected: list[SourceNote]) -> str:
    raw = decision.get("keywords") or []
    keywords: list[str] = []
    if isinstance(raw, str):
        keywords.extend(item.strip() for item in re.split(r"[,\s]+", raw) if item.strip())
    elif isinstance(raw, list):
        keywords.extend(str(item).strip() for item in raw if str(item).strip())
    for note in selected:
        for item in re.split(r"[,\s]+", note.meta.get("keywords", "")):
            clean = item.strip().strip("[]'")
            if clean and clean not in keywords:
                keywords.append(clean)
    return "[" + ", ".join(keywords[:8]) + "]"


def render_semantic_note(decision: dict[str, Any], selected: list[SourceNote]) -> str:
    title = frontmatter_value(str(decision["title"]))
    source_ids = [note.note_id for note in selected]
    related = "[" + ", ".join(source_ids) + "]"
    reflection_id = frontmatter_value(str(decision.get("id") or slugify(title, "reflection")))
    problem_type = frontmatter_value(str(decision.get("problem_type") or "knowledge"))
    if problem_type not in {"knowledge", "pattern", "decision", "preference", "failure-mode", "bug"}:
        problem_type = "knowledge"
    # Citations are required in the decision insight for validation, but they are
    # provenance, not prose — keep them in `related` and strip the inline
    # "(because of <id>)" markers from the readable body.
    insight = BECAUSE_RE.sub("", str(decision["insight"]))
    insight = re.sub(r"[ \t]{2,}", " ", insight).strip()
    return (
        "---\n"
        f"title: {title}\n"
        f"date: {TODAY}\n"
        f"problem_type: {problem_type}\n"
        "type: semantic\n"
        f"created: {TODAY}\n"
        f"last_accessed: {TODAY}\n"
        "status: active\n"
        f"valid_from: {TODAY}\n"
        "valid_to:\n"
        "superseded_by:\n"
        "trust: \"0.8\"\n"
        f"keywords: {keywords_text(decision, selected)}\n"
        f"related: {related}\n"
        f"origin_session: compact-memory:{reflection_id}\n"
        "verify:\n"
        "applies_to: user\n"
        "---\n\n"
        f"Insight: {insight}\n"
    )


def unique_path(directory: Path, basename: str) -> Path:
    path = directory / f"{basename}.md"
    index = 2
    while path.exists():
        path = directory / f"{basename}-{index}.md"
        index += 1
    return path


def render_index(root: Path) -> str:
    try:
        from scripts.build_memory_index import render_index as build_render_index
    except ModuleNotFoundError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from scripts.build_memory_index import render_index as build_render_index
    return build_render_index(memory_user_dir(root))


def projected_index_with_note(root: Path, path: Path, note_text: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp) / "repo"
        tmp_user_dir = tmp_root / "memory" / "user"
        tmp_user_dir.mkdir(parents=True, exist_ok=True)
        source_user_dir = memory_user_dir(root)
        if source_user_dir.exists():
            for source in source_user_dir.glob("*.md"):
                if source.name == path.name:
                    continue
                shutil.copy2(source, tmp_user_dir / source.name)
        (tmp_user_dir / path.name).write_text(note_text, encoding="utf-8")
        return render_index(tmp_root)


def rebuild_index(root: Path) -> None:
    script = Path(__file__).resolve().parents[3] / "scripts" / "build_memory_index.py"
    result = subprocess.run(["python3", str(script), "--root", str(root)], text=True, capture_output=True)
    if result.returncode != 0:
        raise CompactMemoryError(result.stderr or result.stdout)


def semantic_duplicate(notes: list[SourceNote], decision: dict[str, Any], source_ids: list[str]) -> bool:
    title = str(decision.get("title") or "").strip().lower()
    source_set = set(source_ids)
    for note in notes:
        if note.meta.get("status", "active").strip().lower() not in ACTIVE_STATUS:
            continue
        if note.meta.get("type", "").strip().lower() != "semantic":
            continue
        existing_title = note.meta.get("title", "").strip().lower()
        if title and existing_title == title:
            return True
        related = {item.strip() for item in re.split(r"[,\s]+", note.meta.get("related", "")) if item.strip()}
        if source_set and source_set.issubset(related):
            return True
    return False


def replace_frontmatter_line(text: str, key: str, value: str) -> str:
    if not text.startswith("---\n"):
        raise CompactMemoryError("target note is missing frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise CompactMemoryError("target note is missing frontmatter")
    frontmatter = text[4:end]
    rest = text[end + len("\n---") :]
    if rest.startswith("\n\n"):
        body_prefix = "\n\n"
        body = rest[2:]
    elif rest.startswith("\n"):
        body_prefix = "\n"
        body = rest[1:]
    else:
        body_prefix = ""
        body = rest
    lines = frontmatter.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.split(":", 1)[0].strip() == key:
            lines[index] = f"{key}: {value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(lines) + "\n---" + body_prefix + body


def mark_stale(note: SourceNote, reason: str) -> None:
    text = note.path.read_text(encoding="utf-8")
    text = replace_frontmatter_line(text, "status", "stale")
    text = replace_frontmatter_line(text, "valid_to", TODAY)
    text = replace_frontmatter_line(text, "stale_reason", frontmatter_value(reason))
    assert_no_secrets(text, source=str(note.path))
    note.path.write_text(text, encoding="utf-8")


def preflight_budget(root: Path, path: Path, note_text: str, max_note_chars: int, max_index_chars: int, reflection_id: str) -> None:
    try:
        assert_no_secrets(note_text, source=str(path))
    except SecretFoundError as exc:
        raise CompactMemoryError(f"redact gate rejected {reflection_id}: {exc}") from exc
    if len(note_text) > max_note_chars:
        raise CompactMemoryError(f"discard {reflection_id} char_budget_exceeded note_chars={len(note_text)} max_note_chars={max_note_chars}")
    user_dir = memory_user_dir(root)
    projected = projected_index_with_note(root, path, note_text)
    if len(projected) > max_index_chars:
        raise CompactMemoryError(f"discard {reflection_id} char_budget_exceeded index_chars={len(projected)} max_index_chars={max_index_chars}")
    assert_no_secrets(projected, source=str(user_dir / "INDEX.md"))


def stale_sources(decision: dict[str, Any]) -> dict[str, str]:
    raw = decision.get("stale_sources") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(key).strip(): str(value).strip() or "refuted" for key, value in raw.items() if str(key).strip()}


def selected_notes_by_id(selected: list[SourceNote]) -> dict[str, SourceNote]:
    result: dict[str, SourceNote] = {}
    for note in selected:
        result[note.note_id] = note
        result[note.path.stem] = note
    return result


def validate_stale_sources(decision: dict[str, Any], selected: list[SourceNote], reflection_id: str) -> list[tuple[SourceNote, str]]:
    selected_by_id = selected_notes_by_id(selected)
    resolved: list[tuple[SourceNote, str]] = []
    for source_id, reason in stale_sources(decision).items():
        note = selected_by_id.get(source_id)
        if not note:
            raise CompactMemoryError(f"decision {reflection_id}: unknown_source {source_id}")
        resolved.append((note, reason))
    return resolved


def compact(root: Path, args: argparse.Namespace) -> tuple[int, list[str]]:
    decision = load_json(args.decision_file)
    reflection_id = str(decision.get("id") or "reflection").strip() or "reflection"
    if str(decision.get("action") or "ADD").upper() == "SKIP":
        return 0, [f"skip {reflection_id} decision_skip:{decision.get('reason', '')}"]
    notes = read_source_notes(root)
    requested_ids = decision_source_ids(decision)
    selected = select_sources(notes, args.topic or " ".join(requested_ids), requested_ids)
    if len(selected) < 2:
        return 0, [f"skip {reflection_id} below_threshold sources={len(selected)}"]
    reflection_id, citations = validate_decision(decision, selected)
    stale_to_mark = validate_stale_sources(decision, selected, reflection_id)
    if semantic_duplicate(notes, decision, citations):
        return 0, [f"skip {reflection_id} duplicate_semantic"]
    note_text = render_semantic_note(decision, selected)
    path = unique_path(memory_user_dir(root), slugify(str(decision.get("title") or "reflection"), reflection_id))
    preflight_budget(root, path, note_text, args.max_note_chars, args.max_index_chars, reflection_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(note_text, encoding="utf-8")
    for note, reason in stale_to_mark:
        mark_stale(note, reason)
    rebuild_index(root)
    return 0, [f"write {reflection_id} {path.relative_to(root)} sources={','.join(citations)}"]


def read_index_rows(root: Path) -> list[dict[str, str]]:
    index_path = memory_user_dir(root) / "INDEX.md"
    try:
        return parse_index_rows(index_path.read_text(encoding="utf-8"))
    except OSError:
        return []


def holdout_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CompactMemoryError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        query = str(row.get("query") or "").strip()
        expected = str(row.get("expected") or "").strip()
        if not query or not expected:
            raise CompactMemoryError(f"{path}:{line_no}: query and expected are required")
        rows.append({"query": query, "expected": expected})
    return rows


def evaluate_recall(root: Path, args: argparse.Namespace) -> tuple[int, list[str]]:
    rows = holdout_rows(args.holdout)
    notes_by_name = {note.path.name: note for note in read_source_notes(root)}
    index_rows = read_index_rows(root)
    hits = 0
    for row in rows:
        terms = query_terms(row["query"])
        scored = []
        for index_row in index_rows:
            if inactive_memory_status(index_row.get("status", "active")):
                continue
            note = notes_by_name.get(index_row.get("file", ""))
            if not note:
                continue
            meta = {**index_row, **note.meta}
            if inactive_memory_status(meta.get("status", "active")):
                continue
            score = score_note(index_search_text(index_row, meta), "", terms)
            if score > 0:
                scored.append((score, note.path.name, note))
        scored.sort(key=lambda item: (-item[0], item[1]))
        top = scored[: args.top_k]
        expected = row["expected"]
        if any(expected in {note.note_id, note.path.stem, note.path.name} for _score, _name, note in top):
            hits += 1
    total = len(rows)
    hit_rate = hits / total if total else 0.0
    suffix = f"hits={hits} total={total} hit_rate={hit_rate:.3f} threshold={args.threshold:.3f} top_k={args.top_k}"
    if hit_rate >= args.threshold:
        return 0, [f"embedding_decision lexical_sufficient {suffix}"]
    return 2, [f"embedding_decision embedding_required {suffix}"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compact repeated episodic memory into cited semantic memory.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--topic", default="")
    parser.add_argument("--decision-file", type=Path)
    parser.add_argument("--max-note-chars", type=int, default=DEFAULT_MAX_NOTE_CHARS)
    parser.add_argument("--max-index-chars", type=int, default=DEFAULT_MAX_INDEX_CHARS)
    parser.add_argument("--evaluate-recall", action="store_true")
    parser.add_argument("--holdout", type=Path)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()

    root = args.root.resolve()
    try:
        if args.evaluate_recall:
            if not args.holdout:
                raise CompactMemoryError("--holdout is required with --evaluate-recall")
            code, lines = evaluate_recall(root, args)
        else:
            if not args.decision_file:
                raise CompactMemoryError("--decision-file is required")
            code, lines = compact(root, args)
    except CompactMemoryError as exc:
        message = str(exc)
        if message.startswith("discard "):
            print(message, file=sys.stderr)
        else:
            print(f"compact_memory failed: {message}", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

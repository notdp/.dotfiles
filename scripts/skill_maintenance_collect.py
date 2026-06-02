#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"https?://\S*(?:private|token|secret)\S*", re.I),
    re.compile(r"(?:token|secret|password|api[_-]?key)\s*[:=]\s*\S+", re.I),
]


def run_git(repo: Path, args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def preflight(repo: Path) -> dict[str, Any]:
    _, branch, _ = run_git(repo, ["branch", "--show-current"])
    _, head, _ = run_git(repo, ["rev-parse", "HEAD"])
    _, status, _ = run_git(repo, ["status", "--short"])
    return {
        "repo": str(repo),
        "branch": branch,
        "head": head,
        "dirty_files": [line for line in status.splitlines() if line],
    }


def inventory(repo: Path) -> dict[str, Any]:
    skill_files = sorted(repo.glob("coding-skills/*/SKILL.md"))
    root_commands = sorted((repo / "commands").glob("*.md")) if (repo / "commands").exists() else []
    hook_scripts = sorted((repo / "scripts" / "hooks").glob("*.py")) if (repo / "scripts" / "hooks").exists() else []
    hook_tests = sorted((repo / "scripts" / "tests").glob("test_hook_*.py")) if (repo / "scripts" / "tests").exists() else []
    return {
        "skill_count": len(skill_files),
        "skills": [str(path.relative_to(repo)) for path in skill_files],
        "commands": [str(path.relative_to(repo)) for path in root_commands],
        "agents_file": str((repo / "agents" / "AGENTS.md").relative_to(repo)) if (repo / "agents" / "AGENTS.md").exists() else None,
        "hook_scripts": [str(path.relative_to(repo)) for path in hook_scripts],
        "hook_tests": [str(path.relative_to(repo)) for path in hook_tests],
        "micro_refs": str((repo / "docs" / "refs-micro-index.md").relative_to(repo)) if (repo / "docs" / "refs-micro-index.md").exists() else None,
    }


def verify_skills(repo: Path) -> list[dict[str, Any]]:
    script = repo / "scripts" / "verify_skills.py"
    if not script.exists():
        return [{"id": "verify-skills-missing", "severity": "blocker", "area": "skills", "issue": "scripts/verify_skills.py missing", "evidence": str(script)}]
    result = subprocess.run(["python3", str(script)], cwd=repo, text=True, capture_output=True, timeout=120)
    findings: list[dict[str, Any]] = []
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if result.returncode != 0:
        findings.append({"id": "verify-skills-failed", "severity": "blocker", "area": "skills", "issue": "verify_skills failed", "evidence": output[-2000:]})
    for line in output.splitlines():
        if "GUARDRAIL WARNING" in line:
            findings.append({"id": "skill-guardrail-warning", "severity": "should", "area": "skills", "issue": line.strip(), "evidence": "python3 scripts/verify_skills.py"})
        elif "RISK WARNING" in line:
            severity = "should" if high_risk_category_count(line) >= 2 else "observe"
            findings.append({"id": "skill-risk-warning", "severity": severity, "area": "skills", "issue": line.strip(), "evidence": "python3 scripts/verify_skills.py"})
        elif line.startswith("validated ") and " skill routing cases" in line:
            findings.append({"id": "skill-routing-cases-validated", "severity": "observe", "area": "skills", "issue": "skill routing cases validated", "evidence": line.strip()})
        elif line.startswith("validated agent assets:"):
            findings.append({"id": "agent-assets-validated", "severity": "observe", "area": "assets", "issue": "agent assets validated", "evidence": line.strip()})
    return findings


def high_risk_category_count(line: str) -> int:
    marker = "categories:"
    if marker not in line:
        return 0
    categories = [category.strip() for category in line.split(marker, 1)[1].split(",")]
    return len([category for category in categories if category])


def has_sensitive(value: str) -> bool:
    return any(pattern.search(value) for pattern in SENSITIVE_PATTERNS)


def encoded_repo_session_dir(repo: Path, home: Path) -> Path:
    encoded = str(repo).replace("/", "-")
    return home / ".factory" / "sessions" / encoded


def content_parts(message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message.get("content")
    return content if isinstance(content, list) else []


def summarize_session(path: Path, repo: Path) -> dict[str, Any] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not lines:
        return None
    title = path.stem
    cwd = ""
    tool_counts: Counter[str] = Counter()
    sensitive = False
    errors: Counter[str] = Counter()
    for index, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            errors["json-decode"] += 1
            continue
        if index == 0:
            title = obj.get("sessionTitle") or obj.get("title") or title
            cwd = obj.get("cwd") or cwd
        rendered = json.dumps(obj, ensure_ascii=False)
        if has_sensitive(rendered):
            sensitive = True
        message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        for part in content_parts(message):
            if part.get("type") == "tool_use":
                name = part.get("name")
                if isinstance(name, str):
                    tool_counts[name] += 1
    if cwd and str(repo) not in cwd and ".dotfiles" not in cwd:
        return None
    if sum(tool_counts.values()) < 1:
        return None
    return {
        "id": path.stem,
        "title": title,
        "cwd": cwd,
        "tool_counts": dict(tool_counts),
        "error_categories": dict(errors),
        "sensitive_content_present": sensitive,
    }


def sample_sessions(repo: Path, home: Path, seed: str, limit_min: int = 3, limit_max: int = 5) -> list[dict[str, Any]]:
    session_root = encoded_repo_session_dir(repo, home)
    candidates = sorted(session_root.glob("*.jsonl"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True) if session_root.exists() else []
    summaries = [summary for path in candidates if (summary := summarize_session(path, repo))]
    if not summaries:
        return []
    rng = random.Random(seed)
    sample_size = min(limit_max, max(min(limit_min, len(summaries)), min(len(summaries), limit_max)))
    selected = summaries[:]
    rng.shuffle(selected)
    return selected[:sample_size]


def refs_summary(repo: Path, fetch: bool) -> list[dict[str, Any]]:
    gitmodules = repo / ".gitmodules"
    if not gitmodules.exists():
        return []
    refs: list[dict[str, Any]] = []
    current: dict[str, str] = {}
    for line in gitmodules.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("[submodule"):
            if current.get("path"):
                refs.append(current)
            current = {}
        elif stripped.startswith("path ="):
            current["path"] = stripped.split("=", 1)[1].strip()
        elif stripped.startswith("url ="):
            current["url"] = stripped.split("=", 1)[1].strip()
    if current.get("path"):
        refs.append(current)
    output = []
    for item in refs:
        ref_path = repo / item["path"]
        old_code, old_head, _ = run_git(ref_path, ["rev-parse", "HEAD"]) if ref_path.exists() else (1, "", "missing")
        fetch_status = "skipped"
        if fetch and ref_path.exists():
            try:
                code, _, err = run_git(ref_path, ["fetch", "--all", "--tags", "--prune"], timeout=120)
                fetch_status = "ok" if code == 0 else f"failed: {err}"
            except subprocess.TimeoutExpired:
                fetch_status = "failed: timeout after 120s"
        remote_code, remote_head, _ = run_git(ref_path, ["rev-parse", "origin/HEAD"]) if ref_path.exists() else (1, "", "missing")
        if remote_code != 0 and ref_path.exists():
            remote_code, remote_head, _ = run_git(ref_path, ["rev-parse", "origin/main"])
        output.append({"path": item["path"], "url": item.get("url", ""), "old": old_head if old_code == 0 else "missing", "remote": remote_head if remote_code == 0 else "unknown", "fetch": fetch_status})
    return output


def refs_metadata_findings(repo: Path, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in refs:
        path = item.get("path")
        if not isinstance(path, str) or not path:
            continue
        ref_path = repo / path
        if not ref_path.exists():
            findings.append(
                {
                    "id": "refs-metadata-warning",
                    "severity": "should",
                    "area": "refs",
                    "issue": ".gitmodules declares a ref path that is missing from the working tree",
                    "evidence": path,
                }
            )
            continue
        if item.get("old") == "missing":
            findings.append(
                {
                    "id": "refs-metadata-warning",
                    "severity": "should",
                    "area": "refs",
                    "issue": "ref path exists but git metadata could not resolve HEAD",
                    "evidence": path,
                }
            )
        fetch_status = item.get("fetch")
        if isinstance(fetch_status, str) and fetch_status.startswith("failed:"):
            findings.append(
                {
                    "id": "refs-metadata-warning",
                    "severity": "should",
                    "area": "refs",
                    "issue": "refs fetch failed without stopping collection",
                    "evidence": f"{path}: {fetch_status}",
                }
            )
    if refs and not findings:
        findings.append(
            {
                "id": "refs-metadata-validated",
                "severity": "observe",
                "area": "refs",
                "issue": "refs metadata paths validated",
                "evidence": f"refs={len(refs)}",
            }
        )
    return findings


def hook_signals_from_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals = []
    for session in sessions:
        tool_counts = session.get("tool_counts", {})
        shell_count = sum(tool_counts.get(name, 0) for name in ("bash", "execute", "shell"))
        if shell_count:
            signals.append({"signal": "shell-tool-used", "category": "observe", "sessions": [session["id"]], "evidence": f"shell tool count={shell_count}", "affected_hook": "command_guard", "proposal": "inspect if repeated failures appear"})
    return signals


def collect(repo: Path, fetch: bool, home: Path) -> dict[str, Any]:
    pre = preflight(repo)
    refs = refs_summary(repo, fetch=fetch)
    findings = verify_skills(repo) + refs_metadata_findings(repo, refs)
    sessions = sample_sessions(repo, home, seed=pre.get("head") or "skill-maintenance")
    return {
        "preflight": pre,
        "inventory": inventory(repo),
        "refs": refs,
        "sessions": sessions,
        "hook_signals": hook_signals_from_sessions(sessions),
        "deterministic_findings": findings,
        "review": {"status": "model-dispatch-unavailable", "reason": "actual model dispatch evidence is unavailable"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect skill maintenance signals as JSON, including summarized real session I/O.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument("--fetch", action="store_true", help="Fetch refs remotes before comparing local remote-tracking HEADs. Disabled by default.")
    parser.add_argument("--no-fetch", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    payload = collect(args.repo.resolve(), fetch=args.fetch and not args.no_fetch, home=Path.home())
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

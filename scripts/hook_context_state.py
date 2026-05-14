#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALIDATION_RE = re.compile(r"(run-verify\.sh|pytest|npm test|tsc|verify_skills\.py|unittest|pass|failed|ok)", re.I)
TODO_RE = re.compile(r"^\s*\d+\.\s+\[(?:in_progress|pending|completed)\].*", re.I | re.M)
MAX_CONTEXT_CHARS = 2000


def project_root() -> Path:
    return Path(os.environ.get("FACTORY_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def state_path(root: Path) -> Path:
    return root / ".factory" / "scratch" / "compact-state.json"


def suppress() -> dict:
    return {"suppressOutput": True}


def load_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(stringify(item) for item in value)
    if isinstance(value, dict):
        if "text" in value:
            return stringify(value["text"])
        if "content" in value:
            return stringify(value["content"])
        return " ".join(stringify(item) for item in value.values())
    return str(value) if value is not None else ""


def transcript_lines(path: str | None, *, max_lines: int = 400) -> list[dict]:
    if not path:
        return []
    transcript = Path(path).expanduser()
    if not transcript.exists():
        return []
    lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:]
    records: list[dict] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def last_user_prompt(records: list[dict]) -> str:
    for record in reversed(records):
        if record.get("role") == "user":
            content = stringify(record.get("content")).strip()
            if content:
                return content[:500]
        message = record.get("message")
        if isinstance(message, dict) and message.get("role") == "user":
            content = stringify(message.get("content")).strip()
            if content:
                return content[:500]
    return ""


def recent_validation(records: list[dict]) -> str:
    snippets: list[str] = []
    for record in records[-120:]:
        text = stringify(record)
        if VALIDATION_RE.search(text):
            snippets.append(re.sub(r"\s+", " ", text).strip()[:240])
    return " | ".join(snippets[-3:])


def recent_todos(records: list[dict]) -> list[str]:
    matches: list[str] = []
    for record in records[-120:]:
        text = stringify(record)
        matches.extend(match.group(0).strip() for match in TODO_RE.finditer(text))
    return matches[-8:]


def changed_files(root: Path) -> list[str]:
    result = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            files.append(path)
    return files[:80]


def build_state(root: Path, hook_input: dict) -> dict:
    records = transcript_lines(hook_input.get("transcript_path"))
    return {
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "cwd": str(root),
        "last_user_prompt": last_user_prompt(records),
        "changed_files": changed_files(root),
        "recent_validation": recent_validation(records),
        "recent_todos": recent_todos(records),
        "risks": [],
    }


def save_state(root: Path, hook_input: dict) -> dict:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_state(root, hook_input), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return suppress()


def load_state(root: Path) -> dict:
    try:
        return json.loads(state_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def compact_context(state: dict) -> str:
    if not state:
        return ""
    lines = [
        "# Compact Recovery Capsule",
        "",
        f"- Last user goal: {state.get('last_user_prompt') or 'unknown'}",
        f"- Changed files: {', '.join(state.get('changed_files') or []) or 'none recorded'}",
        f"- Recent validation: {state.get('recent_validation') or 'none recorded'}",
    ]
    todos = state.get("recent_todos") or []
    if todos:
        lines.append("- Recent todos:")
        lines.extend(f"  - {todo}" for todo in todos[:8])
    risks = state.get("risks") or []
    if risks:
        lines.append("- Risks:")
        lines.extend(f"  - {risk}" for risk in risks[:5])
    lines.append("- Next: re-open the changed files and verify current state before continuing.")
    context = "\n".join(lines)
    return context[:MAX_CONTEXT_CHARS]


def session_start(root: Path, hook_input: dict) -> dict:
    if hook_input.get("source") != "compact":
        return suppress()
    context = compact_context(load_state(root))
    if not context:
        return suppress()
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
        "suppressOutput": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Save and restore compact recovery context.")
    parser.add_argument("--event", choices=["pre-compact", "session-start"], required=True)
    args = parser.parse_args()

    root = project_root()
    hook_input = load_input()
    output = save_state(root, hook_input) if args.event == "pre-compact" else session_start(root, hook_input)
    sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

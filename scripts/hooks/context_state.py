#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from .redact import URL_RE, redact
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from redact import URL_RE, redact


VALIDATION_RE = re.compile(r"(run-verify\.sh|pytest|npm test|tsc|verify_skills\.py|unittest|pass|failed|ok)", re.I)
BOUNDARY_DECISION_RE = re.compile(r"Boundary decisions:\s*(.*?)(?:\n\n|\Z)", re.I | re.S)
BLOCKER_RE = re.compile(r"^\s*(?:\b(?:Blocked|Blocker)\b|阻塞)[:：]\s*(.+)", re.I | re.M)
MAX_CONTEXT_CHARS = 2000
STATE_TTL_DAYS = 14


def project_root() -> Path:
    return Path(os.environ.get("FACTORY_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def state_dir(root: Path) -> Path:
    return root / ".agent-state" / "hooks" / "compact-state"


def old_neutral_state_path(root: Path) -> Path:
    return root / ".agent-state" / "hooks" / "compact-state.json"


def legacy_state_path(root: Path) -> Path:
    return root / ".factory" / "scratch" / "compact-state.json"


def slug(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-._")
    return safe[:80] if safe else ""


def state_key(hook_input: dict) -> str:
    transcript_path = hook_input.get("transcript_path")
    if isinstance(transcript_path, str) and transcript_path.strip():
        digest = hashlib.sha256(str(Path(transcript_path).expanduser()).encode("utf-8")).hexdigest()[:16]
        return f"transcript-{digest}"
    for key in ["session_id", "sessionId", "conversation_id", "conversationId", "turn_id", "turnId"]:
        value = hook_input.get(key)
        if isinstance(value, str) and value.strip():
            return slug(value)
    return "default"


def state_path(root: Path, hook_input: dict) -> Path:
    return state_dir(root) / f"{state_key(hook_input)}.json"


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
                return redact(content)[:500]
        message = record.get("message")
        if isinstance(message, dict) and message.get("role") == "user":
            content = stringify(message.get("content")).strip()
            if content:
                return redact(content)[:500]
    return ""


def recent_validation(records: list[dict]) -> str:
    snippets: list[str] = []
    for record in records[-120:]:
        text = stringify(record)
        if VALIDATION_RE.search(text):
            snippets.append(redact(re.sub(r"\s+", " ", text).strip())[:240])
    return " | ".join(snippets[-3:])


def boundary_decisions(records: list[dict]) -> str:
    decisions: list[str] = []
    for record in records[-120:]:
        text = stringify(record)
        for match in BOUNDARY_DECISION_RE.finditer(text):
            body = re.sub(r"\s+", " ", match.group(1)).strip()
            if body:
                decisions.append(redact(body)[:240])
    return " | ".join(decisions[-3:])


def blockers(records: list[dict]) -> str:
    found: list[str] = []
    for record in records[-120:]:
        text = stringify(record)
        for match in BLOCKER_RE.finditer(text):
            found.append(redact(match.group(1).strip())[:240])
    return " | ".join(found[-3:])


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
        "state_key": state_key(hook_input),
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "cwd": str(root),
        "goal": last_user_prompt(records),
        "current_step": "not inferred",
        "last_user_prompt": last_user_prompt(records),
        "changed_files": changed_files(root),
        "recent_validation": recent_validation(records),
        "boundary_decisions": boundary_decisions(records),
        "blockers": blockers(records),
        "next_action": "not inferred; re-open changed files and verify current state before continuing",
        "risks": [],
    }


def ensure_agent_state_ignored(root: Path) -> None:
    gitignore = root / ".gitignore"
    try:
        current = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if any(line.strip() == ".agent-state/" for line in current.splitlines()):
            return
        suffix = "" if not current or current.endswith("\n") else "\n"
        gitignore.write_text(current + suffix + ".agent-state/\n", encoding="utf-8")
    except OSError:
        return


def save_state(root: Path, hook_input: dict) -> dict:
    path = state_path(root, hook_input)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleanup_expired_states(path.parent)
    ensure_agent_state_ignored(root)
    path.write_text(json.dumps(build_state(root, hook_input), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return suppress()


def parse_updated_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def cleanup_expired_states(directory: Path) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=STATE_TTL_DAYS)
    for path in directory.glob("*.json"):
        state = read_json(path)
        updated_at = parse_updated_at(state.get("updated_at"))
        if updated_at is None or updated_at >= cutoff:
            continue
        remove_state_file(path)


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_state_file(root: Path, hook_input: dict) -> tuple[dict, Path | None]:
    paths: list[Path] = [state_path(root, hook_input)]
    paths.extend([old_neutral_state_path(root), legacy_state_path(root)])
    for path in paths:
        state = read_json(path)
        if state:
            return state, path
    return {}, None


def remove_state_file(path: Path | None) -> None:
    if not path:
        return
    try:
        path.unlink()
    except OSError:
        return


def compact_context(state: dict) -> str:
    if not state:
        return ""
    lines = [
        "# Compact Recovery Capsule",
        "",
        "TaskCheckpoint:",
        f"- Goal: {state.get('goal') or state.get('last_user_prompt') or 'unknown'}",
        f"- Current step: {state.get('current_step') or 'not inferred'}",
        f"- Changed files: {', '.join(state.get('changed_files') or []) or 'none recorded'}",
        f"- Recent validation: {state.get('recent_validation') or 'none recorded'}",
        f"- Boundary decisions: {state.get('boundary_decisions') or 'none recorded'}",
        f"- Blockers: {state.get('blockers') or 'none recorded'}",
        f"- Next action: {state.get('next_action') or 'not inferred; re-open changed files and verify current state before continuing'}",
    ]
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
    state, path = load_state_file(root, hook_input)
    context = compact_context(state)
    if not context:
        return suppress()
    remove_state_file(path)
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

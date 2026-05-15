#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


HIGH_RISK_RE = re.compile(
    r"(封装|wrap|wrapper|包装|包一层|接入|对接|集成|adapter|integration|service\s+wrap|"
    r"schema|response_model|metric|metrics|埋点|指标|data source|数据源|canonical|snapshot|"
    r"sampling|limit|prod|生产|context|hook|CLAUDE\.md|AGENTS\.md)",
    re.I,
)
FACT_RE = re.compile(
    r"(Boundary decisions:|Callers:|caller|importers|Contract cases:|Data source:|Metric route:|"
    r"Schema contract:|用户批准|user-approved|approved by user|我需要确认|需要你确认|请确认)",
    re.I,
)
EDIT_TOOLS = {"ApplyPatch", "Create", "Edit", "Write", "MultiEdit"}
MAX_TRANSCRIPT_CHARS = 80000


def load_input() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def suppress() -> dict[str, bool]:
    return {"suppressOutput": True}


def transcript_text(path: str | None) -> str:
    if not path:
        return ""
    transcript = Path(path).expanduser()
    if not transcript.exists():
        return ""
    return transcript.read_text(encoding="utf-8", errors="replace")[-MAX_TRANSCRIPT_CHARS:]


def record_text(record: dict[str, Any]) -> str:
    message = record.get("message", record)
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content or "")


def recent_user_prompt(transcript: str) -> str:
    for raw_line in reversed(transcript.splitlines()):
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        role = record.get("role") or record.get("type") or record.get("message", {}).get("role")
        if role == "user":
            return record_text(record)
    return ""


def has_boundary_facts(transcript: str) -> bool:
    return bool(FACT_RE.search(transcript[-20000:]))


def should_gate(tool_name: str, transcript: str) -> bool:
    if tool_name not in EDIT_TOOLS:
        return False
    prompt = recent_user_prompt(transcript)
    return bool(HIGH_RISK_RE.search(prompt) and not has_boundary_facts(transcript))


def gate_payload(mode: str) -> dict[str, Any]:
    message = (
        "Boundary gate advisory: high-risk boundary prompt detected before edit, but no boundary facts "
        "were found. First list Boundary decisions, Callers, Contract cases, Data source, Metric route, "
        "or Schema contract, or ask the user to confirm the boundary."
    )
    if mode == "block":
        return {"decision": "block", "reason": message, "suppressOutput": True}
    return {"systemMessage": message}


def main() -> int:
    hook_input = load_input()
    tool_name = str(hook_input.get("tool_name") or hook_input.get("toolName") or "")
    transcript = transcript_text(hook_input.get("transcript_path"))
    mode = os.environ.get("BOUNDARY_GATE_MODE", "advisory").lower()
    if should_gate(tool_name, transcript):
        sys.stdout.write(json.dumps(gate_payload(mode), ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(json.dumps(suppress(), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

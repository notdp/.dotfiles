#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


RISK_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("schema-contract", re.compile(r"(schema|response_model|request|response|envelope)", re.I)),
    ("observability-routing", re.compile(r"(metric|metrics|埋点|指标)", re.I)),
    ("data-source", re.compile(r"(data source|数据源|canonical|snapshot)", re.I)),
    ("shared-path", re.compile(r"(封装|wrapper|包装|包一层|接入|对接|adapter|集成层|集成接口|集成方案|integration\s+(?:layer|point|module)|service\s+wrap)", re.I)),
    ("context-surface", re.compile(r"(context|hook|prompt|capsule|CLAUDE\.md|AGENTS\.md|PreToolUse|PostToolUse|UserPromptSubmit)", re.I)),
    ("limit-default-fallback", re.compile(r"(sampling|limit|fallback|default|默认值|上限|兜底)", re.I)),
    ("operational-side-effect", re.compile(r"(\bprod\b|production|线上|生产环境|生产数据|生产库|生产集群|生产系统|生产服务|生产配置|部署到生产|上生产)", re.I)),
)
CODE_FENCE_RE = re.compile(r"```.*?```", re.S)
CONTEXT_SURFACE_PATH_RE = re.compile(
    r"(^|/)(agents/AGENTS\.md|\.claude/settings\.json|\.factory/settings\.json|scripts/hooks/|scripts/hook_|agents/context-capsules/|skills/|commands/)",
    re.I,
)
FACT_FIELD_RE = re.compile(
    r"^\s*-?\s*(Boundary facts|Boundary decisions|Risk types|Callers|Contract cases|Data source|Metric route|"
    r"Schema contract|User approval)\s*:\s*(?P<value>.*)$",
    re.I,
)
USER_APPROVAL_RE = re.compile(r"(用户批准|user-approved|approved by user|批准|同意|确认)", re.I)
EMPTY_VALUE_RE = re.compile(r"^\s*(?:none|无|n/a|not applicable)\s*$", re.I)
EDIT_TOOLS = {"ApplyPatch", "Create", "Edit", "Write", "MultiEdit"}
MAX_TRANSCRIPT_CHARS = 80000
AGENT_CONFIG_PATH_RE = re.compile(
    r"(?:^|/)(\.config/(?:kilo|opencode)|\.claude|\.factory|\.codex|\.cursor|\.aider)(?:/|$)",
    re.I,
)


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


def transcript_records(transcript: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_line in transcript.splitlines():
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def record_role(record: dict[str, Any]) -> str:
    message = record.get("message")
    role = record.get("role") or record.get("type")
    if role:
        return str(role)
    if isinstance(message, dict):
        return str(message.get("role") or "")
    return ""


def recent_user_prompt_index(records: list[dict[str, Any]]) -> tuple[int, str]:
    for index in range(len(records) - 1, -1, -1):
        record = records[index]
        if record_role(record) == "user":
            return index, record_text(record)
    return -1, ""


def classify_risks(prompt: str) -> set[str]:
    return {risk for risk, pattern in RISK_RULES if pattern.search(CODE_FENCE_RE.sub("", prompt))}


def tool_target_path(hook_input: dict[str, Any]) -> str:
    tool_input = hook_input.get("tool_input") or hook_input.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def filter_risks_for_target(risks: set[str], target_path: str) -> set[str]:
    if "context-surface" not in risks or not target_path or CONTEXT_SURFACE_PATH_RE.search(target_path):
        return risks
    return risks - {"context-surface"}


def field_has_value(raw_value: str) -> bool:
    value = raw_value.strip()
    return bool(value and not EMPTY_VALUE_RE.fullmatch(value))


def structured_fields(records: list[dict[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for record in records:
        text = record_text(record)
        for line in text.splitlines():
            match = FACT_FIELD_RE.match(line)
            if not match:
                continue
            field = match.group(1).lower()
            if field == "boundary facts" and not field_has_value(match.group("value")):
                fields.add(field)
                continue
            if match and field_has_value(match.group("value")):
                fields.add(field)
    return fields


def user_approval_present(records: list[dict[str, Any]]) -> bool:
    return any(record_role(record) == "user" and USER_APPROVAL_RE.search(record_text(record)) for record in records)


def complete_boundary_facts_present(fields: set[str]) -> bool:
    return {"boundary facts", "risk types"} <= fields


def missing_boundary_facts(risks: set[str], records_after_prompt: list[dict[str, Any]]) -> list[str]:
    fields = structured_fields(records_after_prompt)
    if user_approval_present(records_after_prompt):
        return []

    missing: list[str] = []
    if "schema-contract" in risks and not ({"schema contract", "contract cases"} & fields):
        missing.append("Schema contract or Contract cases")
    if "observability-routing" in risks and "metric route" not in fields:
        missing.append("Metric route")
    if "data-source" in risks and "data source" not in fields:
        missing.append("Data source")
    if "shared-path" in risks and not ({"callers", "contract cases"} & fields):
        missing.append("Callers or Contract cases")
    if "context-surface" in risks and not complete_boundary_facts_present(fields):
        missing.append("Boundary facts with Risk types")
    if "limit-default-fallback" in risks and not (complete_boundary_facts_present(fields) or "contract cases" in fields):
        missing.append("Boundary facts with Risk types or Contract cases")
    if "operational-side-effect" in risks and "user approval" not in fields:
        missing.append("User approval")
    return missing


def should_gate(tool_name: str, transcript: str, target_path: str = "") -> tuple[bool, list[str]]:
    if tool_name not in EDIT_TOOLS:
        return False, []
    records = transcript_records(transcript)
    prompt_index, prompt = recent_user_prompt_index(records)
    if prompt_index < 0:
        return True, ["recent user prompt"]
    risks = filter_risks_for_target(classify_risks(prompt), target_path)
    if not risks:
        return False, []
    missing = missing_boundary_facts(risks, records[prompt_index + 1 :])
    return bool(missing), missing


def is_outside_repo_agent_config(target_path: str, repo_root: Path) -> bool:
    """True when an edit targets an agent runtime config dir (kilo/opencode/claude/
    factory/codex/cursor/aider) that lives outside the repo. Editing the repo's own
    source is fine; writing the deployed config directly bypasses the git SSOT."""
    if not target_path:
        return False
    path = Path(target_path).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    try:
        resolved = path.resolve()
        if resolved.is_relative_to(repo_root.resolve()):
            return False
    except (OSError, RuntimeError, ValueError):
        return False
    return bool(AGENT_CONFIG_PATH_RE.search(str(resolved)))


def gitops_advisory_payload() -> dict[str, Any]:
    return {
        "systemMessage": (
            "Boundary gate advisory: this edit targets an agent runtime config outside the repo "
            "(kilo/opencode/claude/factory/...). Writing deployed config directly bypasses the git "
            "SSOT. Route through /guard-gitops and make the change in the repo source instead."
        )
    }


def gate_payload(mode: str, missing: list[str]) -> dict[str, Any]:
    missing_text = ", ".join(missing) if missing else "Boundary facts"
    message = (
        "Boundary gate advisory: high-risk boundary prompt detected before edit, but no boundary facts "
        f"were found. Missing: {missing_text}. First list a structured `Boundary facts:` block or ask the user to confirm the boundary."
    )
    if mode == "block":
        return {"decision": "block", "reason": message, "suppressOutput": True}
    return {"systemMessage": message}


def main() -> int:
    hook_input = load_input()
    tool_name = str(hook_input.get("tool_name") or hook_input.get("toolName") or "")
    transcript = transcript_text(hook_input.get("transcript_path"))
    mode = os.environ.get("BOUNDARY_GATE_MODE", "advisory").lower()
    target_path = tool_target_path(hook_input)
    should_warn, missing = should_gate(tool_name, transcript, target_path)
    repo_root = Path(os.environ.get("FACTORY_PROJECT_DIR") or os.getcwd())
    if should_warn:
        payload = gate_payload(mode, missing)
    elif tool_name in EDIT_TOOLS and is_outside_repo_agent_config(target_path, repo_root):
        payload = gitops_advisory_payload()
    else:
        payload = suppress()
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

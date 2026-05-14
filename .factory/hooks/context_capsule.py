#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


OPERATIONAL_PROMPT_RE = re.compile(
    r"(刷数据|同步|迁移|回填|修复数据|批处理|dry-?run|apply|run-until-empty|concurrenc|"
    r"backfill|migration|migrate|sync|pipeline|batch|etl|repair|reconcile)",
    re.I,
)
CAPSULE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "security-gitops.md",
        re.compile(r"(prod|生产|deploy|部署|ssh|scp|push|release|secret|token|auth|permission|权限|db|database|数据库|kubectl|terraform|helm)", re.I),
    ),
    ("operational-task.md", OPERATIONAL_PROMPT_RE),
    (
        "debug-task.md",
        re.compile(r"(bug|error|fail|failed|flaky|traceback|exception|报错|失败|异常|复现|incident)", re.I),
    ),
    (
        "ui-task.md",
        re.compile(r"(ui|css|react|vue|svelte|tsx|jsx|页面|视觉|截图|figma|overflow|mobile|desktop)", re.I),
    ),
    (
        "planning-task.md",
        re.compile(r"(方案|计划|架构|设计|怎么做|approach|architecture|plan|options|phase|spec)", re.I),
    ),
)
MAX_PROMPT_CONTEXT_CHARS = 2200


def config_root() -> Path:
    return Path(__file__).resolve().parents[2]


def project_root() -> Path:
    return Path(os.environ.get("FACTORY_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def read_capsule(name: str) -> str:
    path = config_root() / "agents" / "context-capsules" / name
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def json_context(event_name: str, context: str) -> str:
    if not context:
        return json.dumps({"suppressOutput": True})
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": context,
            },
            "suppressOutput": True,
        },
        ensure_ascii=False,
    )


def load_hook_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def session_context(event_name: str) -> str:
    capsule = read_capsule("agent-discipline.md")
    return json_context(event_name, capsule)


def prompt_context(hook_input: dict) -> str:
    prompt = str(hook_input.get("prompt") or "")
    capsules = [read_capsule(name) for name, pattern in CAPSULE_RULES if pattern.search(prompt)]
    capsules = [capsule for capsule in capsules if capsule]
    if not capsules:
        return json.dumps({"suppressOutput": True})
    context = "\n\n---\n\n".join(capsules)[:MAX_PROMPT_CONTEXT_CHARS]
    return json_context("UserPromptSubmit", context)


def post_tool_context(root: Path) -> str:
    contexts: list[str] = []
    for script_name in ["scan_operational_task_contract.py", "scan_diff_residue.py"]:
        scanner = config_root() / "scripts" / script_name
        if not scanner.exists():
            continue
        result = subprocess.run(
            ["python3", str(scanner), "--hook"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if not result.stdout.strip():
            continue
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        context = payload.get("hookSpecificOutput", {}).get("additionalContext")
        if context:
            contexts.append(str(context))
    if contexts:
        return json_context("PostToolUse", "\n\n---\n\n".join(contexts))
    return json.dumps({"suppressOutput": True})


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject short Droid context capsules.")
    parser.add_argument("--event", choices=["session-start", "pre-compact", "prompt", "post-tool"], required=True)
    args = parser.parse_args()

    root = project_root()
    hook_input = load_hook_input()
    if args.event == "session-start":
        print(session_context("SessionStart"))
    elif args.event == "pre-compact":
        print(session_context("PreCompact"))
    elif args.event == "prompt":
        print(prompt_context(hook_input))
    else:
        print(post_tool_context(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DROID_HOOKS: dict[str, Any] = {
    "UserPromptSubmit": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": '"$FACTORY_PROJECT_DIR"/scripts/hooks/context_capsule.py --event prompt',
                    "timeout": 10,
                }
            ]
        }
    ],
    "PostToolUse": [
        {
            "matcher": "ApplyPatch|Create|Edit",
            "hooks": [
                {
                    "type": "command",
                    "command": '"$FACTORY_PROJECT_DIR"/scripts/hooks/context_capsule.py --event post-tool',
                    "timeout": 15,
                }
            ],
        }
    ],
    "PreToolUse": [
        {
            "matcher": "ApplyPatch|Create|Edit",
            "hooks": [
                {
                    "type": "command",
                    "command": '"$FACTORY_PROJECT_DIR"/scripts/hooks/boundary_gate.py',
                    "timeout": 10,
                }
            ],
        },
        {
            "matcher": "Execute",
            "hooks": [
                {
                    "type": "command",
                    "command": '"$FACTORY_PROJECT_DIR"/scripts/hooks/command_guard.py',
                    "timeout": 10,
                }
            ],
        },
    ],
    "Stop": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": '"$FACTORY_PROJECT_DIR"/scripts/hooks/stop_check.py',
                    "timeout": 10,
                }
            ]
        }
    ],
}

MANAGED_COMMAND_PARTS = (
    "/scripts/hooks/context_state.py",
    "/scripts/hooks/context_capsule.py",
    "/scripts/hooks/boundary_gate.py",
    "/scripts/hooks/command_guard.py",
    "/scripts/hooks/stop_check.py",
    "scripts/hooks/context_state.py",
    "scripts/hooks/context_capsule.py",
    "scripts/hooks/boundary_gate.py",
    "scripts/hooks/command_guard.py",
    "scripts/hooks/stop_check.py",
    "/scripts/hook_context_state.py",
    "/scripts/hook_boundary_gate.py",
    "/scripts/hook_command_guard.py",
    "/scripts/hook_stop_check.py",
    "/.factory/hooks/context_capsule.py",
)
CODEX_HOOKS_BEGIN = "# dotfiles hooks: begin"
CODEX_HOOKS_END = "# dotfiles hooks: end"


def settings_path(project_dir: Path) -> Path:
    return project_dir / ".factory" / "settings.json"


def claude_settings_path(project_dir: Path) -> Path:
    return project_dir / ".claude" / "settings.json"


def codex_config_path(project_dir: Path) -> Path:
    return project_dir / ".codex" / "config.toml"


def load_settings(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def desired_droid_settings(current: dict[str, Any]) -> dict[str, Any]:
    next_settings = dict(current)
    next_settings["hooks"] = DROID_HOOKS
    return next_settings


def shell_command(project_dir: Path, script_name: str, args: str = "") -> str:
    script_path = (project_dir / "scripts" / "hooks" / script_name).as_posix()
    return f'"{script_path}"{(" " + args) if args else ""}'


def desired_claude_hooks(project_dir: Path) -> dict[str, Any]:
    return {
        "UserPromptSubmit": [
            {
                "hooks": [
                    {"type": "command", "command": shell_command(project_dir, "context_capsule.py", "--event prompt"), "timeout": 10}
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [
                    {"type": "command", "command": shell_command(project_dir, "context_capsule.py", "--event post-tool"), "timeout": 15}
                ],
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{"type": "command", "command": shell_command(project_dir, "boundary_gate.py"), "timeout": 10}],
            },
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": shell_command(project_dir, "command_guard.py"), "timeout": 10}],
            },
        ],
        "Stop": [
            {
                "hooks": [{"type": "command", "command": shell_command(project_dir, "stop_check.py"), "timeout": 10}]
            }
        ],
    }


def is_managed_command(command: Any) -> bool:
    if not isinstance(command, str):
        return False
    return any(part in command for part in MANAGED_COMMAND_PARTS)


def without_managed_hooks(hooks: Any) -> dict[str, Any]:
    if not isinstance(hooks, dict):
        return {}
    pruned: dict[str, Any] = {}
    for event_name, entries in hooks.items():
        if not isinstance(entries, list):
            pruned[event_name] = entries
            continue
        kept_entries: list[Any] = []
        for entry in entries:
            if not isinstance(entry, dict):
                kept_entries.append(entry)
                continue
            entry_hooks = entry.get("hooks")
            if not isinstance(entry_hooks, list):
                kept_entries.append(entry)
                continue
            kept_hooks = [hook for hook in entry_hooks if not is_managed_command(hook.get("command") if isinstance(hook, dict) else None)]
            if kept_hooks:
                next_entry = dict(entry)
                next_entry["hooks"] = kept_hooks
                kept_entries.append(next_entry)
        if kept_entries:
            pruned[event_name] = kept_entries
    return pruned


def merged_hooks(current_hooks: Any, desired_hooks: dict[str, Any]) -> dict[str, Any]:
    next_hooks = without_managed_hooks(current_hooks)
    for event_name, entries in desired_hooks.items():
        next_hooks.setdefault(event_name, [])
        if isinstance(next_hooks[event_name], list):
            next_hooks[event_name].extend(entries)
        else:
            next_hooks[event_name] = entries
    return next_hooks


def desired_claude_settings(current: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    next_settings = dict(current)
    next_settings["hooks"] = merged_hooks(current.get("hooks"), desired_claude_hooks(project_dir))
    return next_settings


def render_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def codex_hook_table(event_name: str, command: str, matcher: str | None = None) -> str:
    lines = [f"[[hooks.{event_name}]]"]
    if matcher:
        lines.append(f"matcher = {toml_string(matcher)}")
    lines.extend(
        [
            "",
            f"[[hooks.{event_name}.hooks]]",
            'type = "command"',
            f"command = {toml_string(command)}",
        ]
    )
    return "\n".join(lines)


def desired_codex_hook_block(project_dir: Path) -> str:
    entries = [
        codex_hook_table("UserPromptSubmit", shell_command(project_dir, "context_capsule.py", "--event prompt")),
        codex_hook_table("PreToolUse", shell_command(project_dir, "boundary_gate.py"), "*"),
        codex_hook_table("PreToolUse", shell_command(project_dir, "command_guard.py"), "*"),
        codex_hook_table("PostToolUse", shell_command(project_dir, "context_capsule.py", "--event post-tool"), "*"),
        codex_hook_table("Stop", shell_command(project_dir, "stop_check.py")),
    ]
    return "\n".join([CODEX_HOOKS_BEGIN, *entries, CODEX_HOOKS_END, ""])


def strip_codex_hook_block(content: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(CODEX_HOOKS_BEGIN)}.*?{re.escape(CODEX_HOOKS_END)}\n?",
        re.S,
    )
    return pattern.sub("\n", content).strip() + ("\n" if content.strip() else "")


def ensure_codex_hooks_feature(content: str) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "[features]":
            continue
        section_end = len(lines)
        for cursor in range(index + 1, len(lines)):
            stripped = lines[cursor].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section_end = cursor
                break
        for cursor in range(index + 1, section_end):
            if re.match(r"\s*hooks\s*=", lines[cursor]):
                lines[cursor] = "hooks = true"
                return "\n".join(lines).rstrip() + "\n"
        lines.insert(index + 1, "hooks = true")
        return "\n".join(lines).rstrip() + "\n"
    prefix = "[features]\nhooks = true\n\n"
    return prefix + content.lstrip()


def desired_codex_config(current: str, project_dir: Path) -> str:
    base = ensure_codex_hooks_feature(strip_codex_hook_block(current)).rstrip()
    return base + "\n\n" + desired_codex_hook_block(project_dir)


def droid_check(project_dir: Path) -> int:
    path = settings_path(project_dir)
    current = load_settings(path)
    if current.get("hooks") == DROID_HOOKS:
        sys.stdout.write(f"ok: {path} uses scripts/hooks runtime\n")
        return 0
    sys.stdout.write(f"mismatch: {path} does not match scripts/hooks runtime\n")
    return 1


def droid_print(project_dir: Path) -> int:
    current = load_settings(settings_path(project_dir))
    sys.stdout.write(render_json(desired_droid_settings(current)))
    return 0


def droid_apply(project_dir: Path) -> int:
    path = settings_path(project_dir)
    current = load_settings(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(desired_droid_settings(current)), encoding="utf-8")
    sys.stdout.write(f"updated: {path}\n")
    return 0


def claude_check(project_dir: Path) -> int:
    path = claude_settings_path(project_dir)
    current = load_settings(path)
    if current == desired_claude_settings(current, project_dir):
        sys.stdout.write(f"ok: {path} uses scripts/hooks runtime\n")
        return 0
    sys.stdout.write(f"mismatch: {path} does not match scripts/hooks runtime\n")
    return 1


def claude_print(project_dir: Path) -> int:
    current = load_settings(claude_settings_path(project_dir))
    sys.stdout.write(render_json(desired_claude_settings(current, project_dir)))
    return 0


def claude_apply(project_dir: Path) -> int:
    path = claude_settings_path(project_dir)
    current = load_settings(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(desired_claude_settings(current, project_dir)), encoding="utf-8")
    sys.stdout.write(f"updated: {path}\n")
    return 0


def codex_check(project_dir: Path) -> int:
    path = codex_config_path(project_dir)
    current = load_text(path)
    if current == desired_codex_config(current, project_dir):
        sys.stdout.write(f"ok: {path} uses scripts/hooks runtime\n")
        return 0
    sys.stdout.write(f"mismatch: {path} does not match scripts/hooks runtime\n")
    return 1


def codex_print(project_dir: Path) -> int:
    sys.stdout.write(desired_codex_config(load_text(codex_config_path(project_dir)), project_dir))
    return 0


def codex_apply(project_dir: Path) -> int:
    path = codex_config_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desired_codex_config(load_text(path), project_dir), encoding="utf-8")
    sys.stdout.write(f"updated: {path}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check, print, or apply hook adapter configuration.")
    parser.add_argument("--target", choices=["droid", "claude", "codex"], required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--print", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm --apply writes project hook configuration.")
    parser.add_argument("--project-dir", default=".", help="Project directory, defaults to current working directory.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if args.apply and not args.yes:
        sys.stdout.write("refusing: --apply requires --yes confirmation\n")
        return 1

    if args.target == "droid":
        if args.check:
            return droid_check(project_dir)
        if args.print:
            return droid_print(project_dir)
        return droid_apply(project_dir)

    if args.target == "claude":
        if args.check:
            return claude_check(project_dir)
        if args.print:
            return claude_print(project_dir)
        return claude_apply(project_dir)

    if args.check:
        return codex_check(project_dir)
    if args.print:
        return codex_print(project_dir)
    return codex_apply(project_dir)


if __name__ == "__main__":
    raise SystemExit(main())

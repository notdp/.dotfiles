#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


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
AIDER_HOOKS_BEGIN = "# dotfiles aider config: begin"
AIDER_HOOKS_END = "# dotfiles aider config: end"
CLIPROXY_BASE_URL = "http://localhost:8317/v1"
# 只 2 个真模型, 每个带 5 个思考档(kilo/opencode 用 variants 选择器选一次; droid 无选择器 → 每档一条 customModel)。
# efforts: 档位标签 → 实际 reasoningEffort(gpt 后端无 max, 返回 400, 故 gpt 的 max clamp 成 xhigh; opus 的 max 是真档)。
CLIPROXY_MODELS = (
    {
        "id": "gpt-5.5", "family": "gpt-5", "default": "high",
        "efforts": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh", "max": "xhigh"},
    },
    {
        "id": "claude-opus-4-8", "family": "claude", "default": "high",
        "efforts": {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh", "max": "max"},
    },
)
EFFORT_LABELS = ("low", "medium", "high", "xhigh", "max")
LOCAL_MODEL_CONTEXT_LIMIT = 1_000_000
LOCAL_MODEL_INPUT_LIMIT = 1_000_000
LOCAL_MODEL_OUTPUT_LIMIT = 128_000
LOCAL_CLAUDE_OUTPUT_LIMIT = 64_000
COMPACTION_THRESHOLD_PERCENT = 60
DROID_COMPACTION_TOKEN_LIMIT = 600_000
OPENCODE_COMPACTION_RESERVED = 20000
OPENCODE_COMPACTION_PRESERVE_RECENT = 20000
OPEN_EXTERNAL_DIRECTORIES = (
    "/Users/zhenninglang/.config/paw/images/**",
    "/Users/zhenninglang/Downloads/**",
    "/Users/zhenninglang/Projects/**",
)


def settings_path(project_dir: Path) -> Path:
    return project_dir / ".factory" / "settings.json"


def user_settings_path() -> Path:
    return home_path() / ".factory" / "settings.json"


def claude_settings_path(project_dir: Path) -> Path:
    return project_dir / ".claude" / "settings.json"


def codex_config_path(project_dir: Path) -> Path:
    return project_dir / ".codex" / "config.toml"


def opencode_config_path(config_dir: Path) -> Path:
    return config_dir / "opencode.json"


def kilo_config_path(config_dir: Path) -> Path:
    jsonc_path = config_dir / "kilo.jsonc"
    if jsonc_path.exists():
        return jsonc_path
    return config_dir / "kilo.json"


def aider_config_path(config_path: Path) -> Path:
    return config_path


def runtime_root() -> Path:
    return Path(__file__).resolve().parents[1]


def home_path() -> Path:
    return Path.home()


def default_opencode_config_dir() -> Path:
    return home_path() / ".config" / "opencode"


def default_kilo_config_dir() -> Path:
    if config_dir := os.environ.get("KILO_CONFIG_DIR"):
        return Path(config_dir).expanduser()
    if config_path := os.environ.get("KILO_CONFIG"):
        return Path(config_path).expanduser().parent
    if xdg_config_home := os.environ.get("XDG_CONFIG_HOME"):
        return Path(xdg_config_home).expanduser() / "kilo"
    return home_path() / ".config" / "kilo"


def default_aider_config_path() -> Path:
    return home_path() / ".aider.conf.yml"


def load_settings(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def strip_jsonc_comments(content: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    quote = ""
    escape = False
    while index < len(content):
        char = content[index]
        next_char = content[index + 1] if index + 1 < len(content) else ""
        if in_string:
            result.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                in_string = False
            index += 1
            continue
        if char in {'"', "'"}:
            in_string = True
            quote = char
            result.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            index += 2
            while index < len(content) and content[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(content) and content[index : index + 2] != "*/":
                index += 1
            index += 2
            continue
        result.append(char)
        index += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(result))


def load_jsonc_settings(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    data = json.loads(strip_jsonc_comments(content))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def shell_command(script_name: str, args: str = "") -> str:
    script_path = (runtime_root() / "scripts" / "hooks" / script_name).as_posix()
    return f'"{script_path}"{(" " + args) if args else ""}'


def desired_droid_hooks() -> dict[str, Any]:
    return {
        "UserPromptSubmit": [
            {
                "hooks": [
                    {"type": "command", "command": shell_command("context_capsule.py", "--event prompt"), "timeout": 10}
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "ApplyPatch|Create|Edit",
                "hooks": [
                    {"type": "command", "command": shell_command("context_capsule.py", "--event post-tool"), "timeout": 15}
                ],
            }
        ],
        "PreToolUse": [
            {
                "matcher": "ApplyPatch|Create|Edit",
                "hooks": [{"type": "command", "command": shell_command("boundary_gate.py"), "timeout": 10}],
            },
            {
                "matcher": "Execute",
                "hooks": [{"type": "command", "command": shell_command("command_guard.py"), "timeout": 10}],
            },
        ],
        "Stop": [
            {
                "hooks": [{"type": "command", "command": shell_command("stop_check.py"), "timeout": 10}]
            }
        ],
    }


def desired_droid_settings(current: dict[str, Any]) -> dict[str, Any]:
    next_settings = dict(current)
    next_settings["hooks"] = desired_droid_hooks()
    return next_settings


def desired_droid_model_settings(current: dict[str, Any]) -> dict[str, Any]:
    next_settings = dict(current)
    # 接管 customModels: 用统一 spec 生成的 10 个(覆盖现有, "其它模型都不要")
    next_settings["customModels"] = build_droid_custom_models()
    next_settings["compactionTokenLimit"] = DROID_COMPACTION_TOKEN_LIMIT
    next_settings["compactionTokenLimitPerModel"] = {
        model["id"]: DROID_COMPACTION_TOKEN_LIMIT for model in next_settings["customModels"]
    }
    return next_settings


def desired_claude_hooks(project_dir: Path) -> dict[str, Any]:
    return {
        "UserPromptSubmit": [
            {
                "hooks": [
                    {"type": "command", "command": shell_command("context_capsule.py", "--event prompt"), "timeout": 10}
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [
                    {"type": "command", "command": shell_command("context_capsule.py", "--event post-tool"), "timeout": 15}
                ],
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{"type": "command", "command": shell_command("boundary_gate.py"), "timeout": 10}],
            },
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": shell_command("command_guard.py"), "timeout": 10}],
            },
        ],
        "Stop": [
            {
                "hooks": [{"type": "command", "command": shell_command("stop_check.py"), "timeout": 10}]
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


def cliproxy_api_key() -> str:
    settings = load_settings(home_path() / ".factory" / "settings.json")
    for model in settings.get("customModels", []):
        if isinstance(model, dict) and model.get("baseUrl") == CLIPROXY_BASE_URL:
            api_key = model.get("apiKey")
            if isinstance(api_key, str) and api_key:
                return api_key
    return "hellowd"


def dotfiles_agents_path() -> str:
    return (runtime_root() / "agents" / "AGENTS.md").as_posix()


def dotfiles_skills_path() -> str:
    return (runtime_root() / "skills").as_posix()


def dotfiles_commands_path() -> str:
    return (runtime_root() / "commands").as_posix()


def opencode_plugin_path() -> str:
    return (runtime_root() / "scripts" / "opencode" / "dotfiles_hooks.mjs").as_posix()


def kilo_plugin_path() -> str:
    return (runtime_root() / "scripts" / "kilo" / "dotfiles_hooks.mjs").as_posix()


def local_model_limit(output: int = LOCAL_MODEL_OUTPUT_LIMIT) -> dict[str, int]:
    return {
        "context": LOCAL_MODEL_CONTEXT_LIMIT,
        "input": LOCAL_MODEL_INPUT_LIMIT,
        "output": output,
    }


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
        codex_hook_table("UserPromptSubmit", shell_command("context_capsule.py", "--event prompt")),
        codex_hook_table("PreToolUse", shell_command("boundary_gate.py"), "*"),
        codex_hook_table("PreToolUse", shell_command("command_guard.py"), "*"),
        codex_hook_table("PostToolUse", shell_command("context_capsule.py", "--event post-tool"), "*"),
        codex_hook_table("Stop", shell_command("stop_check.py")),
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


def desired_opencode_config(current: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(current)
    next_config.setdefault("$schema", "https://opencode.ai/config.json")
    next_config["model"] = "cliproxy/gpt-5.5"
    next_config["small_model"] = "cliproxy/gpt-5.5"
    next_config["compaction"] = {
        "auto": True,
        "threshold_percent": COMPACTION_THRESHOLD_PERCENT,
        "reserved": OPENCODE_COMPACTION_RESERVED,
        "preserve_recent_tokens": OPENCODE_COMPACTION_PRESERVE_RECENT,
    }
    instructions = [item for item in next_config.get("instructions", []) if isinstance(item, str)]
    if dotfiles_agents_path() not in instructions:
        instructions.append(dotfiles_agents_path())
    next_config["instructions"] = instructions

    skills = next_config.get("skills") if isinstance(next_config.get("skills"), dict) else {}
    paths = [item for item in skills.get("paths", []) if isinstance(item, str)]
    if dotfiles_skills_path() not in paths:
        paths.append(dotfiles_skills_path())
    next_config["skills"] = {**skills, "paths": paths}

    plugins = [item for item in next_config.get("plugin", []) if isinstance(item, (str, list))]
    if opencode_plugin_path() not in plugins:
        plugins.append(opencode_plugin_path())
    next_config["plugin"] = plugins

    provider = next_config.get("provider") if isinstance(next_config.get("provider"), dict) else {}
    provider["cliproxy"] = build_cliproxy_provider()
    next_config["provider"] = provider
    return next_config


def _effort_options(effort: str) -> dict[str, str]:
    return {"reasoningEffort": effort, "reasoning_effort": effort}


def build_cliproxy_provider() -> dict[str, Any]:
    """kilo/opencode provider: 2 个模型, 每个带 variants 档位表(选择器选一次, 不在模型名里烤档)。"""
    models: dict[str, dict[str, Any]] = {}
    for spec in CLIPROXY_MODELS:
        out_limit = LOCAL_CLAUDE_OUTPUT_LIMIT if spec["family"] == "claude" else LOCAL_MODEL_OUTPUT_LIMIT
        efforts = spec["efforts"]
        models[spec["id"]] = {
            "name": spec["id"],
            "family": spec["family"],
            "attachment": True,
            "reasoning": True,
            "tool_call": True,
            "modalities": {"input": ["text", "image"], "output": ["text"]},
            "limit": local_model_limit(out_limit),
            "options": _effort_options(efforts[spec["default"]]),
            "variants": {label: _effort_options(efforts[label]) for label in EFFORT_LABELS},
        }
    return {
        "name": "CLIProxyAPI",
        "npm": "@ai-sdk/openai-compatible",
        "options": {"baseURL": CLIPROXY_BASE_URL, "apiKey": cliproxy_api_key()},
        "models": models,
    }


def build_droid_custom_models() -> list[dict[str, Any]]:
    """droid customModels: droid 无"模型内档位选择器", 故每个(模型×思考档)一条。
    默认档用裸名(gpt-5.5), 其余加后缀(gpt-5.5-xhigh)。"""
    key = cliproxy_api_key()
    out: list[dict[str, Any]] = []
    index = 1
    for spec in CLIPROXY_MODELS:
        for label in EFFORT_LABELS:
            display = spec["id"] if label == spec["default"] else f"{spec['id']}-{label}"
            out.append({
                "model": spec["id"],
                "id": f"custom:{display}",
                "index": index,
                "baseUrl": CLIPROXY_BASE_URL,
                "apiKey": key,
                "displayName": display,
                "reasoningEffort": spec["efforts"][label],
                "noImageSupport": False,
                "provider": "openai",
            })
            index += 1
    return out


def desired_kilo_config(current: dict[str, Any]) -> dict[str, Any]:
    next_config = dict(current)
    next_config.setdefault("$schema", "https://app.kilo.ai/config.json")
    next_config["model"] = "cliproxy/gpt-5.5"
    next_config["small_model"] = "cliproxy/gpt-5.5"
    next_config["compaction"] = {
        "auto": True,
        "threshold_percent": COMPACTION_THRESHOLD_PERCENT,
        "reserved": OPENCODE_COMPACTION_RESERVED,
        "preserve_recent_tokens": OPENCODE_COMPACTION_PRESERVE_RECENT,
    }

    instructions = [item for item in next_config.get("instructions", []) if isinstance(item, str)]
    if dotfiles_agents_path() not in instructions:
        instructions.append(dotfiles_agents_path())
    next_config["instructions"] = instructions

    skills = next_config.get("skills") if isinstance(next_config.get("skills"), dict) else {}
    paths = [item for item in skills.get("paths", []) if isinstance(item, str)]
    if dotfiles_skills_path() not in paths:
        paths.append(dotfiles_skills_path())
    next_config["skills"] = {**skills, "paths": paths}

    plugins = [item for item in next_config.get("plugin", []) if isinstance(item, (str, list))]
    if kilo_plugin_path() not in plugins:
        plugins.append(kilo_plugin_path())
    next_config["plugin"] = plugins

    provider = next_config.get("provider") if isinstance(next_config.get("provider"), dict) else {}
    provider["cliproxy"] = build_cliproxy_provider()
    next_config["provider"] = provider

    permission = next_config.get("permission") if isinstance(next_config.get("permission"), dict) else {}
    dotfiles_glob = f"{runtime_root().as_posix()}/*"
    read_permission = permission.get("read") if isinstance(permission.get("read"), dict) else {}
    external_directory = (
        permission.get("external_directory") if isinstance(permission.get("external_directory"), dict) else {}
    )
    read_permission[dotfiles_glob] = "allow"
    external_directory[dotfiles_glob] = "allow"
    for directory_glob in OPEN_EXTERNAL_DIRECTORIES:
        external_directory[directory_glob] = "allow"
    next_config["permission"] = {
        **permission,
        "read": read_permission,
        "external_directory": external_directory,
    }
    return next_config


def opencode_package_json(current: dict[str, Any]) -> dict[str, Any]:
    next_package = dict(current)
    dependencies = next_package.get("dependencies") if isinstance(next_package.get("dependencies"), dict) else {}
    dependencies.setdefault("@opencode-ai/plugin", "1.15.10")
    dependencies["@ai-sdk/openai-compatible"] = "^1.0.22"
    next_package["dependencies"] = dependencies
    return next_package


def kilo_package_json(current: dict[str, Any]) -> dict[str, Any]:
    next_package = dict(current)
    dependencies = next_package.get("dependencies") if isinstance(next_package.get("dependencies"), dict) else {}
    dependencies.setdefault("@kilocode/plugin", "7.3.1")
    dependencies["@ai-sdk/openai-compatible"] = "^1.0.22"
    next_package["dependencies"] = dependencies
    return next_package


def strip_aider_block(content: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(AIDER_HOOKS_BEGIN)}.*?{re.escape(AIDER_HOOKS_END)}\n?",
        re.S,
    )
    return pattern.sub("\n", content).strip() + ("\n" if content.strip() else "")


def desired_aider_block() -> str:
    agents_path = dotfiles_agents_path()
    return "\n".join(
        [
            AIDER_HOOKS_BEGIN,
            "model: gpt-5.5",
            "reasoning-effort: low",
            "check-model-accepts-settings: false",
            f"openai-api-base: {CLIPROXY_BASE_URL}",
            f"openai-api-key: {cliproxy_api_key()}",
            "read:",
            f"  - {agents_path}",
            "auto-commits: false",
            "dirty-commits: false",
            "attribute-author: false",
            "attribute-committer: false",
            "analytics-disable: true",
            AIDER_HOOKS_END,
            "",
        ]
    )


def desired_aider_config(current: str) -> str:
    base = strip_aider_block(current).rstrip()
    block = desired_aider_block()
    return (base + "\n\n" if base else "") + block


def agent_asset_links() -> list[tuple[Path, Path]]:
    agents = Path(dotfiles_agents_path())
    skills = Path(dotfiles_skills_path())
    commands = Path(dotfiles_commands_path())
    opencode_dir = default_opencode_config_dir()
    kilo_dir = default_kilo_config_dir()
    return [
        (home_path() / ".claude" / "commands", commands),
        (home_path() / ".claude" / "skills", skills),
        (home_path() / ".codex" / "AGENTS.md", agents),
        (home_path() / ".codex" / "prompts", commands),
        (home_path() / ".codex" / "skills", skills),
        (home_path() / ".factory" / "AGENTS.md", agents),
        (home_path() / ".factory" / "commands", commands),
        (home_path() / ".factory" / "skills", skills),
        (opencode_dir / "AGENTS.md", agents),
        (opencode_dir / "commands", commands),
        (opencode_dir / "skills", skills),
        (kilo_dir / "AGENTS.md", agents),
        (kilo_dir / "commands", commands),
        (kilo_dir / "skills", skills),
    ]


def link_status(link: Path, target: Path) -> str:
    if link.is_symlink():
        try:
            if link.resolve() == target.resolve():
                return "ok"
        except FileNotFoundError:
            return "mismatch"
        return "mismatch"
    if link.exists():
        return "blocked"
    return "missing"


def apply_agent_asset_link(link: Path, target: Path) -> str:
    status = link_status(link, target)
    if status == "ok":
        return f"ok: {link} -> {target}"
    if status == "blocked":
        raise RuntimeError(f"blocked: {link} exists and is not a symlink")
    link.parent.mkdir(parents=True, exist_ok=True)
    if status == "mismatch":
        link.unlink()
    link.symlink_to(target, target_is_directory=target.is_dir())
    return f"linked: {link} -> {target}"


def agent_assets_check() -> int:
    failures = 0
    for link, target in agent_asset_links():
        status = link_status(link, target)
        sys.stdout.write(f"{status}: {link} -> {target}\n")
        if status != "ok":
            failures += 1
    return 1 if failures else 0


def agent_assets_print() -> int:
    for link, target in agent_asset_links():
        sys.stdout.write(f"{link} -> {target}\n")
    return 0


def agent_assets_apply() -> int:
    try:
        for link, target in agent_asset_links():
            sys.stdout.write(apply_agent_asset_link(link, target) + "\n")
    except RuntimeError as error:
        sys.stdout.write(str(error) + "\n")
        return 1
    return 0


def droid_check(project_dir: Path) -> int:
    path = settings_path(project_dir)
    current = load_settings(path)
    if current.get("hooks") == desired_droid_hooks():
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


def droid_models_check(path: Path) -> int:
    current = load_settings(path)
    if current == desired_droid_model_settings(current):
        sys.stdout.write(f"ok: {path} uses 600K compaction configuration\n")
        return 0
    sys.stdout.write(f"mismatch: {path} does not match 600K compaction configuration\n")
    return 1


def droid_models_print(path: Path) -> int:
    sys.stdout.write(render_json(desired_droid_model_settings(load_settings(path))))
    return 0


def droid_models_apply(path: Path) -> int:
    current = load_settings(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(desired_droid_model_settings(current)), encoding="utf-8")
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


def opencode_check(config_dir: Path) -> int:
    path = opencode_config_path(config_dir)
    current = load_settings(path)
    if current == desired_opencode_config(current):
        sys.stdout.write(f"ok: {path} uses dotfiles model/context configuration\n")
        return 0
    sys.stdout.write(f"mismatch: {path} does not match dotfiles model/context configuration\n")
    return 1


def opencode_print(config_dir: Path) -> int:
    sys.stdout.write(render_json(desired_opencode_config(load_settings(opencode_config_path(config_dir)))))
    return 0


def opencode_apply(config_dir: Path) -> int:
    path = opencode_config_path(config_dir)
    current = load_settings(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(desired_opencode_config(current)), encoding="utf-8")
    package_path = config_dir / "package.json"
    package_path.write_text(render_json(opencode_package_json(load_settings(package_path))), encoding="utf-8")
    sys.stdout.write(f"updated: {path}\n")
    return 0


def kilo_check(config_dir: Path) -> int:
    path = kilo_config_path(config_dir)
    current = load_jsonc_settings(path)
    if current == desired_kilo_config(current):
        sys.stdout.write(f"ok: {path} uses dotfiles model/context configuration\n")
        return 0
    sys.stdout.write(f"mismatch: {path} does not match dotfiles model/context configuration\n")
    return 1


def kilo_print(config_dir: Path) -> int:
    path = kilo_config_path(config_dir)
    sys.stdout.write(render_json(desired_kilo_config(load_jsonc_settings(path))))
    return 0


def kilo_apply(config_dir: Path) -> int:
    path = kilo_config_path(config_dir)
    current = load_jsonc_settings(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(desired_kilo_config(current)), encoding="utf-8")
    package_path = config_dir / "package.json"
    package_path.write_text(render_json(kilo_package_json(load_settings(package_path))), encoding="utf-8")
    sys.stdout.write(f"updated: {path}\n")
    return 0


def aider_check(config_path: Path) -> int:
    path = aider_config_path(config_path)
    current = load_text(path)
    if current == desired_aider_config(current):
        sys.stdout.write(f"ok: {path} uses dotfiles model/context configuration\n")
        return 0
    sys.stdout.write(f"mismatch: {path} does not match dotfiles model/context configuration\n")
    return 1


def aider_print(config_path: Path) -> int:
    sys.stdout.write(desired_aider_config(load_text(aider_config_path(config_path))))
    return 0


def aider_apply(config_path: Path) -> int:
    path = aider_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desired_aider_config(load_text(path)), encoding="utf-8")
    sys.stdout.write(f"updated: {path}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check, print, or apply hook adapter configuration.")
    parser.add_argument(
        "--target",
        choices=["droid", "droid-models", "claude", "codex", "opencode", "kilo", "aider", "agent-assets"],
        required=True,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--print", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm --apply writes project hook configuration.")
    parser.add_argument("--project-dir", default=".", help="Project directory, defaults to current working directory.")
    parser.add_argument("--settings-path", type=Path, default=user_settings_path(), help="Droid user settings file path.")
    parser.add_argument("--config-dir", type=Path, default=None, help="OpenCode or Kilo config directory.")
    parser.add_argument("--config-path", type=Path, default=default_aider_config_path(), help="Aider config file path.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if args.apply and not args.yes:
        sys.stdout.write("refusing: --apply requires --yes confirmation\n")
        return 1

    if args.target == "agent-assets":
        if args.check:
            return agent_assets_check()
        if args.print:
            return agent_assets_print()
        return agent_assets_apply()

    if args.target == "droid":
        if args.check:
            return droid_check(project_dir)
        if args.print:
            return droid_print(project_dir)
        return droid_apply(project_dir)

    if args.target == "droid-models":
        path = args.settings_path.expanduser().resolve()
        if args.check:
            return droid_models_check(path)
        if args.print:
            return droid_models_print(path)
        return droid_models_apply(path)

    if args.target == "claude":
        if args.check:
            return claude_check(project_dir)
        if args.print:
            return claude_print(project_dir)
        return claude_apply(project_dir)

    if args.target == "opencode":
        config_dir = (args.config_dir or default_opencode_config_dir()).expanduser().resolve()
        if args.check:
            return opencode_check(config_dir)
        if args.print:
            return opencode_print(config_dir)
        return opencode_apply(config_dir)

    if args.target == "kilo":
        config_dir = (args.config_dir or default_kilo_config_dir()).expanduser().resolve()
        if args.check:
            return kilo_check(config_dir)
        if args.print:
            return kilo_print(config_dir)
        return kilo_apply(config_dir)

    if args.target == "aider":
        config_path = args.config_path.expanduser().resolve()
        if args.check:
            return aider_check(config_path)
        if args.print:
            return aider_print(config_path)
        return aider_apply(config_path)

    if args.check:
        return codex_check(project_dir)
    if args.print:
        return codex_print(project_dir)
    return codex_apply(project_dir)


if __name__ == "__main__":
    raise SystemExit(main())

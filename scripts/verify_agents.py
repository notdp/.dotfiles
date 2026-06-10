#!/usr/bin/env python3
"""verify_agents.py — coding-agents/ subagent 定义的机器门禁。

目录布局（来源：docs/specs/coding-agents-fp-judge.md + 2026-06-10 kilo/opencode 适配）：
- coding-agents/claude/    → ~/.claude/agents（Claude Code 格式：tools 白名单 + model alias）
- coding-agents/opencode/  → ~/.config/opencode/agents 与 ~/.config/kilo/agents
  （OpenCode/Kilo 同构格式：mode + permission 三态收权；tools 字段已弃用禁用）

通用校验：文件名 kebab-case、description 触发语义、机器路径扫描、body 行数 warn。
Claude 规则：name/description/tools/model 必填；model ∈ alias 集；tools ⊆ 内置∪mcp__*；
            只读角色（*-judge/-reviewer/-auditor）禁写禁执行。
OpenCode 规则：description/mode 必填；mode ∈ {subagent,primary,all}；禁用已弃用 tools 字段；
            禁用 name 字段（文件名即名字）；model 如存在必须 provider/model-id 形式；
            只读角色必须 permission.edit=deny 且 permission.bash=deny
            （运行时强制已实测：bash deny → "bash tool is not available"，2026-06-10）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_CLAUDE_MODELS = {"opus", "sonnet", "haiku", "fable", "inherit"}
# 官方内置工具名（来源：code.claude.com/docs/en/tools-reference，2026-06 快照）
CLAUDE_BUILTIN_TOOLS = {
    "Agent", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList",
    "Edit", "EnterPlanMode", "EnterWorktree", "ExitPlanMode", "ExitWorktree",
    "Glob", "Grep", "LSP", "ListMcpResourcesTool", "Monitor", "NotebookEdit",
    "PowerShell", "PushNotification", "Read", "ReadMcpResourceTool",
    "RemoteTrigger", "ScheduleWakeup", "SendMessage", "ShareOnboardingGuide",
    "Skill", "TaskCreate", "TaskGet", "TaskList", "TaskStop", "TaskUpdate",
    "TodoWrite", "ToolSearch", "WaitForMcpServers", "WebFetch", "WebSearch",
    "Workflow", "Write",
}
MCP_TOOL_PATTERN = re.compile(r"mcp__[\w-]+(?:__[\w-]+)?")
# 写 / 执行类工具：只读角色（judge/reviewer/auditor）禁用
CLAUDE_MUTATING_TOOLS = {"Write", "Edit", "Bash", "NotebookEdit", "PowerShell"}
READ_ONLY_ROLE_SUFFIXES = ("-judge", "-reviewer", "-auditor")
OPENCODE_MODES = {"subagent", "primary", "all"}
OPENCODE_PERMISSION_ACTIONS = {"allow", "ask", "deny"}
OPENCODE_MODEL_PATTERN = re.compile(r"\S+/\S+")
NAME_CASE_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TRIGGER_PREFIXES = ("Use when ", "Invoke when ", "用于", "当")
MACHINE_PATH_PATTERN = re.compile(r"/(?:Users|home)/[A-Za-z0-9][\w.-]*/")
BODY_LENGTH_WARN_THRESHOLD = 200


class ValidationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def parse_frontmatter(agent_file: Path) -> tuple[dict[str, object], list[str]]:
    """解析 frontmatter：支持 key: value 与一层嵌套 map（如 permission 块）。"""
    lines = agent_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        fail(f"INVALID FRONTMATTER: {agent_file} 必须以 --- 开头")
    try:
        end_index = lines.index("---", 1)
    except ValueError:
        fail(f"INVALID FRONTMATTER: {agent_file} 缺少结束 ---")

    frontmatter: dict[str, object] = {}
    current_map: dict[str, str] | None = None
    for raw in lines[1:end_index]:
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            if current_map is None:
                fail(f"INVALID FRONTMATTER LINE: {agent_file}: {raw!r}（缩进行必须属于某个嵌套 map）")
            key, _, value = raw.strip().partition(":")
            if not _:
                fail(f"INVALID FRONTMATTER LINE: {agent_file}: {raw!r}")
            current_map[key.strip()] = value.strip()
            continue
        if ":" not in raw:
            fail(f"INVALID FRONTMATTER LINE: {agent_file}: {raw!r}（只支持 key: value）")
        key, value = raw.split(":", 1)
        key, value = key.strip(), value.strip()
        if value:
            frontmatter[key] = value
            current_map = None
        else:
            current_map = {}
            frontmatter[key] = current_map
    return frontmatter, lines[end_index + 1 :]


def validate_common(agent_file: Path, frontmatter: dict[str, object], body_lines: list[str]) -> list[str]:
    warnings: list[str] = []
    if not NAME_CASE_PATTERN.fullmatch(agent_file.stem):
        fail(f"NAME CASE: {agent_file.name} 文件名必须是 kebab-case")

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description:
        fail(f"MISSING FIELD: {agent_file.name} 缺少必填字段 description")
    if not any(prefix in description[:24] for prefix in TRIGGER_PREFIXES):
        fail(
            f"TRIGGER SEMANTICS: {agent_file.stem} description 必须以触发语义开头"
            f"（{' / '.join(TRIGGER_PREFIXES)}），让主 agent 知道何时委派"
        )

    body_text = "\n".join(body_lines)
    machine_path = MACHINE_PATH_PATTERN.search(body_text)
    if machine_path:
        fail(f"MACHINE PATH: {agent_file.stem} body 含机器特定路径 {machine_path.group(0)!r}，用 ~ 或相对路径")
    if len(body_lines) > BODY_LENGTH_WARN_THRESHOLD:
        warnings.append(
            f"WARN BODY LENGTH: {agent_file.stem} body {len(body_lines)} 行 > {BODY_LENGTH_WARN_THRESHOLD}，"
            f"考虑下沉细节"
        )
    return warnings


def validate_claude_agent(agent_file: Path) -> list[str]:
    frontmatter, body_lines = parse_frontmatter(agent_file)
    warnings = validate_common(agent_file, frontmatter, body_lines)

    for field in ("name", "tools", "model"):
        if not frontmatter.get(field):
            fail(f"MISSING FIELD: claude/{agent_file.name} 缺少必填字段 {field}（model 必须显式声明，不靠默认 inherit）")

    name = frontmatter["name"]
    if name != agent_file.stem:
        fail(f"NAME MISMATCH: claude/{agent_file.name} frontmatter name={name!r} 必须与文件名一致")

    model = frontmatter["model"]
    if model not in ALLOWED_CLAUDE_MODELS:
        fail(f"INVALID MODEL: claude/{name} model={model!r} 必须 ∈ {sorted(ALLOWED_CLAUDE_MODELS)}")

    raw_tools = frontmatter["tools"]
    if not isinstance(raw_tools, str):
        fail(f"INVALID TOOLS: claude/{name} tools 必须是逗号分隔字符串")
    tools = [item.strip() for item in raw_tools.split(",") if item.strip()]
    if not tools:
        fail(f"EMPTY TOOLS: claude/{name} tools 必须显式列出（省略=继承全部，本仓库禁止）")
    for tool in tools:
        if tool in CLAUDE_BUILTIN_TOOLS or MCP_TOOL_PATTERN.fullmatch(tool):
            continue
        fail(
            f"UNKNOWN TOOL: claude/{name} tools 含 {tool!r}；"
            f"必须是内置工具名或 mcp__server__tool 形式（禁止裸 MCP 名 / agent 名 / skill 名）"
        )

    if agent_file.stem.endswith(READ_ONLY_ROLE_SUFFIXES):
        forbidden = sorted(set(tools) & CLAUDE_MUTATING_TOOLS)
        if forbidden:
            fail(
                f"ROLE CAP: claude/{name} 是只读角色（{'/'.join(READ_ONLY_ROLE_SUFFIXES)} 后缀），禁用 {forbidden}"
            )
    return warnings


def validate_opencode_agent(agent_file: Path) -> list[str]:
    frontmatter, body_lines = parse_frontmatter(agent_file)
    warnings = validate_common(agent_file, frontmatter, body_lines)
    stem = agent_file.stem

    if "name" in frontmatter:
        fail(f"FORBIDDEN FIELD: opencode/{agent_file.name} 不写 name 字段（OpenCode/Kilo 以文件名为名）")
    if "tools" in frontmatter:
        fail(f"DEPRECATED FIELD: opencode/{stem} tools 字段已弃用，用 permission 三态收权")

    mode = frontmatter.get("mode")
    if mode not in OPENCODE_MODES:
        fail(f"INVALID MODE: opencode/{stem} mode={mode!r} 必填且 ∈ {sorted(OPENCODE_MODES)}")

    model = frontmatter.get("model")
    if model is not None:
        if not isinstance(model, str) or not OPENCODE_MODEL_PATTERN.fullmatch(model):
            fail(f"INVALID MODEL: opencode/{stem} model={model!r} 必须是 provider/model-id 形式（或省略=继承默认）")

    permission = frontmatter.get("permission")
    if permission is not None:
        if not isinstance(permission, dict):
            fail(f"INVALID PERMISSION: opencode/{stem} permission 必须是嵌套 map")
        for key, action in permission.items():
            if action not in OPENCODE_PERMISSION_ACTIONS:
                fail(
                    f"INVALID PERMISSION: opencode/{stem} permission.{key}={action!r} 必须 ∈ "
                    f"{sorted(OPENCODE_PERMISSION_ACTIONS)}"
                )

    if stem.endswith(READ_ONLY_ROLE_SUFFIXES):
        perm = permission if isinstance(permission, dict) else {}
        missing = [key for key in ("edit", "bash") if perm.get(key) != "deny"]
        if missing:
            fail(
                f"ROLE CAP: opencode/{stem} 是只读角色（{'/'.join(READ_ONLY_ROLE_SUFFIXES)} 后缀），"
                f"必须 permission 中 {missing} 均为 deny"
            )
    return warnings


RUNTIME_VALIDATORS = {
    "claude": validate_claude_agent,
    "opencode": validate_opencode_agent,
}


def run(repo_root: Path) -> int:
    agents_root = repo_root / "coding-agents"
    if not agents_root.is_dir():
        print(f"MISSING DIR: {agents_root}", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    total = 0
    for entry in sorted(agents_root.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_file() and entry.suffix == ".md" and entry.name != "README.md":
            errors.append(f"MISPLACED FILE: {entry.name} 必须放在 runtime 子目录（{'/'.join(sorted(RUNTIME_VALIDATORS))}）下")
            continue
        if not entry.is_dir():
            continue
        validator = RUNTIME_VALIDATORS.get(entry.name)
        if validator is None:
            errors.append(f"UNKNOWN RUNTIME DIR: coding-agents/{entry.name}（已知: {sorted(RUNTIME_VALIDATORS)}）")
            continue
        for agent_file in sorted(entry.rglob("*.md")):
            if agent_file.name == "README.md":
                continue
            total += 1
            try:
                warnings.extend(validator(agent_file))
            except ValidationError as exc:
                errors.append(str(exc))

    if total == 0 and not errors:
        print(f"EMPTY DIR: {agents_root} 没有任何 subagent 定义", file=sys.stderr)
        return 1

    for warning in warnings:
        print(warning, file=sys.stderr)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"verify_agents: {total} 个 agent，{len(errors)} 个错误", file=sys.stderr)
        return 1
    print(f"verify_agents: {total} 个 agent 全部通过（warn {len(warnings)}）")
    return 0


def main() -> int:
    repo_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    return run(repo_root)


if __name__ == "__main__":
    sys.exit(main())

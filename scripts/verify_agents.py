#!/usr/bin/env python3
"""verify_agents.py — coding-agents/ subagent 定义的机器门禁。

校验项（来源：docs/specs/coding-agents-fp-judge.md）：
1. frontmatter 必填字段：name / description / tools / model
2. name 必须 kebab-case 且与文件名一致
3. description 必须含触发语义前缀（与 verify_skills.py 同款）
4. model ∈ 官方 alias 集合（含 inherit；显式声明模型预算，不靠默认值）
5. tools 必须 ⊆ 内置工具白名单 ∪ mcp__* 前缀（杜绝裸 MCP 名 / agent 名混入）
6. 角色权限上限：*-judge / *-reviewer / *-auditor 禁写禁执行
7. body 不得含机器特定绝对路径；行数超阈值仅 warn
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_MODELS = {"opus", "sonnet", "haiku", "fable", "inherit"}
# 官方内置工具名（来源：code.claude.com/docs/en/tools-reference，2026-06 快照）
BUILTIN_TOOLS = {
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
MUTATING_TOOLS = {"Write", "Edit", "Bash", "NotebookEdit", "PowerShell"}
READ_ONLY_ROLE_SUFFIXES = ("-judge", "-reviewer", "-auditor")
NAME_CASE_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TRIGGER_PREFIXES = ("Use when ", "Invoke when ", "用于", "当")
MACHINE_PATH_PATTERN = re.compile(r"/(?:Users|home)/[A-Za-z0-9][\w.-]*/")
BODY_LENGTH_WARN_THRESHOLD = 200
REQUIRED_FIELDS = ("name", "description", "tools", "model")


class ValidationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def parse_frontmatter(agent_file: Path) -> tuple[dict[str, str], list[str]]:
    lines = agent_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        fail(f"INVALID FRONTMATTER: {agent_file} 必须以 --- 开头")
    try:
        end_index = lines.index("---", 1)
    except ValueError:
        fail(f"INVALID FRONTMATTER: {agent_file} 缺少结束 ---")
    frontmatter: dict[str, str] = {}
    for raw in lines[1:end_index]:
        if not raw.strip():
            continue
        if ":" not in raw:
            fail(f"INVALID FRONTMATTER LINE: {agent_file}: {raw!r}（只支持 key: value，tools 用逗号分隔字符串）")
        key, value = raw.split(":", 1)
        frontmatter[key.strip()] = value.strip()
    return frontmatter, lines[end_index + 1 :]


def validate_agent(agent_file: Path) -> list[str]:
    warnings: list[str] = []
    frontmatter, body_lines = parse_frontmatter(agent_file)

    for field in REQUIRED_FIELDS:
        if not frontmatter.get(field):
            fail(f"MISSING FIELD: {agent_file.name} 缺少必填字段 {field}（model 必须显式声明，不靠默认 inherit）")

    name = frontmatter["name"]
    if not NAME_CASE_PATTERN.fullmatch(name):
        fail(f"NAME CASE: {agent_file.name} name={name!r} 必须是 kebab-case")
    if name != agent_file.stem:
        fail(f"NAME MISMATCH: {agent_file.name} frontmatter name={name!r} 必须与文件名一致")

    description = frontmatter["description"]
    if not any(prefix in description[:24] for prefix in TRIGGER_PREFIXES):
        fail(
            f"TRIGGER SEMANTICS: {name} description 必须以触发语义开头"
            f"（{' / '.join(TRIGGER_PREFIXES)}），让主 agent 知道何时委派"
        )

    model = frontmatter["model"]
    if model not in ALLOWED_MODELS:
        fail(f"INVALID MODEL: {name} model={model!r} 必须 ∈ {sorted(ALLOWED_MODELS)}")

    tools = [item.strip() for item in frontmatter["tools"].split(",") if item.strip()]
    if not tools:
        fail(f"EMPTY TOOLS: {name} tools 必须显式列出（省略=继承全部，本仓库禁止）")
    for tool in tools:
        if tool in BUILTIN_TOOLS:
            continue
        if MCP_TOOL_PATTERN.fullmatch(tool):
            continue
        fail(
            f"UNKNOWN TOOL: {name} tools 含 {tool!r}；"
            f"必须是内置工具名或 mcp__server__tool 形式（禁止裸 MCP 名 / agent 名 / skill 名）"
        )

    if name.endswith(READ_ONLY_ROLE_SUFFIXES):
        forbidden = sorted(set(tools) & MUTATING_TOOLS)
        if forbidden:
            fail(
                f"ROLE CAP: {name} 是只读角色（{'/'.join(READ_ONLY_ROLE_SUFFIXES)} 后缀），"
                f"禁用 {forbidden}"
            )

    body_text = "\n".join(body_lines)
    machine_path = MACHINE_PATH_PATTERN.search(body_text)
    if machine_path:
        fail(f"MACHINE PATH: {name} body 含机器特定路径 {machine_path.group(0)!r}，用 ~ 或相对路径")

    if len(body_lines) > BODY_LENGTH_WARN_THRESHOLD:
        warnings.append(
            f"WARN BODY LENGTH: {name} body {len(body_lines)} 行 > {BODY_LENGTH_WARN_THRESHOLD}，"
            f"考虑下沉细节（上游 154 个 agent 均值 246 行是反面教材）"
        )
    return warnings


def run(repo_root: Path) -> int:
    agents_root = repo_root / "coding-agents"
    if not agents_root.is_dir():
        print(f"MISSING DIR: {agents_root}", file=sys.stderr)
        return 1

    agent_files = sorted(p for p in agents_root.rglob("*.md") if p.name != "README.md")
    if not agent_files:
        print(f"EMPTY DIR: {agents_root} 没有任何 subagent 定义", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    seen_names: set[str] = set()
    for agent_file in agent_files:
        try:
            warnings.extend(validate_agent(agent_file))
            stem = agent_file.stem
            if stem in seen_names:
                errors.append(f"DUPLICATE NAME: {stem}")
            seen_names.add(stem)
        except ValidationError as exc:
            errors.append(str(exc))

    for warning in warnings:
        print(warning, file=sys.stderr)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"verify_agents: {len(agent_files)} 个 agent，{len(errors)} 个错误", file=sys.stderr)
        return 1
    print(f"verify_agents: {len(agent_files)} 个 agent 全部通过（warn {len(warnings)}）")
    return 0


def main() -> int:
    repo_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    return run(repo_root)


if __name__ == "__main__":
    sys.exit(main())

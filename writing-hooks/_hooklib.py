"""writing-hooks 共享库：解析 Claude Code hook stdin、抽取写作产物内容、统一输出。

每个 hook 支持两种调用：
1. Hook 模式（无参数）：从 stdin 读 PostToolUse/PreToolUse JSON，抽取 file_path + 内容。
2. CLI 模式（`python3 <hook>.py <file>`）：直接扫描文件，便于测试与手动跑。

退出码约定（对齐 Claude Code hook）：
- 0 = 放行（含"仅告警"——告警走 stdout，不阻断）。
- 2 = 阻断 / 反馈给模型（违反硬条款）。诊断写 stderr。

写作 hook 只在创作项目 .claude/settings.json 注册，不进任何编程 agent 的全局配置。
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

WRITING_SUFFIXES = {".md", ".markdown", ".txt", ".mdx"}
SKIP_PATH_PARTS = {".git", "node_modules", ".venv", "dist", "build"}


@dataclass
class Target:
    path: str
    content: str


def _from_stdin() -> Target | None:
    raw = sys.stdin.read().strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    # Write 用 content；Edit 用 new_string；MultiEdit 取所有 new_string
    content = tool_input.get("content")
    if content is None:
        content = tool_input.get("new_string")
    if content is None and isinstance(tool_input.get("edits"), list):
        content = "\n".join(str(e.get("new_string", "")) for e in tool_input["edits"])
    if content is None:
        # 没有内容（如非写入工具），尝试读磁盘文件
        if path and Path(path).exists():
            content = Path(path).read_text(encoding="utf-8", errors="replace")
        else:
            content = ""
    return Target(path=str(path), content=str(content))


def get_target() -> Target | None:
    """返回待检查目标；CLI 模式读文件，hook 模式读 stdin。无可检查内容返回 None。"""
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if not p.exists():
            return None
        return Target(path=str(p), content=p.read_text(encoding="utf-8", errors="replace"))
    return _from_stdin()


def is_writing_artifact(path: str) -> bool:
    if not path:
        return False
    p = Path(path)
    if any(part in SKIP_PATH_PARTS for part in p.parts):
        return False
    return p.suffix.lower() in WRITING_SUFFIXES


def block(hook: str, findings: list[str]) -> int:
    sys.stderr.write(f"[{hook}] 阻断（违反写作硬约束 _shared/writing-constraints.md）：\n")
    for f in findings:
        sys.stderr.write(f"  - {f}\n")
    return 2


def warn(hook: str, findings: list[str]) -> int:
    sys.stdout.write(f"[{hook}] 告警（建议处理，未阻断）：\n")
    for f in findings:
        sys.stdout.write(f"  - {f}\n")
    return 0


def ok(hook: str) -> int:
    return 0

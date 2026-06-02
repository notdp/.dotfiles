#!/usr/bin/env python3
"""publish_confirm — 覆盖/发布确认门（writing-constraints §7）。

设计为高精度、低打扰：只在**明确的发布信号**下硬拦（exit 2），不拦普通编辑/保存
（避免每次存稿都被阻断）。发布信号（任一）：
  - 目标路径含 publish / 发布 / dist / release 段
  - frontmatter 出现 `publish: true` / `status: publish`

命中即阻断并提示：发布/覆盖原文需用户显式放行（对齐边界审批 + guard-gitops）。

用法：hook 读 stdin（PreToolUse 更合适）；CLI `python3 publish_confirm.py <file>`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hooklib import block, get_target, is_writing_artifact  # noqa: E402

HOOK = "publish_confirm"
PUBLISH_PATH = re.compile(r"(^|/)(publish|发布|dist|release)(/|$)", re.I)
PUBLISH_FLAG = re.compile(r"^\s*(publish:\s*true|status:\s*publish)\s*$", re.I | re.M)


def is_publish(path: str, content: str) -> list[str]:
    signals = []
    if PUBLISH_PATH.search(path):
        signals.append(f"目标路径含发布目录段：{path}")
    if PUBLISH_FLAG.search(content):
        signals.append("frontmatter 标记 publish: true / status: publish")
    return signals


def main() -> int:
    target = get_target()
    if target is None or not is_writing_artifact(target.path):
        return 0
    signals = is_publish(target.path, target.content)
    if signals:
        return block(HOOK, signals + ["发布/覆盖对外产物需用户显式放行；确认无误后再放行此动作"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

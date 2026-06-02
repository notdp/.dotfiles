#!/usr/bin/env python3
"""provenance_guard — provenance 泄漏门（writing-constraints §7）。

硬拦（exit 2，高精度）：
  - 作者本机绝对路径（/Users/<name>/、/home/<name>/、C:\\Users\\<name>）误入产物

告警（不阻断，低精度）：
  - 疑似内部元信息：赞助/sponsored 披露、内部 slug/session id 行

用法：hook 读 stdin；CLI `python3 provenance_guard.py <file>`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hooklib import block, get_target, is_writing_artifact, warn  # noqa: E402

HOOK = "provenance_guard"
MACHINE_PATH = re.compile(r"(/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[Cc]:\\Users\\[A-Za-z0-9._-]+)")
# 匿名占位不算泄漏（/Users/.../ 这种）
ANON = re.compile(r"/Users/\.\.\.|/home/\.\.\.")
SOFT_MARKERS = (re.compile(r"赞助|sponsored", re.I), re.compile(r"\bsession[_-]?id\b|内部 slug", re.I))


def scan(content: str) -> tuple[list[str], list[str]]:
    hard, soft = [], []
    for i, line in enumerate(content.splitlines(), 1):
        for m in MACHINE_PATH.finditer(line):
            seg = m.group(0)
            if ANON.search(line):
                continue
            hard.append(f"L{i}: 本机绝对路径泄漏「{seg}」，发布前应移除或匿名化")
        for rx in SOFT_MARKERS:
            if rx.search(line):
                soft.append(f"L{i}: 疑似内部元信息（赞助/会话 id 等），确认是否应进产物")
                break
    return hard, soft


def main() -> int:
    target = get_target()
    if target is None or not is_writing_artifact(target.path):
        return 0
    hard, soft = scan(target.content)
    if soft:
        warn(HOOK, soft[:20])
    if hard:
        return block(HOOK, hard[:40])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

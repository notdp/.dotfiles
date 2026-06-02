#!/usr/bin/env python3
"""length_budget — 篇幅/结构预算门（writing-constraints §5）。

硬拦（exit 2）：
  - 单段落超过 ~400 中文字（应拆段）
  - 标题层级跳级（如 # 直接到 ###）

代码块（``` 围栏）内不计。用法：hook 读 stdin；CLI `python3 length_budget.py <file>`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hooklib import block, get_target, is_writing_artifact  # noqa: E402

HOOK = "length_budget"
MAX_PARA_CJK = 400
HEADING = re.compile(r"^(#{1,6})\s+\S")
CJK = re.compile(r"[一-鿿]")


def scan(content: str) -> list[str]:
    findings: list[str] = []
    lines = content.splitlines()

    in_fence = False
    prev_level = 0
    para_chars = 0
    para_start = 0
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            para_chars = 0
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            level = len(m.group(1))
            if prev_level and level > prev_level + 1:
                findings.append(f"L{i}: 标题层级跳级（H{prev_level}→H{level}），不要跳级")
            prev_level = level
            para_chars = 0
            continue
        if not line.strip():
            para_chars = 0
            para_start = 0
            continue
        if para_chars == 0:
            para_start = i
        para_chars += len(CJK.findall(line))
        if para_chars > MAX_PARA_CJK and para_chars - len(CJK.findall(line)) <= MAX_PARA_CJK:
            findings.append(f"L{para_start}: 单段落超过 {MAX_PARA_CJK} 中文字（已 {para_chars}+），应拆段（每段一论点）")
    return findings


def main() -> int:
    target = get_target()
    if target is None or not is_writing_artifact(target.path):
        return 0
    findings = scan(target.content)
    if findings:
        return block(HOOK, findings[:40])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

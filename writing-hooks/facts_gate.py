#!/usr/bin/env python3
"""facts_gate — 事实/引用校验门（writing-constraints §3）。

仅告警（始终 exit 0）：检查事实/引用类产物的标注与引用完整性。
启发式（无法替代人工核验事实真伪），故只 warn：
  - 出现数据/统计/百分比但无引用列表 → 提醒补来源
  - 出现 研究表明/专家认为/数据显示 等归因但无来源 → 提醒
  - 报告 [推断]/[未验证] 标注计数，供作者自查是否齐全

用法：hook 读 stdin；CLI `python3 facts_gate.py <file>`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hooklib import get_target, is_writing_artifact, warn  # noqa: E402

HOOK = "facts_gate"
ATTRIB = re.compile(r"(研究表明|专家认为|数据显示|有研究|据统计|调查显示)")
STAT = re.compile(r"\d+(\.\d+)?\s*%|\b\d{3,}\b")
CITATION_HINT = re.compile(r"参考|引用|来源|references?|\[\d+\]|https?://", re.I)


def scan(content: str) -> list[str]:
    notes: list[str] = []
    has_citation = bool(CITATION_HINT.search(content))
    attrib_hits = len(ATTRIB.findall(content))
    stat_hits = len(STAT.findall(content))
    inferred = content.count("[推断]") + content.count("[未验证]") + content.count("[猜测]")

    if attrib_hits and not has_citation:
        notes.append(f"出现 {attrib_hits} 处归因措辞（研究表明/专家认为等）但无来源/引用，补来源或标 [未验证]")
    if stat_hits >= 2 and not has_citation:
        notes.append(f"出现 {stat_hits} 处数据/百分比但无引用列表，补来源或标 [未验证]")
    notes.append(f"标注计数：[推断]/[未验证]/[猜测] 共 {inferred} 处（自查是否覆盖了所有未证实断言）")
    return notes


def main() -> int:
    target = get_target()
    if target is None or not is_writing_artifact(target.path):
        return 0
    warn(HOOK, scan(target.content))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

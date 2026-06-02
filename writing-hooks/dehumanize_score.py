#!/usr/bin/env python3
"""dehumanize_score — 去 AI 味评分门（writing-constraints §2、§4）。

仅告警（始终 exit 0）：对成稿做编号模式扫描 + 粗评分，低于阈值给提醒。
自评不替代人工 acceptance（对齐 AGENTS：inner-loop verifier ≠ 验收）。

用法：hook 读 stdin；CLI `python3 dehumanize_score.py <file>`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hooklib import get_target, is_writing_artifact, warn  # noqa: E402

HOOK = "dehumanize_score"
THRESHOLD = 70  # 满分 100，低于此给提醒

CLICHE = ("总而言之", "综上所述", "值得注意的是", "赋能", "抓手", "闭环", "深入探讨", "保驾护航", "不仅仅是", "更是一种")
FILLER = ("某种程度上", "在一定意义上", "众所周知", "不言而喻")
TRIAD = re.compile(r"(首先|第一)[，,].*(其次|第二)[，,].*(最后|第三)")


def score(content: str) -> tuple[int, list[str]]:
    notes: list[str] = []
    penalty = 0
    text = content
    cliche_hits = sum(text.count(w) for w in CLICHE)
    filler_hits = sum(text.count(w) for w in FILLER)
    em = len(re.findall(r"—{1,2}", text))
    triad = 1 if TRIAD.search(text) else 0
    if cliche_hits:
        penalty += min(cliche_hits * 6, 40); notes.append(f"AI 套话 {cliche_hits} 处")
    if filler_hits:
        penalty += min(filler_hits * 5, 20); notes.append(f"填充短语 {filler_hits} 处")
    if em:
        penalty += min(em * 4, 16); notes.append(f"em dash {em} 处")
    if triad:
        penalty += 10; notes.append("首先/其次/最后 三段套")
    # 节奏：句长方差太小（机器稿迹象）
    sentences = re.split(r"[。！？\n]", text)
    lens = [len(s) for s in sentences if s.strip()]
    if len(lens) >= 6:
        avg = sum(lens) / len(lens)
        var = sum((x - avg) ** 2 for x in lens) / len(lens)
        if var < 60:
            penalty += 8; notes.append("句长过于均匀（缺节奏变化）")
    return max(0, 100 - penalty), notes


def main() -> int:
    target = get_target()
    if target is None or not is_writing_artifact(target.path):
        return 0
    s, notes = score(target.content)
    if s < THRESHOLD:
        warn(HOOK, [f"去 AI 味评分 {s}/100（阈值 {THRESHOLD}，自评仅供参考，不替代人工）"] + notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

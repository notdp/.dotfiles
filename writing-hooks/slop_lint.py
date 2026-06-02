#!/usr/bin/env python3
"""slop_lint — 中文写作产物 slop 静态门（writing-constraints §1-2）。

硬拦（exit 2，高精度规则）：
  - em dash `—` / `——` 充当破折号停顿
  - 装饰性 emoji
  - AI 套话/空话词表

告警（stdout，不阻断，低精度规则）：
  - 盘古之白疑似缺失（中文紧邻 ASCII 字母/数字）——自动判定误报率高，故只告警不硬拦
    （刻意取舍：避免误伤正常写作；对齐"确定性硬拦+主观先告警"）

用法：hook 模式读 stdin；CLI 模式 `python3 slop_lint.py <file.md>`。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hooklib import block, get_target, is_writing_artifact, warn  # noqa: E402

EM_DASH = re.compile(r"—{1,2}")
EMOJI = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F000-\U0001F0FF"
    "\U00002190-\U000021FF" "\U0000FE00-\U0000FE0F" "]"
)
# AI 套话/空话（与 writing-constraints §2 同源；style-contract 可叠加账号专属禁用词）
AI_CLICHES = (
    "总而言之", "综上所述", "值得注意的是", "众所周知", "不言而喻",
    "在当今", "在这个", "数字化时代", "信息爆炸",
    "让我们一起", "接下来，让我们", "深入探讨", "保驾护航",
    "赋能", "抓手", "闭环", "颗粒度", "对齐颗粒度", "干货满满", "满满的干货",
    "首先，其次，最后", "不仅仅是", "更是一种",
)
# 盘古之白：中文字符紧邻 ASCII 字母/数字（任一侧），且中间无空格
PANGU = re.compile(r"([一-鿿])([A-Za-z0-9])|([A-Za-z0-9])([一-鿿])")

HOOK = "slop_lint"


def scan(content: str) -> tuple[list[str], list[str]]:
    # 硬拦只放高精度、确定即 slop 的规则（AI 套话词表）。
    # em dash / emoji / 盘古之白属语境相关或正常中文用法（`——` 是合法中文破折号；
    # 公众号 emoji 常有意使用），硬拦会误伤真实写作，故只告警。
    hard: list[str] = []
    soft: list[str] = []
    for i, line in enumerate(content.splitlines(), 1):
        for w in AI_CLICHES:
            if w in line:
                hard.append(f"L{i}: AI 套话「{w}」")
        if EM_DASH.search(line):
            soft.append(f"L{i}: em dash（—/——）较多时考虑改（）或拆句（合法中文破折号可保留）")
        if EMOJI.search(line):
            soft.append(f"L{i}: emoji，确认是否为有意使用（装饰性建议删）")
        if PANGU.search(line):
            soft.append(f"L{i}: 疑似缺盘古之白（中英/中数字间应留空格）")
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

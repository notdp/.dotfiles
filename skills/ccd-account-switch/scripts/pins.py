#!/usr/bin/env python3
"""对账 pin：索引里 isStarred 的会话 vs 侧栏自己的 pin 存储，列出侧栏漏掉的。只读。

侧栏（claude.ai 下发的页面）不直接用索引里的 isStarred，而是有自己的 pin 存储：
IndexedDB https_claude.ai 里的 store:pin-state:dframe-starred-code（starredIds）。
切号重启后它会从索引重新收 pin，2026-10-19 实测 27 条只收进 23 条，漏掉的 4 条
索引里 isStarred 仍是 true、能搜到，但不在 Pinned 区。原因不明（不是按时间截断）。

补救：对输出的每条调 mcp__ccd_sidebar__set_pinned(session_id, true)，走 app 自己的
接口写进侧栏存储；别去改 IndexedDB。

    python3 pins.py <accountUuid>/<orgUuid>
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
IDB = os.path.expanduser('~/Library/Application Support/Claude/IndexedDB/https_claude.ai_0.indexeddb.leveldb')
REC = re.compile(rb'\{"state":\{"starredIds":\[(.*?)\]\},"version":\d+,"updatedAt":(\d+)\}')


def sidebar_starred():
    """侧栏 pin 存储最新一版（按 updatedAt、同时间按文件内偏移取最后）。读不到返回 None。"""
    recs = []
    for f in sorted(glob.glob(os.path.join(IDB, '*'))):
        try:
            b = open(f, 'rb').read()
        except OSError:
            continue
        for m in REC.finditer(b):
            recs.append((int(m.group(2)), f, m.start(), m.group(1)))
    if not recs:
        return None
    # 同一时刻有长度为 0 的另一份记录交替出现（猜是别的 scope），取非空里最新的
    full = [r for r in recs if r[3]] or recs
    t, _, _, body = max(full, key=lambda r: (r[0], r[1], r[2]))
    return {x.decode() for x in re.findall(rb'local_[0-9a-f-]{36}', body)}


def main(rel):
    d = os.path.join(ROOT, rel.rstrip('/'))
    star = {}
    for p in glob.glob(os.path.join(d, 'local_*.json')):
        x = json.load(open(p))
        if x.get('isStarred') and not x.get('isArchived'):
            star[x['sessionId']] = x.get('title', '')
    side = sidebar_starred()
    if side is None:
        sys.exit(f'索引里 pinned {len(star)} 条；侧栏 pin 存储读不到（可能已压进 .ldb），在侧栏里人工核对数量。')
    miss = sorted(set(star) - side)
    print(f'索引 pinned {len(star)}  侧栏 pinned {len(side & set(star))}  侧栏漏掉 {len(miss)}')
    for i in miss:
        print(f'  {i}  {star[i][:40]}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

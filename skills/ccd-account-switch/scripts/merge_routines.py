#!/usr/bin/env python3
"""routine 注册表传火：DST 按 SRC 对齐，再掐灭其他所有账号目录里的火把。

调度状态（lastRunAt/lastScheduledFor）按账号隔离，哪个目录的时间戳停在过去，
CCD 在那个账号下醒来就按"错过了排期"补跑——切一次号大概率触发一轮重复执行
（实测 git log 里 08-20 21:21、08-21 19:50 的 daily-skills-update bump 都是
切号补跑出来的第二次）。所以传火对 routine 要做三件事：

  1. DST 已有的条目：配置按 SRC 对齐。SRC 是刚交棒的火种，配置最新——别信
     "DST 是用户当前账号所以更新"，2026-09-01 实测 DST 的 ccd-shortcuts/tokamak
     cron 停在 08-29 之前的旧值，正是靠 SRC 才修回来的。时间戳取两边较晚的，
     避免回拨触发补跑。SRC 独有的照搬，DST 独有的原样保留。
  2. 其他所有账号目录（含 SRC）的条目 enabled=false 并打 snuffedByPassFire
     标记——火把只有一支，只在当前账号烧。
  3. 下次传火见到带标记的条目重新点燃；用户自己关掉的（enabled=false 无标记）
     保持关闭。

掐灭之后切回旧账号 routine 不会自己跑，要跑就再传一次火（或 UI 里手动开）。
绝对不要 cp 整个文件过去：注册表顶层还有 recordedSkips 等账号私有状态。

用法: merge_routines.py <SRC> <DST> [--go]
"""
import glob
import json
import os
import sys

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
TS = ('lastRunAt', 'lastScheduledFor')      # ISO 字符串，字典序即时间序
SNUFF = 'snuffedByPassFire'

reg = lambda p: os.path.join(ROOT, p.rstrip('/'), 'scheduled-tasks.json')


def merged(s, d):
    """单条任务：SRC 配置为准，时间戳取较晚的，带 snuff 标记的重新点燃。"""
    out = {k: v for k, v in s.items() if k != SNUFF}
    for k in TS:
        vals = [v for v in (s.get(k), (d or {}).get(k)) if v]
        if vals:
            out[k] = max(vals)
    if s.get(SNUFF):
        out['enabled'] = True
    return out


def main(src, dst, go):
    tag = '' if go else '[dry] '
    s, d = json.load(open(reg(src))), json.load(open(reg(dst)))
    by_id = {t['id']: t for t in d['scheduledTasks']}
    tasks, changes = [], []
    for st in s['scheduledTasks']:
        dt = by_id.pop(st['id'], None)
        mt = merged(st, dt)
        tasks.append(mt)
        if dt is None:
            changes.append(f"  {st['id']}: 新条目")
        else:
            diff = [f"{k} {dt.get(k)!r} -> {mt[k]!r}" for k in mt if dt.get(k) != mt[k]]
            if diff:
                changes.append(f"  {st['id']}: {'; '.join(diff)}")
    tasks += by_id.values()                  # DST 独有的原样保留
    d['scheduledTasks'] = tasks
    if go:
        json.dump(d, open(reg(dst), 'w'), indent=2, ensure_ascii=False)
    print(f"{tag}DST {len(tasks)} 条，调整 {len(changes)} 条:")
    print('\n'.join(changes or ['  无']))

    for f in sorted(glob.glob(os.path.join(ROOT, '*', '*', 'scheduled-tasks.json'))):
        if os.path.samefile(f, reg(dst)):
            continue
        data = json.load(open(f))
        lit = [t for t in data.get('scheduledTasks', []) if t.get('enabled')]
        for t in lit:
            t['enabled'] = False
            t[SNUFF] = True
        if lit:
            if go:
                json.dump(data, open(f, 'w'), indent=2, ensure_ascii=False)
            print(f"{tag}掐灭 {os.path.dirname(os.path.relpath(f, ROOT))}: "
                  f"{[t['id'] for t in lit]}")


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--go']
    if len(a) != 2:
        sys.exit(__doc__)
    main(a[0], a[1], '--go' in sys.argv)

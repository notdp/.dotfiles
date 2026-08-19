#!/usr/bin/env python3
"""把一个账号目录摊成表格：Routines / Pinned / 各项目。

两处用：确认 SRC 是不是用户要的那份数据，以及用户问"现在有什么"时看当前账号。
分组对着 CCD 侧栏来，用户能逐条核对。归档的不进表——侧栏看不见，列出来只会
让用户对不上号，末尾报个数就够了。

用法: table.py <accountUuid>/<orgUuid>
"""
import collections
import glob
import json
import os
import sys
import datetime

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
LEDGER = os.path.expanduser('~/.claude/ccd-account-emails.json')
stamp = lambda ms: datetime.datetime.fromtimestamp(ms / 1000).strftime('%m-%d %H:%M') \
    if isinstance(ms, (int, float)) and ms else '-'


def main(rel):
    d = os.path.join(ROOT, rel.rstrip('/'))
    em = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    S = sorted([json.load(open(f)) for f in glob.glob(os.path.join(d, 'local_*.json'))],
               key=lambda x: -x.get('lastActivityAt', 0))
    if not S:
        sys.exit(f"{rel} 里没有 local_*.json")
    live = [x for x in S if not x.get('isArchived') and not x.get('scheduledTaskId')]
    runs = collections.Counter(x['scheduledTaskId'] for x in S if x.get('scheduledTaskId'))
    row = lambda x: (f"| {x.get('title', '(无标题)')[:36]} | {stamp(x.get('lastActivityAt'))} "
                     f"| {x.get('completedTurns', 0)} | {str(x.get('model', '')).replace('claude-', '')} |")

    print(f"## {rel.rstrip('/')}\n")
    print(f"**{em.get(rel.split('/')[0], {}).get('email', '邮箱未知')}** · "
          f"最后活动 {stamp(live[0].get('lastActivityAt')) if live else '-'} · 可见 {len(live)} · "
          f"pinned {sum(1 for x in live if x.get('isStarred'))} · "
          f"归档 {sum(1 for x in S if x.get('isArchived'))} · routine {sum(runs.values())} · "
          f"墓碑 {len(glob.glob(os.path.join(d, 'deleted_*')))}")

    tf = os.path.join(d, 'scheduled-tasks.json')
    tasks = json.load(open(tf))['scheduledTasks'] if os.path.exists(tf) else []
    if tasks:
        print("\n### Routines\n\n| Routine | cron | 最后执行 | 执行次数 |\n|---|---|---|---|")
        for k in tasks:
            print(f"| {k['id']} | `{k.get('cronExpression')}` | {str(k.get('lastRunAt'))[:16]} "
                  f"| {runs.get(k['id'], 0)} |")

    star = [x for x in live if x.get('isStarred')]
    if star:
        print(f"\n### Pinned ({len(star)})\n\n| 标题 | 项目 | 最后活动 | 轮数 | 模型 |\n|---|---|---|---|---|")
        for x in star:
            print(f"| {x.get('title', '')[:36]} | {os.path.basename(x.get('originCwd', ''))} |"
                  + row(x).split('|', 2)[2])

    g = collections.defaultdict(list)
    for x in live:
        if not x.get('isStarred'):
            g[os.path.basename(x.get('originCwd', ''))].append(x)
    big = [k for k in sorted(g, key=lambda k: -len(g[k])) if len(g[k]) >= 3]
    for k in big:
        print(f"\n### {k} ({len(g[k])})\n\n| 标题 | 最后活动 | 轮数 | 模型 |\n|---|---|---|---|")
        for x in g[k]:
            print(row(x))
    rest = [(k, x) for k in g if k not in big for x in g[k]]
    if rest:
        print(f"\n### 其余项目 ({len(rest)})\n\n| 项目 | 标题 | 最后活动 | 轮数 | 模型 |\n|---|---|---|---|---|")
        for k, x in sorted(rest, key=lambda kx: -kx[1].get('lastActivityAt', 0)):
            print(f"| {k} | {x.get('title', '')[:36]} |" + row(x).split('|', 2)[2])
    print(f"\n另有归档 {sum(1 for x in S if x.get('isArchived'))} 条（侧栏不显示）。")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

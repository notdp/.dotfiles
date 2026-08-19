#!/usr/bin/env python3
"""记下 accountUuid -> 邮箱，并列出所有账号目录（选 SRC 用）。

CCD 只保留当前登录账号的 profile，切号即覆盖，所以旧账号的邮箱本地拿不到
——除非提前记下来。CLI 状态滞后于 CCD 这个毛病在这里反而是好事：切号后第一次
跑，~/.claude.json 里往往还是上一棒的邮箱，正好记账。记的是 uuid 和邮箱的配对，
跟"当前是谁"无关，所以滞不滞后都记得对。
"""
import datetime
import glob
import json
import os

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
LEDGER = os.path.expanduser('~/.claude/ccd-account-emails.json')
SOURCES = [
    '~/.claude.json',
    '~/.claude/backups/.claude.json.backup.*',
    '~/Library/Application Support/Claude/local-agent-mode-sessions/*/*/*/.claude/.claude.json',
]


def record_emails():
    em = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    before = len(em)
    for pattern in SOURCES:
        for f in glob.glob(os.path.expanduser(pattern)):
            try:
                o = json.load(open(f)).get('oauthAccount') or {}
            except Exception:
                continue
            if o.get('accountUuid') and o.get('emailAddress'):
                em.setdefault(o['accountUuid'], {}).update(
                    email=o['emailAddress'], org=o.get('organizationUuid'),
                    seenAt=datetime.datetime.now().isoformat(timespec='seconds'))
    json.dump(em, open(LEDGER, 'w'), indent=1, ensure_ascii=False)
    print(f"邮箱映射 {len(em)} 条（新增 {len(em) - before}） -> {LEDGER}\n")
    return em


def main():
    em = record_emails()
    stamp = lambda ms: datetime.datetime.fromtimestamp(ms / 1000).strftime('%m-%d %H:%M') if ms else '-'
    last = lambda d: max([json.load(open(f)).get('lastActivityAt', 0)
                          for f in glob.glob(os.path.join(d, 'local_*.json'))] or [0])
    dirs = sorted(glob.glob(os.path.join(ROOT, '*/*/')), key=lambda d: -last(d))
    print(f"{'目录':<76}{'可见':>5}{'pin':>4}{'归档':>5}{'routine':>8}{'墓碑':>6}  {'最后活动':<12} 邮箱")
    for d in dirs:
        S = [json.load(open(f)) for f in glob.glob(os.path.join(d, 'local_*.json'))]
        if not S:
            continue
        rel = os.path.relpath(d, ROOT)
        vis = [x for x in S if not x.get('isArchived') and not x.get('scheduledTaskId')]
        print(f"{rel + '/':<76}{len(vis):>5}{sum(1 for x in vis if x.get('isStarred')):>4}"
              f"{sum(1 for x in S if x.get('isArchived')):>5}"
              f"{sum(1 for x in S if x.get('scheduledTaskId')):>8}"
              f"{len(glob.glob(os.path.join(d, 'deleted_*'))):>6}  {stamp(last(d)):<12} "
              f"{em.get(rel.split('/')[0], {}).get('email', '?')}")


if __name__ == '__main__':
    main()

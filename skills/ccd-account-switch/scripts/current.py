#!/usr/bin/env python3
"""认出 CCD 当前登录的账号（DST），只信最新写入的那份 leveldb 记录。

2026-09-02 栽过一次：原来的一行 grep 把整个 leveldb 目录 strings 到一起数频次，
结果匹配到的是 8 月的旧 .ldb（rira@franxx.ai），而当天 02:18 刚写的 061265.log 里
的真账号（dp0x7ce@gmail.com）因为两个字段在字节流里不相邻，压根没被那条正则捞到。
照那个结论传火，SRC 和 DST 正好反过来——当天全部工作的索引会被 8 月的旧状态覆盖。

所以这里的规矩是：按 mtime 从新到旧扫，第一个含 account_uuid 的文件就是判据，
文件内取偏移最大的那次出现（leveldb 的 .log 是追加写，后写的在后面）。频次不作数，
旧文件不作数。
"""
import glob
import os
import re
import sys
import time

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
LEVELDB = os.path.expanduser('~/Library/Application Support/Claude/Local Storage/leveldb')

PAT_ACCT = re.compile(rb'"account_uuid":"([0-9a-f-]{36})"')
PAT_ORG = re.compile(rb'"organization_uuid":"([0-9a-f-]{36})"')


def scan(path):
    try:
        with open(path, 'rb') as fh:
            blob = fh.read()
    except OSError:
        return [], []
    return [(m.start(), m.group(1).decode()) for m in PAT_ACCT.finditer(blob)], \
           [(m.start(), m.group(1).decode()) for m in PAT_ORG.finditer(blob)]


def org_dirs(acct):
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, acct, '*'))
                  if os.path.isdir(p))


def visible_count(acct, org):
    n = 0
    for p in glob.glob(os.path.join(ROOT, acct, org, 'local_*.json')):
        n += 1
    return n


def main():
    files = sorted(glob.glob(os.path.join(LEVELDB, '*')), key=os.path.getmtime, reverse=True)
    if not files:
        sys.exit(f'leveldb 目录空或不存在: {LEVELDB}')

    verdict = None
    rows = []
    for path in files:
        accts, orgs = scan(path)
        if not accts:
            continue
        seen = sorted({a for _, a in accts})
        rows.append((os.path.basename(path), os.path.getmtime(path), len(accts), seen))
        if verdict is None:
            off, acct = accts[-1]
            org = min(orgs, key=lambda t: abs(t[0] - off))[1] if orgs else None
            verdict = (path, acct, org)

    if verdict is None:
        sys.exit('leveldb 里没有 account_uuid，CCD 可能没登录过；直接问用户当前邮箱。')

    path, acct, org = verdict
    have = org_dirs(acct)
    recorded = org
    if org not in have or visible_count(acct, org) == 0:
        # 记录里的 org 没有对应目录（多 org 账号），退回到有会话的那个
        ranked = sorted(have, key=lambda o: visible_count(acct, o), reverse=True)
        if ranked:
            org = ranked[0]

    print(f'当前账号（DST）: {acct}/{org}')
    print(f'  判据: {os.path.basename(path)}  写于 {time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(path)))}')
    if org != recorded:
        print(f'  记录里的 org {recorded} 没有会话目录，退回到会话最多的 {org}')
    others = [f'{o[:8]}({visible_count(acct, o)})' for o in have if o != org]
    if others:
        print(f'  同账号下另有 org（会话数）: {", ".join(others)} —— 空目录，别选')
    print()
    print('leveldb 里出现过的账号（新 -> 旧，只有第一行作数）:')
    for name, mtime, hits, seen in rows:
        mark = '  <- 判据' if name == os.path.basename(path) else ''
        print(f'  {time.strftime("%m-%d %H:%M", time.localtime(mtime))}  {name:<20} {hits:>4} 次  {" ".join(s[:8] for s in seen)}{mark}')
    if len(rows) > 1 and any(acct not in seen for _, _, _, seen in rows[1:]):
        print('\n注意: 旧文件里是别的账号，那是切号前的残留，不要拿来投票。')


if __name__ == '__main__':
    main()

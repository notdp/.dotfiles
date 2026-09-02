#!/usr/bin/env python3
"""认出 CCD 当前登录的账号（DST）。

两个判据，锚点优先：

1. **锚点**：本会话自己的索引文件落在哪个目录，哪个就是当前账号。CCD 只往当前账号
   目录写正在跑的会话，这个信号不会半写。文件名由 `CLAUDE_CODE_HOST_SESSION_ID`
   给出（形如 `local_<uuid>`），退路是拿 `CLAUDE_CODE_SESSION_ID` 去 grep 各目录
   索引里的 `cliSessionId`。
2. **leveldb**：按 mtime 从新到旧扫，第一个含 account_uuid 的文件作数，文件内取偏移
   最大的那次出现（.log 是追加写）。频次不作数，旧文件不作数。

两边打架时**锚点赢**，见下面第二个跟头。

栽过两次：

2026-09-02 上午：原来这里是一行 `strings 整个 leveldb 目录 | grep | uniq -c`，捞到的是
8 月的旧 .ldb（rira@franxx.ai），而当天 02:18 刚写的 061265.log 里的真账号
（dp0x7ce@gmail.com）因为两个字段在字节流里不相邻，压根没被那条正则捞到。于是改成了
上面第 2 条。

2026-09-02 08:41：只有 leveldb 判据的版本又报错了一次，而且正好把方向搞反。用户 08:39
切号，08:41 跑本脚本时 CCD 还在追写 061284.log——那一刻文件 47306 字节，里面只有旧账号
d56e75fa 的 10 条记录；新账号 1e7f4a9f 的 15 条（偏移 49448~60609）是几十秒后才落盘的。
"取最新文件里偏移最大的那次"这条规则没错，错在文件还没写完。而用户跑这个 skill 的时机
恰恰就是刚切完号，正撞在这个窗口上。照那个结论传火，当天全部工作的索引会被旧账号覆盖。
所以有了第 1 条锚点。
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
    return len(glob.glob(os.path.join(ROOT, acct, org, 'local_*.json')))


def pair_of(path):
    """从索引文件路径反推 <accountUuid>/<orgUuid>。"""
    org = os.path.basename(os.path.dirname(path))
    acct = os.path.basename(os.path.dirname(os.path.dirname(path)))
    return acct, org


def anchor():
    """本会话的索引文件在哪个目录。返回 (acct, org, 怎么找到的) 或 None。"""
    host = os.environ.get('CLAUDE_CODE_HOST_SESSION_ID', '').strip()
    if host:
        hits = glob.glob(os.path.join(ROOT, '*', '*', host + '.json'))
        if hits:
            hits.sort(key=os.path.getmtime, reverse=True)
            acct, org = pair_of(hits[0])
            extra = f'，另有 {len(hits) - 1} 个同名副本（取 mtime 最新）' if len(hits) > 1 else ''
            return acct, org, f'本会话索引 {host}.json{extra}'

    cli = os.environ.get('CLAUDE_CODE_SESSION_ID', '').strip()
    if cli:
        needle = f'"cliSessionId": "{cli}"'
        needle_compact = f'"cliSessionId":"{cli}"'
        hits = []
        for p in glob.glob(os.path.join(ROOT, '*', '*', 'local_*.json')):
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                    head = fh.read(4096)
            except OSError:
                continue
            if needle in head or needle_compact in head:
                hits.append(p)
        if hits:
            hits.sort(key=os.path.getmtime, reverse=True)
            acct, org = pair_of(hits[0])
            return acct, org, f'cliSessionId {cli[:8]} 落在 {os.path.basename(hits[0])}'
    return None


def from_leveldb():
    """返回 (判据文件, acct, org, 扫描明细) 或 (None, None, None, [])。"""
    files = sorted(glob.glob(os.path.join(LEVELDB, '*')), key=os.path.getmtime, reverse=True)
    verdict, rows = None, []
    for path in files:
        accts, orgs = scan(path)
        if not accts:
            continue
        rows.append((os.path.basename(path), os.path.getmtime(path), len(accts),
                     sorted({a for _, a in accts})))
        if verdict is None:
            off, acct = accts[-1]
            org = min(orgs, key=lambda t: abs(t[0] - off))[1] if orgs else None
            verdict = (path, acct, org)
    if verdict is None:
        return None, None, None, rows
    return verdict[0], verdict[1], verdict[2], rows


def settle_org(acct, org):
    """记录里的 org 没有对应目录（多 org 账号）时，退回到会话最多的那个。"""
    have = org_dirs(acct)
    if org in have and visible_count(acct, org) > 0:
        return org, False
    ranked = sorted(have, key=lambda o: visible_count(acct, o), reverse=True)
    return (ranked[0], True) if ranked else (org, False)


def main():
    anc = anchor()
    ldb_path, ldb_acct, ldb_org, rows = from_leveldb()

    if anc:
        acct, org, how = anc
        source = f'锚点（{how}）'
    elif ldb_acct:
        acct = ldb_acct
        org, _ = settle_org(ldb_acct, ldb_org)
        source = 'leveldb（没找到锚点，可能不是在 CCD 会话里跑的）'
    else:
        sys.exit('锚点和 leveldb 都没给出账号，CCD 可能没登录过；直接问用户当前邮箱。')

    if anc:
        settled, moved = settle_org(acct, org)
        if moved:
            print(f'注意: 锚点目录 {org[:8]} 没有会话，退回到 {settled[:8]}')
            org = settled

    print(f'当前账号（DST）: {acct}/{org}')
    print(f'  判据: {source}')

    if anc and ldb_acct:
        ldb_org_settled, _ = settle_org(ldb_acct, ldb_org)
        stamp = time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(ldb_path)))
        if ldb_acct == acct:
            print(f'  leveldb 同意: {os.path.basename(ldb_path)} 写于 {stamp}')
        else:
            print()
            print(f'  !! leveldb 说的是 {ldb_acct}/{ldb_org_settled}（{os.path.basename(ldb_path)} '
                  f'写于 {stamp}），跟锚点不一致。')
            print('  !! 以锚点为准。刚切完号时 CCD 还在追写 leveldb，这时候读到的是切号前的旧账号，')
            print('  !! 照它传火会把新账号的索引覆盖成旧状态——2026-09-02 就这么栽过一次。')
            print('  !! 如果你确信自己没在切号窗口上，先停手问用户当前登录的邮箱。')
    elif not anc:
        print('  没有 CLAUDE_CODE_HOST_SESSION_ID / CLAUDE_CODE_SESSION_ID，锚点用不了。')
        print('  刚切完号的话 leveldb 可能还没写完，拿目录 mtime 和用户口述的邮箱对一遍再动手。')

    others = [f'{o[:8]}({visible_count(acct, o)})' for o in org_dirs(acct) if o != org]
    if others:
        print(f'  同账号下另有 org（会话数）: {", ".join(others)} —— 空目录，别选')

    if rows:
        print()
        print('leveldb 里出现过的账号（新 -> 旧，只有第一行作数）:')
        for name, mtime, hits, seen in rows:
            mark = '  <- leveldb 判据' if ldb_path and name == os.path.basename(ldb_path) else ''
            print(f'  {time.strftime("%m-%d %H:%M", time.localtime(mtime))}  {name:<20} '
                  f'{hits:>4} 次  {" ".join(s[:8] for s in seen)}{mark}')
        if len(rows[0][3]) > 1:
            print('  ^ 判据文件里不止一个账号，是切号瞬间的特征，别按频次投票。')


if __name__ == '__main__':
    main()

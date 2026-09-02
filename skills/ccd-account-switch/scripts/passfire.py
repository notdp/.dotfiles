#!/usr/bin/env python3
"""一句话传火：在 CCD 会话里跑，认账号 → 选上一棒 → 备份 → 传 session 索引 → 传 routine → 复核。

    python3 passfire.py          # 只看数字，不写
    python3 passfire.py --go     # 真写
    python3 passfire.py --src <accountUuid>/<orgUuid> [--go]   # 不信自动选的 SRC 时手动指定

只在 CCD 会话内可用：DST 靠本会话索引文件所在目录（锚点）判定，这个信号不会半写；
终端里没有锚点直接退出，不退回 leveldb（刚切完号时 leveldb 还在追写，2026-09-02 判反过两次）。
SRC = 除 DST 外最后活动最近的那个账号目录。同账号下的空 org 目录不算。

五步全是原有脚本的函数，本文件只负责串起来并把判断打印给人看：
  current.anchor / settle_org  → DST
  accounts.record_emails       → 邮箱账本（顺手记账，切号后旧账号邮箱只有这里有）
  pass_fire.main               → session 索引（先 dry 再 --go）
  merge_routines.main          → routine 注册表 + 掐灭其他目录
复核：传完再算一次"DST 里 SRC 已删的"，必须是 0。
"""
import contextlib
import datetime
import glob
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import accounts          # noqa: E402
import current           # noqa: E402
import merge_routines    # noqa: E402
import pass_fire         # noqa: E402

ROOT = current.ROOT
BACKUP = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions-backup')


def last_activity(d):
    ts = [json.load(open(f)).get('lastActivityAt', 0) for f in glob.glob(os.path.join(d, 'local_*.json'))]
    return max(ts or [0])


def stamp(ms):
    return datetime.datetime.fromtimestamp(ms / 1000).strftime('%m-%d %H:%M') if ms else '-'


def visible(d):
    return sum(1 for f in glob.glob(os.path.join(d, 'local_*.json'))
               if not (x := json.load(open(f))).get('isArchived') and not x.get('scheduledTaskId'))


def pick_src(dst_rel):
    dst_acct = dst_rel.split('/')[0]
    cands = []
    for d in glob.glob(os.path.join(ROOT, '*/*/')):
        rel = os.path.relpath(d, ROOT)
        if rel.split('/')[0] == dst_acct or not glob.glob(os.path.join(d, 'local_*.json')):
            continue
        cands.append((last_activity(d), rel))
    cands.sort(reverse=True)
    return cands


def main():
    go = '--go' in sys.argv
    src_rel = None
    if '--src' in sys.argv:
        src_rel = sys.argv[sys.argv.index('--src') + 1].strip('/')

    anc = current.anchor()
    if not anc:
        sys.exit('没有锚点（CLAUDE_CODE_HOST_SESSION_ID / CLAUDE_CODE_SESSION_ID）。'
                 '这条命令只能在 CCD 会话里跑，不退回 leveldb。')
    acct, org, how = anc
    org, moved = current.settle_org(acct, org)
    dst_rel = f'{acct}/{org}'

    with contextlib.redirect_stdout(io.StringIO()):
        em = accounts.record_emails()
    mail = lambda rel: em.get(rel.split('/')[0], {}).get('email', '?')

    cands = pick_src(dst_rel)
    if src_rel is None:
        if not cands:
            sys.exit('除 DST 外没有带会话的账号目录，没什么可传的。')
        src_rel = cands[0][1]
    src_dir, dst_dir = os.path.join(ROOT, src_rel), os.path.join(ROOT, dst_rel)
    if not os.path.isdir(src_dir):
        sys.exit(f'SRC 目录不存在: {src_rel}')

    print(f"DST（当前账号）: {mail(dst_rel):<24} {dst_rel}   可见 {visible(dst_dir)}   判据: {how}"
          + ('   （锚点 org 为空目录，已退回有会话的 org）' if moved else ''))
    print(f"SRC（上一棒）  : {mail(src_rel):<24} {src_rel}   可见 {visible(src_dir)}   最后活动 {stamp(last_activity(src_dir))}")
    if len(cands) > 1:
        print('  其他候选（更早）: ' + ', '.join(f'{mail(r)} {r[:8]} {stamp(t)}' for t, r in cands[1:4]))
    print()

    if go:
        if os.path.exists(BACKUP):
            shutil.rmtree(BACKUP)
        shutil.copytree(dst_dir, BACKUP)
        print(f'已备份 DST -> {BACKUP}')

    print('session 索引:')
    pass_fire.main(src_rel, dst_rel, go)
    print('routine 注册表:')
    merge_routines.main(src_rel, dst_rel, go)

    stale = pass_fire.ids(dst_dir, 'local_*.json') & pass_fire.ids(src_dir, 'deleted_*')
    print()
    if go:
        print(f"复核: DST 里 SRC 已删的 = {len(stale)}（应为 0）" + ('  OK' if not stale else '  !! 没清干净'))
        print('重启 CCD 才会读到新索引；恢复的 routine 各 Run now 一次重新批权限。')
    else:
        print('看着对就加 --go。')


if __name__ == '__main__':
    main()

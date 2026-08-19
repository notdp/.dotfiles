#!/usr/bin/env python3
"""传火：把上一棒账号的 session 索引传给当前账号。

默认只报数字不动文件，确认后加 --go 才真写。这个默认值是拿教训换的——
从文档里抠命令出来跑很容易抠错块，默认安全就不会一跑就出事。

三条规则各挡一个坑，都是实测踩出来的：

  已删的不复活  传火链上 SRC 独有的会话几乎全是用户删的（实测 132 条独有，
                132 条在 DST 都有 deleted_ 墓碑，零例外）。无脑全量 cp 会一次
                复活上百条。
  新的不盖旧的  local_*.json 里的 cliSessionId 指向 transcript，旧索引指着旧
                transcript，会话打开后内容停在过去、轮数变少（实测一个 116 轮
                的会话显示成 19 轮）。混在几百个文件里只有逐个开会话才看得出来。
  在用的不误杀  SRC 的墓碑不能盖到 DST 还在用的同 id 会话上（实测 4 条中招）。

因为规则是"更新的赢"，多个旧目录任意顺序跑都行，重复跑也是幂等的。
DST 是空目录时三条规则一条都不触发，结果跟全量 cp 逐字节一致。

用法: pass_fire.py <SRC> <DST> [--go]
"""
import glob
import json
import os
import shutil
import sys

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
uid = lambda f: os.path.basename(f).replace('local_', '').replace('.json', '')


def main(src, dst, go):
    src, dst = os.path.join(ROOT, src.rstrip('/')), os.path.join(ROOT, dst.rstrip('/'))
    dead = {os.path.basename(x)[8:] for x in glob.glob(os.path.join(dst, 'deleted_*'))}
    live = {uid(x) for x in glob.glob(os.path.join(dst, 'local_*.json'))}

    sent = skipped_dead = skipped_new = 0
    for f in glob.glob(os.path.join(src, 'local_*.json')):
        i = uid(f)
        target = os.path.join(dst, f'local_{i}.json')
        if i in dead:                                              # 用户删过，不复活
            skipped_dead += 1
            continue
        if i in live and json.load(open(target)).get('lastActivityAt', 0) >= \
                json.load(open(f)).get('lastActivityAt', 0):        # DST 更新，不盖回旧的
            skipped_new += 1
            continue
        if go:
            shutil.copyfile(f, target)
        sent += 1

    marks = 0
    for f in glob.glob(os.path.join(src, 'deleted_*')):
        b = os.path.basename(f)
        if b[8:] in live or os.path.exists(os.path.join(dst, b)):   # 在用的别误杀，已有的不重传
            continue
        if go:
            shutil.copyfile(f, os.path.join(dst, b))
        marks += 1

    print(f"{'' if go else '[dry] '}传入会话 {sent}  跳过(用户已删) {skipped_dead}  "
          f"跳过(DST 更新) {skipped_new}  传入墓碑 {marks}")
    if not go:
        print("看着对就加 --go 真写。写之前记得先备份 DST。")


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--go']
    if len(a) != 2:
        sys.exit(__doc__)
    main(a[0], a[1], '--go' in sys.argv)

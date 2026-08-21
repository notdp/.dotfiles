#!/usr/bin/env python3
"""传火：把上一棒账号的 session 列表原样传给当前账号。

传火不是合并两个目录，是整个火种传给下一位——传完 DST 就该跟 SRC 看到的一样。

CCD 侧栏只认 local_<id>.json 在不在，完全不看 deleted_ 墓碑（实测：CCD 列出 302
条，DST 的 local 文件 306 减 3 归档减 1 当前会话，精确吻合）。所以墓碑一个都不用
搬，只拿来当"SRC 见过这个 id"的证据：

  SRC 有 local、无墓碑   SRC 侧栏显示中     -> 拷给 DST
  SRC 有墓碑             用户删过           -> DST 有的话也删掉
  SRC 从没见过这个 id    DST 切号后新建的   -> 原样留着

唯一的例外判断：切号后在 DST 里用过的会话，DST 版本更新，别拿 SRC 的旧版盖回去
（旧索引指着旧 transcript，会话打开后轮数变少。实测 2026-08-21 有 1 条 146 轮的
会被打回 145 轮）。

旧版本比时间戳、判谁新谁旧、还把 SRC 的墓碑拷进 DST，是把传火写成了合并。后果是
只加不减：用户在旧账号删掉的，新账号一直留着。2026-08-21 炸过一次——切到新账号后
72 条已删会话（ordo_ai 占 51 条）挂在侧栏，因为新账号目录停在 08-16 的全量状态，
而用户 08-18 才在旧账号删了 500 多条，删除动作从不跨账号同步。

删掉的索引移到 claude-code-sessions-pruned/，不 rm，搬回来即可恢复。transcript
正文在 ~/.claude/projects/ 里，本来就不受影响。

用法: pass_fire.py <SRC> <DST> [--go]
"""
import glob
import json
import os
import shutil
import sys

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
PRUNED = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions-pruned')
ids = lambda d, pat: {os.path.basename(f).split('_', 1)[1].replace('.json', '')
                      for f in glob.glob(os.path.join(d, pat))}


def main(src, dst, go):
    src, dst = os.path.join(ROOT, src.rstrip('/')), os.path.join(ROOT, dst.rstrip('/'))
    dead = ids(src, 'deleted_*')
    have = ids(src, 'local_*.json') - dead          # SRC 侧栏现在显示的
    stale = ids(dst, 'local_*.json') & dead         # DST 还留着、但 SRC 已删的

    if go and stale:
        os.makedirs(PRUNED, exist_ok=True)
    for i in stale:
        if go:
            shutil.move(os.path.join(dst, f'local_{i}.json'),
                        os.path.join(PRUNED, f'local_{i}.json'))
    kept = 0
    for i in have:
        a, b = os.path.join(src, f'local_{i}.json'), os.path.join(dst, f'local_{i}.json')
        if os.path.exists(b) and json.load(open(b)).get('lastActivityAt', 0) > \
                                 json.load(open(a)).get('lastActivityAt', 0):
            kept += 1                        # 切号后在 DST 用过，别拿 SRC 的旧版盖回去
            continue
        if go:
            shutil.copyfile(a, b)

    mine = ids(dst, 'local_*.json') - have - dead
    print(f"{'' if go else '[dry] '}传入 {len(have) - kept}  清掉 DST 里 SRC 已删的 {len(stale)}  "
          f"DST 更新跳过 {kept}  DST 独有保留 {len(mine)}")
    if not go:
        print(f"看着对就加 --go 真写。清掉的会移到 {PRUNED}，不是 rm。")


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--go']
    if len(a) != 2:
        sys.exit(__doc__)
    main(a[0], a[1], '--go' in sys.argv)

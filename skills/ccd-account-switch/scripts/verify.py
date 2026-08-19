#!/usr/bin/env python3
"""传火后校验：有没有哪一棒的会话在 DST 既没索引也没墓碑。

漏传数为 0 说明传火链完整。local 和墓碑并存是正常的（CCD 按 local 优先显示），
但数量不该比传火前多——多了说明 SRC 的墓碑盖到了 DST 还在用的会话上。

用法: verify.py <DST>
"""
import glob
import os
import sys

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')
uid = lambda f: os.path.basename(f).replace('local_', '').replace('.json', '')


def main(rel):
    dst = os.path.join(ROOT, rel.rstrip('/'))
    live = {uid(x) for x in glob.glob(os.path.join(dst, 'local_*.json'))}
    dead = {os.path.basename(x)[8:] for x in glob.glob(os.path.join(dst, 'deleted_*'))}
    print(f"可见 {len(live)}  墓碑 {len(dead)}  两者并存 {len(live & dead)} "
          f"(local 优先，会照常显示；数量不该比传火前多)")
    leaked = 0
    for d in sorted(glob.glob(os.path.join(ROOT, '*/*/'))):
        if os.path.realpath(d) == os.path.realpath(dst):
            continue
        missing = {uid(x) for x in glob.glob(os.path.join(d, 'local_*.json'))} - live - dead
        if missing:
            print(f"  漏传 {len(missing)} 条 <- {os.path.relpath(d, ROOT)}")
            leaked += 1
    print("传火链完整，没有漏传" if not leaked
          else "上面这些会话在 DST 既无索引也无墓碑，是真漏了")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

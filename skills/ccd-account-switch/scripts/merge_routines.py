#!/usr/bin/env python3
"""routine 注册表也是传火：DST 已有的任务原样不动，只补 SRC 独有的。

scheduled-tasks.json 的 scheduledTasks 是数组（不是以 id 为键的对象），按 id 对。

绝对不要 cp 整个文件过去。老写法是先 diff 再让人判断要不要覆盖，实测不可靠——
一次误覆盖就把 tokamak 的 cron 从 `0 12 * * *` 打回旧的 `0 */6 * * *`，三个任务的
lastRunAt 全部回拨一天（可能触发补跑），useWorktree 字段丢失。DST 的配置是用户在
当前账号里改过的，永远比 SRC 新。

用法: merge_routines.py <SRC> <DST> [--go]
"""
import json
import os
import sys

ROOT = os.path.expanduser('~/Library/Application Support/Claude/claude-code-sessions')


def main(src, dst, go):
    load = lambda p: json.load(open(os.path.join(ROOT, p.rstrip('/'), 'scheduled-tasks.json')))
    d, s = load(dst), load(src)
    have = {t['id'] for t in d['scheduledTasks']}
    add = [t for t in s['scheduledTasks'] if t['id'] not in have]
    d['scheduledTasks'] += add
    if go:
        json.dump(d, open(os.path.join(ROOT, dst.rstrip('/'), 'scheduled-tasks.json'), 'w'),
                  indent=2, ensure_ascii=False)
    print(f"{'' if go else '[dry] '}补入 {len(add)} 个: {[t['id'] for t in add] or '无'}   "
          f"DST 原有 {len(have)} 个原样保留")


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--go']
    if len(a) != 2:
        sys.exit(__doc__)
    main(a[0], a[1], '--go' in sys.argv)

#!/usr/bin/env python3
"""环境（session preset）传火：把 SRC 账号的环境列表并进 DST 账号。

环境选择器里自己建的那些（"New environment" 建出来的 fleet / hive / otto ...）存在
~/Library/Application Support/Claude/ccd-session-presets.json，按 accountUuid 分开：
{"byAccount": {<accountUuid>: {"presets": [...], "builtIns": {...}, "seededFromDraft": bool}}}。
切号后新账号是空的，会话索引里的 envScopeId / startedFromEnvironmentId 指向的环境也就没了。
2026-10-19 实测：旧号 9 个，新号 0 个。

规则跟 routine 一样：同 id 以 SRC 为准（SRC 是刚交棒的火种），DST 独有的保留，
builtIns（This computer 的默认模型/effort）也取 SRC 的。只改 DST 那一个 key，别的账号不动。
sshConfigId 指向的 ssh_configs.json 不分账号，不用搬。

CCD 主进程每次读这个文件都重新读盘，但前端页面把环境列表缓存在内存里，
写完要重启 CCD 才看得到；重启前别在环境选择器里增删改，否则前端会用旧列表把 DST 这一项整份写回去。

用法: merge_presets.py <SRC accountUuid/orgUuid> <DST accountUuid/orgUuid> [--go]
"""
import json
import os
import sys

PATH = os.path.expanduser('~/Library/Application Support/Claude/ccd-session-presets.json')
MAX = 200       # CCD 自己的上限（Tma=200）


def main(src, dst, go):
    tag = '' if go else '[dry] '
    sa, da = src.split('/')[0], dst.split('/')[0]
    if not os.path.exists(PATH):
        print(f'{tag}没有 {os.path.basename(PATH)}，跳过')
        return
    data = json.load(open(PATH))
    by = data.setdefault('byAccount', {})
    s = by.get(sa)
    if not s or not s.get('presets'):
        print(f'{tag}SRC 没有环境，跳过')
        return
    d = by.get(da) or {'presets': []}
    src_ids = {p['id'] for p in s['presets']}
    keep = [p for p in d.get('presets', []) if p['id'] not in src_ids]
    merged = list(s['presets']) + keep
    if len(merged) > MAX:
        sys.exit(f'合并后 {len(merged)} 个，超过 CCD 上限 {MAX}，没写')
    out = {**d, 'presets': merged}
    if s.get('builtIns') is not None:
        out['builtIns'] = s['builtIns']
    added = len(src_ids - {p['id'] for p in d.get('presets', [])})
    print(f"{tag}环境: DST {len(d.get('presets', []))} -> {len(merged)}（新增 {added}，DST 独有保留 {len(keep)}）"
          + ('  builtIns 按 SRC 对齐' if s.get('builtIns') not in (None, d.get('builtIns')) else ''))
    if go:
        by[da] = out
        tmp = PATH + '.tmp'
        with open(tmp, 'w') as fh:
            json.dump(data, fh, ensure_ascii=False, indent='\t')   # 跟 CCD 自己写的格式一致
        os.chmod(tmp, 0o600)
        os.replace(tmp, PATH)


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--go']
    if len(a) != 2:
        sys.exit(__doc__)
    main(a[0], a[1], '--go' in sys.argv)

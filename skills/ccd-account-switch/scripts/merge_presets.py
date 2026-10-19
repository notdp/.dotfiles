#!/usr/bin/env python3
"""环境（session preset）传火：把 SRC 账号的环境列表并进 DST 账号。

环境选择器里自己建的那些（"New environment" 建出来的 fleet / hive / otto ...）按账号存。
切号后新账号是空的。2026-10-19 实测：旧号 9 个，新号 0 个。

规则跟 routine 一样：同 id 以 SRC 为准（SRC 是刚交棒的火种），DST 独有的保留，
builtIns（This computer 的默认模型/effort）也取 SRC 的。只改 DST 那一个账号，别的不动。
sshConfigId 指向的 ssh_configs.json 不分账号，不用搬。

**真正的存储在页面 localStorage，文件只是镜像**：claude.ai 页面把每个账号的环境存在
localStorage 的 `persisted.ccd-session-presets.<accountUuid>`（值里带 fileMirrored 标记），
再用 SessionPresets.replaceAll 写成 ~/Library/Application Support/Claude/ccd-session-presets.json
（{"byAccount": {<accountUuid>: {"presets": [...], "builtIns": {...}, ...}}}）。
2026-10-19 实测两次：CCD 运行中改文件，Cmd+R 后被写回 0；等 CCD 退出后改文件、重开 30 秒
复查还是 9，几小时后又被写回 0。所以只拿文件当"读"的来源（SRC 的环境从镜像里读），
写入走页面：--go 生成一段 JS，用户在 CCD 里右键 → Inspect Element → Console 粘贴执行。
它备份原值到 <key>.bak-ccd-env，只替换该账号的 presets，然后重载界面；key 不存在或结构
对不上就报错停止，不改任何东西。前提是 developer_settings.json 里 allowDevTools 为 true。
控制台要连在 https://claude.ai 那层页面上（输入行上方的 top 下拉框可切）。
执行后页面会刷新镜像文件，可以用镜像文件里 DST 的数量复核。

用法:
  merge_presets.py <SRC> <DST>                 # 看合并结果
  merge_presets.py <SRC> <DST> --go            # 生成 JS 到 ~/.claude/ccd-restore-env.js
  merge_presets.py --catalog <file> <DST> --go # 用 file 里的 DST 那一项（{"presets": [...]}）生成 JS
SRC/DST 都是 <accountUuid>/<orgUuid>（只用前半段）。
"""
import json
import os
import sys

PATH = os.path.expanduser('~/Library/Application Support/Claude/ccd-session-presets.json')
JS_OUT = os.path.expanduser('~/.claude/ccd-restore-env.js')
MAX = 200       # CCD 自己的上限（Tma=200）

JS = r"""// CCD 环境恢复：把账号 %(acct)s 的环境列表写进页面 localStorage，然后重载界面。
// 只改这一个账号的 presets；改前把原值备份到 <key>.bak-ccd-env。key 不存在或结构对不上就报错停止。
(() => {
  const ACCT = %(acct_json)s;
  const PRESETS = %(presets)s;
  const key = 'persisted.ccd-session-presets.' + ACCT;
  const raw = localStorage.getItem(key);
  if (raw === null) {
    const near = Object.keys(localStorage).filter(k => k.includes('ccd-session-presets'));
    console.error('没有 ' + key + '，停止。现有相关 key：', near, '；当前 origin：', location.origin);
    return;
  }
  const obj = JSON.parse(raw);
  let target = null;                       // 第一个带 presets 数组的对象，通常是 obj.state
  (function walk(o) {
    if (!o || typeof o !== 'object' || target) return;
    if (Array.isArray(o.presets)) { target = o; return; }
    for (const v of Object.values(o)) walk(v);
  })(obj);
  if (!target) { console.error('值里没找到 presets 数组，停止。key=', key, raw.slice(0, 300)); return; }
  console.log('key =', key, '；当前 presets 数 =', target.presets.length);
  localStorage.setItem(key + '.bak-ccd-env', raw);
  target.presets = PRESETS;
  localStorage.setItem(key, JSON.stringify(obj));
  console.log('已写入', PRESETS.length, '个环境，1 秒后重载界面');
  setTimeout(() => location.reload(), 1000);
})();
"""


def merged(src_acct, dst_acct, data):
    """返回 (DST 新的一项, 说明) 或 (None, 跳过原因)。"""
    by = data.get('byAccount', {})
    s = by.get(src_acct)
    if not s or not s.get('presets'):
        return None, 'SRC 没有环境，跳过'
    d = by.get(dst_acct) or {'presets': []}
    src_ids = {p['id'] for p in s['presets']}
    keep = [p for p in d.get('presets', []) if p['id'] not in src_ids]
    out = {**d, 'presets': list(s['presets']) + keep}
    if s.get('builtIns') is not None:
        out['builtIns'] = s['builtIns']
    added = len(src_ids - {p['id'] for p in d.get('presets', [])})
    return out, (f"环境: DST {len(d.get('presets', []))} -> {len(out['presets'])}"
                 f"（新增 {added}，DST 独有保留 {len(keep)}）")


def write_js(dst_acct, entry):
    if len(entry['presets']) > MAX:
        raise ValueError(f"{len(entry['presets'])} 个，超过 CCD 上限 {MAX}")
    with open(JS_OUT, 'w') as fh:
        fh.write(JS % {'acct': dst_acct, 'acct_json': json.dumps(dst_acct),
                       'presets': json.dumps(entry['presets'], ensure_ascii=False)})
    return JS_OUT


def main(src, dst, go, catalog=None):
    tag = '' if go else '[dry] '
    da = dst.split('/')[0]
    if catalog:
        entry = json.load(open(catalog))
        print(f"{tag}环境: DST 将整份换成 {os.path.basename(catalog)} 里的 {len(entry['presets'])} 个")
    else:
        data = json.load(open(PATH)) if os.path.exists(PATH) else {}
        entry, note = merged(src.split('/')[0], da, data)
        print(f'{tag}{note}')
        if entry is None:
            return
    if go:
        out = write_js(da, entry)
        print(f'已生成 {out}。在 CCD 里右键 → Inspect Element → Console（连在 https://claude.ai），'
              f'粘贴整段执行；界面重载后用 {os.path.basename(PATH)} 里 DST 的数量复核。')


if __name__ == '__main__':
    argv = sys.argv[1:]
    go = '--go' in argv
    cat = None
    if '--catalog' in argv:
        i = argv.index('--catalog')
        cat = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    a = [x for x in argv if x != '--go']
    if (cat and len(a) != 1) or (not cat and len(a) != 2):
        sys.exit(__doc__)
    main(None if cat else a[0], a[-1], go, cat)

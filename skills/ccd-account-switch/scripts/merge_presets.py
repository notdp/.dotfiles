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
复查还是 9，几小时后又被写回 0。所以只拿文件当"读"的来源（SRC 的环境从镜像里读），写入走页面存储，两条路：

1. 自动（--go 默认）：起一个脱离 CCD 进程组的守护进程，等用户 Cmd+Q、CCD 主进程真正退出后，
   先把 Local Storage/leveldb 整目录备份到 ~/.claude/ccd-ls-backup-<时间>，再用 lsset.mjs
   （node + classic-level，首次自动装到 ~/.cache/ccd-account-switch/node）直接改 LevelDB 里
   persisted.ccd-session-presets.<DST> 的 presets，然后 open -a Claude，等页面把镜像文件刷新后
   比对环境 id 复核。日志 ~/.claude/ccd-preset-apply.log，最后一行是 OK 或 FALLBACK。
   CCD 开着时 LevelDB 有 LOCK，lsset 打不开就什么都不写——用户抢先手动重开也安全。
   读回不一致会从备份整目录还原。2026-10-19：编码在副本上读写过，并用独立的 headless Chrome
   读回验证（118 个 key 都在、改的值读得出）；对真实 CCD 的整条链还没跑过。
2. 手动兜底：同时生成 ~/.claude/ccd-restore-env.js。自动那条失败（日志 FALLBACK）时，让用户在
   CCD 里右键 → Inspect Element → Console（连在 https://claude.ai）粘贴执行：备份原值到
   <key>.bak-ccd-env，只替换该账号的 presets，重载界面。需要 developer_settings.json 里
   allowDevTools 为 true。

用法:
  merge_presets.py <SRC> <DST>                 # 看合并结果
  merge_presets.py <SRC> <DST> --go            # 起守护进程自动写，并生成兜底 JS
  merge_presets.py --catalog <file> <DST> --go # 同上，但 DST 那一项用 file 里的（{"presets": [...]}）
  merge_presets.py ... --go --manual           # 只生成兜底 JS，不起守护进程
SRC/DST 都是 <accountUuid>/<orgUuid>（只用前半段）。
"""
import json
import os
import shutil
import subprocess
import sys
import time

PATH = os.path.expanduser('~/Library/Application Support/Claude/ccd-session-presets.json')
JS_OUT = os.path.expanduser('~/.claude/ccd-restore-env.js')
HERE = os.path.dirname(os.path.abspath(__file__))
E = os.environ.get          # 下面几个可用环境变量覆盖，只为测试
LS_DIR = E('CCD_LS_DIR', os.path.expanduser('~/Library/Application Support/Claude/Local Storage/leveldb'))
CCD_BIN = E('CCD_BIN', '/Applications/Claude.app/Contents/MacOS/Claude')
OPEN_CMD = E('CCD_OPEN', 'open -a Claude').split()
MIRROR = E('CCD_MIRROR', None)
DEP_DIR = os.path.expanduser('~/.cache/ccd-account-switch/node')
LOG = os.path.expanduser(E('CCD_PRESET_LOG', '~/.claude/ccd-preset-apply.log'))
PENDING = os.path.expanduser('~/.claude/ccd-preset-pending.json')
WAIT = int(E('CCD_WAIT', str(12 * 3600)))       # 最多等 12 小时
RECHECK = int(E('CCD_RECHECK', '45'))            # 重开后等页面刷新镜像的秒数
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


def log(msg):
    with open(LOG, 'a') as fh:
        fh.write(time.strftime('%m-%d %H:%M:%S ') + msg + '\n')


def ccd_running():
    out = subprocess.run(['ps', '-axo', 'comm='], capture_output=True, text=True).stdout
    return any(line.strip() == CCD_BIN for line in out.splitlines())


def ensure_dep():
    """node + classic-level。返回 node 绝对路径，装不上返回 None。"""
    node, npm = shutil.which('node'), shutil.which('npm')
    if not node or not npm:
        return None
    if not os.path.isdir(os.path.join(DEP_DIR, 'node_modules', 'classic-level')):
        os.makedirs(DEP_DIR, exist_ok=True)
        r = subprocess.run([npm, 'i', '--silent', '--prefix', DEP_DIR, 'classic-level@1.4.1'],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print('装 classic-level 失败:', (r.stderr or r.stdout).strip()[-300:])
            return None
    return node


def daemon(node, dst_acct, presets):
    """脱离 CCD 进程组；等 CCD 退出 → 备份 → 写 LevelDB → 重开 → 复核。"""
    with open(PENDING, 'w') as fh:
        json.dump(presets, fh, ensure_ascii=False)
    pid = os.fork()
    if pid:
        os.waitpid(pid, 0)
        return
    os.setsid()
    if os.fork():
        os._exit(0)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    fallback = f'FALLBACK：在 CCD 控制台粘贴 {JS_OUT}'
    try:
        log(f'守护 pid={os.getpid()} 等 CCD 退出，DST={dst_acct[:8]}，{len(presets)} 个环境')
        t0 = time.time()
        while ccd_running():
            if time.time() - t0 > WAIT:
                log('CCD 一直没退出，放弃，什么都没写。' + fallback)
                os._exit(0)
            time.sleep(2)
        time.sleep(3)
        backup = os.path.expanduser(time.strftime('~/.claude/ccd-ls-backup-%m%d-%H%M%S'))
        shutil.copytree(LS_DIR, backup, ignore=shutil.ignore_patterns('LOCK'))
        r = subprocess.run([node, os.path.join(HERE, 'lsset.mjs'), DEP_DIR, LS_DIR, dst_acct, PENDING],
                           capture_output=True, text=True, timeout=120)
        res = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[-300:]
        if r.returncode == 5:
            shutil.rmtree(LS_DIR)
            shutil.copytree(backup, LS_DIR)
            log(f'写入后读回不一致，已从 {backup} 还原。{fallback}')
        elif r.returncode != 0:
            log(f'没写（lsset 退出码 {r.returncode}: {res}）。{fallback}')
        else:
            log(f'已写 LevelDB: {res}；备份 {backup}')
        subprocess.run(OPEN_CMD)
        if r.returncode != 0:
            os._exit(0)
        time.sleep(RECHECK)
        mirror = MIRROR or os.path.expanduser('~/Library/Application Support/Claude/ccd-session-presets.json')
        got = json.load(open(mirror)).get('byAccount', {}).get(dst_acct, {}).get('presets', [])
        want = {p['id'] for p in presets}
        if {p['id'] for p in got} == want:
            log(f'OK：重开 {RECHECK}s 后镜像里 DST 有 {len(got)} 个环境，和写入的一致')
        else:
            log(f'镜像里 DST 是 {len(got)} 个，期望 {len(want)}（页面可能还没刷新，去环境选择器看一眼）。'
                f'不对的话 {fallback}')
    except Exception as e:  # noqa: BLE001
        log(f'守护出错: {e!r}。{fallback}')
    os._exit(0)


def main(src, dst, go, catalog=None, manual=False):
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
        node = None if manual else ensure_dep()
        if node:
            daemon(node, da, entry['presets'])
            print(f'环境：已起守护进程，Cmd+Q 后自动写入并重开 CCD，结果看 {LOG} 最后一行（OK / FALLBACK）。'
                  f'兜底脚本 {out}。')
        else:
            print(f'环境：没法自动写（{"指定了 --manual" if manual else "node / classic-level 不可用"}），'
                  f'重启后在 CCD 里右键 → Inspect Element → Console（连在 https://claude.ai）粘贴 {out}。')

if __name__ == '__main__':
    argv = sys.argv[1:]
    go = '--go' in argv
    manual = '--manual' in argv
    argv = [x for x in argv if x != '--manual']
    cat = None
    if '--catalog' in argv:
        i = argv.index('--catalog')
        cat = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    a = [x for x in argv if x != '--go']
    if (cat and len(a) != 1) or (not cat and len(a) != 2):
        sys.exit(__doc__)
    main(None if cat else a[0], a[-1], go, cat, manual)

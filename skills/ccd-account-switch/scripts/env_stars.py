#!/usr/bin/env python3
"""环境 star 的快照与写回。

环境选择器里的 Starred 存在 claude.ai 页面的 IndexedDB：
keyval-store / keyval / "store:pin-state:epitaxy-starred-environments"，
值是 JSON 字符串 {"state":{"starredIds":["machine-preset:<环境 id>", ...]},"version":0,"updatedAt":...}。
**切号时页面会把整个 IndexedDB 清空重建**（2026-10-19 18:51 实测：库里最早一条记录就是切号那刻），
所以 star 只能在切号之前存下来，传火在切号之后才跑，那时已经读不到了。

- snapshot：由常驻的 watch_stars.mjs 在 star 变化后调用（launchd KeepAlive 拉起；不是轮询）。
  从 config.json 的 lastKnownAccountUuid 认当前账号，先直接从 IndexedDB 原始文件里读最新的 star 记录
  （快路径：key 是大端 UTF-16，后面跟着 JSON 字符串），读不到再拷一份用同版本 Electron 读，
  按账号存进 ~/.claude/ccd-env-stars.json。读到空列表而已有非空快照时不覆盖
  （切号瞬间 config 可能还是旧账号、库已经清空）。
- restore <SRC>：只能在 CCD 退出后跑（merge_presets 的守护进程在写完环境、重开 CCD 之前调用）。
  备份 IndexedDB → 拷到临时 userData → 同版本 Electron 把 SRC 快照里的 star 并进去 → 读回确认 →
  替换真实目录；任何一步失败都不替换，替换出错从备份还原。
- install / uninstall：装/卸 launchd 常驻任务 ~/Library/LaunchAgents/<LABEL>.plist（跑 watch_stars.mjs）。
- show：打印快照。

Electron 版本必须跟 CCD 内置的一致（版本更高的 Chromium 可能升级库格式）：自动从
Electron Framework 里读版本号，按需装到 ~/.cache/ccd-account-switch/electron-<版本>。
2026-10-20 实测：真实 CCD 退出后写回 5 个 star，重开后 Starred 显示 6 个。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.expanduser('~/Library/Application Support/Claude')
IDB = os.environ.get('CCD_IDB_DIR', os.path.join(APP, 'IndexedDB'))          # 环境变量只为测试
NAMES = ['https_claude.ai_0.indexeddb.leveldb', 'https_claude.ai_0.indexeddb.blob']
KEY = 'store:pin-state:epitaxy-starred-environments'
STORE = os.path.expanduser(os.environ.get('CCD_STARS_STORE', '~/.claude/ccd-env-stars.json'))
LOG = os.path.expanduser(os.environ.get('CCD_STARS_LOG', '~/.claude/ccd-env-stars.log'))
FRAMEWORK = '/Applications/Claude.app/Contents/Frameworks/Electron Framework.framework/Electron Framework'
CACHE = os.path.expanduser('~/.cache/ccd-account-switch')
LABEL = 'com.ccd-account-switch.env-stars'
PLIST = os.path.expanduser(f'~/Library/LaunchAgents/{LABEL}.plist')
CCD_BIN = os.environ.get('CCD_BIN', '/Applications/Claude.app/Contents/MacOS/Claude')


def log(msg):
    with open(LOG, 'a') as fh:
        fh.write(time.strftime('%m-%d %H:%M:%S ') + msg + '\n')


def ccd_running():
    out = subprocess.run(['ps', '-axo', 'comm='], capture_output=True, text=True).stdout
    return any(line.strip() == CCD_BIN for line in out.splitlines())


def electron_version():
    with open(FRAMEWORK, 'rb') as fh:
        m = re.search(rb'Electron/(\d+\.\d+\.\d+)', fh.read())
    return m.group(1).decode() if m else None


def ensure_electron():
    """返回同版本 Electron 可执行文件路径，装不上返回 None。"""
    ver = electron_version()
    npm = shutil.which('npm') or '/opt/homebrew/bin/npm'
    if not ver or not os.path.exists(npm):
        return None
    d = os.path.join(CACHE, f'electron-{ver}')
    exe = os.path.join(d, 'node_modules/electron/dist/Electron.app/Contents/MacOS/Electron')
    if not os.path.exists(exe):
        os.makedirs(d, exist_ok=True)
        env = dict(os.environ, PATH=os.path.dirname(npm) + ':' + os.environ.get('PATH', '/usr/bin:/bin'))
        r = subprocess.run([npm, 'i', '--silent', '--prefix', d, f'electron@{ver}'],
                           capture_output=True, text=True, timeout=900, env=env)
        if not os.path.exists(exe):        # 实测 npm 有时不跑 electron 的 postinstall，手动补一次下载
            node = shutil.which('node', path=env['PATH']) or 'node'
            subprocess.run([node, os.path.join(d, 'node_modules/electron/install.js')],
                           capture_output=True, text=True, timeout=900, env=env, cwd=d)
        if r.returncode != 0 or not os.path.exists(exe):
            log(f'装 electron@{ver} 失败: {(r.stderr or r.stdout).strip()[-300:]}')
            return None
    return exe


def run_idbset(exe, userdata, *args):
    r = subprocess.run([exe, os.path.join(HERE, 'idbset.js'), userdata, *args],
                       capture_output=True, text=True, timeout=120)
    line = next((l for l in r.stdout.splitlines() if l.startswith('{')), None)
    if not line:
        raise RuntimeError(f'idbset 没有输出 exit={r.returncode} {r.stderr.strip()[-300:]}')
    return json.loads(line)


def copy_idb(dst_root):
    os.makedirs(os.path.join(dst_root, 'IndexedDB'), exist_ok=True)
    for n in NAMES:
        src = os.path.join(IDB, n)
        if os.path.exists(src):
            shutil.copytree(src, os.path.join(dst_root, 'IndexedDB', n), ignore=shutil.ignore_patterns('LOCK'))


def ids_of(value):
    if not value:
        return []
    return (json.loads(value).get('state') or {}).get('starredIds') or []


REC = re.compile(rb'\{"state":\{"starredIds":\[([^\]]*)\]\},"version":\d+,"updatedAt":(\d+)\}')


def read_fast():
    """直接从 IndexedDB 原始文件里找最新的 star 记录。返回 ids 列表；找不到返回 None（交给 Electron）。"""
    key = KEY.encode('utf-16-be')
    best = None
    d = os.path.join(IDB, NAMES[0])
    for n in os.listdir(d) if os.path.isdir(d) else []:
        if not n.endswith(('.log', '.ldb')):
            continue
        try:
            b = open(os.path.join(d, n), 'rb').read()
        except OSError:
            continue
        for m in re.finditer(re.escape(key), b):
            j = REC.search(b[m.end():m.end() + 800])
            if j and (best is None or int(j.group(2)) >= best[0]):
                best = (int(j.group(2)), [x.decode() for x in re.findall(rb'"([^"]+)"', j.group(1))])
    return best[1] if best else None


def current_account():
    try:
        return json.load(open(os.path.join(APP, 'config.json'))).get('lastKnownAccountUuid')
    except (OSError, ValueError):
        return None


def load_store():
    try:
        return json.load(open(STORE))
    except (OSError, ValueError):
        return {}


def snapshot():
    acct = current_account()
    if not acct:
        log('快照跳过：认不出当前账号')
        return
    ids = read_fast()
    if ids is None:
        exe = ensure_electron()
        if not exe:
            log('快照跳过：快路径没读到，Electron 也不可用')
            return
        with tempfile.TemporaryDirectory(prefix='ccd-stars-') as tmp:
            copy_idb(tmp)
            ids = ids_of(run_idbset(exe, tmp, 'get', KEY)['before'])
    if acct != current_account():
        log('快照期间账号变了，丢弃这次结果')
        return
    store = load_store()
    old = (store.get(acct) or {}).get('ids') or []
    if not ids and old:
        log(f'快照 {acct[:8]}: 读到空列表，保留已有的 {len(old)} 个（可能正在切号）')
        return
    if ids != old:
        store[acct] = {'ids': ids, 'at': time.strftime('%Y-%m-%dT%H:%M:%S')}
        tmpf = STORE + '.tmp'
        json.dump(store, open(tmpf, 'w'), indent=1)
        os.replace(tmpf, STORE)
        log(f'快照 {acct[:8]}: {len(ids)} 个 star')


def restore(src_acct):
    """把 SRC 账号快照里的 star 并进当前 IndexedDB。返回一行结果说明。CCD 必须已退出。"""
    if ccd_running():
        return 'star 没写：CCD 还在运行'
    want = (load_store().get(src_acct) or {}).get('ids') or []
    if not want:
        return f'star 没写：没有 {src_acct[:8]} 的快照（launchd 快照任务装了吗？）'
    exe = ensure_electron()
    if not exe:
        return 'star 没写：同版本 Electron 不可用'
    ts = time.strftime('%m%d-%H%M%S')
    backup = os.path.expanduser(os.environ.get('CCD_IDB_BACKUP_ROOT', '~/.claude') + f'/ccd-idb-backup-{ts}')
    copy_idb(backup)
    with tempfile.TemporaryDirectory(prefix='ccd-stars-') as tmp:
        copy_idb(tmp)
        ids_file = os.path.join(tmp, 'ids.json')
        json.dump(want, open(ids_file, 'w'))
        after = ids_of(run_idbset(exe, tmp, 'merge', KEY, ids_file)['after'])
        if not all(x in after for x in want):
            return f'star 没写：写入后读回不含全部 {len(want)} 个'
        try:
            for n in NAMES:
                new, dst = os.path.join(tmp, 'IndexedDB', n), os.path.join(IDB, n)
                if os.path.exists(new):
                    shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(new, dst)
        except Exception as e:  # noqa: BLE001
            for n in NAMES:
                dst = os.path.join(IDB, n)
                shutil.rmtree(dst, ignore_errors=True)
                if os.path.exists(os.path.join(backup, 'IndexedDB', n)):
                    shutil.copytree(os.path.join(backup, 'IndexedDB', n), dst)
            return f'star 没写：替换出错 {e!r}，已从 {backup} 还原'
    return f'已写回 {len(want)} 个 star（合并后 {len(after)} 个）；IndexedDB 备份 {backup}'


def install():
    node = shutil.which('node') or '/opt/homebrew/bin/node'
    py = shutil.which('python3') or '/usr/bin/python3'
    base = os.path.expanduser('~/.claude/skills/ccd-account-switch/scripts')
    ensure_electron()                       # restore 要用，提前装好
    plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{node}</string><string>{base}/watch_stars.mjs</string><string>{py}</string><string>{base}/env_stars.py</string></array>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardErrorPath</key><string>{LOG}</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict></plist>
'''
    os.makedirs(os.path.dirname(PLIST), exist_ok=True)
    open(PLIST, 'w').write(plist)
    uid = os.getuid()
    subprocess.run(['launchctl', 'bootout', f'gui/{uid}/{LABEL}'], capture_output=True)
    r = subprocess.run(['launchctl', 'bootstrap', f'gui/{uid}', PLIST], capture_output=True, text=True)
    print(f'launchd 任务 {LABEL}：{"已装" if r.returncode == 0 else "装失败 " + r.stderr.strip()}'
          f'（常驻监听 star 变化，日志 {LOG}）')


def uninstall():
    subprocess.run(['launchctl', 'bootout', f'gui/{os.getuid()}/{LABEL}'], capture_output=True)
    if os.path.exists(PLIST):
        os.remove(PLIST)
    print('已卸载', LABEL)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'snapshot':
        try:
            snapshot()
        except Exception as e:  # noqa: BLE001
            log(f'快照出错: {e!r}')
    elif cmd == 'restore' and len(sys.argv) == 3:
        print(restore(sys.argv[2]))
    elif cmd == 'install':
        install()
    elif cmd == 'uninstall':
        uninstall()
    elif cmd == 'show':
        print(json.dumps(load_store(), indent=1, ensure_ascii=False))
    else:
        sys.exit(__doc__)

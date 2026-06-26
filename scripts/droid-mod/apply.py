#!/usr/bin/env python3
"""droid-mod 入口: 备份 → 移除签名 → 应用 mod → 补偿 → 签名

用法:
    python3 apply.py              # 应用全部未修改的 mod
    python3 apply.py mod-cycle-custom-model,mod-extend-kitty-timeout
    python3 apply.py 1,3          # 用编号选
    python3 apply.py status       # 仅显示状态
    python3 apply.py restore      # 恢复备份

归档说明:
    已归档的 mod 保留在 mods/_archive/ 下，不再出现在列表中，也不再参与补偿计算。
    当前归档: mod-hide-command-truncation, mod-expand-diff-lines, mod-unlock-max-custom-effort
"""
import subprocess, sys, platform, shutil
from pathlib import Path

DROID = Path.home() / '.local/bin/droid'
DIR = Path(__file__).parent

MODS = [
    {
        'key': 'mod-cycle-custom-model',
        'id': '1',
        'script': 'mod_cycle_custom_model',
        'desc': 'Ctrl+N 直接切换 custom model',
    },
    {
        'key': 'mod-fix-multiline-history-down',
        'id': '2',
        'script': 'mod_fix_multiline_history_down',
        'desc': '修复多行历史按 ↓ 无法回到空输入框',
    },
    {
        'key': 'mod-highlight-welcome-modified',
        'id': '3',
        'script': 'mod_highlight_welcome_modified',
        'desc': 'Welcome/Header 高亮 Modified 标记',
    },
    {
        'key': 'mod-extend-kitty-timeout',
        'id': '5',
        'script': 'mod_extend_kitty_timeout',
        'desc': '将 kitty 检测超时扩到 999ms',
    },
]
MOD_KEYS = {m['key'] for m in MODS}
MOD_IDS = {m['id']: m['key'] for m in MODS}
IS_MAC = platform.system() == 'Darwin'


def get_version():
    r = subprocess.run([str(DROID), '--version'], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else 'unknown'


def backup():
    ver = get_version()
    dest = DROID.parent / f'droid.backup.{ver}'
    if not dest.exists():
        shutil.copy2(DROID, dest)
        print(f'  备份: {dest.name}')
    else:
        print(f'  备份已存在: {dest.name}')


def codesign_remove():
    if IS_MAC:
        subprocess.run(['codesign', '--remove-signature', str(DROID)],
                       capture_output=True)


def codesign_sign():
    if IS_MAC:
        subprocess.run(['codesign', '--remove-signature', str(DROID)],
                       capture_output=True)
        subprocess.run(['codesign', '-s', '-', str(DROID)], check=True,
                       capture_output=True)


def run_status():
    subprocess.run([sys.executable, str(DIR / 'status.py')])


def run_restore():
    subprocess.run([sys.executable, str(DIR / 'restore.py')] + sys.argv[2:])


def run_mod(mod):
    script = DIR / 'mods' / f'{mod["script"]}.py'
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        print(f'  {line}')
    if r.stderr.strip():
        for line in r.stderr.strip().splitlines():
            print(f'  [err] {line}')
    return r.returncode == 0


def run_compensate(bytes_diff):
    if bytes_diff == 0:
        return True
    r = subprocess.run(
        [sys.executable, str(DIR / 'compensations' / 'comp_universal.py'), str(bytes_diff)],
        capture_output=True, text=True)
    for line in r.stdout.strip().splitlines():
        print(f'  {line}')
    if r.returncode != 0:
        for line in r.stderr.strip().splitlines():
            print(f'  [err] {line}')
        return False
    return True


def main():
    if not DROID.exists():
        print(f'错误: {DROID} 不存在')
        sys.exit(1)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'status':
            run_status()
            return
        if cmd == 'restore':
            run_restore()
            return

    # 解析 mod 选择
    selected = MOD_KEYS
    if len(sys.argv) > 1:
        tokens = [x.strip() for x in sys.argv[1].split(',') if x.strip()]
        selected = set()
        invalid = []
        for token in tokens:
            if token in MOD_KEYS:
                selected.add(token)
            elif token in MOD_IDS:
                selected.add(MOD_IDS[token])
            else:
                invalid.append(token)
        if invalid:
            print(f'错误: 未知 mod {invalid}，可选: {sorted(MOD_KEYS)}')
            print(f'编号: {sorted(MOD_IDS)}')
            sys.exit(1)
        if not selected:
            print(f'用法: {sys.argv[0]} [status|restore|mod-cycle-custom-model,...|1,2,...]')
            sys.exit(1)

    ver = get_version()
    print(f'droid v{ver}\n')

    # 1. 备份
    print('[1/4] 备份')
    backup()

    # 2. 移除签名
    print('[2/4] 移除签名')
    codesign_remove()
    print('  done' if IS_MAC else '  跳过 (非 macOS)')

    # 3. 应用 mod
    print('[3/4] 应用修改')
    size_before = DROID.stat().st_size
    ok, fail = 0, 0
    for mod in MODS:
        if mod['key'] not in selected:
            continue
        print(f'  {mod["key"]}: {mod["desc"]}')
        if run_mod(mod):
            ok += 1
        else:
            fail += 1
    size_after = DROID.stat().st_size
    byte_diff = size_after - size_before
    print(f'  完成 {ok} 个' + (f', 失败 {fail} 个' if fail else '') +
          (f', 字节变化 {byte_diff:+d}' if byte_diff else ''))

    # 任一 mod 失败 → 二进制可能处于半改状态；从备份恢复并中止，不补偿、不签名、非 0 退出。
    if fail:
        print(f'\n{fail} 个 mod 应用失败，从备份恢复并中止（不补偿、不签名）。')
        run_restore()
        sys.exit(1)

    # 4. 补偿 + 签名
    print('[4/4] 补偿 + 签名')
    comp_ok = True
    if byte_diff > 0:
        comp_ok = run_compensate(byte_diff)
    elif byte_diff == 0:
        print('  无需补偿')
    else:
        print(f'  警告: 字节减少 {byte_diff}，跳过补偿')

    if not comp_ok:
        print(f'\n补偿失败，从备份恢复...')
        run_restore()
        sys.exit(1)

    codesign_sign()
    print('  签名完成' if IS_MAC else '  跳过签名 (非 macOS)')

    print(f'\n完成。新开 droid 窗口验证。')


if __name__ == '__main__':
    main()

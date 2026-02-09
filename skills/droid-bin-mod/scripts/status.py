#!/usr/bin/env python3
"""检查 droid 当前状态：原版/已修改/部分修改"""
import re
from pathlib import Path

droid = Path.home() / '.local/bin/droid'
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'

with open(droid, 'rb') as f:
    data = f.read()

results = {}

# mod1: 截断条件
if b'if(!0||!' in data:
    results['mod1'] = 'modified'
elif b'isTruncated:!1}' in data:
    results['mod1'] = 'original'
else:
    results['mod1'] = 'unknown'

# mod2: 命令阈值
if b'command.length>99' in data:
    results['mod2'] = 'modified'
elif b'command.length>50' in data:
    results['mod2'] = 'original'
else:
    results['mod2'] = 'unknown'

# mod3+mod5: 输出行数 (VAR=4/99,VAR2=5,VAR3=200)
if re.search(V + rb'=99,' + V + rb'=5,' + V + rb'=200', data):
    results['mod3'] = 'modified'
    results['mod5'] = 'modified'
elif re.search(V + rb'=4,' + V + rb'=5,' + V + rb'=200', data):
    results['mod3'] = 'original'
    results['mod5'] = 'original'
else:
    results['mod3'] = 'unknown'
    results['mod5'] = 'unknown'

# mod4: diff行数
if re.search(rb'var ' + V + rb'=99,' + V + rb',', data):
    results['mod4'] = 'modified'
elif re.search(rb'var ' + V + rb'=20,' + V + rb',', data):
    results['mod4'] = 'original'
else:
    results['mod4'] = 'unknown'

# mod6: custom model cycle
def _mod6_detect_fn(data, fn_name: bytes, getter: bytes, *, window: int = 800):
    # 既要兼容 original 也要兼容 modified（modified 会在 { 后插入 PARAM=...;）
    sig_pat = fn_name + rb'\((' + V + rb')\)\{'
    matches = list(re.finditer(sig_pat, data))
    if not matches:
        return 'unknown'

    m_best = None
    for m in matches:
        region = data[m.start():m.start() + window]
        # 通过 getter 进一步确认是目标函数
        if b'return this.' + getter + b'()' in region:
            m_best = m
            break
    if m_best is None:
        m_best = matches[0]

    param = m_best.group(1)
    region = data[m_best.start():m_best.start() + window]

    # modified: cycleModel(H){H=this.customModels.map(m=>m.id);if(...)
    modified_prefix = fn_name + b'(' + param + b'){' + param + b'=this.customModels.map(m=>m.id);if('
    if modified_prefix in region:
        return 'modified'

    # original: if(!this.validateModelAccess(D).allowed)continue;
    if b'if(!this.validateModelAccess(' in region:
        return 'original'

    return 'unknown'


cm = _mod6_detect_fn(data, b'cycleModel', b'getModel')
csm = _mod6_detect_fn(data, b'cycleSpecModeModel', b'getSpecModeModel')
if cm == 'modified' and csm == 'modified':
    results['mod6'] = 'modified'
elif cm == 'original' and csm == 'original':
    results['mod6'] = 'original'
else:
    results['mod6'] = 'unknown'

# 输出
total = 6
mod_count = sum(1 for v in results.values() if v == 'modified')
orig_count = sum(1 for v in results.values() if v == 'original')

print(f"droid 状态:\n")
for name, status in results.items():
    icon = '✓' if status == 'modified' else '○' if status == 'original' else '?'
    label = {'modified': '已修改', 'original': '原版', 'unknown': '未知'}[status]
    note = ' (由 mod3 控制)' if name == 'mod5' else ''
    print(f"  {icon} {name}: {label}{note}")

print()
if mod_count == total:
    print("结论: 已修改")
elif orig_count == total:
    print("结论: 原版")
else:
    print(f"结论: 部分修改 ({mod_count}/{total})")

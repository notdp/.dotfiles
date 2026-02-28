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
# 检测 peekNextCycleModel, peekNextCycleSpecModeModel, cycleSpecModeModel
def _mod6_detect():
    targets = [b'peekNextCycleModel', b'peekNextCycleSpecModeModel', b'cycleSpecModeModel']
    modified = original = 0
    for fn in targets:
        for m in re.finditer(fn + rb'\(' + V + rb'\)\{', data):
            region = data[m.start():m.start() + 600]
            if b'=this.customModels.map(m=>m.id)' in region:
                modified += 1
            elif b'validateModelAccess(' in region:
                original += 1
    if modified > 0 and original == 0:
        return 'modified'
    elif original > 0 and modified == 0:
        return 'original'
    return 'unknown'

results['mod6'] = _mod6_detect()

# mod7: mission 门控
if b'statsigName:"enable_extra_mod0",defaultValue:!0' in data:
    results['mod7'] = 'modified'
elif b'statsigName:"enable_extra_mode",defaultValue:!1' in data:
    results['mod7'] = 'original'
else:
    results['mod7'] = 'unknown'

# mod8: mission 模型白名单
if b'Y9H={includes:()=>!0}' in data:
    results['mod8'] = 'modified'
elif b'Y9H=["gpt-' in data:
    results['mod8'] = 'original'
else:
    results['mod8'] = 'unknown'

# 输出
total = 8
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

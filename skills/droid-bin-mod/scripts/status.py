#!/usr/bin/env python3
"""检查 droid 当前状态：原版/已修改/部分修改"""
from pathlib import Path

droid = Path.home() / '.local/bin/droid'

with open(droid, 'rb') as f:
    data = f.read()

# 用语义数字检测 (这些数字有含义，升级后通常不变)
# mod1: 检测短路条件 !0|| (修改后) vs &&! (原版)
# mod2: command.length>99 (修改后) vs >50 (原版)
# mod3b: =8, (修改后) vs =80, (原版)，配合 =3) 确认是截断函数
# mod4: =99, (修改后) vs =20, (原版)，配合 var 和后面跟变量声明

results = {}

# mod1: 截断条件
if b'if(!0||!' in data:
    results['mod1'] = 'modified'
elif b'isTruncated:!1}' in data:  # 用不变的字符串确认函数存在
    results['mod1'] = 'original'
else:
    results['mod1'] = 'unknown'

# mod2: 命令阈值 (command.length 是不变的)
if b'command.length>99' in data:
    results['mod2'] = 'modified'
elif b'command.length>50' in data:
    results['mod2'] = 'original'
else:
    results['mod2'] = 'unknown'

# mod3b: 字节补偿 (80和3是截断参数，全局唯一组合)
if b'=80,' in data and b'=3)' in data:
    results['mod3b'] = 'original'
elif b'=8,' in data and b'=3)' in data:
    results['mod3b'] = 'modified'
else:
    results['mod3b'] = 'unknown'

# mod4: diff行数 (检测 =20, 或 =99, 配合 var 声明上下文)
# 用 exec-preview 附近的特征来间接判断
import re
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'
if re.search(rb'var ' + V + rb'=99,' + V + rb',', data):
    results['mod4'] = 'modified'
elif re.search(rb'var ' + V + rb'=20,' + V + rb',', data):
    results['mod4'] = 'original'
else:
    results['mod4'] = 'unknown'

# 输出
mod_count = sum(1 for v in results.values() if v == 'modified')
orig_count = sum(1 for v in results.values() if v == 'original')

print(f"droid 状态:\n")
for name, status in results.items():
    icon = '✓' if status == 'modified' else '○' if status == 'original' else '?'
    label = {'modified': '已修改', 'original': '原版', 'unknown': '未知'}[status]
    print(f"  {icon} {name}: {label}")

print()
if mod_count == 4:
    print("结论: 已修改")
elif orig_count == 4:
    print("结论: 原版")
else:
    print(f"结论: 部分修改 ({mod_count}/4)")

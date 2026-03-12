#!/usr/bin/env python3
"""mod4: diff显示行数 20→99 行 (0 bytes)

var VAR=20,VAR= 用 Interrupted 锚点定位
"""
import sys, re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

if re.search(rb'var ' + V + rb'=99,' + V, data):
    print("mod4 已应用，跳过")
    sys.exit(0)

matches = list(re.finditer(rb'var (' + V + rb')=20,(' + V + rb')', data))
if not matches:
    print("mod4 失败: 未找到 var VAR=20,VAR")
    sys.exit(1)

best = None
for m in matches:
    region = data[m.start():m.start()+200]
    if b'Interrupted' in region:
        best = m
        break
if not best:
    if len(matches) > 1:
        print(f"警告: 找到 {len(matches)} 处 var VAR=20，用第1处")
    best = matches[0]

var1 = best.group(1)
old = b'var ' + var1 + b'=20,'
new = b'var ' + var1 + b'=99,'
data = data.replace(old, new, 1)

if len(data) != original_size:
    print(f"警告: 大小变化 {len(data) - original_size:+d} bytes")

save_droid(data)
print(f"mod4 diff行数: {var1.decode()}=20 → {var1.decode()}=99 (0 bytes)")
print("mod4 完成")

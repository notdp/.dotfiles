#!/usr/bin/env python3
"""mod3: 输出预览行数 → 99 行 (0 bytes, 同时解决 mod5)

renderResult 中 VAR=VAR?8:4 → VAR=99||4
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()

if re.search(V + rb'=99\|\|4', data):
    print("mod3 已应用，跳过")
    sys.exit(0)

pattern = rb'(' + V + rb')=(' + V + rb')\?8:4'
matches = list(re.finditer(pattern, data))
if not matches:
    print("mod3 失败: 未找到 VAR=VAR?8:4")
    sys.exit(1)

best = None
for m in matches:
    region = data[max(0, m.start()-200):m.start()]
    if b'renderResult' in region or b'xR()' in region:
        best = m
        break
if not best:
    best = matches[0]

old = best.group(0)
var_d, var_b = best.group(1), best.group(2)
new = var_d + b'=99||4'
data = data.replace(old, new, 1)
save_droid(data)
print(f"mod3 输出行数: {var_d.decode()}={var_b.decode()}?8:4 → {var_d.decode()}=99||4 (0 bytes)")
print("mod3 完成 (同时解决 mod5)")

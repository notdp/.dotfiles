#!/usr/bin/env python3
"""mod3: 输出预览行数 → 99 行

v0.96.0-0.99.x: renderResult 中 VAR=VAR?8:4 → VAR=99||4 (0 bytes)
v0.104.0+:      bXH({maxLines:R?Y1A:8, ...}) → maxLines:R?Y1A:99 (+3 bytes × 3处 = +9 bytes)

自动探测版本格式，选择正确的 patch 路径。
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

# ─── 路径 A: 0.104.0+ 使用 bXH/maxLines 模式 ─────────────────────────────
# maxLines:VAR?VAR:8 (折叠视图 8 行) → maxLines:VAR?VAR:99 (折叠视图 99 行)
pat_new = re.compile(rb'(maxLines:[a-zA-Z0-9_$]{1,4}\?[a-zA-Z0-9_$]{1,4}):8')
matches_new = list(pat_new.finditer(data))

# 已应用检测
if re.search(rb'maxLines:[a-zA-Z0-9_$]{1,4}\?[a-zA-Z0-9_$]{1,4}:99', data):
    print("mod3 (maxLines) 已应用，跳过")
    sys.exit(0)

if matches_new:
    new_data, count = pat_new.subn(rb'\1:99', data)
    delta = len(new_data) - original_size
    print(f"mod3 (bXH/maxLines, 0.104.0+): {count} 处替换 (+{delta} bytes)")
    save_droid(new_data)
    print("mod3 完成")
    sys.exit(0)

# ─── 路径 B: 0.96.0-0.99.x 旧 VAR=VAR?8:4 模式 ──────────────────────────
if re.search(V + rb'=99\|\|4', data):
    print("mod3 (旧格式) 已应用，跳过")
    sys.exit(0)

pattern_old = rb'(' + V + rb')=(' + V + rb')\?8:4'
matches_old = list(re.finditer(pattern_old, data))
if not matches_old:
    print("mod3 失败: 未找到 maxLines:VAR?VAR:8 (0.104.0+) 或 VAR=VAR?8:4 (0.99.x)")
    sys.exit(1)

best = None
for m in matches_old:
    region = data[max(0, m.start()-200):m.start()]
    if b'renderResult' in region or b'xR()' in region:
        best = m
        break
if not best:
    best = matches_old[0]

old = best.group(0)
var_d, var_b = best.group(1), best.group(2)
new = var_d + b'=99||4'
data = data.replace(old, new, 1)
save_droid(data)
print(f"mod3 (旧格式, 0.99.x): {var_d.decode()}={var_b.decode()}?8:4 → {var_d.decode()}=99||4 (0 bytes)")
print("mod3 完成")

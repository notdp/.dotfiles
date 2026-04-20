#!/usr/bin/env python3
"""mod4: diff显示行数 20→99 行 (0 bytes)

v0.74+: kGH() 函数使用 uhf=20,Jhf=2000 作为参数默认值
v0.49+: var XX=20,YY, 模式
"""
import sys, re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

# --- 检查已应用 ---
# v0.74+ 模式
if re.search(rb'var ' + V + rb'=99,' + V + rb'=2000', data):
    print("mod4 已应用 (v0.74+ 模式)，跳过")
    sys.exit(0)
# v0.49+ 模式
if re.search(rb'var ' + V + rb'=99,' + V + rb',', data):
    print("mod4 已应用 (v0.49+ 模式)，跳过")
    sys.exit(0)

# --- v0.74+ 模式: var uhf=20,Jhf=2000 (kGH 函数默认参数) ---
pattern_74 = rb'(var )(' + V + rb')=20,(' + V + rb'=2000)'
match = re.search(pattern_74, data)
if match:
    old = match.group(0)
    new = match.group(1) + match.group(2) + b'=99,' + match.group(3)
    assert len(old) == len(new), f"byte mismatch: {len(old)} vs {len(new)}"
    data = data.replace(old, new, 1)
    save_droid(data)
    print(f"mod4 diff行数 (v0.74+): {match.group(2).decode()}=20 → 99 (0 bytes)")
    print("mod4 完成")
    sys.exit(0)

# --- v0.49+ 模式: var XX=20,YY, ---
pattern_49 = rb'(var )(' + V + rb')=20,(' + V + rb'),'
match = re.search(pattern_49, data)
if match:
    old = match.group(0)
    new = match.group(1) + match.group(2) + b'=99,' + match.group(3) + b','
    assert len(old) == len(new), f"byte mismatch"
    data = data.replace(old, new, 1)
    save_droid(data)
    print(f"mod4 diff行数 (v0.49+): {match.group(2).decode()}=20 → 99 (0 bytes)")
    print("mod4 完成")
    sys.exit(0)

print("mod4 失败: 未找到 diff 行数配置")
sys.exit(1)

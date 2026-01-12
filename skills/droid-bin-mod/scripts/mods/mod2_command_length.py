#!/usr/bin/env python3
"""mod2: 命令显示阈值 50→99 字符 (0 bytes)"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, replace_one

data = load_droid()
original_size = len(data)

# command.length>50 → >99
data, _ = replace_one(
    data,
    rb'command\.length>(\d+)',
    lambda m: b'command.length>99',
    'mod2 命令阈值')

if len(data) != original_size:
    print(f"警告: 大小变化 {len(data) - original_size:+d} bytes")

save_droid(data)
print("mod2 完成")

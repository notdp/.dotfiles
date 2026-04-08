#!/usr/bin/env python3
"""mod13: 禁用自动更新，checkForUpdates() 直接返回 null (0 bytes)"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid

data = load_droid()
original_size = len(data)

ALREADY_APPLIED = b'checkForUpdates(){return null;/*'
if ALREADY_APPLIED in data:
    print("mod13 已应用，跳过")
    sys.exit(0)

ANCHOR = b'async checkForUpdates(){'
anchor_pos = data.find(ANCHOR)
if anchor_pos == -1:
    raise ValueError("未找到 async checkForUpdates(){")

body_start = anchor_pos + len(ANCHOR)
semicolon = data.index(b';', body_start)
old_stmt = data[body_start:semicolon + 1]

new_core = b'return null;'
padding = len(old_stmt) - len(new_core) - 4  # 4 = len("/**/")
if padding < 0:
    raise ValueError(f"原语句太短: {old_stmt!r} ({len(old_stmt)} bytes)")

new_stmt = new_core + b'/*' + b' ' * padding + b'*/'
assert len(new_stmt) == len(old_stmt), f"长度不匹配: {len(new_stmt)} != {len(old_stmt)}"

data = data[:body_start] + new_stmt + data[semicolon + 1:]
assert len(data) == original_size, f"mod13 大小变化 {len(data) - original_size:+d} bytes"

print(f"mod13: {old_stmt.decode('utf-8', errors='replace')} → {new_stmt.decode('utf-8', errors='replace')} (0 bytes)")
save_droid(data)
print("mod13 完成: checkForUpdates() 已短路，自动更新已禁用")

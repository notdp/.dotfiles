#!/usr/bin/env python3
"""mod8: Mission 模型白名单恒通过 (0 bytes)

将 Y9H 数组替换为 {includes:()=>!0}（空格填充至等长）。
Y9H.includes(任何值) 恒返回 true，一处改动同时解决:
1. enter-mission 不再强切模型（else 分支永不执行）
2. 模型切换警告不再因 custom model 触发（只保留 reasoning effort 检查）
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid

data = load_droid()
original_size = len(data)

# 定位 Y9H 数组定义
marker = b'Y9H=["gpt-'
pos = data.find(marker)
if pos == -1:
    if b'Y9H={includes:()=>!0}' in data:
        print("mod8 已应用，跳过")
        sys.exit(0)
    print("mod8 失败: 未找到 Y9H 数组定义")
    sys.exit(1)

# 提取完整数组: Y9H=[...]
start = pos + 4  # skip 'Y9H='
depth = 0
end = start
for i in range(start, start + 200):
    if data[i:i+1] == b'[':
        depth += 1
    elif data[i:i+1] == b']':
        depth -= 1
        if depth == 0:
            end = i + 1
            break

old_array = data[start:end]
new_obj = b'{includes:()=>!0}'
pad = len(old_array) - len(new_obj)
if pad < 0:
    print(f"mod8 失败: 替换对象 ({len(new_obj)}b) 比原数组 ({len(old_array)}b) 长")
    sys.exit(1)

replacement = new_obj + b' ' * pad

data = data[:start] + replacement + data[end:]

assert len(data) == original_size, f"大小变化 {len(data) - original_size:+d} bytes"
save_droid(data)
print(f"mod8 白名单恒通过: Y9H={old_array.decode()} → Y9H={new_obj.decode()} (+{pad} spaces, 0 bytes)")
print("mod8 完成")

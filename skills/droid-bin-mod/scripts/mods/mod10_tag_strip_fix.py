#!/usr/bin/env python3
"""mod10: 修复 ym9 tag 剥离函数找不到闭标签时截断全部后续内容的 bug (0 bytes)

Bug: ym9() 在渲染管道中剥离 <system-notification>/<system-reminder> 标签。
     当文本包含字面量开标签但无闭标签时（如 model 输出 `<system-notification>`），
     if(D<0){A=A.slice(0,B);break} 会从开标签位置截断一切后续内容。

Fix: A=A.slice(0,B) → A=A.slice(0  )
     slice(0) 返回原字符串，等于 no-op，找不到闭标签时保留原文。
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid

data = load_droid()
original_size = len(data)

old = b'if(D<0){A=A.slice(0,B);break}'
new = b'if(D<0){A=A.slice(0  );break}'

if new in data:
    print("mod10 已应用，跳过")
    sys.exit(0)

if old not in data:
    raise ValueError("mod10 目标未找到! ym9 函数可能已被修改或版本不同")

data = data.replace(old, new, 1)

assert len(data) == original_size, f"mod10 大小变化 {len(data) - original_size:+d} bytes"

save_droid(data)
print("mod10 完成: ym9 tag strip 找不到闭标签时不再截断")

"""共享工具函数"""
import re
from pathlib import Path

DROID_PATH = Path.home() / '.local/bin/droid'

# JS变量名模式 (适应任意混淆: A, aB, _x, $1, AB12 等)
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'

def load_droid():
    """加载 droid 二进制"""
    with open(DROID_PATH, 'rb') as f:
        return f.read()

def save_droid(data):
    """保存 droid 二进制"""
    with open(DROID_PATH, 'wb') as f:
        f.write(data)

def replace_one(data, pattern, replacer, name, near_marker=None, max_dist=500):
    """替换一处匹配，返回 (新data, 字节变化)"""
    matches = list(re.finditer(pattern, data))
    if not matches:
        raise ValueError(f"{name} 未找到!")
    
    if near_marker and len(matches) > 1:
        marker_pos = data.find(near_marker)
        if marker_pos == -1:
            raise ValueError(f"marker {near_marker} 未找到!")
        best = None
        for m in matches:
            dist = marker_pos - m.start()
            if 0 < dist < max_dist:
                if best is None or dist < (marker_pos - best.start()):
                    best = m
        if best is None:
            raise ValueError(f"{name} 在 marker 附近未找到!")
        matches = [best]
    elif len(matches) > 1:
        print(f"警告: {name} 找到 {len(matches)} 处，用第1处")
    
    old = matches[0].group(0)
    new = replacer(matches[0])
    new_data = data.replace(old, new, 1)
    diff = len(new) - len(old)
    print(f"{name}: {old} → {new} ({diff:+d} bytes)")
    return new_data, diff

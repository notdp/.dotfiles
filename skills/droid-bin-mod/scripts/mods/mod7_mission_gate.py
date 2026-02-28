#!/usr/bin/env python3
"""mod7: Mission 门控破解 (0 bytes)

修改 EnableAGIMode 定义:
- statsigName 末尾改一字符使 Statsig 查不到 key → 返回 undefined
- defaultValue !1→!0 使 ?? fallback 为 true
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid

data = load_droid()
original_size = len(data)

target  = b'statsigName:"enable_extra_mode",defaultValue:!1'
replace = b'statsigName:"enable_extra_mod0",defaultValue:!0'

assert len(target) == len(replace), "length mismatch"

pos = data.find(target)
if pos == -1:
    if data.find(b'statsigName:"enable_extra_mod0",defaultValue:!0') != -1:
        print("mod7 已应用，跳过")
        sys.exit(0)
    print("mod7 失败: 未找到 EnableAGIMode 定义")
    sys.exit(1)

data = data[:pos] + replace + data[pos+len(target):]

assert len(data) == original_size, f"大小变化 {len(data) - original_size:+d} bytes"
save_droid(data)
print(f"mod7 门控破解: enable_extra_mode → enable_extra_mod0, defaultValue !1→!0 (0 bytes)")
print("mod7 完成")

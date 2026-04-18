#!/usr/bin/env python3
"""mod10: 修复 tag 剥离函数找不到闭标签时截断全部后续内容的 bug (0 bytes)

Bug: <system-reminder>/<system-notification> 两个 tag 的剥离函数
     当文本含字面量开标签但无闭标签时，if(VAR<0){VAR=VAR.slice(0,VAR);break}
     会从开标签位置截断后续内容。

Fix: VAR=VAR.slice(0,VAR) → VAR=VAR.slice(0  )
     slice(0) 返回原字符串，等于 no-op，保留原文。

v0.99.x 及以下: 1 处 (硬编码变量 D/A/B)
v0.104.0+:      2 处（两个 tag 各一处，minified 变量变化）
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid

data = load_droid()
original_size = len(data)

# 兼容任意单字符变量命名的通用模式
pat = re.compile(rb'if\(([A-Za-z])<0\)\{([A-Za-z])=\2\.slice\(0,([A-Za-z])\);break\}')

# 先做已应用检测: 搜索被替换后的 no-op 形态 "slice(0  )"
fixed_pat = re.compile(rb'if\(([A-Za-z])<0\)\{([A-Za-z])=\2\.slice\(0  \);break\}')
already = len(list(fixed_pat.finditer(data)))
matches = list(pat.finditer(data))

if not matches and already > 0:
    print(f"mod10 已应用，跳过 ({already} 处)")
    sys.exit(0)

if not matches:
    raise ValueError("mod10 目标未找到! tag strip 函数可能已被重写")

applied = 0
for m in matches:
    cond_var = m.group(1)    # 如 D / h / A
    target_var = m.group(2)  # 如 A / T
    idx_var = m.group(3)     # 如 B / L / R
    old = b'if(' + cond_var + b'<0){' + target_var + b'=' + target_var + b'.slice(0,' + idx_var + b');break}'
    new = b'if(' + cond_var + b'<0){' + target_var + b'=' + target_var + b'.slice(0  );break}'
    assert len(old) == len(new), f"长度不匹配: {len(old)} vs {len(new)}"
    before = data
    data = data.replace(old, new, 1)
    if data != before:
        applied += 1
        print(f"✓ patch {applied}: {old.decode()} → {new.decode()}")

if applied == 0:
    print("mod10 全部已应用")
    sys.exit(0)

assert len(data) == original_size, f"mod10 大小变化 {len(data) - original_size:+d} bytes"

save_droid(data)
print(f"mod10 完成: {applied}/{len(matches)} 处 tag strip 修复 (0 bytes)")

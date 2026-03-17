#!/usr/bin/env python3
"""mod8: Mission 模型白名单恒通过 (0 bytes)

直接将两处 Y9H.includes(X) 调用替换为 !0 (true) + 空格填充:
1. enter-mission: Y9H.includes(I) → !0 — 永远走 if 分支，不强切模型
2. vO 回调: Y9H.includes(kA) → !0 — 警告只检查 reasoning effort

比替换 Y9H 数组→对象更稳定（不改数据结构，只改条件表达式）。

锚点稳定性: Y9H、h9H 和参数名 (I, kA) 均为混淆产物，版本间会变。
脚本通过正则 V 匹配所有 JS 标识符，配合上下文关键字 (getReasoningEffort) 定位，
h9H 不再硬编码，而是通过 V 模式动态匹配。
"""
import re
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)
applied = 0

# --- 修改点 1: enter-mission 的 Y9H.includes(X) ---
# 上下文: getReasoningEffort();if(Y9H.includes(X)){if(!h9H
pat1 = rb'(' + V + rb')\.includes\((' + V + rb')\)\)\{if\(!' + V
m1 = None
for candidate in re.finditer(pat1, data):
    ctx = data[max(0, candidate.start()-120):candidate.start()+100]
    if b'getReasoningEffort' in ctx:
        m1 = candidate
        break

if m1:
    var_name = m1.group(1)  # e.g. Y9H
    arg_name = m1.group(2)  # e.g. I
    target1 = var_name + b'.includes(' + arg_name + b')'
    replace1 = b'!0' + b' ' * (len(target1) - 2)
    data = data[:m1.start()] + replace1 + data[m1.start()+len(target1):]
    print(f"mod8a enter-mission: {target1.decode()} → !0 (0 bytes)")
    applied += 1
else:
    # 检测是否已应用: !0 + 空格 + ){if(!h9H
    if re.search(rb'!0\s+\)\{if\(!' + V, data):
        print("mod8a enter-mission 已应用，跳过")
        applied += 1
    else:
        print("mod8 失败: 未找到 enter-mission 中的白名单检查")
        sys.exit(1)

# --- 修改点 2: vO 回调的 Y9H.includes(X) ---
# 上下文: if(!(Y9H.includes(X)&&h9H.includes(
pat2 = rb'if\(!\((' + V + rb')\.includes\((' + V + rb')\)&&' + V + rb'\.includes\('
m2 = re.search(pat2, data)

if m2:
    var_name = m2.group(1)  # e.g. Y9H
    arg_name = m2.group(2)  # e.g. kA
    target2 = var_name + b'.includes(' + arg_name + b')'
    replace2 = b'!0' + b' ' * (len(target2) - 2)
    offset = m2.start(1)  # group(1) 起始 = VAR 名位置
    data = data[:offset] + replace2 + data[offset+len(target2):]
    print(f"mod8b vO 回调: {target2.decode()} → !0 (0 bytes)")
    applied += 1
else:
    # 检测是否已应用: if(!(!0 + 空格 + &&h9H.includes(
    if re.search(rb'if\(!\(!0\s+&&' + V + rb'\.includes\(', data):
        print("mod8b vO 回调已应用，跳过")
        applied += 1
    else:
        print("mod8 失败: 未找到 vO 回调中的白名单检查")
        sys.exit(1)

assert len(data) == original_size, f"大小变化 {len(data) - original_size:+d} bytes"
save_droid(data)
print(f"mod8 完成 ({applied}/2 修改)")

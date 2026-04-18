#!/usr/bin/env python3
"""mod11: 修复 YcM/NcM 部分 JSON 解析器对 \\uXXXX Unicode 转义的处理 (+136 bytes)

问题根因:
  YcM 的字符串解析器在处理 \\uXXXX 时，
  switch default case 只取 backslash 后一个字符，导致:
    \\u5de5 → u5de5  (backslash 被吃掉)

修改:
  两处 default:A+=V;break}}else A+=H[ 的 switch default case
  → V=="u"时解码4位hex为实际Unicode字符

字节变化: +136B (每处 +68B × 2 处)
补偿: 由 comp_universal.py 统一处理 (不在此脚本内补偿)

来源: ryanflavor/.dotfiles mod15
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

# ─── 检查是否已应用 ───────────────────────────────────────────────────────
if b'?(A+=String.fromCharCode(parseInt(H.slice(' in data:
    print("mod11 已应用，跳过")
    sys.exit(0)

# ─── 找两处 default case (value 解析器 + key 解析器) ──────────────────────
# 模式: default:A+=X;break}}else A+=H[Y];Y++
pattern = re.compile(rb'default:A\+=([A-Z]);break\}\}else A\+=H\[([A-Z])\];\2\+\+')
matches = list(pattern.finditer(data))
if len(matches) < 2:
    print(f"mod11 失败: 找到 {len(matches)} 处 default case，预期 2 处")
    print("  检查: strings ~/.local/bin/droid | grep 'default:A+='")
    sys.exit(1)
if len(matches) > 2:
    print(f"警告: 找到 {len(matches)} 处 default case，取前 2 处")

# 从后往前 patch，避免偏移量问题
for i in reversed(range(2)):
    m = matches[i]
    char_var = m.group(1)
    loop_var = m.group(2)
    old_bytes = b'default:A+=' + char_var + b';break}}else A+=H['
    new_bytes = (b'default:' + char_var + b'=="u"?(A+=String.fromCharCode(parseInt(H.slice('
                + loop_var + b'+1,' + loop_var + b'+5),16)),'
                + loop_var + b'+=4):A+=' + char_var + b';break}}else A+=H[')
    pos = m.start()
    data = data[:pos] + new_bytes + data[pos + len(old_bytes):]
    label = 'value' if i == 0 else 'key'
    print(f"✓ Patch {i+1} ({label}): default:A+={char_var.decode()} → Unicode decode "
          f"(+{len(new_bytes)-len(old_bytes)}B) at pos {pos}")

delta = len(data) - original_size
save_droid(data)
print(f"mod11 完成 (+{delta} bytes, 需由 comp_universal.py 补偿)")

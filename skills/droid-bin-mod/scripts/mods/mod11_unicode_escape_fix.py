#!/usr/bin/env python3
"""mod11: 修复 ucM/NcM 部分JSON解析器对 \\uXXXX Unicode 转义的处理

问题根因:
  YcM 的字符串解析器在处理 \\uXXXX 时，
  switch default case 只取 backslash 后一个字符，导致:
    \\u5de5 → u5de5  (backslash 被吃掉)

修改:
  两处 default:A+=V;break}}else A+=H[ 的 switch default case
  → V=="u"时解码4位hex为实际Unicode字符

补偿: 利用 mod8 创建的死代码区域
字节变化: +120B (由 mod8 死代码区域补偿)

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
# X 是当前字符变量, Y 是循环索引变量
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
    char_var = m.group(1)   # B 或 C 等 (当前字符)
    loop_var = m.group(2)   # R 等 (循环索引)
    old_bytes = b'default:A+=' + char_var + b';break}}else A+=H['
    new_bytes = (b'default:' + char_var + b'=="u"?(A+=String.fromCharCode(parseInt(H.slice('
                + loop_var + b'+1,' + loop_var + b'+5),16)),'
                + loop_var + b'+=4):A+=' + char_var + b';break}}else A+=H[')
    pos = m.start()
    data = data[:pos] + new_bytes + data[pos + len(old_bytes):]
    label = 'value' if i == 0 else 'key'
    print(f"✓ Patch {i+1} ({label}): default:A+={char_var.decode()} → Unicode decode "
          f"(+{len(new_bytes)-len(old_bytes)}B) at pos {pos}")

# ─── 计算增量 ────────────────────────────────────────────────────────────
delta = len(data) - original_size
print(f"  当前总增量: {delta:+d}B (需要补偿)")

# ─── 补偿: 压缩 mod8 死代码区域 ─────────────────────────────────────────
DEAD_ANCHOR = b'provider==="openai"&&!1)return(await new '
dead_pos = data.find(DEAD_ANCHOR)
if dead_pos < 0:
    print("mod11 补偿失败: 未找到 mod8 死代码锚点")
    print("  需要先应用 mod8")
    sys.exit(1)

dead_start = dead_pos + len(DEAD_ANCHOR) - len(b'return(await new ')
dead_end_marker = b'.output_text;'
dead_end = data.find(dead_end_marker, dead_start, dead_start + 500)
if dead_end < 0:
    print("mod11 补偿失败: 未找到死代码结尾 .output_text;")
    sys.exit(1)
dead_end += len(dead_end_marker)

dead_size = dead_end - dead_start
print(f"  死代码区域: pos {dead_start}-{dead_end}, {dead_size}B")

target_size = dead_size - delta
min_dead = b'return null;'
if target_size < len(min_dead):
    print(f"mod11 失败: 补偿空间不足 (需要 {delta}B, 最多 {dead_size - len(min_dead)}B)")
    sys.exit(1)

pad_size = target_size - len(min_dead) - 4
if pad_size < 0:
    new_dead = min_dead + b' ' * (target_size - len(min_dead))
else:
    new_dead = min_dead + b'/*' + b' ' * pad_size + b'*/'
assert len(new_dead) == target_size, f"补偿长度错误: {len(new_dead)} != {target_size}"

data = data[:dead_start] + new_dead + data[dead_end:]
print(f"✓ 补偿: 死代码 {dead_size}B → {target_size}B (节省 {dead_size - target_size}B)")

# ─── 验证文件大小 ──────────────────────────────────────────────────────────
final_size = len(data)
if final_size != original_size:
    print(f"✗ 文件大小变化: {original_size} → {final_size} ({final_size - original_size:+d}B)")
    sys.exit(1)

save_droid(data)
print(f"✓ mod11 完成，文件大小不变 ({final_size}B)")

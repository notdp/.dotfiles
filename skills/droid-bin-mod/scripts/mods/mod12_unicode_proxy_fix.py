#!/usr/bin/env python3
"""mod12: 修复 proxy 发送 u5de5（无反斜杠）的 JSON 序列化 bug

问题根因:
  上游 proxy (192.168.10.69:8317) 在 partial_json 中传递中文时
  使用了错误的格式: u5de5 (无反斜杠) 而非正确的 \\u5de5 (有反斜杠)

  推理/正文走 text_delta.text (直接 UTF-8 字节) → 中文正常
  工具调用走 input_json_delta.partial_json (JSON 字符串) → 触发 bug

  - mod11 只修了 YcM fallback 路径 (JSON.parse 失败时)
  - 本 mod 在 wU$ 预处理中拦截，覆盖 JSON.parse 和 YcM 两条路径

修改:
  wU$(H) 入口处添加: H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,'\\\\u$1');
  将无前置反斜杠的 uXXXX → \\uXXXX，使 JSON.parse 正确解码

补偿:
  进一步压缩 mod8/mod11 已利用的死代码区域 (当前75B → 26B，释放49B)

字节变化: +49B (由 mod8 死代码区域残余空间补偿)

注: Droid 对 "heredoc 传中文问题" 的诊断是错误的
    实际问题是 proxy 的 JSON 序列化 bug，不是 shell heredoc
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

# ─── 检查是否已应用 ───────────────────────────────────────────────────────
if b'H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,' in data:
    print("mod12 已应用，跳过")
    sys.exit(0)

# ─── Patch: 在 wU$ 函数入口添加预处理 ────────────────────────────────────
# 定位 wU$ 函数: function wU$(H){if(!H.trim())return{data:{},isComplete:!1};
WU_PATTERN = re.compile(
    rb'function (' + V + rb')\(H\)\{if\(!H\.trim\(\)\)return\{data:\{\},isComplete:!1\};'
)
# 在 try{return{data:JSON.parse 之前插入预处理
WU_INSERT_ANCHOR = b'try{return{data:JSON.parse(H)||{},isComplete:!0}}'

# 验证 wU$ 存在
wu_match = WU_PATTERN.search(data)
if not wu_match:
    print("mod12 失败: 未找到 wU$ 等价函数")
    sys.exit(1)

func_name = wu_match.group(1).decode()
wu_pos = wu_match.start()
print(f"  找到 wU$ 等价函数: {func_name} at pos {wu_pos}")

# 在 wU$ 的 try{JSON.parse 之前插入预处理
# 找到 wU$ 内的 try{return{data:JSON.parse
search_start = wu_pos
search_end = wu_pos + 400
wu_region = data[search_start:search_end]
insert_idx = wu_region.find(WU_INSERT_ANCHOR)
if insert_idx < 0:
    print("mod12 失败: 未在 wU$ 中找到 try{JSON.parse 锚点")
    sys.exit(1)

insert_pos = search_start + insert_idx

# 插入内容: H=H.replace(/(?<!\\)u([0-9a-fA-F]{4})/g,'\\u$1');
# 在二进制中表示（注意 JS 正则中 \\ 表示一个反斜杠）
INSERTION = b"H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,'\\\\u$1');"
data = data[:insert_pos] + INSERTION + data[insert_pos:]
delta = len(data) - original_size
print(f"✓ wU$ 预处理: 添加 u5de5 → \\u5de5 转换 ({delta:+d}B)")

# ─── 验证效果 ─────────────────────────────────────────────────────────────
# 快速验证新代码在 wU$ 中
new_wu_region = data[wu_pos:wu_pos+250].decode('utf-8', errors='replace')
printable = ''.join(c if 32 <= ord(c) < 127 else '?' for c in new_wu_region)
print(f"  wU$ 新代码预览: {printable[:200]}")

# ─── 补偿: 进一步压缩 mod8 死代码区域 ──────────────────────────────────
# 当前死代码: provider==="openai"&&!1)return null;/* ... */ (75B after mod11)
# 目标: 缩减到 75-49=26B

DEAD_ANCHOR = b'provider==="openai"&&!1)return null;'
dead_pos = data.find(DEAD_ANCHOR)
if dead_pos < 0:
    print("mod12 补偿失败: 未找到 mod8/mod11 死代码锚点")
    sys.exit(1)

# 找到死代码区域的结尾
dead_start = dead_pos + len(b'provider==="openai"&&!1)')  # return null; 开始
# mod11 后的形态是: return null;/* ... */if(...)
dead_end = data.find(b'if(', dead_start, dead_start + 500)
if dead_end < 0:
    print("mod12 补偿失败: 未找到死代码结尾 if(")
    sys.exit(1)

dead_code = data[dead_start:dead_end]
dead_size = len(dead_code)
print(f"  死代码当前: {dead_size}B → 需要压缩到 {dead_size - delta}B")

target_size = dead_size - delta  # 补偿 +delta
min_dead = b'return null;'  # 12B 最小替换

if target_size < len(min_dead):
    print(f"mod12 失败: 补偿空间不足 ({dead_size}B, 需要 {delta}B)")
    sys.exit(1)

# 生成替换内容: "return null;/* spaces */"
pad_needed = target_size - len(min_dead)
if pad_needed >= 4:
    new_dead = min_dead + b'/*' + b' ' * (pad_needed - 4) + b'*/'
elif pad_needed > 0:
    new_dead = min_dead + b' ' * pad_needed
else:
    new_dead = min_dead

assert len(new_dead) == target_size, f"补偿长度错误: {len(new_dead)} != {target_size}"
data = data[:dead_start] + new_dead + data[dead_end:]
print(f"✓ 补偿: 死代码 {dead_size}B → {target_size}B")

# ─── 验证文件大小 ──────────────────────────────────────────────────────────
final_size = len(data)
if final_size != original_size:
    print(f"✗ 文件大小变化: {original_size} → {final_size} ({final_size - original_size:+d}B)")
    sys.exit(1)

save_droid(data)
print(f"✓ mod12 完成，文件大小不变 ({final_size}B)")
print()
print("效果:")
print("  - wU$(buffer) 预处理: u5de5 → \\u5de5")
print("  - JSON.parse 和 YcM 两条路径都能正确处理中文")
print("  - 修复 proxy 发送无反斜杠 Unicode 的 bug (workaround)")
print()
print("注: droid 对 'heredoc 传中文' 的诊断是错误的")
print("    实际是 proxy JSON 序列化 bug")

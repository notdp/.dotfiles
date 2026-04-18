#!/usr/bin/env python3
"""mod12: 修复 proxy 发送 u5de5（无反斜杠）的 JSON 序列化 bug (+49 bytes)

问题根因:
  上游 proxy 在 partial_json 中传递中文时使用错误格式:
    u5de5 (无反斜杠) 而非正确的 \\u5de5

  推理/正文走 text_delta.text → UTF-8 字节直传，中文正常
  工具调用走 input_json_delta.partial_json → JSON 字符串路径，触发 bug

  - mod11 只修了 YcM fallback 路径 (JSON.parse 失败时)
  - 本 mod 在 wU$ 预处理中拦截，覆盖 JSON.parse 和 YcM 两条路径

修改:
  wU$(H)/r_T(H) 函数入口添加:
    H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,'\\\\u$1');
  将无前置反斜杠的 uXXXX → \\uXXXX，使 JSON.parse 正确解码

字节变化: +49B
补偿: 由 comp_universal.py 统一处理 (不在此脚本内补偿)

注: droid 对 "heredoc 传中文" 的诊断是错误的
    实际是 proxy JSON 序列化 bug
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

# ─── Patch: 在 wU$/r_T 函数入口添加预处理 ────────────────────────────────
# 定位函数: function VAR(H){if(!H.trim())return{data:{},isComplete:!1};
WU_PATTERN = re.compile(
    rb'function (' + V + rb')\(H\)\{if\(!H\.trim\(\)\)return\{data:\{\},isComplete:!1\};'
)
WU_INSERT_ANCHOR = b'try{return{data:JSON.parse(H)||{},isComplete:!0}}'

wu_match = WU_PATTERN.search(data)
if not wu_match:
    print("mod12 失败: 未找到 wU$/r_T 等价函数")
    sys.exit(1)

func_name = wu_match.group(1).decode()
wu_pos = wu_match.start()
print(f"  找到 wU$ 等价函数: {func_name} at pos {wu_pos}")

# 在函数体内 try{JSON.parse 之前插入预处理
search_start = wu_pos
search_end = wu_pos + 400
wu_region = data[search_start:search_end]
insert_idx = wu_region.find(WU_INSERT_ANCHOR)
if insert_idx < 0:
    print("mod12 失败: 未在函数内找到 try{JSON.parse 锚点")
    sys.exit(1)

insert_pos = search_start + insert_idx

# 插入内容: H=H.replace(/(?<!\\)u([0-9a-fA-F]{4})/g,'\\u$1');
INSERTION = b"H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,'\\\\u$1');"
data = data[:insert_pos] + INSERTION + data[insert_pos:]
delta = len(data) - original_size

print(f"✓ 函数入口预处理: 添加 u5de5 → \\u5de5 转换 (+{delta}B)")
save_droid(data)
print(f"mod12 完成 (+{delta} bytes, 需由 comp_universal.py 补偿)")

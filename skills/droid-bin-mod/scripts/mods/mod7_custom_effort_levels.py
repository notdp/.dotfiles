#!/usr/bin/env python3
"""mod9: custom model 支持完整 effort 级别 (+132 bytes)

问题: 两个函数对 custom model 硬编码 supportedReasoningEfforts 为 ["off","low","medium","high"]，
缺少 anthropic 的 "max" 和 openai 的 "xhigh"。

代码路径 (变量名随版本混淆变化，用 regex 匹配):
  1. zsH 函数 (模型列表映射, .map 回调): VAR?["off","low","medium","high"]:["none"]
  2. lB 函数 (按 ID 解析单个模型):       VAR?["off","low","medium","high"]:["none"]

每处用 defaultReasoningEffort:REF.reasoningEffort 中的 REF 变量做 provider 检查:
  REF.provider=="openai" ? xhigh列表 : max列表

字节: +132 bytes，由 comp_universal.py 统一补偿。
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()

total_diff = 0
applied = 0

# 统一用 regex 匹配所有 custom model effort 列表
# 模式: supportedReasoningEfforts:COND?["off","low","medium","high"]:["none"],defaultReasoningEffort:REF.reasoningEffort
pat_orig = (rb'supportedReasoningEfforts:(' + V + rb')\?\["off","low","medium","high"\]:\["none"\],'
            rb'defaultReasoningEffort:(' + V + rb')\.reasoningEffort')
pat_max  = (rb'supportedReasoningEfforts:(' + V + rb')\?\["off","low","medium","high","max"\]:\["none"\],'
            rb'defaultReasoningEffort:(' + V + rb')\.reasoningEffort')

# 已应用检测: VAR.provider=="openai" 模式
pat_done = rb'supportedReasoningEfforts:' + V + rb'\?' + V + rb'\.provider=="openai"\?'

# 从后往前替换，避免 offset 漂移
replacements = []
for pat, label in [(pat_max, "max-only"), (pat_orig, "original")]:
    for m in re.finditer(pat, data):
        # 跳过已有 provider 检查的 (被之前的 pat 覆盖过)
        ctx_before = data[max(0, m.start()-100):m.start()]
        if b'.provider==' in ctx_before:
            continue
        replacements.append((m.start(), m.end(), m.group(0), m.group(1), m.group(2), label))

if not replacements:
    done_count = len(re.findall(pat_done, data))
    if done_count >= 2:
        print("mod9: 全部已应用")
        sys.exit(0)
    else:
        print(f"错误: custom model effort 列表未找到 (provider-aware={done_count})")
        sys.exit(1)

# 从后往前替换
for start, end, old, var_cond_b, var_ref_b, label in sorted(replacements, key=lambda x: x[0], reverse=True):
    var_cond = var_cond_b.decode()
    var_ref = var_ref_b.decode()
    new = (f'supportedReasoningEfforts:{var_cond}?{var_ref}.provider=="openai"?'
           f'["none","low","medium","high","xhigh"]:["off","low","medium","high","max"]:["none"],'
           f'defaultReasoningEffort:{var_ref}.reasoningEffort').encode()
    data = data[:start] + new + data[end:]
    diff = len(new) - len(old)
    total_diff += diff
    applied += 1
    print(f"mod9 [{applied}]: {label} → provider-aware ({diff:+d} bytes, cond={var_cond}, ref={var_ref})")

if total_diff == 0:
    print("mod9: 全部已应用")
else:
    print(f"mod9: {applied} 处修改, 总计 {total_diff:+d} bytes")
    save_droid(data)

#!/usr/bin/env python3
"""mod9: custom model 支持完整 effort 级别 (+132 bytes)

问题: 两个函数对 custom model 硬编码 supportedReasoningEfforts 为 ["off","low","medium","high"]，
缺少 anthropic 的 "max" 和 openai 的 "xhigh"。

代码路径:
  1. KOH 函数 (构建完整模型列表): L?["off","low","medium","high"]:["none"]
     → 按 provider 区分 (+66 bytes)
  2. $A 函数 (按 ID 解析当前活跃模型): B?["off","low","medium","high"]:["none"]
     → 按 provider 区分 (+66 bytes)

字节: +132 bytes，由 comp_universal.py 统一补偿。
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid

data = load_droid()

total_diff = 0

# --- 路径 1: KOH 函数 (模型列表构建) ---
OLD1 = b'supportedReasoningEfforts:L?["off","low","medium","high"]:["none"]'
NEW1 = b'supportedReasoningEfforts:L?T.provider=="openai"?["none","low","medium","high","xhigh"]:["off","low","medium","high","max"]:["none"]'

if b'T.provider=="openai"' in data:
    print("mod9 路径1 (KOH): 已应用，跳过")
else:
    if OLD1 not in data:
        print("错误: KOH 中的 effort 列表未找到")
        sys.exit(1)
    data = data.replace(OLD1, NEW1, 1)
    diff1 = len(NEW1) - len(OLD1)
    total_diff += diff1
    print(f"mod9 路径1 (KOH): effort 列表已修改 ({diff1:+d} bytes)")

# --- 路径 2: $A 函数 (单模型解析, Ctrl+N / Tab / setModel 都走这里) ---
# 变量名会随版本混淆变化，用正则匹配
import re
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'
# 匹配: supportedReasoningEfforts:VAR?["off","low","medium","high"]:["none"],defaultReasoningEffort:VAR.reasoningEffort
# 排除已修改的 KOH (含 T.provider)
pat2_orig = (rb'supportedReasoningEfforts:(' + V + rb')\?\["off","low","medium","high"\]:\["none"\],'
             rb'defaultReasoningEffort:(' + V + rb')\.reasoningEffort')
pat2_max  = (rb'supportedReasoningEfforts:(' + V + rb')\?\["off","low","medium","high","max"\]:\["none"\],'
             rb'defaultReasoningEffort:(' + V + rb')\.reasoningEffort')
# 找所有匹配，排除 KOH (已含 T.provider 在前方上下文)
found = False
for pat, label in [(pat2_max, "max-only"), (pat2_orig, "original")]:
    for m in re.finditer(pat, data):
        # 检查上下文中是否有 KOH 特征 (T.provider 出现在紧邻的前方)
        ctx_before = data[max(0,m.start()-100):m.start()]
        if b'T.provider==' in ctx_before:
            continue  # 跳过 KOH
        var_cond = m.group(1).decode()  # e.g. C or B
        var_ref = m.group(2).decode()   # e.g. D or R
        old2 = m.group(0)
        new2 = (f'supportedReasoningEfforts:{var_cond}?{var_ref}.provider=="openai"?'
                f'["none","low","medium","high","xhigh"]:["off","low","medium","high","max"]:["none"],'
                f'defaultReasoningEffort:{var_ref}.reasoningEffort').encode()
        data = data[:m.start()] + new2 + data[m.start()+len(old2):]
        diff2 = len(new2) - len(old2)
        total_diff += diff2
        print(f"mod9 路径2 ($A): {label} → provider-aware ({diff2:+d} bytes, var={var_cond}/{var_ref})")
        found = True
        break
    if found:
        break
if not found:
    # 如果没有原始/max-only 模式，检查是否已经有 provider-aware 的非 KOH 匹配
    pat2_done = (rb'supportedReasoningEfforts:' + V + rb'\?' + V + rb'\.provider=="openai"\?')
    done_count = len(re.findall(pat2_done, data))
    if done_count >= 2:
        print("mod9 路径2 ($A): 已应用，跳过")
    else:
        print("错误: $A 中的 effort 列表未找到")
        sys.exit(1)

if total_diff == 0:
    print("mod9: 全部已应用")
else:
    print(f"mod9: 总计 {total_diff:+d} bytes")
    save_droid(data)

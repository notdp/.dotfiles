#!/usr/bin/env python3
"""mod7: custom model 支持完整 effort 级别 (+66 bytes per match)

问题: custom model 硬编码 supportedReasoningEfforts 为 ["off","low","medium","high"]，
缺少 anthropic 的 "max" 和 openai 的 "xhigh"。

修改: 根据 provider 返回正确的 effort 列表:
  - openai:    ["none","low","medium","high","xhigh"]
  - anthropic: ["off","low","medium","high","xhigh","max"]  (claude-opus-4-7 等支持 xhigh)

使用正则匹配变量名，适应混淆。
"""
import re, sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()

if b'.provider=="openai"?["none"' in data:
    print("mod7 已应用，跳过")
    sys.exit(0)

# 匹配: VAR?["off","low","medium","high"]:["none"]
# 需要从上下文中找到 model 对象变量 (含 .provider) 来构建替换
pattern = re.compile(
    rb'(supportedReasoningEfforts:)(' + V + rb')(\?\["off","low","medium","high"\]:\["none"\])'
    rb'(,defaultReasoningEffort:)(' + V + rb')(\.reasoningEffort)'
)

matches = list(pattern.finditer(data))
if not matches:
    print("错误: effort 列表模式未找到")
    sys.exit(1)

total_diff = 0
# 从后往前替换，避免偏移问题
for m in reversed(matches):
    cond_var = m.group(2)  # E or I (bool: has reasoning)
    model_var = m.group(5)  # D or A (model object with .provider)
    old = m.group(0)
    # 构建新代码: COND?MODEL.provider=="openai"?[openai list]:[anthropic list]:["none"]
    new = (
        m.group(1) + cond_var + b'?' + model_var + b'.provider=="openai"'
        b'?["none","low","medium","high","xhigh"]'
        b':["off","low","medium","high","xhigh","max"]'
        b':["none"]'
        + m.group(4) + m.group(5) + m.group(6)
    )
    data = data[:m.start()] + new + data[m.end():]
    diff = len(new) - len(old)
    total_diff += diff
    print(f"  match: {cond_var.decode()}?[...] → {model_var.decode()}.provider check ({diff:+d} bytes)")

print(f"mod7: {len(matches)} 处 effort 列表已修改 (总计 {total_diff:+d} bytes)")
save_droid(data)

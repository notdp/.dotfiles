#!/usr/bin/env python3
"""mod10: 适配 Opus 4.7 adaptive thinking 多轮保留 (0 bytes)

问题: P7I 函数在每次请求时检测历史 (I7I/D7I)，若存在 assistant 消息但首块
不是 thinking/redacted_thinking，就剥离当前请求的 thinking 配置并从历史中
删除所有 thinking 块。Opus 4.7 的 {type:"adaptive", display:"summarized"}
模式下，assistant 响应首块通常直接是 tool_use，触发该剥离机制，导致从第
二轮起 thinking 配置被永久关闭，adaptive 自适应预算失效。

修复: 将 P7I 内 `if(V.thinking){if(V(V)||V(V))` 的内层条件短路为 !1，
跳过历史检测与剥离。字节中性，无需补偿。

变量名说明: V1=T(thinking cfg), V2=I7I, V3=B(history), V4=D7I，均为 v0.104
混淆实例，版本变化时通过正则匹配自动适配。
"""
import re
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

# 幂等检查: 补丁后的内层条件为 !1 加空格
PATTERN_APPLIED = re.compile(rb'if\(' + V + rb'\.thinking\)\{if\(!1 {2,}\)')
if PATTERN_APPLIED.search(data):
    print("mod10 已应用，跳过")
    sys.exit(0)

# 目标: if(T.thinking){if(I7I(B)||D7I(B))
# 改为: if(T.thinking){if(!1            )   (内层条件等长替换为 !1 + 空格)
PATTERN = re.compile(
    rb'(if\(' + V + rb'\.thinking\)\{if\()'
    rb'(' + V + rb'\(' + V + rb'\)\|\|' + V + rb'\(' + V + rb'\))'
    rb'(\))'
)

matches = list(PATTERN.finditer(data))
if not matches:
    raise ValueError("mod10: 未找到 P7I thinking-stripping 模式")
if len(matches) > 1:
    print(f"警告: mod10 找到 {len(matches)} 处，用第 1 处")

m = matches[0]
prefix, inner, suffix = m.group(1), m.group(2), m.group(3)
replacement_inner = b'!1' + b' ' * (len(inner) - 2)
assert len(replacement_inner) == len(inner)

old = m.group(0)
new = prefix + replacement_inner + suffix
data = data[:m.start()] + new + data[m.end():]
assert len(data) == original_size

print(f"mod10: {old.decode()} → {new.decode()} (0 bytes)")
save_droid(data)
print("mod10 完成: adaptive thinking 多轮保留已启用")

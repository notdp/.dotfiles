#!/usr/bin/env python3
"""mod-fix-multiline-history-down: 修复多行历史记录按↓无法返回空输入框 (0 bytes)

问题: 多行文本最后一行按↓调用 onDownArrowAtBottom 并返回 true,
     拦截了外层 handler 的历史导航 (navigateNext)。
修复: 将 V(),!0 替换为等长空格 + !1, 让该分支返回 false,
     由外层历史导航接管。

二进制中目标片段 (V 为任意混淆变量名):
    if(hR.downArrow&&lR&&V)return V(),!0;return!1
替换为:
    if(hR.downArrow&&lR&&V)return       !1;return!1
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, replace_one, V

NAME = 'mod-fix-multiline-history-down'

data = load_droid()
original_size = len(data)

# 已修改形态: V() 与 ,!0 已被等长空格覆盖, 仅剩 return ...!1;return!1
modified_pat = rb'downArrow&&' + V + rb'&&' + V + rb'\)return\s+!1;return!1'
if re.search(modified_pat, data):
    print(f"{NAME} 已应用，跳过")
    sys.exit(0)

# Pattern: if(...&&V1)return V1(),!0;return!1
# Replace:                  ^^^^^^^ → spaces(len(V1)+4) + !1
data, _ = replace_one(
    data,
    rb'(if\([^)]*&&)(' + V + rb')\)return \2\(\),!0;return!1',
    lambda m: m.group(1) + m.group(2) + b')return ' + b' ' * (len(m.group(2)) + 3) + b'!1;return!1',
    f'{NAME} 多行历史')

if len(data) != original_size:
    print(f"警告: 大小变化 {len(data) - original_size:+d} bytes")

save_droid(data)
print(f"{NAME} 完成")

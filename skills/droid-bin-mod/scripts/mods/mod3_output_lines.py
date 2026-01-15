#!/usr/bin/env python3
"""mod3: 输出预览行数 4→99 行 (+1 byte, 需要补偿)

修改变量定义 aGR=4 → aGR=99
同时解决 mod5 (输出提示条件也用 aGR)
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()

# 模式: VAR=4,VAR2=5,VAR3=200 (输出行数配置)
pattern = rb'(' + V + rb')=4,(' + V + rb')=5,(' + V + rb')=200'
match = re.search(pattern, data)

if not match:
    print("mod3 失败: 未找到输出行数配置 (VAR=4,VAR2=5,VAR3=200)")
    sys.exit(1)

var1, var2, var3 = match.group(1), match.group(2), match.group(3)
old = match.group(0)
new = var1 + b'=99,' + var2 + b'=5,' + var3 + b'=200'

data = data.replace(old, new, 1)
save_droid(data)
print(f"mod3 输出行数: {var1.decode()}=4 → {var1.decode()}=99 (+1 byte)")
print("mod3 完成 (同时解决 mod5, 需要补偿 -1 byte)")

#!/usr/bin/env python3
"""mod5: 输出提示条件 (由 mod3 自动处理)

mod3 修改 D=B?8:4→99||4 后，J>D 自动变为 >99
此脚本仅检查状态，不做修改
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, V

data = load_droid()

if re.search(V + rb'=99\|\|4', data):
    print("mod5: 已由 mod3 处理，跳过")
else:
    print("mod5: 请先运行 mod3")
    sys.exit(1)

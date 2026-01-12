#!/usr/bin/env python3
"""补偿: T=3 → T=33 (+1 byte)
截断函数签名: func(A, R=80, T=3)
T 是行数限制，被 mod1 短路后不再生效
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, replace_one, V

data = load_droid()

data, diff = replace_one(
    data,
    rb'(' + V + rb')=80,(' + V + rb')=3\)',
    lambda m: m.group(1) + b'=80,' + m.group(2) + b'=33)',
    'compensation T=3→T=33')

save_droid(data)
print(f"补偿完成 ({diff:+d} bytes)")

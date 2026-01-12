#!/usr/bin/env python3
"""mod3: 输出预览行数 4→99 行 (+1 byte, 需要补偿)"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, replace_one, V

data = load_droid()
original_size = len(data)

# slice(0,X),Y=z.length → slice(0,99)...
# 用 exec-preview 定位，因为 slice(0,X) 出现很多次
data, diff = replace_one(
    data,
    rb'slice\(0,(\d)\),(' + V + rb')=(' + V + rb')\.length',
    lambda m: b'slice(0,99),' + m.group(2) + b'=' + m.group(3) + b'.length',
    'mod3 输出行数',
    near_marker=b'exec-preview')

save_droid(data)
print(f"mod3 完成 (需要 {-diff:+d} bytes 补偿)")

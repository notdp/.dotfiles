#!/usr/bin/env python3
"""通用补偿: 修改截断函数内的 substring 长度

0.49+ 版本中，mod3 改为修改变量定义 (0 bytes)，通常不需要补偿。
此脚本保留用于特殊情况。

用法: python3 comp_substring.py <bytes>
  bytes: 需要补偿的字节数（负数=缩减，正数=扩展）
  范围: -9 到 +∞
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

def main():
    if len(sys.argv) < 2:
        print("0.49+ 版本通常不需要补偿")
        print("用法: python3 comp_substring.py <bytes>")
        sys.exit(0)
    
    try:
        comp_bytes = int(sys.argv[1])
    except ValueError:
        print(f"错误: 无效的字节数 '{sys.argv[1]}'")
        sys.exit(1)
    
    if comp_bytes < -9:
        print(f"错误: 最大只能缩减 -9 bytes，你指定了 {comp_bytes}")
        sys.exit(1)
    
    data = load_droid()
    
    pattern = rb'(' + V + rb')\.(substring[a-z]*)\(0,(' + V + rb')\);return\{text:\1,isTruncated:!0\}'
    match = re.search(pattern, data)
    
    if not match:
        print("补偿失败: 未找到目标模式")
        sys.exit(1)
    
    var1, old_func, var2 = match.group(1), match.group(2), match.group(3)
    new_len = max(0, 9 + comp_bytes)
    new_func = b'x' * new_len
    
    old = match.group(0)
    new = var1 + b'.' + new_func + b'(0,' + var2 + b');return{text:' + var1 + b',isTruncated:!0}'
    actual_diff = len(new) - len(old)
    
    data = data.replace(old, new, 1)
    save_droid(data)
    print(f"补偿: {old_func.decode()} → {new_func.decode() or '(空)'} ({actual_diff:+d} bytes)")

if __name__ == '__main__':
    main()

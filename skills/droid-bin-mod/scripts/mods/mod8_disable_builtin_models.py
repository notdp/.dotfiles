#!/usr/bin/env python3
"""mod8: 禁用 droid 官方内置模型，只允许 BYOK custom model (0 bytes)

修改 validateModelAccess 函数的最终 return:
  return{allowed:!0,isCustomModel:!1}  →  return{allowed:!1,isCustomModel:!1}

效果: 所有非 custom: 前缀的模型（即 droid 官方内置模型）在 /model 菜单中不可选。
BYOK custom model 不受影响。

稳定锚点: 'isCustomModel:!1};return{allowed:' + 'isCustomModel:!1}}' 结构在
validateModelAccess 函数中唯一，不受混淆影响（均为字符串常量/关键字）。
"""
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid

data = load_droid()
original_size = len(data)

OLD = b'isCustomModel:!1};return{allowed:!0,isCustomModel:!1}}'
NEW = b'isCustomModel:!1};return{allowed:!1,isCustomModel:!1}}'

if OLD not in data and NEW in data:
    print("mod8 已应用，跳过")
    sys.exit(0)

count = data.count(OLD)
if count == 0:
    print("mod8 失败: 未找到 validateModelAccess 的 non-custom return")
    sys.exit(1)

data = data.replace(OLD, NEW)
assert len(data) == original_size, f"大小变化 {len(data) - original_size:+d} bytes"

save_droid(data)
print(f"mod8 禁用内置模型: {count} 处 allowed:!0 → !1 (0 bytes)")
print("mod8 完成")

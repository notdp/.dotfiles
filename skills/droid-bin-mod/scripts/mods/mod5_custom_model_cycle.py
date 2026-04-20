#!/usr/bin/env python3
"""mod5: Ctrl+N 只在 custom model 间切换 (0 bytes)

修改 peekNextCycleModel, peekNextCycleSpecModeModel, cycleSpecModeModel：
- 函数入口覆盖参数 → this.customModels.map(m=>m.id)
- 移除 validateModelAccess 检查（custom model 不需要）
cycleModel 是委托函数（无 validateModelAccess），无需修改。
"""
import sys, re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

if b'=this.customModels.map(m=>m.id);' in data:
    print("mod5 已应用，跳过")
    sys.exit(0)

INSERT = b'=this.customModels.map(m=>m.id);'
VALIDATE_PAT = rb'if\(!this\.validateModelAccess\(' + V + rb'\)\.allowed\)continue;'

TARGETS = [
    b'peekNextCycleModel',
    b'peekNextCycleSpecModeModel',
    b'cycleSpecModeModel',
]

for fn_name in TARGETS:
    # Support both 1-param fn(H){...} and 2-param fn(H,A){...} signatures
    entry_pat = fn_name + rb'\((' + V + rb')(?:,' + V + rb')?\)\{if\(\1\.length===0\)'
    m_entry = re.search(entry_pat, data)
    if not m_entry:
        raise ValueError(f"{fn_name.decode()} 入口未找到!")

    param = m_entry.group(1)
    full_match = m_entry.group(0)
    region_start = m_entry.start()

    m_check = re.search(VALIDATE_PAT, data[region_start:region_start + 600])
    if not m_check:
        raise ValueError(f"{fn_name.decode()} validateModelAccess 未找到!")

    # Use the actual matched text to build replacement
    prefix_end = full_match.find(b'{if(')
    old_entry = full_match
    new_entry = full_match[:prefix_end+1] + param + INSERT + full_match[prefix_end+1:]
    extra = len(new_entry) - len(old_entry)

    old_check = m_check.group(0)
    pad = len(old_check) - extra
    if pad < 4:
        raise ValueError(f"{fn_name.decode()} 填充空间不足: {pad} < 4")
    new_check = b'/*' + b' ' * (pad - 4) + b'*/'

    # Replace validateModelAccess check first (it's after entry)
    check_offset = region_start + m_check.start()
    data = data[:check_offset] + new_check + data[check_offset + len(old_check):]

    # Re-find old_entry since offsets haven't changed before check_offset
    entry_offset = data.find(old_entry, max(0, region_start - 10), region_start + len(old_entry) + 10)
    if entry_offset == -1:
        raise ValueError(f"{fn_name.decode()} entry 替换定位失败")
    data = data[:entry_offset] + new_entry + data[entry_offset + len(old_entry):]

    print(f"{fn_name.decode()}: {param.decode()}{INSERT.decode()} (+{extra}/-{extra}), net 0")

assert len(data) == original_size, f"大小变化 {len(data) - original_size:+d}"
save_droid(data)
print(f"mod5 完成 ({len(TARGETS)} 个函数)")

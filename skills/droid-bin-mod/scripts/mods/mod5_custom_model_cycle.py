#!/usr/bin/env python3
"""mod6: Ctrl+N 在 custom models 间直接切换（不弹 selector）

不修改 peekNextCycleModel 等内部函数，直接替换 Ctrl+N 的 ul callback：
- 用 GR().getCustomModels() 获取 custom model 列表
- 手动计算下一个 index
- 调用 handler (Yk) 完成切换
"""
import sys, re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

MARKER = b'let RR=c8A();if(RR.length<=1)return;'
if MARKER in data:
    print("mod6 已应用，跳过")
    sys.exit(0)

# 匹配原版 ul callback（toggle popup 模式）
ORIGINAL_PAT = re.compile(
    rb'(?P<prefix>(?P<cb>\w+)=(?P<react>\w+)\.useCallback\(\(\)=>\{)'
    rb'if\((?P<models>\w+)\.length<=1\)return;'
    rb'let (?P<policy>\w+)=(?P<service>\w+)\(\)\.getModelPolicy\(\);'
    rb'if\(!(?P=models)\.some\(\((?P<item>\w+)\)=>(?P<access>\w+)\((?P=item),(?P=policy)\)\.allowed\)\)return;'
    rb'(?P<toggle>\w+)\(\((?P<state>\w+)\)=>!(?P=state)\)'
    rb'\},\[(?P<dep>\w+)\]\)'
    rb'(?=,(?P<handler>\w+)=\w+\.useCallback\(async\((?P<handler_arg>\w+)\)=>\{)'
)

m = ORIGINAL_PAT.search(data)
if not m:
    print("mod6 失败: 未找到原版 Ctrl+N callback")
    print("  检查: strings ~/.local/bin/droid | grep 'getModelPolicy'")
    sys.exit(1)

old = m.group(0)
prefix = m.group('prefix')
handler = m.group('handler')
dep = m.group('dep')

new = (
    prefix
    + b'let RR=c8A();'
    + b'if(RR.length<=1)return;'
    + b'let oR=VT().getModel(),gA=RR[(RR.indexOf(oR)+1)%RR.length];'
    + b'if(gA)' + handler + b'(gA)'
    + b'},[' + dep + b'])'
)

delta = len(new) - len(old)
data = data.replace(old, new, 1)

print(f"mod6: ul callback → direct cycle ({delta:+d} bytes)")
print(f"  handler={handler.decode()}, dep={dep.decode()}")

# delta 可能非零，由 comp_universal 统一补偿
if delta != 0:
    print(f"  需要补偿: {delta:+d} bytes")

save_droid(data)
print("mod6 完成")

#!/usr/bin/env python3
"""mod10: custom model 保持不变时支持 /fast (0 bytes)

目标:
  - /fast on/off 对 custom model 生效
  - 保持请求仍走 custom model 的 baseUrl/apiKey
  - 不切到 Droid 内置模型

实现:
  1. /fast 命令对 custom model 改为写 sessionSettings.fast
  2. 请求元信息函数 j() 在 custom model 且 sessionSettings.fast===当前模型时，
     用底层 base model 的 fast variant 配置生成请求参数
     - anthropic: speed="fast" + fast beta
     - openai: service_tier="priority"
  3. bI9/iWR 做等价缩写，命令描述字符串做补偿，整体 0 bytes
"""
import re
import sys

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

if b'sessionSettings.fast===FH' in data and b'L.sessionSettings.fast=C?D:""' in data:
    print('mod10 已应用，跳过')
    sys.exit(0)

def replace_exact(blob, old, new, name):
    idx = blob.find(old)
    if idx == -1:
        raise ValueError(f'{name} 未找到! 可能版本不兼容')
    blob = blob.replace(old, new, 1)
    diff = len(new) - len(old)
    print(f'{name}: {diff:+d} bytes')
    return blob, diff


def replace_regex(blob, pattern, replacer, name):
    m = re.search(pattern, blob)
    if not m:
        raise ValueError(f'{name} 未找到! 可能版本不兼容')
    old = m.group(0)
    new = replacer(m)
    blob = blob[:m.start()] + new + blob[m.end():]
    diff = len(new) - len(old)
    print(f'{name}: {diff:+d} bytes')
    return blob, diff


total_diff = 0

# bI9: helper 名和 Map 变量在版本间会变（G2_/J2_ 等）
pat_bi9 = rb'function bI9\(H\)\{let T=zi\(H\);return T\?(' + V + rb')\.get\(T\):void 0\}'


def repl_bi9(m):
    mapping = m.group(1)
    return b'function bI9(H){return ' + mapping + b'.get(zi(H))}'


data, diff = replace_regex(data, pat_bi9, repl_bi9, 'bI9 等价缩写')
total_diff += diff

# baseVariant helper：0.77 是 iWR，0.79 变成 bWR
pat_base = rb'function (' + V + rb')\(H\)\{let T=zi\(H\);return T\?aG\[T\]\?\.baseVariant:void 0\}'


def repl_base(m):
    fn = m.group(1)
    return b'function ' + fn + b'(H){return aG[zi(H)]?.baseVariant}'


data, diff = replace_regex(data, pat_base, repl_base, 'baseVariant helper 等价缩写')
total_diff += diff

# j(): custom model 请求元信息注入 fast flag
pat_j = (
    rb'EH=zK\(FH,KH\)\?\?null,wH=EH\?EH\.model:FH,LH=yB\(FH\)\.modelProvider,'
    rb'vH,(' + V + rb')=EH\?(' + V + rb')\(EH\.model\):FH;'
    rb'if\(\1\)try\{vH=kz\(\{modelId:\1\}\)\}catch\{\}'
    rb'return\{model:wH,provider:LH,apiModelProvider:vH\?\.apiModelProvider,config:vH,customModel:EH,isSpecMode:NH,reasoningEffort:_H\}'
)


def repl_j(m):
    resolved_var = m.group(1)
    base_helper = m.group(2)
    return (
        b'EH=zK(FH,KH)??null,QH=iT().sessionSettings.fast===FH,wH=EH?EH.model:FH,LH=yB(FH).modelProvider,'
        b'vH,' + resolved_var + b'=EH?(QH?bI9(EH.model)??' + base_helper + b'(EH.model):' + base_helper + b'(EH.model)):FH;'
        b'if(' + resolved_var + b')try{vH=kz({modelId:' + resolved_var + b'})}catch{}'
        b'return{model:wH,provider:LH,apiModelProvider:vH?.apiModelProvider,config:vH,customModel:EH,isSpecMode:NH,reasoningEffort:_H}'
    )


data, diff = replace_regex(data, pat_j, repl_j, 'j() custom fast 请求注入')
total_diff += diff

# /fast: notifier helper 和 baseVariant helper 在版本间会变（AgH/RgH, iWR/bWR）
pat_fast = (
    rb'execute:\(H,T\)=>\{let\{addMessage:R\}=T,A=H\[0\]\?\.toLowerCase\(\);'
    rb'if\(A&&A!=="on"&&A!=="off"\)return (' + V + rb')\(R,`Invalid argument "\$\{H\[0\]\}"\. Usage: /fast, /fast on, or /fast off`\),\{handled:!0\};'
    rb'let L=iT\(\),D=L.getModel\(\),C=!A\|\|A==="on",h=!!(' + V + rb')\(D\);'
    rb'if\(C&&h\)\{let Q=yB\(D\);return \1\(R,`Already in fast mode \(\$\{Q\.shortDisplayName\|\|D\}\)`\),\{handled:!0\}\}'
    rb'if\(!C&&!h\)\{let Q=yB\(D\);return \1\(R,`Already using base model \(\$\{Q\.shortDisplayName\|\|D\}\)`\),\{handled:!0\}\}'
    rb'let \$=C\?bI9\(D\):\2\(D\);'
    rb'if\(!\$\)\{let E=`No fast mode available for \$\{yB\(D\)\.shortDisplayName\|\|D\}`;return \1\(R,E\),\{handled:!0\}\}'
    rb'try\{L\.setModel\(\$\)\}catch\(Q\)\{let E=Q instanceof Error\?Q\.message:"Failed to switch model";return \1\(R,E\),\{handled:!0\}\}'
    rb'let W=yB\(\$\);return \1\(R,`Switched to \$\{W\.shortDisplayName\|\|\$\}`\),\{handled:!0\}\}'
)


def repl_fast(m):
    notify = m.group(1)
    base_helper = m.group(2)
    return (
        b'execute:(H,T)=>{let{addMessage:R}=T,A=H[0]?.toLowerCase();if(A&&A!=="on"&&A!=="off")return ' + notify + b'(R,`Bad arg "${H[0]}". Use /fast [on|off]`),{handled:!0};'
        b'let L=iT(),D=L.getModel(),C=!A||A==="on",B=D[6]===":",Q=yB(D),h=B?L.sessionSettings.fast===D:!!' + base_helper + b'(D),$=B?D:C?bI9(D):' + base_helper + b'(D);'
        b'if(C&&h)return ' + notify + b'(R,`Already fast (${Q.shortDisplayName||D})`),{handled:!0};'
        b'if(!C&&!h)return ' + notify + b'(R,`Already base (${Q.shortDisplayName||D})`),{handled:!0};'
        b'if(B){if(C&&!bI9(Q.id))$=void 0;else L.sessionSettings.fast=C?D:"",L.currentSessionId&&L.saveSessionSettings({async:!0,shouldSyncToCloud:!0})}'
        b'if(!$)return ' + notify + b'(R,`No fast for ${Q.shortDisplayName||D}`),{handled:!0};'
        b'try{B||L.setModel($)}catch(h){return ' + notify + b'(R,h instanceof Error?h.message:"Switch failed"),{handled:!0}}'
        b'return ' + notify + b'(R,B?`Fast ${C?"on":"off"} (${Q.shortDisplayName||D})`:`Switched to ${yB($).shortDisplayName||$}`),{handled:!0}}'
    )


data, diff = replace_regex(data, pat_fast, repl_fast, '/fast 命令改为支持 custom model')
total_diff += diff

for old, new, name in [
    (
        b'Enable fast mode for the current model (/fast off to disable)',
        b'Toggle fast mode now',
        'fast 描述补偿',
    ),
    (
        b'Favorite the current session for quick access',
        b'Favorite session',
        'favorite 描述补偿',
    ),
    (
        b'Fork the current session',
        b'Fork session',
        'fork 描述补偿',
    ),
    (
        b'Generate a blog post style semantic diff for changes',
        b'Generate semantic diff',
        'generate_blog 描述补偿',
    ),
    (
        b'Install and set up Git AI for tracking AI-generated code attribution',
        b'Install and set up Git AI',
        'git-ai 描述补偿',
    ),
]:
    data, diff = replace_exact(data, old, new, name)
    total_diff += diff

assert total_diff == 0, f'mod10 总字节变化异常: {total_diff:+d}'
assert len(data) == original_size, f'mod10 大小变化 {len(data) - original_size:+d} bytes'

save_droid(data)
print('mod10 完成 (net 0 bytes)')

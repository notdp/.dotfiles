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
  3. 针对旧版/0.80.0 两套二进制结构分别补丁，并通过描述字符串补偿回 0 bytes
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


def has_regex(blob, pattern):
    return re.search(pattern, blob) is not None


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

legacy_pat_j = (
    rb'EH=zK\(FH,KH\)\?\?null,wH=EH\?EH\.model:FH,LH=yB\(FH\)\.modelProvider,'
    rb'vH,(' + V + rb')=EH\?(' + V + rb')\(EH\.model\):FH;'
    rb'if\(\1\)try\{vH=kz\(\{modelId:\1\}\)\}catch\{\}'
    rb'return\{model:wH,provider:LH,apiModelProvider:vH\?\.apiModelProvider,config:vH,customModel:EH,isSpecMode:NH,reasoningEffort:_H\}'
)


def repl_legacy_j(m):
    resolved_var = m.group(1)
    base_helper = m.group(2)
    return (
        b'EH=zK(FH,KH)??null,QH=iT().sessionSettings.fast===FH,wH=EH?EH.model:FH,LH=yB(FH).modelProvider,'
        b'vH,' + resolved_var + b'=EH?(QH?bI9(EH.model)??' + base_helper + b'(EH.model):' + base_helper + b'(EH.model)):FH;'
        b'if(' + resolved_var + b')try{vH=kz({modelId:' + resolved_var + b'})}catch{}'
        b'return{model:wH,provider:LH,apiModelProvider:vH?.apiModelProvider,config:vH,customModel:EH,isSpecMode:NH,reasoningEffort:_H}'
    )


legacy_pat_fast = (
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


def repl_legacy_fast(m):
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


def apply_replacements(items):
    global data, total_diff
    for old, new, name in items:
        data, diff = replace_exact(data, old, new, name)
        total_diff += diff


if has_regex(data, legacy_pat_j) and has_regex(data, legacy_pat_fast):
    pat_bi9 = rb'function bI9\(H\)\{let T=zi\(H\);return T\?(' + V + rb')\.get\(T\):void 0\}'
    pat_base = rb'function (' + V + rb')\(H\)\{let T=zi\(H\);return T\?aG\[T\]\?\.baseVariant:void 0\}'

    def repl_bi9(m):
        mapping = m.group(1)
        return b'function bI9(H){return ' + mapping + b'.get(zi(H))}'

    def repl_base(m):
        fn = m.group(1)
        return b'function ' + fn + b'(H){return aG[zi(H)]?.baseVariant}'

    data, diff = replace_regex(data, pat_bi9, repl_bi9, 'bI9 等价缩写')
    total_diff += diff
    data, diff = replace_regex(data, pat_base, repl_base, 'baseVariant helper 等价缩写')
    total_diff += diff
    data, diff = replace_regex(data, legacy_pat_j, repl_legacy_j, 'j() custom fast 请求注入')
    total_diff += diff
    data, diff = replace_regex(data, legacy_pat_fast, repl_legacy_fast, '/fast 命令改为支持 custom model')
    total_diff += diff
else:
    current_j_old = (
        b'let FH=NH?.isSpecMode??H.isSpecMode(),_H=NH?.modelId??(FH?H.getSpecModeModel():H.getModel()),'
        b'KH=NH?.reasoningEffort??(FH?H.getSpecModeReasoningEffort():H.getReasoningEffort()),EH=mR().getCustomModels(),'
        b'wH=SK(_H,EH)??null,LH=wH?wH.model:_H,jH=yB(_H).modelProvider,VH,PH=wH?AJH(wH.model):_H;'
        b'if(PH)try{VH=DY({modelId:PH})}catch{}return{model:LH,provider:jH,apiModelProvider:VH?.apiModelProvider,config:VH,customModel:wH,isSpecMode:FH,reasoningEffort:KH}'
    )
    current_j_new = (
        b'let _H=NH?.isSpecMode??H.isSpecMode(),FH=NH?.modelId??(_H?H.getSpecModeModel():H.getModel()),'
        b'KH=NH?.reasoningEffort??(_H?H.getSpecModeReasoningEffort():H.getReasoningEffort()),EH=mR().getCustomModels(),'
        b'QH=iT().sessionSettings.fast===FH,wH=SK(FH,EH)??null,LH=wH?wH.model:FH,jH=yB(FH).modelProvider,VH,'
        b'PH=wH?(QH?H$9(wH.model)??AJH(wH.model):AJH(wH.model)):FH;if(PH)try{VH=DY({modelId:PH})}catch{}'
        b'return{model:LH,provider:jH,apiModelProvider:VH?.apiModelProvider,config:VH,customModel:wH,isSpecMode:_H,reasoningEffort:KH}'
    )
    current_fast_old = (
        b'execute:(H,T)=>{let{addMessage:R}=T,A=H[0]?.toLowerCase();if(A&&A!=="on"&&A!=="off")return '
        b'qgH(R,`Invalid argument "${H[0]}". Usage: /fast, /fast on, or /fast off`),{handled:!0};'
        b'let L=iT(),D=L.getModel(),C=!A||A==="on",h=!!oWR(D);if(C&&h){let Q=yB(D);return '
        b'qgH(R,`Already in fast mode (${Q.shortDisplayName||D})`),{handled:!0}}'
        b'if(!C&&!h){let Q=yB(D);return qgH(R,`Already using base model (${Q.shortDisplayName||D})`),{handled:!0}}'
        b'let $=C?H$9(D):oWR(D);if(!$){let E=`No fast mode available for ${yB(D).shortDisplayName||D}`;'
        b'return qgH(R,E),{handled:!0}}try{L.setModel($)}catch(Q){let E=Q instanceof Error?Q.message:"Failed to switch model";'
        b'return qgH(R,E),{handled:!0}}let W=yB($);return qgH(R,`Switched to ${W.shortDisplayName||$}`),{handled:!0}}'
    )
    current_fast_new = (
        b'execute:(H,T)=>{let{addMessage:R}=T,A=H[0]?.toLowerCase();if(A&&A!=="on"&&A!=="off")return '
        b'qgH(R,`Bad arg "${H[0]}". Use /fast [on|off]`),{handled:!0};'
        b'let L=iT(),D=L.getModel(),C=!A||A==="on",B=D[6]===":",Q=yB(D),h=B?L.sessionSettings.fast===D:!!oWR(D),'
        b'$=B?D:C?H$9(D):oWR(D);if(C&&h)return qgH(R,`Already fast (${Q.shortDisplayName||D})`),{handled:!0};'
        b'if(!C&&!h)return qgH(R,`Already base (${Q.shortDisplayName||D})`),{handled:!0};'
        b'if(B){if(C&&!H$9(Q.id))$=void 0;else L.sessionSettings.fast=C?D:"",'
        b'L.currentSessionId&&L.saveSessionSettings({async:!0,shouldSyncToCloud:!0})}'
        b'if(!$)return qgH(R,`No fast for ${Q.shortDisplayName||D}`),{handled:!0};'
        b'try{B||L.setModel($)}catch(h){return qgH(R,h instanceof Error?h.message:"Switch failed"),{handled:!0}}'
        b'return qgH(R,B?`Fast ${C?"on":"off"} (${Q.shortDisplayName||D})`:`Switched to ${yB($).shortDisplayName||$}`),{handled:!0}}'
    )

    data, diff = replace_exact(data, current_j_old, current_j_new, 'j() custom fast 请求注入')
    total_diff += diff
    data, diff = replace_exact(data, current_fast_old, current_fast_new, '/fast 命令改为支持 custom model')
    total_diff += diff
    apply_replacements([
        (b'Show settings configuration errors', b'Show config issue', 'status 描述补偿'),
        (b'Manage plugins and marketplaces', b'Manage plugins', 'plugins 描述补偿'),
    ])


apply_replacements([
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
])

assert total_diff == 0, f'mod10 总字节变化异常: {total_diff:+d}'
assert len(data) == original_size, f'mod10 大小变化 {len(data) - original_size:+d} bytes'

save_droid(data)
print('mod10 完成 (net 0 bytes)')

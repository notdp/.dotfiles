#!/usr/bin/env python3
"""mod10: custom model /fast support

Robust approach:
- Phase 1: find fast_fn/base_fn from function definitions (small regex, stable)
- Phase 2: find /fast handler by anchor string, extract names with small patterns
  - handler_start: rfind execute: before anchor
  - handler_end: last {handled:!0}} within handler_start + 1200B
  - No giant regex — tolerant of async, extra checks, rearranged code
- Phase 3: j() function patch (structural regex, stable method/property names)
- Phase 4: replace /fast handler
- Phase 5: byte compensation
"""
import re
import sys

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

if b'.sessionSettings.fast=C?D:""' in data:
    print('mod10 已应用，跳过')
    sys.exit(0)

total_diff = 0

# ============================================================
# Phase 1: discover fast_fn, base_fn from their definitions
# ============================================================
# Anchors: function signature + .get(T) / .baseVariant — stable

fast_fn_pat = (
    rb'function (' + V + rb')\(H\)\{let T=(' + V + rb')\(H\);'
    rb'return T\?(' + V + rb')\.get\(T\):void 0\}'
)
fast_fn_matches = list(re.finditer(fast_fn_pat, data))
assert len(fast_fn_matches) == 1, f'fast variant: expected 1, found {len(fast_fn_matches)}'
fast_fn = fast_fn_matches[0].group(1)
zi_fn = fast_fn_matches[0].group(2)

base_fn_pat = (
    rb'function (' + V + rb')\(H\)\{let T=' + re.escape(zi_fn) +
    rb'\(H\);return T\?(' + V + rb')\[T\]\?\.baseVariant:void 0\}'
)
base_fn_m = re.search(base_fn_pat, data)
assert base_fn_m, 'base variant function not found'
base_fn = base_fn_m.group(1)

print(f'Phase1: fast={fast_fn.decode()}, base={base_fn.decode()}, resolver={zi_fn.decode()}')

# ============================================================
# Phase 2: find /fast handler boundaries + extract names
# ============================================================
# Anchor: "Usage: /fast, /fast on, or /fast off" — unique, stable

ANCHOR = b'Usage: /fast, /fast on, or /fast off'

def find_fast_handler(data):
    """Find /fast handler [start, end) by anchor + boundary detection."""
    anchor_pos = data.find(ANCHOR)
    assert anchor_pos >= 0, '/fast anchor not found'

    # handler_start: execute: before anchor (within 300B — handler preamble is ~130B)
    start = data.rfind(b'execute:', max(0, anchor_pos - 300), anchor_pos)
    assert start >= 0, 'execute: not found before anchor'

    # handler_end: last {handled:!0}} within handler body
    # handler is typically ~900B; 1200B gives margin without hitting next command
    MARKER = b'{handled:!0}}'
    search_end = start + 1200
    last_end = -1
    pos = start
    while True:
        idx = data.find(MARKER, pos, search_end)
        if idx < 0:
            break
        last_end = idx + len(MARKER)
        pos = idx + 1
    assert last_end >= 0, 'handler end not found'

    return start, last_end

handler_start, handler_end = find_fast_handler(data)
handler = data[handler_start:handler_end]
print(f'Phase2: handler [{handler_start}:{handler_end}] ({len(handler)}B)')

# Extract names with small, independent patterns — no structural dependency
notify_m = re.search(rb'(' + V + rb')\(R,`Invalid argument', handler)
assert notify_m, 'notify fn not found'
notify_fn = notify_m.group(1)

state_m = re.search(rb'let L=(' + V + rb')\(\),D=L\.getModel\(\)', handler)
assert state_m, 'state fn not found'
state_fn = state_m.group(1)

info_m = re.search(rb'(' + V + rb')\(D\)\.shortDisplayName', handler)
assert info_m, 'info fn not found'
info_fn = info_m.group(1)

print(f'Phase2: notify={notify_fn.decode()}, state={state_fn.decode()}, info={info_fn.decode()}')

# ============================================================
# Phase 3: patch j() function
# ============================================================
# Anchors: isSpecMode, getSpecModeModel, getCustomModels, apiModelProvider — method names

j_pat = (
    rb'(?P<arg>' + V + rb')\)=>\{let (?P<isSpec>' + V + rb')=(?P=arg)\?\.isSpecMode\?\?H\.isSpecMode\(\),'
    rb'(?P<model>' + V + rb')=(?P=arg)\?\.modelId\?\?'
    rb'\((?P=isSpec)\?H\.getSpecModeModel\(\):H\.getModel\(\)\),'
    rb'(?P<effort>' + V + rb')=(?P=arg)\?\.reasoningEffort\?\?'
    rb'\((?P=isSpec)\?H\.getSpecModeReasoningEffort\(\):H\.getReasoningEffort\(\)\),'
    rb'(?P<customs>' + V + rb')=(?P<customsFn>' + V + rb')\(\)\.getCustomModels\(\),'
    rb'(?P<cm>' + V + rb')=(?P<lookupFn>' + V + rb')\((?P=model),(?P=customs)\)\?\?null,'
    rb'(?P<modelOut>' + V + rb')=(?P=cm)\?(?P=cm)\.model:(?P=model),'
    rb'(?P<prov>' + V + rb')=(?P<infoFn>' + V + rb')\((?P=model)\)\.modelProvider,'
    rb'(?P<config>' + V + rb'),'
    rb'(?P<resolved>' + V + rb')=(?P=cm)\?'
    rb'(?P<helperFn>' + V + rb')\((?P=cm)\.model\):(?P=model);'
    rb'if\((?P=resolved)\)try\{(?P=config)='
    rb'(?P<resolverFn>' + V + rb')\(\{modelId:(?P=resolved)\}\)\}catch\{\}'
    rb'return\{model:(?P=modelOut),provider:(?P=prov),'
    rb'apiModelProvider:(?P=config)\?\.apiModelProvider,'
    rb'config:(?P=config),customModel:(?P=cm),'
    rb'isSpecMode:(?P=isSpec),reasoningEffort:(?P=effort)\}'
)

j_m = re.search(j_pat, data)
assert j_m, 'j() function not found'
d = j_m.groupdict()

j_new = (
    d['arg'] + b')=>{let ' + d['isSpec'] + b'=' + d['arg'] + b'?.isSpecMode??H.isSpecMode(),'
    + d['model'] + b'=' + d['arg'] + b'?.modelId??('
    + d['isSpec'] + b'?H.getSpecModeModel():H.getModel()),'
    + d['effort'] + b'=' + d['arg'] + b'?.reasoningEffort??('
    + d['isSpec'] + b'?H.getSpecModeReasoningEffort():H.getReasoningEffort()),'
    + d['customs'] + b'=' + d['customsFn'] + b'().getCustomModels(),'
    + b'W0=' + state_fn + b'().sessionSettings.fast===' + d['model'] + b','
    + d['cm'] + b'=' + d['lookupFn'] + b'('
    + d['model'] + b',' + d['customs'] + b')??null,'
    + d['modelOut'] + b'=' + d['cm'] + b'?' + d['cm'] + b'.model:'
    + d['model'] + b','
    + d['prov'] + b'=' + d['infoFn'] + b'(' + d['model'] + b').modelProvider,'
    + d['config'] + b','
    + d['resolved'] + b'=' + d['cm'] + b'?(W0?'
    + fast_fn + b'(' + d['cm'] + b'.model)??'
    + d['helperFn'] + b'(' + d['cm'] + b'.model):'
    + d['helperFn'] + b'(' + d['cm'] + b'.model)):'
    + d['model'] + b';'
    + b'if(' + d['resolved'] + b')try{' + d['config'] + b'='
    + d['resolverFn'] + b'({modelId:' + d['resolved'] + b'})}catch{}'
    + b'return{model:' + d['modelOut'] + b',provider:' + d['prov'] + b','
    + b'apiModelProvider:' + d['config'] + b'?.apiModelProvider,'
    + b'config:' + d['config'] + b',customModel:' + d['cm'] + b','
    + b'isSpecMode:' + d['isSpec'] + b',reasoningEffort:' + d['effort'] + b'}'
)

j_diff = len(j_new) - len(j_m.group(0))
data = data[:j_m.start()] + j_new + data[j_m.end():]
total_diff += j_diff
print(f'Phase3: j() {j_diff:+d}B')

# ============================================================
# Phase 4: re-find and replace /fast handler (offsets shifted by j() patch)
# ============================================================

handler_start2, handler_end2 = find_fast_handler(data)

fast_new = (
    b'execute:(H,T)=>{let{addMessage:R}=T,A=H[0]?.toLowerCase();'
    b'if(A&&A!=="on"&&A!=="off")return '
    + notify_fn + b'(R,`Bad arg "${H[0]}". Use /fast [on|off]`),{handled:!0};'
    b'let L=' + state_fn + b'(),D=L.getModel(),C=!A||A==="on",'
    b'B=D[6]===":",Q=' + info_fn + b'(D),'
    b'h=B?L.sessionSettings.fast===D:!!' + base_fn + b'(D),'
    b'$=B?D:C?' + fast_fn + b'(D):' + base_fn + b'(D);'
    b'if(C&&h)return ' + notify_fn
    + b'(R,`Already fast (${Q.shortDisplayName||D})`),{handled:!0};'
    b'if(!C&&!h)return ' + notify_fn
    + b'(R,`Already base (${Q.shortDisplayName||D})`),{handled:!0};'
    b'if(B){if(C&&!' + fast_fn + b'(Q.id))$=void 0;'
    b'else L.sessionSettings.fast=C?D:"",'
    b'L.currentSessionId&&L.saveSessionSettings('
    b'{async:!0,shouldSyncToCloud:!0})}'
    b'if(!$)return ' + notify_fn
    + b'(R,`No fast for ${Q.shortDisplayName||D}`),{handled:!0};'
    b'try{B||L.setModel($)}catch(h){return ' + notify_fn
    + b'(R,h instanceof Error?h.message:"Switch failed"),{handled:!0}}'
    b'return ' + notify_fn + b'(R,B?`Fast ${C?"on":"off"} '
    b'(${Q.shortDisplayName||D})`:`Switched to ${'
    + info_fn + b'($).shortDisplayName||$}`),{handled:!0}}'
)

fast_diff = len(fast_new) - (handler_end2 - handler_start2)
data = data[:handler_start2] + fast_new + data[handler_end2:]
total_diff += fast_diff
print(f'Phase4: /fast {fast_diff:+d}B')

# ============================================================
# Phase 5: byte compensation
# ============================================================

COMP_POOL = [
    (b'Install and set up Git AI for tracking AI-generated code attribution',
     b'Install and set up Git AI'),
    (b'Enable fast mode for the current model (/fast off to disable)',
     b'Toggle fast mode now'),
    (b'Generate a blog post style semantic diff for changes',
     b'Generate semantic diff'),
    (b'Favorite the current session for quick access',
     b'Favorite session'),
    (b'Show settings configuration errors',
     b'Show config issue'),
    (b'Manage plugins and marketplaces',
     b'Manage plugins'),
    (b'Fork the current session',
     b'Fork session'),
]

if total_diff > 0:
    remaining = total_diff
    for old, new in COMP_POOL:
        if remaining <= 0:
            break
        if old not in data:
            continue
        savings = len(old) - len(new)
        if savings <= remaining:
            data = data.replace(old, new, 1)
            remaining -= savings
            print(f'  comp -{savings}B: {new.decode()}')
        else:
            padded = new + b' ' * (savings - remaining)
            data = data.replace(old, padded, 1)
            print(f'  comp -{remaining}B (partial): {new.decode()}')
            remaining = 0
    if remaining > 0:
        print(f'ERROR: compensation insufficient by {remaining}B')
        save_droid(data)
        sys.exit(1)
elif total_diff < 0:
    # Pad a help text string to absorb negative diff
    for old, new in COMP_POOL:
        if old in data:
            padded = b' ' * (-total_diff) + old
            data = data.replace(old, padded, 1)
            print(f'  pad +{-total_diff}B before: {old[:40].decode()}...')
            break
    else:
        print(f'WARNING: negative diff {total_diff}B, no padding target found')

final_diff = len(data) - original_size
assert final_diff == 0, f'size mismatch: {final_diff:+d}B'

save_droid(data)
print(f'mod10 done (net 0B)')

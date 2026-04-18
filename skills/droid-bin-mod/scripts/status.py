#!/usr/bin/env python3
"""检查 droid 当前状态：原版/已修改/部分修改，以及 settings.json 配置"""
import json
import re
from pathlib import Path

droid = Path.home() / '.local/bin/droid'
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'

with open(droid, 'rb') as f:
    data = f.read()

results = {}
DESCRIPTIONS = {}

# mod1: 截断条件
DESCRIPTIONS['mod1'] = '截断条件'
if b'if(!0||!' in data:
    results['mod1'] = 'modified'
elif re.search(rb'if\(!' + V + rb'&&!' + V + rb'\)return\{text:' + V + rb',isTruncated:!1\}', data):
    results['mod1'] = 'original'
else:
    results['mod1'] = 'unknown'

# mod2: 命令长度阈值
DESCRIPTIONS['mod2'] = '命令长度'
if b'command.length>99' in data:
    results['mod2'] = 'modified'
elif b'command.length>50' in data:
    results['mod2'] = 'original'
else:
    results['mod2'] = 'unknown'

# mod3: 输出行数 (含 exec hint)
DESCRIPTIONS['mod3'] = '输出行数'
# v0.104.0+: maxLines:VAR?VAR:99 (新)  vs  maxLines:VAR?VAR:8 (原版)
# v0.96-0.99: VAR=99||4 (新) vs VAR=VAR?8:4 (原版)
if re.search(rb'maxLines:[a-zA-Z0-9_$]{1,4}\?[a-zA-Z0-9_$]{1,4}:99', data):
    results['mod3'] = 'modified'
elif re.search(rb'maxLines:[a-zA-Z0-9_$]{1,4}\?[a-zA-Z0-9_$]{1,4}:8', data):
    results['mod3'] = 'original'
elif re.search(V + rb'=99\|\|4', data):
    results['mod3'] = 'modified'
elif re.search(V + rb'=' + V + rb'\?8:4', data):
    results['mod3'] = 'original'
else:
    results['mod3'] = 'unknown'

# mod4: diff 行数
DESCRIPTIONS['mod4'] = 'diff 行数'
if re.search(rb'var ' + V + rb'=99,' + V, data):
    results['mod4'] = 'modified'
elif re.search(rb'var ' + V + rb'=20,' + V, data):
    results['mod4'] = 'original'
else:
    results['mod4'] = 'unknown'

# mod5: Ctrl+N custom model cycle
DESCRIPTIONS['mod5'] = 'Ctrl+N cycle'
# 使用正则兼容不同 minified 函数名（UR/GR 等）
if re.search(rb'=[A-Za-z_$][A-Za-z0-9_$]{0,3}\(\)\.getCustomModels\(\)\.map\(\(gA\)=>gA\.id\);if\(RR\.length<=1\)return;', data):
    results['mod5'] = 'modified'
elif re.search(rb'useCallback\(\(\)=>\{if\(' + V + rb'\.length<=1\)return;let ' + V + rb'=' + V + rb'\(\)\.getModelPolicy', data):
    results['mod5'] = 'original'
else:
    results['mod5'] = 'unknown'

# mod6: mission 模型白名单
DESCRIPTIONS['mod6'] = 'mission 模型'
def _mod6_detect():
    has_orig1 = bool(re.search(V + rb'\.includes\(' + V + rb'\)\)\{if\(!' + V, data))
    has_orig2 = bool(re.search(rb'if\(!\(' + V + rb'\.includes\(' + V + rb'\)&&' + V + rb'\.includes\(', data))
    has_mod1 = bool(re.search(rb'!0\s+\)\{if\(!' + V, data))
    has_mod2 = bool(re.search(rb'if\(!\(!0\s+&&' + V + rb'\.includes\(', data))
    if has_mod1 and has_mod2:
        return 'modified'
    elif has_orig1 and has_orig2:
        return 'original'
    elif has_mod1 or has_mod2:
        return 'partial'
    return 'unknown'
results['mod6'] = _mod6_detect()

# mod7: custom model effort 级别
DESCRIPTIONS['mod7'] = 'effort 级别'
mod7_pa_count = len(re.findall(rb'\.provider=="openai"\?\["none","low","medium","high","xhigh"\]', data))
mod7_orig_pat = rb'supportedReasoningEfforts:' + V + rb'\?\["off","low","medium","high"\]:\["none"\],defaultReasoningEffort:' + V + rb'\.reasoningEffort'
mod7_orig_count = len(re.findall(mod7_orig_pat, data))
if mod7_pa_count >= 2:
    results['mod7'] = 'modified'
elif mod7_pa_count == 0 and mod7_orig_count >= 2:
    results['mod7'] = 'original'
elif mod7_pa_count >= 1:
    results['mod7'] = 'partial'
else:
    results['mod7'] = 'unknown'

# mod8: summarizer openai fix
DESCRIPTIONS['mod8'] = 'summarizer/compress fix'
# Find lxH-equivalent function name dynamically
_lxH_match = re.search(
    rb'function ([A-Za-z_$][A-Za-z0-9_$]{0,5})\(' + V + rb'\)\{return ' + V +
    rb'==="openai"\|\|' + V + rb'==="xai"\}', data)
_lxH = _lxH_match.group(1) if _lxH_match else None

def _mod8_detect():
    if _lxH:
        # v0.99.0+: uses lxH(provider) function call
        byok_patched = bool(re.search(
            _lxH + rb'\(' + V + rb'\.provider\)&&!1\)return\(await ' + V +
            rb'\.responses\.create\(', data))
        byok_original = bool(re.search(
            rb'if\(' + _lxH + rb'\(' + V + rb'\.provider\)\)return\(await ' + V +
            rb'\.responses\.create\(', data))
        proxy_patched = bool(re.search(
            _lxH + rb'\(' + V + rb'\)&&!1\)return\(await ' + V +
            rb'\.responses\.create\(\{model:' + V + rb',input:' + V +
            rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
            rb'\},\{headers:', data))
        proxy_original = bool(re.search(
            rb'if\(' + _lxH + rb'\(' + V + rb'\)\)return\(await ' + V +
            rb'\.responses\.create\(\{model:' + V + rb',input:' + V +
            rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
            rb'\},\{headers:', data))
        if byok_patched and proxy_patched:
            return 'modified'
        elif byok_original and proxy_original:
            return 'original'
        elif byok_patched or proxy_patched:
            return 'partial'
    # v0.96.0 legacy: uses provider==="openai" direct check
    legacy_patched = bool(re.search(rb'provider==="openai"&&!1\)return\(await new ' + V, data))
    legacy_original = bool(re.search(rb'provider==="openai"\)return\(await new ' + V, data))
    if legacy_patched:
        return 'modified'
    elif legacy_original:
        return 'original'
    return 'unknown'
results['mod8'] = _mod8_detect()

# mod9: 禁用自动更新 (可选)
DESCRIPTIONS['mod9'] = '禁用自动更新'
if b'checkForUpdates(){return null;/*' in data:
    results['mod9'] = 'modified'
elif b'async checkForUpdates(){' in data:
    results['mod9'] = 'original'
else:
    results['mod9'] = 'unknown'

# mod10: tag strip fix (ym9 找不到闭标签时不截断)
DESCRIPTIONS['mod10'] = 'tag strip fix'
mod10_pat_fixed = re.compile(rb'if\(([A-Za-z])<0\)\{([A-Za-z])=\2\.slice\(0  \);break\}')
mod10_pat_orig = re.compile(rb'if\(([A-Za-z])<0\)\{([A-Za-z])=\2\.slice\(0,([A-Za-z])\);break\}')
_fixed = len(list(mod10_pat_fixed.finditer(data)))
_orig = len(list(mod10_pat_orig.finditer(data)))
if _fixed >= 2 and _orig == 0:
    results['mod10'] = 'modified'
elif _orig >= 2 and _fixed == 0:
    results['mod10'] = 'original'
elif _fixed >= 1 and _orig >= 1:
    results['mod10'] = 'partial'
else:
    results['mod10'] = 'unknown'

# mod11: unicode escape fix (YcM/NcM parser)
DESCRIPTIONS['mod11'] = 'unicode escape fix'
mod11_patched_count = len(re.findall(
    rb'default:[A-Z]=="u"\?\(A\+=String\.fromCharCode\(parseInt\(H\.slice\([A-Z]\+1,[A-Z]\+5\),16\)\),[A-Z]\+=4\):A\+=[A-Z];break\}\}else A\+=H\[',
    data))
mod11_original_count = len(re.findall(
    rb'default:A\+=[A-Z];break\}\}else A\+=H\[[A-Z]\];[A-Z]\+\+',
    data))
if mod11_patched_count >= 2:
    results['mod11'] = 'modified'
elif mod11_patched_count == 0 and mod11_original_count >= 2:
    results['mod11'] = 'original'
elif mod11_patched_count >= 1:
    results['mod11'] = 'partial'
else:
    results['mod11'] = 'unknown'

# mod12: unicode proxy fix (wU$ preprocess)
DESCRIPTIONS['mod12'] = 'unicode proxy fix'
if b'H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,' in data:
    results['mod12'] = 'modified'
elif re.search(rb'function ' + V + rb'\(H\)\{if\(!H\.trim\(\)\)return\{data:\{\},isComplete:!1\};', data) and b'H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,' not in data:
    results['mod12'] = 'original'
else:
    results['mod12'] = 'unknown'

# 输出
REQUIRED = ['mod1', 'mod2', 'mod3', 'mod4', 'mod5', 'mod6', 'mod7', 'mod8']
OPTIONAL = ['mod9', 'mod10', 'mod11', 'mod12']
total = len(REQUIRED)
mod_count = sum(1 for k in REQUIRED if results.get(k) == 'modified')

print(f"droid 状态:\n")
for name in list(REQUIRED) + list(OPTIONAL):
    status = results.get(name, 'unknown')
    icon = '✓' if status == 'modified' else '○' if status == 'original' else '△' if status == 'partial' else '?'
    label = {'modified': '已修改', 'original': '原版', 'partial': '部分', 'unknown': '未知'}[status]
    opt = ' (可选)' if name in OPTIONAL else ''
    desc = DESCRIPTIONS.get(name, '')
    print(f"  {icon} {name}: {label}  {desc}{opt}")

print()
if mod_count == total:
    print(f"结论: 已修改 ({mod_count}/{total})")
else:
    print(f"结论: 部分修改 ({mod_count}/{total})")

# === settings.json 配置检查 ===
settings_path = Path.home() / '.factory/settings.json'
if not settings_path.exists():
    print(f"\n⚠ settings.json 不存在: {settings_path}")
else:
    try:
        cfg = json.loads(settings_path.read_text())
    except Exception as e:
        print(f"\n⚠ settings.json 解析失败: {e}")
        cfg = None

    if cfg:
        print(f"\nsettings.json 配置检查:\n")
        models = cfg.get('customModels', [])
        if not models:
            print("  ⚠ customModels 为空，未配置任何自定义模型")
        else:
            warnings = []
            for m in models:
                mid = m.get('id', '?')
                name = m.get('displayName', mid)
                provider = m.get('provider', '?')
                effort = m.get('reasoningEffort')
                extra = m.get('extraArgs', {})

                issues = []
                has_mod7 = results.get('mod7') == 'modified'

                if provider == 'anthropic':
                    if not effort:
                        issues.append('缺少 reasoningEffort (建议 "high")')
                    thinking = extra.get('thinking', {})
                    oc = extra.get('output_config', {})
                    removable = []
                    if thinking:
                        removable.append('thinking')
                    if oc.get('effort'):
                        removable.append('output_config.effort')
                    if removable:
                        issues.append(
                            f'extraArgs 中的 {" 和 ".join(removable)} 已不需要'
                            '（Droid 内置 reasoningEffort 已接管）')
                elif provider == 'openai':
                    if not effort:
                        issues.append('缺少 reasoningEffort (建议 "high")')
                    reasoning = extra.get('reasoning', {})
                    if reasoning:
                        issues.append(
                            'extraArgs 中的 reasoning 对象必须移除'
                            '（会覆盖 requestParams.reasoning，导致 Tab 切换 Thinking Level 无效'
                            + ('; mod7 已解锁 xhigh' if has_mod7 else '') + '）')

                icon = '✓' if not issues else '⚠'
                print(f"  {icon} {name} [{provider}]")
                if effort:
                    print(f"    reasoningEffort: {effort}")
                for issue in issues:
                    print(f"    ⚠ {issue}")
                    warnings.append((name, issue))

            mission = cfg.get('missionModelSettings', {})
            model_ids = [m.get('id', '') for m in models]
            if mission:
                print(f"\n  missionModelSettings:")
                wm = mission.get('workerModel', '')
                vm = mission.get('validationWorkerModel', '')
                we = mission.get('workerReasoningEffort', '')
                ve = mission.get('validationWorkerReasoningEffort', '')
                print(f"    Worker:    {wm} ({we})")
                print(f"    Validator: {vm} ({ve})")

            if not warnings:
                print("\n  配置正常 ✓")

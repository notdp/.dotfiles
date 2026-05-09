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

# 已归档（不再参与状态检测）: mod-hide-command-truncation, mod-expand-diff-lines
# 归档文件: mods/_archive/

# mod-cycle-custom-model: Ctrl+N 预览与选择器只显示 custom models
def _mod_cycle_custom_model_detect():
    selector_core_count = len(re.findall(
        rb'(?P<items>' + V + rb')\.push\(\.\.\.(?P<custom>' + V + rb')\.map\(\((?P<item>' + V + rb')\)=>\{let (?P<check>' + V + rb')=(?P<access>' + V + rb')\((?P=item)\.id,(?P<policy>' + V + rb'),(?P=item)\);return\{type:"model",id:(?P=item)\.id,disabled:!(?P=check)\.allowed\}\}\)\);',
        data,
    ))
    tw_core = re.search(
        rb'(?P<models>' + V + rb')=(?P<svc>' + V + rb')\(\)\.getCustomModels\(\)\.map\(m=>m\.id\),(?P<empty>' + V + rb')=!(?P=svc)\(\)\.hasAnyAvailableModel\((?P=models)\),',
        data,
    )
    selector_original_count = len(re.findall(
        rb'(?P<items>' + V + rb')\.push\(\{type:"header",label:(?:(?P<mission>' + V + rb')\?)?(?P<tfn>' + V + rb')\("common:(?:missionModelPicker\.recommendedHeader|modelSelector\.factoryModelsHeader)"\)(?::\s*(?P=tfn)\("common:modelSelector\.factoryModelsHeader"\))?\}\);'
        rb'let (?P<recommended>' + V + rb')=(?P<factory>' + V + rb')\.map\(\((?P<fitem>' + V + rb')\)=>\{let (?P<fcheck>' + V + rb')=(?P<access>' + V + rb')\((?P=fitem),(?P<policy>' + V + rb')\);return\{type:"model",id:(?P=fitem),disabled:!(?P=fcheck)\.allowed\}\}\),',
        data,
    ))
    if selector_core_count > 0 and selector_original_count == 0 and tw_core:
        return 'modified'
    if selector_core_count > 0 or selector_original_count > 0 or tw_core:
        return 'partial'

    tw_original = re.search(
        rb'(?P<prefix>,)(?P<models>' + V + rb')=(?P<src>' + V + rb')\(\),(?P<empty>' + V + rb')=!(?P<svc>' + V + rb')\(\)\.hasAnyAvailableModel\((?P=models)\),',
        data,
    )
    if selector_original_count > 0 and tw_original:
        return 'original'
    return 'unknown'

results['mod-cycle-custom-model'] = _mod_cycle_custom_model_detect()

# mod-fix-multiline-history-down: 多行历史记录按↓修复
# 修改后: V(),!0 → spaces + !1 (返回 false 让外层接管)
mod_fix_multiline_history_down_modified = re.search(rb'downArrow&&' + V + rb'&&' + V + rb'\)return\s+!1;return!1', data)
mod_fix_multiline_history_down_original = re.search(rb'downArrow&&' + V + rb'&&(' + V + rb')\)return \1\(\),!0;return!1', data)
if mod_fix_multiline_history_down_modified:
    results['mod-fix-multiline-history-down'] = 'modified'
elif mod_fix_multiline_history_down_original:
    results['mod-fix-multiline-history-down'] = 'original'
else:
    results['mod-fix-multiline-history-down'] = 'unknown'

# mod-highlight-welcome-modified: Welcome/Header 橙色高亮
style_mod = b'"dim-bold":{color:"#FFA500"' in data
logo_mod = b'logo:{color:"#FFA500"' in data
all_targets = [style_mod, logo_mod]
if all(all_targets):
    results['mod-highlight-welcome-modified'] = 'modified'
elif any(all_targets):
    results['mod-highlight-welcome-modified'] = 'partial'
elif re.search(rb'dimColor:!0,children:"v\d+\.\d+\.\d+"', data) or re.search(rb'"dim-bold":\{color:' + V + rb'\.text\.secondary,', data):
    results['mod-highlight-welcome-modified'] = 'original'
else:
    results['mod-highlight-welcome-modified'] = 'unknown'

# mod-extend-kitty-timeout: kitty keyboard 检测超时
if re.search(rb'setTimeout\(\w+,999\)', data) and b'enableKittyProtocol' in data:
    results['mod-extend-kitty-timeout'] = 'modified'
elif re.search(rb'setTimeout\(\w+,200\)', data) and b'enableKittyProtocol' in data:
    results['mod-extend-kitty-timeout'] = 'original'
else:
    results['mod-extend-kitty-timeout'] = 'unknown'

# 输出
total = len(results)
mod_count = sum(1 for v in results.values() if v == 'modified')
orig_count = sum(1 for v in results.values() if v == 'original')

print(f"droid 状态:\n")
for name, status in results.items():
    icon = '✓' if status == 'modified' else '△' if status == 'partial' else '○' if status == 'original' else '?'
    label = {'modified': '已修改', 'original': '原版', 'unknown': '未知', 'partial': '部分修改'}[status]
    print(f"  {icon} {name}: {label}")

print()
if mod_count == total:
    print("结论: 已修改")
elif orig_count == total:
    print("结论: 原版")
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
                # reasoningEffort 优先级:
                #   有值 (low/medium/high/max/xhigh) → Droid 控制，extraArgs 中的 effort 被忽略
                #   none/off → Droid 不发送 thinking/reasoning，extraArgs 接管
                # 后果: extraArgs 有 effort 时，Tab 切到 off/none 本想关闭思考，
                #       但 extraArgs 会接管并重新开启

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
                            '（Droid 内置 reasoningEffort 已接管）。'
                            '不删后果: Tab 切到 off 时 extraArgs 会接管，思考不会真正关闭')
                elif provider == 'openai':
                    if not effort:
                        issues.append('缺少 reasoningEffort (建议 "high")')
                    reasoning = extra.get('reasoning', {})
                    if reasoning:
                        keep_parts = []
                        if extra.get('text', {}).get('verbosity'):
                            keep_parts.append('text.verbosity')
                        keep_note = '，' + '、'.join(keep_parts) + ' 可保留' if keep_parts else ''
                        issues.append(
                            f'extraArgs 中的整个 reasoning 对象必须移除（包括 summary）'
                            '（responses.create 中 extraArgs 浅展开会覆盖 requestParams.reasoning，'
                            '导致 effort 字段丢失，Tab 切换 Thinking Level 完全无效）'
                            + keep_note)

                icon = '✓' if not issues else '⚠'
                print(f"  {icon} {name} [{provider}]")
                if effort:
                    print(f"    reasoningEffort: {effort}")
                if extra:
                    print(f"    extraArgs: {json.dumps(extra, ensure_ascii=False)}")
                for issue in issues:
                    print(f"    ⚠ {issue}")
                    warnings.append((name, issue))

            # missionModelSettings 检查
            mission = cfg.get('missionModelSettings', {})
            model_ids = [m.get('id', '') for m in models]
            if mission:
                print(f"\n  missionModelSettings:")
                wm = mission.get('workerModel', '')
                vm = mission.get('validationWorkerModel', '')
                we = mission.get('workerReasoningEffort', '')
                ve = mission.get('validationWorkerReasoningEffort', '')
                print(f"    Worker:    {wm} ({we})" + (" ⚠ 不在 customModels 中" if wm and wm not in model_ids else ""))
                print(f"    Validator: {vm} ({ve})" + (" ⚠ 不在 customModels 中" if vm and vm not in model_ids else ""))

            if not warnings:
                print("\n  配置正常 ✓")

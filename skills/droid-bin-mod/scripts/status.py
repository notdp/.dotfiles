#!/usr/bin/env python3
"""检查 droid 当前状态：原版/已修改/部分修改，以及 settings.json 配置

Mod 编号 (2026-04 重排后):
  mod1  截断条件                 (原 mod1)
  mod2  命令显示阈值             (原 mod2)
  mod3  输出行数 (含原 mod5)     (原 mod3)
  mod4  diff 行数                (原 mod4)
  mod5  custom model cycle       (原 mod6)
  mod6  mission 模型白名单       (原 mod8)
  mod7  custom model effort 级别 (原 mod9)
  mod8  禁用内置模型             (原 mod10)
  mod9  禁用自动更新             (原 mod13)

已删除: 原 mod5(合并到 mod3) / mod7 / mod11 / mod12 / mod14 / mod15 / mod16 / mod17
       (mod10 压缩默认模型在 v0.104+ 上游已默认 "current-model"，不再需要 patch)
"""
import json
import re
from pathlib import Path

droid = Path.home() / '.local/bin/droid'
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'

with open(droid, 'rb') as f:
    data = f.read()

results = {}

# mod1: 截断条件
# 检测 if(!0||! 短路 (mod1 原始形态)
# 或 comp_universal 补偿后的直接 return 形态 (FFH 中原始条件 if(!V&&!V) 被移除)
if b'if(!0||!' in data:
    results['mod1'] = 'modified'
elif b'function FFH(' in data:
    ffh = data.find(b'function FFH(')
    ffh_region = data[ffh:ffh + 300]
    has_orig_cond = re.search(rb'if\(!' + V + rb'&&!' + V + rb'\)', ffh_region)
    has_direct_return = b'return{text:H,isTruncated:!1}' in ffh_region
    if not has_orig_cond and has_direct_return:
        results['mod1'] = 'modified'  # comp_universal 补偿后，原始条件已移除
    elif has_orig_cond:
        results['mod1'] = 'original'
    else:
        results['mod1'] = 'unknown'
else:
    results['mod1'] = 'unknown'

# mod2: 命令阈值
if b'command.length>99' in data:
    results['mod2'] = 'modified'
elif b'command.length>50' in data:
    results['mod2'] = 'original'
else:
    results['mod2'] = 'unknown'

# mod3: 输出行数 (合并原 mod5 输出提示)
# v0.74+: VAR=(99) , 模式 (0 bytes, 替换 VAR=VAR2?8:4,)
# v0.49+: VAR=99,VAR2=5,VAR3=200 模式 (+1 byte)
if re.search(V + rb'=\(99\) ,', data):
    results['mod3'] = 'modified'
elif re.search(V + rb'=99,' + V + rb'=5,' + V + rb'=200', data):
    results['mod3'] = 'modified'
elif re.search(rb'=200,' + V + rb'=99,', data) and b'.slice(0,99),u=' in data:
    # v0.104+: =200,X2H=99, 变量 + 输出预览 literal 99
    results['mod3'] = 'modified'
elif re.search(V + rb'=4,' + V + rb'=5,' + V + rb'=200', data):
    results['mod3'] = 'original'
elif re.search(rb'=200,' + V + rb'=8,', data):
    results['mod3'] = 'original'
elif re.search(V + rb'=\(?[48]\)? ?,' , data):
    # v0.74 原版: VAR=VAR2?8:4,
    results['mod3'] = 'original'
else:
    results['mod3'] = 'unknown'

# mod4: diff行数
# v0.74+: var V=99,V=2000 (uhf=99,Jhf=2000)
# v0.49+: var V=99,V, 模式
if re.search(rb'var ' + V + rb'=99,' + V + rb'=2000', data):
    results['mod4'] = 'modified'
elif re.search(rb'var ' + V + rb'=99,' + V + rb',', data):
    results['mod4'] = 'modified'
elif re.search(rb'var ' + V + rb'=20,' + V + rb'=2000', data):
    results['mod4'] = 'original'
elif re.search(rb'var ' + V + rb'=20,' + V + rb',', data):
    results['mod4'] = 'original'
else:
    results['mod4'] = 'unknown'

# mod5: custom model cycle (原 mod6)
def _mod5_detect():
    targets = [b'peekNextCycleModel', b'peekNextCycleSpecModeModel', b'cycleSpecModeModel']
    modified = original = 0
    for fn in targets:
        for m in re.finditer(fn + rb'\(' + V + rb'\)\{', data):
            region = data[m.start():m.start() + 600]
            if b'=this.customModels.map(m=>m.id)' in region:
                modified += 1
            elif b'validateModelAccess(' in region:
                original += 1
    if modified > 0 and original == 0:
        return 'modified'
    elif original > 0 and modified == 0:
        return 'original'
    return 'unknown'

results['mod5'] = _mod5_detect()

# mod6: mission 模型白名单 (原 mod8)
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

# mod7: custom model effort 级别 (原 mod9)
if b'.provider=="openai"' in data and b'["off","low","medium","high","xhigh","max"]' in data:
    results['mod7'] = 'modified'
elif re.search(rb'supportedReasoningEfforts:' + V + rb'\?\["off","low","medium","high"\]:\["none"\]', data):
    results['mod7'] = 'original'
else:
    results['mod7'] = 'unknown'

# mod8: 禁用内置模型 (原 mod10 / validateModelAccess non-custom return)
OLD_BUILTIN = b'isCustomModel:!1};return{allowed:!0,isCustomModel:!1}}'
NEW_BUILTIN = b'isCustomModel:!1};return{allowed:!1,isCustomModel:!1}}'
if NEW_BUILTIN in data and OLD_BUILTIN not in data:
    results['mod8'] = 'modified'
elif OLD_BUILTIN in data:
    results['mod8'] = 'original'
else:
    results['mod8'] = 'unknown'

# mod9: 禁用自动更新 (原 mod13)
if b'checkForUpdates(){return null;/*' in data:
    results['mod9'] = 'modified'
elif b'async checkForUpdates(){' in data:
    results['mod9'] = 'original'
else:
    results['mod9'] = 'unknown'

# 输出
total = len(results)
mod_count = sum(1 for v in results.values() if v == 'modified')
orig_count = sum(1 for v in results.values() if v == 'original')
na_count   = sum(1 for v in results.values() if v == 'n/a')
applicable = total - na_count

print(f"droid 状态:\n")
for name, status in results.items():
    icon  = '✓' if status == 'modified' else '○' if status == 'original' else '△' if status == 'partial' else '-' if status == 'n/a' else '?'
    label = {'modified': '已修改', 'original': '原版', 'partial': '部分', 'unknown': '未知', 'n/a': '不适用'}[status]
    print(f"  {icon} {name}: {label}")

print()
if mod_count == applicable:
    print("结论: 已修改")
elif orig_count == applicable:
    print("结论: 原版")
else:
    print(f"结论: 部分修改 ({mod_count}/{applicable})")

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
                            '导致 effort 字段丢失，Tab 切换 Thinking Level 完全无效'
                            + (f'；mod7 已解锁 xhigh' if has_mod7 else '') + '）'
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
            elif results.get('mod6') == 'modified':
                print(f"\n  ⚠ mod6 已启用但缺少 missionModelSettings")
                print(f"    → 建议配置 workerModel / validationWorkerModel 指向 custom model")

            if not warnings:
                print("\n  配置正常 ✓")

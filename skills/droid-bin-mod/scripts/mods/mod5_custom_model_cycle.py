#!/usr/bin/env python3
"""mod5: Ctrl+N 在 custom models 间直接切换（不弹 selector）

不依赖 minified 外部函数名（如 c8A/ZAA），直接内联:
  GR().getCustomModels().map((gA)=>gA.id)

支持三种状态:
  1. 原版 selector callback → 直接 cycle
  2. 旧错误 patch (peekNextCycleModel) → 修复为直接 cycle
  3. 已应用 → skip

并支持回滚旧的"稳定函数"补丁（customModels.map 注入到 peekNextCycleModel
等函数入口的方案），确保幂等。

直接 cycle 代码:
  let RR=GR().getCustomModels().map((gA)=>gA.id);
  if(RR.length<=1)return;
  let oR=VT().hasSpecModeModel()?VT().getSpecModeModel():VT().getModel(),
      gA=RR[(RR.indexOf(oR)+1)%RR.length];
  if(gA)HANDLER(gA)
"""
import sys, re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

NAME = 'mod5'

# 直接 cycle 代码的稳定标记（用于幂等检测）
# 使用正则以兼容不同 minified 函数名（UR/GR 等）
DIRECT_CALLBACK_MARKER_RE = re.compile(
    rb'=[A-Za-z_$][A-Za-z0-9_$]{0,3}\(\)\.getCustomModels\(\)\.map\(\(gA\)=>gA\.id\);'
    rb'if\(RR\.length<=1\)return;'
)

# 旧稳定函数补丁的标记片段（若之前打过，需先回滚）
STABLE_INSERT = b'=this.customModels.map(m=>m.id);'
STABLE_TARGETS = (
    b'peekNextCycleModel',
    b'peekNextCycleSpecModeModel',
    b'cycleSpecModeModel',
)

# 原版 Ctrl+N callback：弹出 selector popup
ORIGINAL_CALLBACK_PAT = re.compile(
    rb'(?P<prefix>(?P<cb>\w+)=(?P<react>\w+)\.useCallback\(\(\)=>\{)'
    rb'if\((?P<models>\w+)\.length<=1\)return;'
    rb'let (?P<policy>\w+)=(?P<service>\w+)\(\)\.getModelPolicy\(\);'
    rb'if\(!(?P=models)\.some\(\((?P<item>\w+)\)=>(?P<access>\w+)\((?P=item),(?P=policy)\)\.allowed\)\)return;'
    rb'(?P<toggle>\w+)\(\((?P<state>\w+)\)=>!(?P=state)\)'
    rb'\},\[(?P<dep>\w+)\]\)'
    rb'(?=,(?P<handler>\w+)=\w+\.useCallback\(async\((?P<handler_arg>\w+)\)=>\{)'
)

# 旧错误 patch：调用 peekNextCycleModel 版本
BROKEN_CALLBACK_PAT = re.compile(
    rb'(?P<prefix>(?P<cb>\w+)=(?P<react>\w+)\.useCallback\(\(\)=>\{)'
    rb'let (?P<br>\w+)=\w+\(\)\.peekNextCycleModel\(Y8A\(\),VT\(\)\.hasSpecModeModel\(\)\?VT\(\)\.getSpecModeModel\(\):VT\(\)\.getModel\(\)\);'
    rb'if\((?P=br)\)(?P<handler>\w+)\((?P=br)\.modelId\)'
    rb'\},\[(?P<dep>\w+)\]\)'
)


def find_settings_service_getter(data):
    """
    动态探测 "返回 SettingsService 单例的函数"。
    特征: UR().getCustomModels() 这种调用模式，在 getCustomModels 调用的前面。
    取最常见的 fn_name 作为 getter。
    """
    # 收集所有 `XXX().getCustomModels()` 调用中的 XXX
    call_pat = re.compile(rb'([A-Za-z_$][A-Za-z0-9_$]{0,3})\(\)\.getCustomModels\(\)')
    from collections import Counter
    counter = Counter()
    for m in call_pat.finditer(data):
        name = m.group(1)
        # 必须验证：这个名字要能解析到 return 某单例的 function
        fn_def = re.search(rb'function ' + re.escape(name) + rb'\(\)\{return ([A-Za-z_$][A-Za-z0-9_$]*)\}', data)
        if fn_def:
            counter[name] += 1
    if not counter:
        return None
    best, _ = counter.most_common(1)[0]
    return best


def is_direct_callback_patched(data):
    return DIRECT_CALLBACK_MARKER_RE.search(data) is not None


def revert_stable_function_patch(data):
    """回滚旧的稳定函数补丁（customModels.map 注入 + validate 注释）"""
    reverted = 0
    for fn_name in STABLE_TARGETS:
        entry_pat = re.compile(
            fn_name + rb'\((?P<param>' + V + rb')(?:,' + V + rb')?\)\{(?P=param)'
            + re.escape(STABLE_INSERT) + rb'if\((?P=param)\.length===0\)'
        )
        m_entry = entry_pat.search(data)
        if not m_entry:
            continue

        old_entry = m_entry.group(0)
        param = m_entry.group('param')
        new_entry = old_entry.replace(param + STABLE_INSERT, b'', 1)

        region_start = m_entry.start()
        region = data[region_start:region_start + 600]
        m_comment = re.search(
            rb'/\*\s*\*/(?=try\{let ' + V + rb'=PJ\((?P<loop>' + V + rb')\);)',
            region,
        )
        if not m_comment:
            raise ValueError(f"{fn_name.decode()} 稳定函数补丁回滚失败: validate 注释未找到")

        loop_var = m_comment.group('loop')
        old_check = m_comment.group(0)
        new_check = b'if(!this.validateModelAccess(' + loop_var + b').allowed)continue;'

        check_offset = region_start + m_comment.start()
        data = data[:check_offset] + new_check + data[check_offset + len(old_check):]

        entry_offset = data.find(old_entry, max(0, region_start - 10), region_start + len(old_entry) + 10)
        if entry_offset == -1:
            raise ValueError(f"{fn_name.decode()} 稳定函数补丁回滚失败: 入口未重新定位")
        data = data[:entry_offset] + new_entry + data[entry_offset + len(old_entry):]

        reverted += 1
        print(f"  回滚 {fn_name.decode()} 稳定函数补丁")

    return data, reverted


def find_session_service_getter(data):
    """
    动态探测 "返回 SessionController 单例的函数"。
    特征: XXX().getModel() + XXX().hasSpecModeModel() 这种调用模式。
    """
    call_pat = re.compile(rb'([A-Za-z_$][A-Za-z0-9_$]{0,3})\(\)\.getModel\(\)')
    from collections import Counter
    counter = Counter()
    for m in call_pat.finditer(data):
        name = m.group(1)
        # 同名要能同时调用 hasSpecModeModel
        has_spec = re.search(re.escape(name) + rb'\(\)\.hasSpecModeModel', data)
        if has_spec:
            counter[name] += 1
    if not counter:
        return None
    best, _ = counter.most_common(1)[0]
    return best


def build_direct_callback(prefix, handler, dep, settings_fn, session_fn):
    return (
        prefix
        + b'let RR=' + settings_fn + b'().getCustomModels().map((gA)=>gA.id);'
        + b'if(RR.length<=1)return;'
        + b'let oR=' + session_fn + b'().hasSpecModeModel()?' + session_fn + b'().getSpecModeModel():' + session_fn + b'().getModel(),'
        + b'gA=RR[(RR.indexOf(oR)+1)%RR.length];'
        + b'if(gA)' + handler + b'(gA)'
        + b'},[' + dep + b'])'
    )


def patch_callback_to_direct(data):
    if is_direct_callback_patched(data):
        print(f"{NAME} 已应用，跳过")
        return data, False, 0

    # 动态探测函数名（关键修复：0.104.0 里叫 UR/VT，旧版叫 GR/VT）
    settings_fn = find_settings_service_getter(data)
    session_fn = find_session_service_getter(data)
    if not settings_fn or not session_fn:
        raise ValueError(
            f"未能动态探测函数名 (settings={settings_fn}, session={session_fn})"
        )
    print(f"  settings getter: {settings_fn.decode()}()  session getter: {session_fn.decode()}()")

    for label, pattern in (
        ('修复旧错误回调 (peekNextCycleModel)', BROKEN_CALLBACK_PAT),
        ('替换原版 selector 回调', ORIGINAL_CALLBACK_PAT),
    ):
        m = pattern.search(data)
        if not m:
            continue
        old = m.group(0)
        new = build_direct_callback(
            m.group('prefix'), m.group('handler'), m.group('dep'),
            settings_fn, session_fn,
        )
        data = data.replace(old, new, 1)
        delta = len(new) - len(old)
        print(f"{NAME}: {label} ({delta:+d} bytes)")
        print(f"  handler={m.group('handler').decode()}, dep={m.group('dep').decode()}")
        return data, True, delta

    raise ValueError("Ctrl+N 回调未找到（ORIGINAL + BROKEN 模式都不匹配）")


def main():
    data = load_droid()
    original_size = len(data)

    try:
        data, reverted = revert_stable_function_patch(data)
        data, patched, delta = patch_callback_to_direct(data)
    except ValueError as exc:
        print(f"{NAME} 失败: {exc}")
        sys.exit(1)

    if not reverted and not patched:
        return

    save_droid(data)
    total_delta = len(data) - original_size
    if total_delta != 0:
        print(f"  需由 comp_universal.py 补偿: {total_delta:+d} bytes")
    print(f"{NAME} 完成")


if __name__ == '__main__':
    main()

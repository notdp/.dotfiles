#!/usr/bin/env python3
"""mod-cycle-custom-model: Ctrl+N 预览/切换只在 custom models 间循环

兼容 v0.103.x / v0.104.x：通过匹配 selector 结构与 hasAnyAvailableModel()
锚点，保留当前二进制里的混淆变量名后再生成 custom-only patch。
"""
import re
import sys

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import V, load_droid, save_droid

NAME = 'mod-cycle-custom-model'

SELECTOR_PAT = re.compile(
    rb'(?P<items>' + V + rb')\.push\(\{type:"header",label:(?:(?P<mission>' + V + rb')\?)?(?P<tfn>' + V + rb')\("common:(?:missionModelPicker\.recommendedHeader|modelSelector\.factoryModelsHeader)"\)(?::\s*(?P=tfn)\("common:modelSelector\.factoryModelsHeader"\))?\}\);'
    rb'let (?P<recommended>' + V + rb')=(?P<factory>' + V + rb')\.map\(\((?P<fitem>' + V + rb')\)=>\{let (?P<fcheck>' + V + rb')=(?P<access>' + V + rb')\((?P=fitem),(?P<policy>' + V + rb')\);return\{type:"model",id:(?P=fitem),disabled:!(?P=fcheck)\.allowed\}\}\),'
    rb'(?P<hidden_models>' + V + rb')=(?P<hidden>' + V + rb')\.map\(\((?P<hitem>' + V + rb')\)=>\{let (?P<hcheck>' + V + rb')=(?P=access)\((?P=hitem),(?P=policy)\);return\{type:"model",id:(?P=hitem),disabled:!(?P=hcheck)\.allowed\}\}\),'
    rb'(?P<custom_models>' + V + rb')=(?P<custom>' + V + rb')\.map\(\((?P<citem>' + V + rb')\)=>\{let (?P<ccheck>' + V + rb')=(?P=access)\((?P=citem)\.id,(?P=policy),(?P=citem)\);return\{type:"model",id:(?P=citem)\.id,disabled:!(?P=ccheck)\.allowed\}\}\);'
    rb'if\((?P=items)\.push\(\.\.\.(?P=recommended)\),(?P=hidden)\.length>0\)(?:(?P=items)\.push\(\{type:"sep"\}\),)?(?P=items)\.push\(\{type:"toggle-builtins",expanded:(?P<expanded>' + V + rb'),hiddenCount:(?P=hidden)\.length\}\);'
    rb'if\((?P=expanded)\)(?P=items)\.push\(\.\.\.(?P=hidden_models)\);'
    rb'if\((?P=custom_models)\.length>0\)(?P=items)\.push\(\{type:"sep"\}\),(?P=items)\.push\(\{type:"header",label:(?P=tfn)\("common:modelSelector\.customModelsHeader"\)\}\),(?P=items)\.push\(\.\.\.(?P=custom_models)\);'
)

SELECTOR_CORE_PAT = re.compile(
    rb'(?P<items>' + V + rb')\.push\(\.\.\.(?P<custom>' + V + rb')\.map\(\((?P<item>' + V + rb')\)=>\{let (?P<check>' + V + rb')=(?P<access>' + V + rb')\((?P=item)\.id,(?P<policy>' + V + rb'),(?P=item)\);return\{type:"model",id:(?P=item)\.id,disabled:!(?P=check)\.allowed\}\}\)\);'
)

TW_PAT = re.compile(
    rb'(?P<prefix>,)(?P<models>' + V + rb')=(?P<src>' + V + rb')\(\),(?P<empty>' + V + rb')=!(?P<svc>' + V + rb')\(\)\.hasAnyAvailableModel\((?P=models)\),'
)
TW_CORE_PAT = re.compile(
    rb'(?P<models>' + V + rb')=(?P<svc>' + V + rb')\(\)\.getCustomModels\(\)\.map\(m=>m\.id\),(?P<empty>' + V + rb')=!(?P=svc)\(\)\.hasAnyAvailableModel\((?P=models)\),'
)


def is_already_applied(data: bytes) -> bool:
    selector_core_count = len(list(SELECTOR_CORE_PAT.finditer(data)))
    selector_original_count = len(list(SELECTOR_PAT.finditer(data)))
    return bool(
        selector_core_count > 0
        and selector_original_count == 0
        and TW_CORE_PAT.search(data)
        and not TW_PAT.search(data)
    )


def build_selector_core(match: re.Match[bytes]) -> bytes:
    items = match.group('items')
    custom = match.group('custom')
    item = match.group('citem')
    check = match.group('ccheck')
    access = match.group('access')
    policy = match.group('policy')
    return (
        items
        + b'.push(...'
        + custom
        + b'.map(('
        + item
        + b')=>{let '
        + check
        + b'='
        + access
        + b'('
        + item
        + b'.id,'
        + policy
        + b','
        + item
        + b');return{type:"model",id:'
        + item
        + b'.id,disabled:!'
        + check
        + b'.allowed}}));'
    )


def patch_selectors(data: bytes) -> bytes:
    matches = list(SELECTOR_PAT.finditer(data))
    if not matches:
        if SELECTOR_CORE_PAT.search(data):
            print(f'{NAME} selector: 已应用')
            return data
        raise ValueError('selector pattern not found')

    total = len(matches)
    for idx, match in enumerate(reversed(matches), start=1):
        old = match.group(0)
        core = build_selector_core(match)
        pad_len = len(old) - len(core) - 4
        if pad_len < 0:
            raise ValueError(
                f'selector[{total - idx + 1}]: new core ({len(core)}B) + wrapper (4B) 超过 old 长度 ({len(old)}B)'
            )
        new = core + b'/*' + b' ' * pad_len + b'*/'
        data = data[:match.start()] + new + data[match.end():]
        print(
            f'{NAME} selector[{total - idx + 1}]: {len(old)}B → core {len(core)}B + padding {pad_len}B '
            f'(+0 bytes, padding 可供 comp_universal 消费)'
        )
    return data


def patch_tw(data: bytes) -> bytes:
    matches = list(TW_PAT.finditer(data))
    if not matches and TW_CORE_PAT.search(data):
        print(f'{NAME} hasAnyAvailableModel anchor: 已应用')
        return data

    if not matches:
        raise ValueError(
            'hasAnyAvailableModel anchor pattern not found — droid 版本可能变了'
        )

    total = len(matches)
    for idx, match in enumerate(reversed(matches), start=1):
        old = match.group(0)
        new = (
            match.group('prefix')
            + match.group('models')
            + b'='
            + match.group('svc')
            + b'().getCustomModels().map(m=>m.id),'
            + match.group('empty')
            + b'=!'
            + match.group('svc')
            + b'().hasAnyAvailableModel('
            + match.group('models')
            + b'),'
        )
        data = data[:match.start()] + new + data[match.end():]
        print(
            f'{NAME} hasAnyAvailableModel anchor[{total - idx + 1}] → custom: '
            f'{len(old)}B → {len(new)}B ({len(new) - len(old):+d} bytes)'
        )
    return data


def main() -> None:
    data = load_droid()
    if is_already_applied(data):
        print(f'{NAME} 已应用，跳过')
        return

    original_size = len(data)
    try:
        data = patch_selectors(data)
        data = patch_tw(data)
    except ValueError as exc:
        print(f'{NAME} 失败: {exc}')
        sys.exit(1)

    delta = len(data) - original_size
    save_droid(data)
    print(f'{NAME} 完成 ({delta:+d} bytes)')


if __name__ == '__main__':
    main()

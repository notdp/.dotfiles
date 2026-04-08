#!/usr/bin/env python3
"""通用字节补偿: 利用所有 mod 产生的死代码区域

用法: python3 comp_universal.py [bytes]
  无参数: 显示当前可用补偿空间
  bytes:  需要补偿的字节数（正数=缩减，负数=扩展）

补偿区域 (按容量排序):
  1. FFH 死代码 (mod1 短路后的不可达区域)    ~151B
  2. mod8 enter-mission else 死分支           ~37B
  3. mod6 validateModelAccess 注释 (3处)      ~36B
  4. mod8 空格填充 (2处)                      ~25B
  总计: ~249B

需补偿: mod3(+1) + mod9(+132) = +133 bytes

原理:
  - ffh_dead 类型: 整个死代码区域替换为 ;return{text:H,isTruncated:!1} + 注释
  - dead_branch 类型: else EXPR → else{} + 注释填充
  - comment 类型: /* spaces */ → 调整空格数
  - padding 类型: 空格序列 → 调整空格数
"""
import sys, re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

# FFH 死代码最小替换 (保持 mod1 效果: isTruncated:!1 = false)
FFH_MINIMAL = b';return{text:H,isTruncated:!1}'  # 30 bytes


def find_regions(data):
    """扫描所有可用补偿区域，返回 [(name, offset, old_bytes, min_size, type)]"""
    regions = []
    seen = set()

    def add(name, offset, content, min_size, rtype):
        if offset not in seen:
            seen.add(offset)
            regions.append((name, offset, content, min_size, rtype))

    # 1. 截断函数死代码 (mod1 短路后的不可达区域)
    # 用 isTruncated 定位截断函数，不依赖混淆后的函数名
    trunc_pat = re.search(rb'if\(!0\|\|!' + V + rb'\)return\{text:' + V + rb',isTruncated:!1\}', data)
    if not trunc_pat:
        # 也匹配已补偿形态: ;return{text:H,isTruncated:!1} 或 /*...*/return{...}
        trunc_pat = re.search(rb';return\{text:' + V + rb',isTruncated:!1\}', data)
    ffh = trunc_pat.start() if trunc_pat else -1
    if ffh != -1:
        region = data[ffh:ffh + 500]
        s1 = region.find(b'isTruncated:!1}')
        if s1 >= 0:
            # 找结尾: 优先找 !0} (原版/部分修改)，否则找第二个 !1} (已补偿)
            s2 = region.find(b'isTruncated:!0}', s1 + 15)
            if s2 >= 0:
                s2 += 15
            else:
                s2_last = region.rfind(b'isTruncated:!1}')
                if s2_last > s1:
                    s2 = s2_last + 15

            if s2 and s2 > s1 + 15:
                dead_start = ffh + s1 + 15
                dead_end = ffh + s2
                dead_content = data[dead_start:dead_end]
                add('截断函数死代码', dead_start, dead_content, len(FFH_MINIMAL), 'ffh_dead')

    # 2. mod8 enter-mission else 死分支
    pat = rb'\}else ' + V + rb'\.setModel\(' + V + rb',' + V + rb'\),' + V + rb'\.setReasoningEffort\(' + V + rb'\)'
    m = re.search(pat, data)
    if m:
        add('mod8-else', m.start(), m.group(0), 7, 'dead_branch')  # min: }else{}

    # 3. mod8 空格填充 (两处)
    for pat, name in [(rb'!0( +)\)\{if', 'mod8空格A'), (rb'!0( +)&&', 'mod8空格B')]:
        for m2 in re.finditer(pat, data):
            s = len(m2.group(1))
            if s > 3:
                content = data[m2.start():m2.end()]
                add(name, m2.start(), content, len(content) - s + 1, 'padding')

    # 4. mod6 注释 (3个函数) — 排除截断函数区域内的注释
    trunc_end = ffh + 500 if ffh >= 0 else -1
    for m3 in re.finditer(rb'/\*( +)\*/', data):
        if ffh >= 0 and ffh <= m3.start() <= trunc_end:
            continue
        s = len(m3.group(1))
        if 8 <= s <= 40:
            add('mod6注释', m3.start(), m3.group(0), 4, 'comment')

    # 5. help text 字符串缩短
    STRING_POOL = [
        (b'Install and set up Git AI for tracking AI-generated code attribution',
         b'Install and set up Git AI'),
        (b'Enable fast mode for the current model (/fast off to disable)',
         b'Toggle fast mode'),
        (b'Generate a blog post style semantic diff for changes',
         b'Generate semantic diff'),
        (b'Favorite the current session for quick access',
         b'Favorite session'),
        (b'Show settings configuration errors',
         b'Show config errors'),
        (b'Manage plugins and marketplaces',
         b'Manage plugins'),
        (b'Fork the current session',
         b'Fork session'),
    ]
    for old_s, new_s in STRING_POOL:
        pos_s = data.find(old_s)
        if pos_s >= 0:
            add(f'helptext({new_s.decode()[:20]})', pos_s, old_s, len(new_s), 'string')

    return regions


def resize_region(old_bytes, target_size, rtype):
    """生成指定大小的替换内容"""
    if rtype == 'ffh_dead':
        if target_size < len(FFH_MINIMAL):
            return None
        pad = target_size - len(FFH_MINIMAL)
        if pad == 0:
            return FFH_MINIMAL
        if pad >= 4:
            return b';/*' + b' ' * (pad - 4) + b'*/' + FFH_MINIMAL[1:]
        else:
            return b';' + b' ' * pad + FFH_MINIMAL[1:]

    elif rtype == 'comment':
        inner = target_size - 4
        if inner < 0:
            return None
        return b'/*' + b' ' * inner + b'*/'

    elif rtype == 'dead_branch':
        base = b'}else{}'
        if target_size < len(base):
            return None
        extra = target_size - len(base)
        if extra == 0:
            return base
        if extra >= 4:
            return base[:5] + b'{/*' + b' ' * (extra - 4) + b'*/}'
        else:
            return base[:5] + b'{' + b' ' * (extra - 1) + b'}'

    elif rtype == 'padding':
        sp_start = old_bytes.find(b'!0') + 2
        sp_end = sp_start
        while sp_end < len(old_bytes) and old_bytes[sp_end:sp_end + 1] == b' ':
            sp_end += 1
        prefix = old_bytes[:sp_start]
        suffix = old_bytes[sp_end:]
        new_spaces = target_size - len(prefix) - len(suffix)
        if new_spaces < 1:
            return None
        return prefix + b' ' * new_spaces + suffix

    elif rtype == 'string':
        STRING_POOL = [
            (b'Install and set up Git AI for tracking AI-generated code attribution',
             b'Install and set up Git AI'),
            (b'Enable fast mode for the current model (/fast off to disable)',
             b'Toggle fast mode'),
            (b'Generate a blog post style semantic diff for changes',
             b'Generate semantic diff'),
            (b'Favorite the current session for quick access',
             b'Favorite session'),
            (b'Show settings configuration errors',
             b'Show config errors'),
            (b'Manage plugins and marketplaces',
             b'Manage plugins'),
            (b'Fork the current session',
             b'Fork session'),
        ]
        for old_s, new_s in STRING_POOL:
            if old_bytes == old_s:
                pad = target_size - len(new_s)
                if pad < 0:
                    return None
                return new_s + b' ' * pad
        return None

    return None


def compensate(data, needed_bytes):
    """
    补偿指定字节数。
    needed_bytes > 0: 需要缩减
    needed_bytes < 0: 需要扩展
    返回 (new_data, actual_change)
    """
    regions = find_regions(data)
    if not regions:
        return data, 0

    remaining = needed_bytes
    changes = []

    sorted_regions = sorted(regions, key=lambda r: len(r[2]) - r[3], reverse=True)

    for name, offset, old_bytes, min_size, rtype in sorted_regions:
        if remaining == 0:
            break

        current_size = len(old_bytes)
        avail = current_size - min_size

        if remaining > 0:
            shrink = min(remaining, avail)
            if shrink <= 0:
                continue
            target = current_size - shrink
        else:
            target = current_size + abs(remaining)

        new_bytes = resize_region(old_bytes, target, rtype)
        if new_bytes is None:
            continue

        actual = len(new_bytes) - current_size
        changes.append((name, offset, old_bytes, new_bytes, actual))
        remaining -= (-actual)

    # 从后往前替换
    changes.sort(key=lambda c: c[1], reverse=True)
    total_change = 0
    for name, offset, old_bytes, new_bytes, actual in changes:
        data = data[:offset] + new_bytes + data[offset + len(old_bytes):]
        total_change += actual
        print(f"  {name}: {len(old_bytes)}B → {len(new_bytes)}B ({actual:+d})")

    return data, total_change


def main():
    if len(sys.argv) < 2:
        data = load_droid()
        regions = find_regions(data)
        total = sum(len(r[2]) - r[3] for r in regions)
        print(f"可用补偿区域: {len(regions)} 个, 总容量: {total} bytes\n")
        for name, offset, old_bytes, min_size, rtype in regions:
            avail = len(old_bytes) - min_size
            print(f"  {name:20s}  当前={len(old_bytes):3d}B  可用={avail:3d}B  [{rtype}]")
        return

    try:
        needed = int(sys.argv[1])
    except ValueError:
        print(f"错误: 无效的字节数 '{sys.argv[1]}'")
        sys.exit(1)

    if needed == 0:
        print("无需补偿")
        return

    data = load_droid()
    original_size = len(data)

    regions = find_regions(data)
    total_avail = sum(len(r[2]) - r[3] for r in regions)

    if needed > total_avail:
        print(f"错误: 需要 {needed} bytes 但只有 {total_avail} bytes 可用")
        sys.exit(1)

    print(f"补偿 {needed:+d} bytes:")
    data, actual = compensate(data, needed)
    print(f"实际变化: {actual:+d} bytes")

    if abs(actual) != abs(needed):
        print(f"警告: 未完全补偿 (差 {abs(needed) - abs(actual)} bytes)")
        sys.exit(1)

    assert len(data) == original_size + actual
    save_droid(data)
    print("补偿完成")


if __name__ == '__main__':
    main()

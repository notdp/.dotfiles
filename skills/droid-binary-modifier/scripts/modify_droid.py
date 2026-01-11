#!/usr/bin/env python3
"""
Droid Binary Modifier - 修改 Factory Droid CLI 二进制以禁用命令/输出截断

使用正则匹配，适应 JS 混淆后的变量名变化。

使用方法:
    python3 modify_droid.py [--droid-path PATH] [--backup] [--restore] [--dry-run]
"""

import re
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def get_default_droid_path():
    return Path.home() / ".local" / "bin" / "droid"


def get_droid_version(droid_path: Path) -> str:
    """从二进制中提取版本号"""
    try:
        result = subprocess.run(
            [str(droid_path), "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    # 从二进制字符串中提取
    try:
        result = subprocess.run(
            f"strings '{droid_path}' | grep -E '^[0-9]+\\.[0-9]+\\.[0-9]+$' | head -1",
            shell=True, capture_output=True, text=True
        )
        if result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return "unknown"


def backup_droid(droid_path: Path):
    version = get_droid_version(droid_path)
    backup_path = droid_path.parent / f"{droid_path.name}.backup.{version}"
    if not backup_path.exists():
        shutil.copy2(droid_path, backup_path)
        print(f"[OK] 备份创建: {backup_path}")
    else:
        print(f"[INFO] 备份已存在: {backup_path}")
    return backup_path


def restore_droid(droid_path: Path, version: str = None):
    """从备份恢复，可指定版本"""
    backup_dir = droid_path.parent
    if version:
        backup_path = backup_dir / f"{droid_path.name}.backup.{version}"
    else:
        # 找最新的备份
        backups = list(backup_dir.glob(f"{droid_path.name}.backup.*"))
        if not backups:
            print(f"[ERROR] 无备份文件")
            return False
        backup_path = max(backups, key=lambda p: p.stat().st_mtime)
    
    if not backup_path.exists():
        print(f"[ERROR] 备份不存在: {backup_path}")
        return False
    shutil.copy2(backup_path, droid_path)
    print(f"[OK] 已从备份恢复: {backup_path}")
    return True


def remove_signature(droid_path: Path):
    result = subprocess.run(
        ["codesign", "--remove-signature", str(droid_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[OK] 代码签名已移除")
        return True
    if "not signed" in result.stderr:
        print("[INFO] 二进制已无签名")
        return True
    print(f"[ERROR] 移除签名失败: {result.stderr}")
    return False


def add_signature(droid_path: Path):
    result = subprocess.run(
        ["codesign", "-s", "-", str(droid_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[OK] Ad-hoc 签名完成")
        return True
    print(f"[ERROR] 签名失败: {result.stderr}")
    return False


def modify_binary(droid_path: Path, dry_run: bool = False):
    """使用正则匹配执行二进制修改"""
    with open(droid_path, "rb") as f:
        data = f.read()
    
    original_size = len(data)
    modifications = []
    
    # ===== 修改 1: 截断函数的早期返回条件 =====
    # 模式: if(!X&&!Y)return{text:Z,isTruncated:!1}
    # 特征: 两个变量的 && 条件，返回 isTruncated:!1
    # 修改: if(!0||!Y) 使条件永真，永远走这个分支返回原文
    pattern1 = rb'if\(!([A-Za-z_$][A-Za-z0-9_$]*)&&!([A-Za-z_$][A-Za-z0-9_$]*)\)return\{text:([A-Za-z_$][A-Za-z0-9_$]*),isTruncated:!1\}'
    match1 = re.search(pattern1, data)
    if match1:
        old1 = match1.group(0)
        # 替换第一个变量为 0，&& 改为 ||
        new1 = b'if(!0||!' + match1.group(2) + b')return{text:' + match1.group(3) + b',isTruncated:!1}'
        if len(new1) == len(old1):
            if not dry_run:
                data = data.replace(old1, new1, 1)
            modifications.append(("截断条件", old1.decode(), new1.decode(), "永远返回原文"))
        else:
            print(f"[WARN] 长度不匹配: {len(old1)} vs {len(new1)}")
    
    # ===== 修改 2: 截断函数末尾的 isTruncated:!0 =====
    # 需要在截断函数范围内找，通过 R=80,T=3 或类似参数定位
    # 模式: function XXX(A,R=80,T=3) 附近的 isTruncated:!0
    pattern_func = rb'function\s+([A-Za-z_$][A-Za-z0-9_$]*)\(([A-Za-z_$][A-Za-z0-9_$]*),([A-Za-z_$][A-Za-z0-9_$]*)=80,([A-Za-z_$][A-Za-z0-9_$]*)=3\)'
    match_func = re.search(pattern_func, data)
    if match_func:
        func_start = match_func.start()
        # 在函数范围内（~600字节）查找 isTruncated:!0
        search_end = min(func_start + 600, len(data))
        func_range = data[func_start:search_end]
        
        # 找到 isTruncated:!0 (截断返回)
        truncated_pattern = rb'isTruncated:!0'
        if truncated_pattern in func_range:
            pos = data.find(truncated_pattern, func_start)
            if pos != -1 and pos < search_end:
                old2 = b'isTruncated:!0'
                new2 = b'isTruncated:!1'
                if not dry_run:
                    data = data[:pos] + new2 + data[pos+len(old2):]
                modifications.append(("截断返回", "isTruncated:!0", "isTruncated:!1", "不显示截断提示"))
    
    # ===== 修改 3: 截断函数参数 R=80,T=3 =====
    # 这个数值是固定的，直接替换
    old3 = b'=80,T=3'  # 匹配 X=80,T=3 模式（T 是固定的参数名？不一定）
    # 更精确的模式
    pattern3 = rb'([A-Za-z_$][A-Za-z0-9_$]*)=80,([A-Za-z_$][A-Za-z0-9_$]*)=3\)'
    match3 = re.search(pattern3, data)
    if match3:
        old3 = match3.group(0)
        new3 = match3.group(1) + b'=999,' + match3.group(2) + b'=99)'
        if len(new3) == len(old3):
            if not dry_run:
                data = data.replace(old3, new3, 1)
            modifications.append(("截断参数", old3.decode(), new3.decode(), "更宽更多行"))
        else:
            # 长度不同，需要调整
            # 80->999 多2字符, 3->99 多1字符，共多3字符
            # 尝试 80->99, 3->9
            new3_alt = match3.group(1) + b'=99,' + match3.group(2) + b'=9)'
            if len(new3_alt) == len(old3):
                if not dry_run:
                    data = data.replace(old3, new3_alt, 1)
                modifications.append(("截断参数", old3.decode(), new3_alt.decode(), "更宽更多行"))
    
    # ===== 修改 4: 输出预览行数 slice(0,4) =====
    # 特征: 附近有 flexDirection 或 exec-preview
    # 模式: X=Y.slice(0,4),Z=Y.length
    pattern4 = rb'([A-Za-z_$][A-Za-z0-9_$]*)=([A-Za-z_$][A-Za-z0-9_$]*)\.slice\(0,4\),([A-Za-z_$][A-Za-z0-9_$]*)=\2\.length'
    match4 = re.search(pattern4, data)
    if match4:
        old4 = match4.group(0)
        # slice(0,4) -> slice(0,99), 多1字符，需要从 .length 偷1字符变成 .lengt
        new4 = match4.group(1) + b'=' + match4.group(2) + b'.slice(0,99),' + match4.group(3) + b'=' + match4.group(2) + b'.lengt'
        if len(new4) == len(old4):
            if not dry_run:
                data = data.replace(old4, new4, 1)
            modifications.append(("输出预览", "slice(0,4)", "slice(0,99)", "99行预览"))
        else:
            print(f"[WARN] 输出预览长度不匹配: {len(old4)} vs {len(new4)}")
    
    # ===== 修改 5: 命令显示阈值 length>50 和 slice(0,47) =====
    # 模式: command.length>50?`${X.command.slice(0,47)
    pattern5 = rb'command\.length>50\?\`\$\{([A-Za-z_$][A-Za-z0-9_$]*)\.command\.slice\(0,47\)'
    match5 = re.search(pattern5, data)
    if match5:
        old5 = match5.group(0)
        new5 = b'command.length>99?`${' + match5.group(1) + b'.command.slice(0,96)'
        if len(new5) == len(old5):
            if not dry_run:
                data = data.replace(old5, new5, 1)
            modifications.append(("命令阈值", ">50, slice(47)", ">99, slice(96)", "更长命令"))
        else:
            print(f"[WARN] 命令阈值长度不匹配: {len(old5)} vs {len(new5)}")
    
    # 报告结果
    if not modifications:
        print("[WARN] 未找到任何可修改的模式")
        print("可能原因:")
        print("  1. 已经修改过")
        print("  2. 版本不兼容，需要手动分析")
        print("\n手动分析命令:")
        print("  strings ~/.local/bin/droid | grep -E 'isTruncated|slice\\(0,[0-9]|length>[0-9]'")
        return False
    
    print(f"\n修改列表 ({len(modifications)} 项):")
    for name, old, new, desc in modifications:
        print(f"  [{name}]")
        print(f"    原: {old[:60]}{'...' if len(old) > 60 else ''}")
        print(f"    新: {new[:60]}{'...' if len(new) > 60 else ''}")
        print(f"    说明: {desc}")
    
    if dry_run:
        print("\n[DRY-RUN] 未实际修改文件")
        return True
    
    with open(droid_path, "wb") as f:
        f.write(data)
    
    print(f"\n[OK] 二进制已修改 ({original_size} bytes)")
    return True


def verify_droid(droid_path: Path):
    result = subprocess.run(
        [str(droid_path), "--version"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        print(f"[OK] 验证通过: {result.stdout.strip()}")
        return True
    print(f"[ERROR] 验证失败: {result.stderr}")
    return False


def main():
    parser = argparse.ArgumentParser(description="修改 Factory Droid CLI 二进制")
    parser.add_argument("--droid-path", type=Path, default=get_default_droid_path())
    parser.add_argument("--backup", action="store_true", help="仅创建备份")
    parser.add_argument("--restore", action="store_true", help="从备份恢复")
    parser.add_argument("--dry-run", action="store_true", help="只显示会做什么")
    args = parser.parse_args()
    
    droid_path = args.droid_path
    
    if not droid_path.exists():
        print(f"[ERROR] 不存在: {droid_path}")
        sys.exit(1)
    
    print(f"Droid: {droid_path}")
    
    if args.restore:
        sys.exit(0 if restore_droid(droid_path) else 1)
    
    if args.backup:
        backup_droid(droid_path)
        sys.exit(0)
    
    if args.dry_run:
        print("\n=== Dry Run ===")
        modify_binary(droid_path, dry_run=True)
        sys.exit(0)
    
    print("\n=== 开始修改 ===")
    backup_droid(droid_path)
    
    if not remove_signature(droid_path):
        sys.exit(1)
    
    if not modify_binary(droid_path):
        print("[ERROR] 修改失败，恢复中...")
        restore_droid(droid_path)
        sys.exit(1)
    
    if not add_signature(droid_path):
        print("[ERROR] 签名失败，恢复中...")
        restore_droid(droid_path)
        sys.exit(1)
    
    if not verify_droid(droid_path):
        print("[ERROR] 验证失败，恢复中...")
        restore_droid(droid_path)
        sys.exit(1)
    
    print("\n=== 完成 ===")
    print("建议: export DROID_DISABLE_AUTO_UPDATE=1")


if __name__ == "__main__":
    main()

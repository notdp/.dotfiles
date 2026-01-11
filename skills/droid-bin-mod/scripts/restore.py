#!/usr/bin/env python3
"""
独立恢复脚本 - droid 坏了也能用

用法:
    python3 restore.py           # 恢复最新备份
    python3 restore.py 0.46.0    # 恢复指定版本
    python3 restore.py --list    # 列出所有备份
"""

import sys
import shutil
from pathlib import Path

DROID = Path.home() / ".local" / "bin" / "droid"

def list_backups():
    backups = sorted(DROID.parent.glob("droid.backup.*"))
    if not backups:
        print("无备份")
        return
    print("可用备份:")
    for b in backups:
        size_mb = b.stat().st_size / 1024 / 1024
        print(f"  {b.name} ({size_mb:.1f} MB)")

def restore(version=None):
    if version:
        backup = DROID.parent / f"droid.backup.{version}"
    else:
        backups = list(DROID.parent.glob("droid.backup.*"))
        if not backups:
            print("错误: 无备份文件")
            sys.exit(1)
        backup = max(backups, key=lambda p: p.stat().st_mtime)
    
    if not backup.exists():
        print(f"错误: {backup} 不存在")
        sys.exit(1)
    
    # 先删除再复制，避免 macOS 保留旧元数据导致签名失效
    if DROID.exists():
        DROID.unlink()
    shutil.copy2(backup, DROID)
    print(f"已恢复: {backup.name} -> droid")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            list_backups()
        else:
            restore(sys.argv[1])
    else:
        restore()

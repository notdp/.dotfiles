#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import ensure_repo
from common import load_manifest
from common import manifest_update_reason
from common import resolve_repo


def main() -> None:
    parser = argparse.ArgumentParser(
        description="检查 patched Codex 是否落后于当前官方版本"
    )
    parser.add_argument("--repo", help="Codex 仓库路径，默认 ~/Developer/codex")
    parser.add_argument(
        "--print-binary",
        action="store_true",
        help="检查通过时输出 manifest 里的 built_binary 路径",
    )
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    ensure_repo(repo)

    reason = manifest_update_reason(repo)
    if reason:
        print(f"patched codex 需要更新: {reason}")
        print("先运行: codex-patch-update")
        raise SystemExit(1)

    if args.print_binary:
        manifest = load_manifest()
        if manifest is None or not manifest.get("built_binary"):
            print("patched codex 缺少 built_binary 记录")
            print("先运行: codex-patch-update")
            raise SystemExit(1)
        print(manifest["built_binary"])


if __name__ == "__main__":
    main()

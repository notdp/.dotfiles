#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import build
from common import build_manifest
from common import ensure_repo
from common import is_applied
from common import official_version
from common import patch_path_for_version
from common import print_status_lines
from common import release_ref
from common import repo_targets
from common import resolve_repo
from common import run
from common import save_manifest
from common import target_status
from common import warn_and_exit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="按官方 Codex release 版本同步源码、重新应用 tmux -CC patch 并构建"
    )
    parser.add_argument("--repo", help="Codex 仓库路径，默认 ~/Developer/codex")
    parser.add_argument("--debug", action="store_true", help="构建 debug 版本而不是 release")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    ensure_repo(repo)

    official_binary, official_version_value = official_version()
    if official_binary is None or official_version_value is None:
        warn_and_exit("错误: 无法读取官方 codex 版本。先确认 /opt/homebrew/bin/codex 可用，或设置 CODEX_OFFICIAL_BIN。")

    source_ref = release_ref(official_version_value)
    patch_path = patch_path_for_version(official_version_value)

    print(f"仓库: {repo}")
    print(f"官方 codex: {official_binary} ({official_version_value})")
    print(f"目标源码引用: {source_ref}")
    print(f"补丁: {patch_path}")

    lines = target_status(repo)
    if lines and not is_applied(repo):
        print_status_lines(lines)
        warn_and_exit("错误: 目标文件存在非 patch 状态的本地修改。先处理这些改动，再更新。")

    if lines and is_applied(repo):
        run(
            ["git", "restore", "--staged", "--worktree", "--source=HEAD", "--", *repo_targets(repo)],
            cwd=repo,
            check=True,
        )
        print("状态: 已先撤销旧 patch")

    run(["git", "fetch", "origin", "--tags", "--prune"], cwd=repo, check=True)
    run(["git", "switch", "-C", f"patch/{source_ref}", source_ref], cwd=repo, check=True)
    print(f"状态: 已切到 patch/{source_ref}")

    run(["git", "apply", "--check", "--3way", str(patch_path)], cwd=repo, check=True)
    run(["git", "apply", "--3way", str(patch_path)], cwd=repo, check=True)
    run(["git", "reset", "-q", "--", *repo_targets(repo)], cwd=repo, check=False)
    print("状态: patch 已重新应用")

    binary = build(repo, release=not args.debug)
    save_manifest(
        build_manifest(
            repo=repo,
            source_ref=source_ref,
            patch_path=patch_path,
            binary=binary,
            official_binary=official_binary,
            official_version_value=official_version_value,
        )
    )
    print(f"构建完成: {binary}")


if __name__ == "__main__":
    main()

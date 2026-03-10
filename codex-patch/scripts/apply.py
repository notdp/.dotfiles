#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import build
from common import ensure_repo
from common import is_applied
from common import patch_path_for_version
from common import print_status_lines
from common import repo_targets
from common import repo_workspace_version
from common import resolve_repo
from common import run
from common import target_status
from common import warn_and_exit


def main() -> None:
    parser = argparse.ArgumentParser(description="为 Codex 源码仓库应用 tmux -CC 颜色修复补丁")
    parser.add_argument("--repo", help="Codex 仓库路径，默认 ~/Developer/codex")
    parser.add_argument("--no-build", action="store_true", help="只应用补丁，不构建")
    parser.add_argument("--debug", action="store_true", help="构建 debug 版本而不是 release")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    ensure_repo(repo)
    workspace_version = repo_workspace_version(repo)
    patch_path = patch_path_for_version(workspace_version)
    targets = repo_targets(repo)

    print(f"仓库: {repo}")
    print(f"源码版本: {workspace_version}")
    print(f"补丁: {patch_path}")

    lines = target_status(repo)
    if lines and not is_applied(repo):
        print_status_lines(lines)
        warn_and_exit("错误: 目标文件已有本地修改。先清理或手动合并，再应用 patch。")

    if is_applied(repo):
        print("状态: patch 已存在")
    else:
        run(
            ["git", "apply", "--check", "--3way", str(patch_path)],
            cwd=repo,
            check=True,
        )
        run(
            ["git", "apply", "--3way", str(patch_path)],
            cwd=repo,
            check=True,
        )
        run(["git", "reset", "-q", "--", *targets], cwd=repo, check=False)
        print("状态: patch 已应用")

    run(["git", "reset", "-q", "--", *targets], cwd=repo, check=False)

    if args.no_build:
        return

    binary = build(repo, release=not args.debug)
    print(f"构建完成: {binary}")


if __name__ == "__main__":
    main()

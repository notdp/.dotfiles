#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import build
from common import ensure_repo
from common import is_applied
from common import print_status_lines
from common import repo_targets
from common import resolve_repo
from common import run
from common import target_status
from common import warn_and_exit


def main() -> None:
    parser = argparse.ArgumentParser(description="撤销 Codex tmux -CC patch")
    parser.add_argument("--repo", help="Codex 仓库路径，默认 ~/Developer/codex")
    parser.add_argument("--build", action="store_true", help="恢复后顺手构建")
    parser.add_argument("--debug", action="store_true", help="与 --build 一起使用，构建 debug 版本")
    parser.add_argument("--force", action="store_true", help="即使当前状态不确定也强制恢复目标文件")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    ensure_repo(repo)
    targets = repo_targets(repo)

    lines = target_status(repo)
    if lines and not is_applied(repo) and not args.force:
        print_status_lines(lines)
        warn_and_exit("错误: 目标文件存在非 patch 状态的本地修改。确认后加 --force。")

    run(
        ["git", "restore", "--staged", "--worktree", "--source=HEAD", "--", *targets],
        cwd=repo,
        check=True,
    )
    print("状态: 目标文件已恢复到 HEAD")

    if args.build:
        binary = build(repo, release=not args.debug)
        print(f"构建完成: {binary}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from common import build
from common import build_manifest
from common import clear_build_state
from common import ensure_repo
from common import is_applied
from common import is_build_running
from common import latest_git_release_tag
from common import load_build_state
from common import load_manifest
from common import patch_path_for_version
from common import print_status_lines
from common import release_ref
from common import repo_targets
from common import resolve_repo
from common import run
from common import save_build_state
from common import save_manifest
from common import state_dir
from common import target_status
from common import version_from_tag
from common import warn_and_exit


def apply_patch(repo: Path, target_version: str) -> tuple[str, Path]:
    source_ref = release_ref(target_version)
    patch_path = patch_path_for_version(target_version)

    print(f"仓库: {repo}")
    print(f"目标版本: {target_version}")
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

    run(["git", "switch", "-C", f"patch/{source_ref}", source_ref], cwd=repo, check=True)
    print(f"状态: 已切到 patch/{source_ref}")

    run(["git", "apply", "--check", "--3way", str(patch_path)], cwd=repo, check=True)
    run(["git", "apply", "--3way", str(patch_path)], cwd=repo, check=True)
    run(["git", "reset", "-q", "--", *repo_targets(repo)], cwd=repo, check=False)
    print("状态: patch 已重新应用")

    return source_ref, patch_path


def build_foreground(repo: Path, source_ref: str, patch_path: Path, *, release: bool) -> None:
    profile = "debug" if not release else "release"
    print(f"状态: 开始构建 ({profile})，请稍候…", flush=True)
    binary = build(repo, release=release)
    save_manifest(
        build_manifest(
            repo=repo,
            source_ref=source_ref,
            patch_path=patch_path,
            binary=binary,
        )
    )
    print(f"构建完成: {binary}")


def build_background(repo: Path, source_ref: str, patch_path: Path, *, release: bool) -> None:
    if is_build_running():
        old_state = load_build_state()
        old_pid = old_state.get("pid") if old_state else None
        if old_pid:
            import os
            try:
                os.kill(int(old_pid), 9)
            except OSError:
                pass
            print(f"状态: 已终止旧的后台构建 (PID {old_pid})")

    log_path = state_dir() / "build.log"
    worker = Path(__file__).resolve().parent / "_build_worker.py"

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            [
                sys.executable, str(worker),
                "--repo", str(repo),
                "--source-ref", source_ref,
                "--patch-path", str(patch_path),
                *(["--release"] if release else []),
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    save_build_state({
        "pid": proc.pid,
        "version": version_from_tag(source_ref),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "log": str(log_path),
    })

    profile = "release" if release else "debug"
    print(f"状态: 后台构建已启动 ({profile}, PID {proc.pid})")
    print(f"日志: {log_path}")
    print("当前 codex 继续使用旧版本，构建完成后自动切换。")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="同步 Codex 源码至最新 release、重新应用 tmux -CC patch 并构建"
    )
    parser.add_argument("--repo", help="Codex 仓库路径，默认 ~/Developer/codex")
    parser.add_argument("--version", help="指定目标版本号（如 0.114.0），默认使用最新 git tag")
    parser.add_argument("--debug", action="store_true", help="构建 debug 版本而不是 release")
    parser.add_argument("--force", action="store_true", help="跳过版本检查，强制重新构建")
    parser.add_argument("--foreground", action="store_true", help="前台同步构建（默认后台）")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    ensure_repo(repo)

    run(["git", "fetch", "origin", "--tags", "--prune"], cwd=repo, check=True)

    if args.version:
        target_version = args.version
    else:
        latest_tag = latest_git_release_tag(repo)
        if latest_tag is None:
            warn_and_exit("错误: 仓库中没有找到 rust-v* tag。")
        target_version = version_from_tag(latest_tag)

    if not args.force:
        manifest = load_manifest()
        if (
            manifest
            and manifest.get("built_binary_version") == target_version
            and is_applied(repo)
            and not is_build_running()
            and not args.version
        ):
            print(f"已是最新版本 ({target_version})，无需更新。")
            return

        if is_build_running():
            state = load_build_state()
            if state and state.get("version") == target_version:
                print(f"版本 {target_version} 正在后台构建中 (PID {state.get('pid')})。")
                return

    source_ref, patch_path = apply_patch(repo, target_version)
    release = not args.debug

    if args.foreground:
        build_foreground(repo, source_ref, patch_path, release=release)
    else:
        build_background(repo, source_ref, patch_path, release=release)


if __name__ == "__main__":
    main()

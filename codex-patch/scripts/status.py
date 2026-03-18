#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime

from common import binary_path
from common import branch
from common import ensure_repo
from common import is_build_running
from common import latest_git_release_tag
from common import load_build_state
from common import load_manifest
from common import manifest_path
from common import manifest_update_reason
from common import is_applied
from common import patch_path_for_version
from common import repo_workspace_version
from common import print_status_lines
from common import resolve_repo
from common import revision
from common import target_status
from common import version_from_tag


def fmt_mtime(path):
    if not path.exists():
        return "不存在"
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Codex tmux -CC patch 状态")
    parser.add_argument("--repo", help="Codex 仓库路径，默认 ~/Developer/codex")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    ensure_repo(repo)
    workspace_version = repo_workspace_version(repo)
    latest_tag = latest_git_release_tag(repo)
    latest_version = version_from_tag(latest_tag) if latest_tag else None
    manifest = load_manifest()
    update_reason = manifest_update_reason(repo)

    print(f"仓库: {repo}")
    print(f"分支: {branch(repo)}")
    print(f"提交: {revision(repo)}")
    print(f"源码版本: {workspace_version}")
    print(f"补丁文件: {patch_path_for_version(workspace_version)}")
    print(f"补丁状态: {'已应用' if is_applied(repo) else '未应用'}")
    print(f"最新 tag: {latest_tag or '未找到'} ({latest_version or 'N/A'})")
    if latest_version and latest_version != workspace_version:
        print(f"可升级: {workspace_version} → {latest_version}")
    print(f"manifest: {manifest_path()}")
    if manifest is None:
        print("manifest 状态: 不存在")
    else:
        print(
            "manifest 状态: "
            f"{manifest.get('source_ref')} / {manifest.get('built_binary_version')}"
        )
        print(f"manifest binary: {manifest.get('built_binary')}")
    build_state = load_build_state()
    if build_state and is_build_running():
        print(f"后台构建: 进行中 → {build_state.get('version')} (PID {build_state.get('pid')}, 始于 {build_state.get('started_at')})")
        print(f"构建日志: {build_state.get('log')}")
    elif build_state:
        print(f"后台构建: 已结束 (PID {build_state.get('pid')} 不再运行，可能失败)")
        print(f"构建日志: {build_state.get('log')}")
    print(f"需要更新: {'是' if update_reason else '否'}")
    if update_reason:
        print(f"更新原因: {update_reason}")

    print_status_lines(target_status(repo))

    release_bin = binary_path(repo, release=True)
    debug_bin = binary_path(repo, release=False)
    print(f"release 二进制: {release_bin} ({fmt_mtime(release_bin)})")
    print(f"debug 二进制:   {debug_bin} ({fmt_mtime(debug_bin)})")


if __name__ == "__main__":
    main()

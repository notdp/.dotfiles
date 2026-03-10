#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import branch
from common import build
from common import build_manifest
from common import ensure_repo
from common import load_manifest
from common import official_version
from common import patch_path_for_version
from common import repo_workspace_version
from common import resolve_repo
from common import save_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="构建本地 Codex 二进制")
    parser.add_argument("--repo", help="Codex 仓库路径，默认 ~/Developer/codex")
    parser.add_argument("--debug", action="store_true", help="构建 debug 版本而不是 release")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    ensure_repo(repo)
    binary = build(repo, release=not args.debug)
    manifest = load_manifest()
    official_binary, official_version_value = official_version()
    workspace_version = repo_workspace_version(repo)
    source_ref = (
        str(manifest.get("source_ref"))
        if manifest and manifest.get("source_ref")
        else branch(repo).removeprefix("patch/")
    )
    if official_binary is None and manifest and manifest.get("official_binary"):
        official_binary = Path(str(manifest.get("official_binary")))
    if official_version_value is None and manifest and manifest.get("official_version"):
        official_version_value = str(manifest.get("official_version"))
    save_manifest(
        build_manifest(
            repo=repo,
            source_ref=source_ref,
            patch_path=patch_path_for_version(workspace_version),
            binary=binary,
            official_binary=official_binary,
            official_version_value=official_version_value,
        )
    )
    print(f"构建完成: {binary}")


if __name__ == "__main__":
    main()

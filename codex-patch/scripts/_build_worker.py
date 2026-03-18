#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from common import build
from common import build_manifest
from common import clear_build_state
from common import save_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--patch-path", required=True)
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo)

    try:
        binary = build(repo, release=args.release)
        save_manifest(
            build_manifest(
                repo=repo,
                source_ref=args.source_ref,
                patch_path=Path(args.patch_path),
                binary=binary,
            )
        )
        clear_build_state()
        print(f"构建完成: {binary}")
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

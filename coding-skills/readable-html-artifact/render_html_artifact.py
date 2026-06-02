#!/usr/bin/env python3
from __future__ import annotations

import runpy
import sys
from pathlib import Path


THIS_FILE = Path(__file__).resolve()


def renderer_candidates() -> list[Path]:
    return [
        THIS_FILE.parents[2] / "scripts" / "render_html_artifact.py",
        Path.home() / ".dotfiles" / "scripts" / "render_html_artifact.py",
    ]


def main() -> int:
    checked: list[Path] = []
    for candidate in renderer_candidates():
        resolved = candidate.resolve()
        checked.append(resolved)
        if resolved == THIS_FILE:
            continue
        if resolved.is_file():
            runpy.run_path(str(resolved), run_name="__main__")
            return 0

    sys.stderr.write("ERROR: renderer implementation not found. Checked:\n")
    for candidate in checked:
        sys.stderr.write(f"- {candidate}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

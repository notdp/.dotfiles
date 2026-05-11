#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path


def read_optional(path: Path | None) -> str:
    if path is None:
        return ""
    if not path.exists():
        raise RuntimeError(f"missing file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def render_review_html(*, diff_text: str, findings_text: str, validation_text: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Review Artifact</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f8fafc; color: #111827; }}
section {{ background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; margin-bottom: 16px; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #0f172a; color: #e5e7eb; padding: 12px; border-radius: 8px; }}
</style>
</head>
<body>
<h1>Review Artifact</h1>
<section>
<h2>Findings</h2>
<pre>{html.escape(findings_text or "(no findings)")}</pre>
</section>
<section>
<h2>Diff</h2>
<pre>{html.escape(diff_text or "(no diff)")}</pre>
</section>
<section>
<h2>Validation Output</h2>
<pre>{html.escape(validation_text or "(no validation output)")}</pre>
</section>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a static HTML page for review artifacts.")
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--findings", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        html_text = render_review_html(
            diff_text=read_optional(args.diff),
            findings_text=read_optional(args.findings),
            validation_text=read_optional(args.validation),
        )
    except RuntimeError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    sys.stdout.write(f"wrote {args.output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

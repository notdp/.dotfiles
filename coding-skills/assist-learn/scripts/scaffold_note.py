#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: scaffold_note.py <title> [output-file]', file=sys.stderr)
        return 1

    title = sys.argv[1].strip()
    output_file = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    template_path = Path(__file__).resolve().parents[1] / 'templates' / 'learning-note.md'
    content = template_path.read_text()
    content = content.replace('{{title}}', title)
    content = content.replace('{{date}}', date.today().isoformat())

    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content)
        print(output_file)
    else:
        print(content, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Opt-in grep-first retrieval over a learnings store (docs/learnings by default).

Conservative read-side for the compound loop: a tool you choose to run before
starting work ("have we hit this before?"), NOT an always-on injection. Prints a
ranked summary (path + frontmatter), never dumps full note bodies into context.

Usage: learnings_search.py <term...> [--root <dir>] [--top N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from scripts.hooks.memory_score import frontmatter_summary, score_note, split_frontmatter
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from scripts.hooks.memory_score import frontmatter_summary, score_note, split_frontmatter



def search(root: Path, terms: list[str], top: int) -> list[tuple[int, Path, str]]:
    if not root.exists() or not root.is_dir():
        return []
    results: list[tuple[int, Path, str]] = []
    for path in sorted(root.rglob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        frontmatter, body = split_frontmatter(text)
        score = score_note(frontmatter, body, terms)
        if score > 0:
            results.append((score, path, frontmatter_summary(frontmatter)))
    results.sort(key=lambda r: (-r[0], str(r[1])))
    return results[:top]


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the learnings store (opt-in).")
    parser.add_argument("terms", nargs="+", help="search keywords")
    parser.add_argument("--root", default="docs/learnings", help="store root (default: docs/learnings)")
    parser.add_argument("--top", type=int, default=5, help="max results (default: 5)")
    args = parser.parse_args()

    root = Path(args.root)
    terms = [t.lower() for t in args.terms if t.strip()]
    if not terms:
        print("no search terms given", file=sys.stderr)
        return 0

    if not root.exists() or not root.is_dir():
        print(f"no learnings store at {root} (nothing to search)")
        return 0

    hits = search(root, terms, args.top)
    if not hits:
        print(f"no matching learnings in {root} for: {' '.join(terms)}")
        return 0

    print(f"top {len(hits)} learnings in {root} for: {' '.join(terms)}")
    for score, path, summary in hits:
        print(f"- [{score}] {path}")
        if summary:
            print(f"    {summary}")
    print("\nopt-in retrieval: open a note to read its Reusable Pattern; full bodies are not dumped here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

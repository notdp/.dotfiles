#!/usr/bin/env python3
"""Anchor ID generation and stability verification for review-managed Markdown docs.

Anchors are derived from headings: each H1..H6 becomes an addressable comment target.
Duplicate slugs within a single document get numeric suffixes (foo, foo-2, foo-3...).

Stability rule: if comments.json holds open comments under an anchor id that no longer
appears in the current document, the script exits non-zero so callers can stop before
silently orphaning user feedback.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SEPARATOR_RE = re.compile(r"[\s\-_/\\.,:;!?()\[\]{}\"'`~@#$%^&*+=|<>]+")


@dataclass(frozen=True)
class Anchor:
    id: str
    heading: str
    level: int
    line: int


def slugify_heading(text: str) -> str:
    """Slugify a heading into a kebab-case ID. Preserves Unicode word characters."""
    if not text or not text.strip():
        raise ValueError("cannot slugify empty heading")
    lowered = text.strip().lower()
    slug = SEPARATOR_RE.sub("-", lowered)
    slug = slug.strip("-")
    if not slug:
        raise ValueError(f"heading reduces to empty slug: {text!r}")
    return slug


def extract_anchors(md_text: str) -> list[Anchor]:
    """Parse Markdown headings outside fenced code blocks into anchors.

    Duplicate slugs receive numeric suffixes so each anchor in a single document is unique.
    """
    anchors: list[Anchor] = []
    seen: dict[str, int] = {}
    in_code_fence = False

    for index, raw_line in enumerate(md_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if not stripped.startswith("#"):
            continue
        marker, _, rest = stripped.partition(" ")
        if not marker or set(marker) != {"#"} or not 1 <= len(marker) <= 6:
            continue
        heading_text = rest.strip()
        if not heading_text:
            continue
        base = slugify_heading(heading_text)
        count = seen.get(base, 0) + 1
        seen[base] = count
        anchor_id = base if count == 1 else f"{base}-{count}"
        anchors.append(Anchor(id=anchor_id, heading=heading_text, level=len(marker), line=index))

    return anchors


def verify_anchor_stability(doc_anchors: list[Anchor], comments: dict) -> list[str]:
    """Return error messages for anchors that disappeared while still holding open comments."""
    doc_ids = {anchor.id for anchor in doc_anchors}
    anchors_in_comments = comments.get("anchors") or {}
    errors: list[str] = []
    for anchor_id, anchor_payload in anchors_in_comments.items():
        if anchor_id in doc_ids:
            continue
        comment_list = anchor_payload.get("comments") or []
        open_count = sum(1 for c in comment_list if c.get("status") == "open")
        if open_count == 0:
            continue
        heading = anchor_payload.get("heading", anchor_id)
        errors.append(
            f"orphan anchor: {anchor_id!r} (heading {heading!r}) has {open_count} open comment(s) "
            f"but no matching heading in the current doc"
        )
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    extract_p = sub.add_parser("extract", help="Print anchors as TSV: id<TAB>level<TAB>heading")
    extract_p.add_argument("doc", type=Path)

    verify_p = sub.add_parser("verify", help="Verify anchor stability against comments.json")
    verify_p.add_argument("doc", type=Path)
    verify_p.add_argument("comments", type=Path)

    return parser


def _read_doc(path: Path) -> str:
    if not path.exists():
        sys.stderr.write(f"ERROR: missing doc: {path}\n")
        sys.exit(2)
    return path.read_text(encoding="utf-8")


def _read_comments(path: Path) -> dict:
    if not path.exists():
        sys.stderr.write(f"ERROR: missing comments: {path}\n")
        sys.exit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        md = _read_doc(args.doc)
        for anchor in extract_anchors(md):
            sys.stdout.write(f"{anchor.id}\t{anchor.level}\t{anchor.heading}\n")
        return 0

    if args.command == "verify":
        md = _read_doc(args.doc)
        comments = _read_comments(args.comments)
        anchors = extract_anchors(md)
        errors = verify_anchor_stability(anchors, comments)
        if errors:
            for msg in errors:
                sys.stderr.write(f"ERROR: {msg}\n")
            return 1
        sys.stdout.write(f"ok: {len(anchors)} anchors stable\n")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Backfill the `origin_project` frontmatter on existing memory notes (D3).

Notes written before the project dimension existed have no `origin_project`
field, so agentsview groups them all under the General bucket. This one-shot,
idempotent backfill recovers the project for *atomic* notes by mapping their
`origin_session` (a session id) to that session's canonical project in the
agentsview SQLite DB (`sessions.project`, which is already worktree-normalised).

Scope rules (mirrors render_user_note / the synthesize worker):
  - Atomic note whose origin_session maps to a non-empty project  -> origin_project=<project>, scope=project
  - Synthesised topic note (origin_session starts "compact-memory:") -> left untouched (cross-project = General)
  - Atomic note with no session match / empty project              -> left untouched (General)

A note that already carries a non-empty `origin_project` is never modified, so
re-running is safe. `--dry-run` reports what would change without writing.

The DB is opened read-only; the on-disk *.md files are the SSOT and the only
thing this script mutates. git history (memory/user local repo + private backup)
makes any write recoverable.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

INDEX_BASENAME = "INDEX.md"
SYNTHESIZED_PREFIX = "compact-memory:"
DEFAULT_DB = Path.home() / ".agentsview" / "sessions.db"
# Project names the live capture pipeline (memory_capture.classify_origin_scope)
# treats as general/user rather than a project: the dotfiles SSOT repo itself.
# Backfill mirrors that so an origin in dotfiles lands in General, consistent
# with new notes captured from the same place.
GENERAL_PROJECTS = {".dotfiles", "dotfiles"}


def split_frontmatter(text: str) -> tuple[str, str] | None:
    """Return (frontmatter_block, rest) or None when there is no frontmatter."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end], text[end + 5 :]


def frontmatter_field(block: str, key: str) -> str | None:
    for line in block.splitlines():
        head, sep, value = line.partition(":")
        if sep and head.strip() == key:
            return value.strip().strip('"')
    return None


def quote(value: str) -> str:
    """YAML-safe double-quoted scalar, matching assist_consolidate.frontmatter_value."""
    s = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def set_or_insert_field(block: str, key: str, value: str, *, after: str) -> str:
    """Set `key: value` in the frontmatter block, inserting it after the `after`
    line when absent (or appending if `after` is missing too)."""
    lines = block.splitlines()
    rendered = f"{key}: {quote(value)}"
    for i, line in enumerate(lines):
        if line.partition(":")[0].strip() == key:
            lines[i] = rendered
            return "\n".join(lines)
    for i, line in enumerate(lines):
        if line.partition(":")[0].strip() == after:
            lines.insert(i + 1, rendered)
            return "\n".join(lines)
    lines.append(rendered)
    return "\n".join(lines)


def load_project_map(db_path: Path) -> dict[str, str]:
    """Map session id and source_session_id -> non-empty project name."""
    if not db_path.exists():
        return {}
    uri = f"file:{db_path}?mode=ro"
    out: dict[str, str] = {}
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return {}
    try:
        cur = conn.execute(
            "SELECT id, source_session_id, project FROM sessions "
            "WHERE project IS NOT NULL AND project <> ''"
        )
        for sid, source_sid, project in cur.fetchall():
            project = (project or "").strip()
            if not project:
                continue
            for key in (sid, source_sid):
                key = (key or "").strip()
                if key:
                    out.setdefault(key, project)
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    return out


def resolve_project(origin_session: str, project_map: dict[str, str]) -> str:
    project = project_map.get((origin_session or "").strip(), "")
    if project in GENERAL_PROJECTS:
        return ""  # dotfiles SSOT repo = general, mirroring classify_origin_scope
    return project


def backfill_note(path: Path, project_map: dict[str, str]) -> tuple[str, str] | None:
    """Return (action, project) when a write is needed, else None."""
    text = path.read_text(encoding="utf-8")
    parts = split_frontmatter(text)
    if parts is None:
        return None
    block, rest = parts
    existing = frontmatter_field(block, "origin_project")
    if existing:
        return None  # already has a project; never overwrite
    origin_session = frontmatter_field(block, "origin_session") or ""
    if origin_session.startswith(SYNTHESIZED_PREFIX):
        return None  # synthesised cross-project topic -> General
    project = resolve_project(origin_session, project_map)
    if not project:
        return None  # no session match -> General
    new_block = set_or_insert_field(block, "origin_project", project, after="origin_session")
    new_block = set_or_insert_field(new_block, "scope", "project", after="origin_project")
    new_text = "---\n" + new_block + "\n---\n" + rest
    path.write_text(new_text, encoding="utf-8")
    return ("backfilled", project)


def iter_notes(user_dir: Path):
    for path in sorted(user_dir.glob("*.md")):
        if path.name == INDEX_BASENAME:
            continue
        yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="dotfiles repo root (memory/user lives under it)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help="agentsview sessions.db (read-only)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report changes without writing")
    args = parser.parse_args(argv)

    user_dir = args.root / "memory" / "user"
    if not user_dir.exists():
        print(f"no memory/user dir at {user_dir}", file=sys.stderr)
        return 1

    project_map = load_project_map(args.db)
    if not project_map:
        print(f"warning: no session->project map (db {args.db}); only General will result",
              file=sys.stderr)

    changed = 0
    by_project: dict[str, int] = {}
    for path in iter_notes(user_dir):
        if args.dry_run:
            text = path.read_text(encoding="utf-8")
            parts = split_frontmatter(text)
            if parts is None:
                continue
            block, _ = parts
            if frontmatter_field(block, "origin_project"):
                continue
            origin_session = frontmatter_field(block, "origin_session") or ""
            if origin_session.startswith(SYNTHESIZED_PREFIX):
                continue
            project = resolve_project(origin_session, project_map)
            if project:
                changed += 1
                by_project[project] = by_project.get(project, 0) + 1
                print(f"[dry-run] {path.name} -> {project}")
            continue
        result = backfill_note(path, project_map)
        if result:
            _, project = result
            changed += 1
            by_project[project] = by_project.get(project, 0) + 1

    summary = ", ".join(f"{p}={n}" for p, n in sorted(by_project.items())) or "none"
    verb = "would backfill" if args.dry_run else "backfilled"
    print(f"{verb} {changed} note(s): {summary}")
    if changed and not args.dry_run:
        print("note: run scripts/build_memory_index.py --root <root> to refresh INDEX, "
              "then let agentsview resync (or restart) to pick up origin_project.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

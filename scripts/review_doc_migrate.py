#!/usr/bin/env python3
"""Schema validation and migration entrypoint for review comments.json.

v1 is the only supported schema today; this script exists so future schema bumps
have a single, testable migration point instead of ad-hoc reads scattered across
consumers. Adding a v2 means adding `migrate_v1_to_v2` and listing it in
MIGRATIONS; consumers continue calling `migrate(payload, target=CURRENT_SCHEMA_VERSION)`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CURRENT_SCHEMA_VERSION = 1


REQUIRED_FIELDS = ("schema_version", "spec_file", "review_version", "anchors")


def validate(payload: dict) -> None:
    """Raise ValueError if payload is not a valid review comments document at CURRENT_SCHEMA_VERSION."""
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ValueError(f"missing required field: {field!r}")
    version = payload["schema_version"]
    if not isinstance(version, int):
        raise ValueError(f"schema_version must be int, got {type(version).__name__}")
    if version != CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version: {version} (current: {CURRENT_SCHEMA_VERSION})"
        )
    if not isinstance(payload["spec_file"], str):
        raise ValueError("spec_file must be a string")
    if not isinstance(payload["review_version"], int):
        raise ValueError("review_version must be an int")
    if not isinstance(payload["anchors"], dict):
        raise ValueError("anchors must be a dict")


MIGRATIONS: dict[tuple[int, int], callable] = {}  # type: ignore[valid-type]


def migrate(payload: dict, *, target: int) -> dict:
    """Migrate payload up to the target schema version. v1 is identity for now."""
    current = payload.get("schema_version", 1)
    if target == current:
        return payload
    while current < target:
        step = MIGRATIONS.get((current, current + 1))
        if step is None:
            raise ValueError(f"no migration registered for {current} -> {current + 1}")
        payload = step(payload)
        current += 1
    if current != target:
        raise ValueError(f"could not migrate to target version: {target}")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate_p = sub.add_parser("validate", help="Validate a comments.json file against the current schema")
    validate_p.add_argument("file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        if not args.file.exists():
            sys.stderr.write(f"ERROR: missing file: {args.file}\n")
            return 2
        payload = json.loads(args.file.read_text(encoding="utf-8"))
        try:
            validate(payload)
        except ValueError as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 1
        sys.stdout.write(f"ok: {args.file} validates against schema v{CURRENT_SCHEMA_VERSION}\n")
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Extract new review comments from an incoming comments.json against a baseline.

The browser exports a full comments.json snapshot; this script computes the delta so
the consuming agent only sees the new user (or agent) input, not the entire history.
Version monotonicity and spec_file consistency are enforced to prevent processing a
stale or mis-pointed download.

Classification (blocker/question/nit/idea) is intentionally left to the agent's
judgment and not done here — this script is the mechanical preparer only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


VALID_STATUSES = frozenset({"open", "resolved", "answered", "moved"})
VALID_CLASSIFICATIONS = frozenset({"blocker", "question", "nit", "idea"})


def _existing_comment_ids(payload: dict) -> set[str]:
    ids: set[str] = set()
    for anchor_payload in (payload.get("anchors") or {}).values():
        for comment in anchor_payload.get("comments") or []:
            comment_id = comment.get("id")
            if isinstance(comment_id, str):
                ids.add(comment_id)
    return ids


def diff_new_comments(*, baseline: dict, incoming: dict) -> dict:
    """Return a structured plan listing new open comments in `incoming` not in `baseline`."""
    baseline_version = int(baseline.get("review_version", 0))
    incoming_version = int(incoming.get("review_version", 0))
    if incoming_version <= baseline_version:
        raise ValueError(
            f"incoming review_version ({incoming_version}) must advance beyond baseline ({baseline_version})"
        )
    baseline_spec = baseline.get("spec_file")
    incoming_spec = incoming.get("spec_file")
    if baseline_spec and incoming_spec and baseline_spec != incoming_spec:
        raise ValueError(
            f"spec_file mismatch: baseline={baseline_spec!r} incoming={incoming_spec!r}"
        )

    seen_ids = _existing_comment_ids(baseline)
    new_comments: list[dict] = []
    for anchor_id, anchor_payload in (incoming.get("anchors") or {}).items():
        heading = anchor_payload.get("heading", anchor_id)
        for comment in anchor_payload.get("comments") or []:
            comment_id = comment.get("id")
            if not isinstance(comment_id, str) or comment_id in seen_ids:
                continue
            if comment.get("status") != "open":
                continue
            new_comments.append(
                {
                    "anchor_id": anchor_id,
                    "anchor_heading": heading,
                    "comment_id": comment_id,
                    "role": comment.get("role", "user"),
                    "text": comment.get("text", ""),
                    "created_in_version": comment.get("created_in_version"),
                }
            )

    return {
        "spec_file": incoming_spec or baseline_spec,
        "baseline_version": baseline_version,
        "incoming_version": incoming_version,
        "new_comments": new_comments,
    }


def apply_resolution(
    comments: dict,
    *,
    comment_id: str,
    classification: str,
    status: str,
    response: str,
    version: int,
) -> dict:
    """Mutate-and-return: mark a comment with classification/status/response/resolved version."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status!r} (allowed: {sorted(VALID_STATUSES)})")
    if classification not in VALID_CLASSIFICATIONS:
        raise ValueError(
            f"invalid classification: {classification!r} (allowed: {sorted(VALID_CLASSIFICATIONS)})"
        )
    for anchor_payload in (comments.get("anchors") or {}).values():
        for comment in anchor_payload.get("comments") or []:
            if comment.get("id") == comment_id:
                comment["status"] = status
                comment["classification"] = classification
                comment["response"] = response
                comment["resolved_in_version"] = version
                return comments
    raise KeyError(f"comment_id not found: {comment_id!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    diff_p = sub.add_parser("diff", help="Print new-comments plan as JSON")
    diff_p.add_argument("--baseline", type=Path, required=True)
    diff_p.add_argument("--incoming", type=Path, required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "diff":
        for path in (args.baseline, args.incoming):
            if not path.exists():
                sys.stderr.write(f"ERROR: missing file: {path}\n")
                return 2
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        incoming = json.loads(args.incoming.read_text(encoding="utf-8"))
        try:
            plan = diff_new_comments(baseline=baseline, incoming=incoming)
        except ValueError as exc:
            sys.stderr.write(f"ERROR: {exc}\n")
            return 1
        sys.stdout.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

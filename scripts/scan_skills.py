#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from hooks.threat_scan import ThreatFinding, scan_text
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hooks.threat_scan import ThreatFinding, scan_text


SKIP_DIRS = {".git", ".long-loop", "node_modules", ".venv", "__pycache__"}


@dataclass(frozen=True)
class ScanWarning:
    source: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def iter_scan_targets(repo_root: Path) -> list[Path]:
    patterns = [
        "coding-skills/**/SKILL.md",
        "coding-skills/**/*.md",
        "commands/**/*.md",
        "agents/context-capsules/**/*.md",
    ]
    targets: dict[Path, None] = {}
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(repo_root).parts
            if any(part in SKIP_DIRS for part in rel_parts):
                continue
            targets[path] = None
    return sorted(targets)


def scan_repo_with_warnings(repo_root: Path, trust_level: str = "skill") -> tuple[list[ThreatFinding], list[ScanWarning]]:
    findings: list[ThreatFinding] = []
    warnings: list[ScanWarning] = []
    for path in iter_scan_targets(repo_root):
        rel = str(path.relative_to(repo_root))
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.append(ScanWarning(source=rel, message=f"unreadable: {exc}"))
            continue
        findings.extend(scan_text(text, source=rel, trust_level=trust_level))
    return findings, warnings


def scan_repo(repo_root: Path, trust_level: str = "skill") -> list[ThreatFinding]:
    findings, _warnings = scan_repo_with_warnings(repo_root, trust_level=trust_level)
    return findings


def summary_for(findings: list[ThreatFinding]) -> dict[str, object]:
    by_category: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    for finding in findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
        by_decision[finding.decision] = by_decision.get(finding.decision, 0) + 1
    return {"total_findings": len(findings), "by_category": by_category, "by_decision": by_decision}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan skills, commands, and context capsules for prompt-surface threats.")
    parser.add_argument("repo_root", nargs="?", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true", help="Return non-zero when any finding is block-level.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    findings, warnings = scan_repo_with_warnings(repo_root, trust_level="strict" if args.strict else "skill")
    payload = {
        "summary": summary_for(findings),
        "findings": [finding.to_dict() for finding in findings],
        "warnings": [warning.to_dict() for warning in warnings],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for finding in findings:
            print(
                f"{finding.source}:{finding.line}:{finding.column}: "
                f"{finding.category} {finding.decision}: {finding.evidence}"
            )
        for warning in warnings:
            print(f"SECURITY SCAN WARNING: {warning.source}: {warning.message}", file=sys.stderr)
        print(
            "security scan summary: "
            f"total={payload['summary']['total_findings']} "
            f"categories={payload['summary']['by_category']} "
            f"decisions={payload['summary']['by_decision']}"
        )
    return 1 if args.strict and any(finding.decision == "block" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())

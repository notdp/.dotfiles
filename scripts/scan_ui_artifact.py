#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


SCAN_SUFFIXES = {".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
THEME_TOKEN_RE = re.compile(r"--(?:color|brand|theme|token)[\w-]*\s*:", re.I)
TOKEN_USE_RE = re.compile(r"var\(--(?:color|brand|theme|token)[\w-]*\)", re.I)


@dataclass(frozen=True)
class Rule:
    priority: str
    id: str
    pattern: re.Pattern[str]
    issue: str
    fix: str


@dataclass(frozen=True)
class Finding:
    priority: str
    id: str
    file: str
    line: int
    snippet: str
    issue: str
    fix: str


RULES = [
    Rule(
        "P0",
        "ai-default-indigo",
        re.compile(r"#(?:6366f1|4f46e5|4338ca|3730a3|8b5cf6|7c3aed|a855f7)\b|\b(?:indigo|purple|violet|cyan)\b|from-indigo|to-purple|linear-gradient", re.I),
        "Default AI-looking accent or gradient token appears outside a design-system token definition.",
        "Replace with project-approved design tokens or justify the brand color in DESIGN.md.",
    ),
    Rule(
        "P0",
        "emoji-filler",
        re.compile(r"[✨🚀🎯⚡🔥💡✅⭐]"),
        "Emoji-as-icon filler is present in UI copy.",
        "Use purposeful iconography or remove decorative filler.",
    ),
    Rule(
        "P0",
        "filler-copy",
        re.compile(r"\b(?:lorem ipsum|placeholder text|sample content|feature one|feature two|feature three)\b", re.I),
        "Placeholder or generic filler copy is visible.",
        "Replace with real product copy or mark the artifact as a non-shipping mock.",
    ),
    Rule(
        "P0",
        "fictional-metric",
        re.compile(r"\b(?:10x faster|10× faster|99\.9% uptime|3x productive|3× productive)\b", re.I),
        "Unsourced marketing metric appears in UI text.",
        "Remove the metric or attach a cited measurement source.",
    ),
    Rule(
        "P1",
        "overflow-clipping-risk",
        re.compile(r"\b(?:overflow-hidden|truncate|line-clamp)\b|white-space\s*:\s*nowrap", re.I),
        "Text or layout clipping utility can hide content on small screens.",
        "Verify responsive behavior or constrain this to decorative clipping with an accessible alternative.",
    ),
    Rule(
        "P1",
        "heavy-effect-risk",
        re.compile(r"\b(?:backdrop-filter|blur\(|drop-shadow|shadow-2xl|shadow-xl)\b", re.I),
        "Heavy visual effect can create generic glassmorphism or low-contrast UI.",
        "Use the project's elevation tokens or simplify the effect.",
    ),
    Rule(
        "P1",
        "external-placeholder-image",
        re.compile(r"\b(?:placehold\.co|picsum\.photos|placekitten|unsplash\.com)\b", re.I),
        "External placeholder image source is present.",
        "Use real assets, local fixtures, or an explicit mock-only marker.",
    ),
    Rule(
        "P1",
        "raw-hex-color",
        re.compile(r"#[0-9a-fA-F]{3,8}\b"),
        "Raw hex color appears outside a design-system token definition.",
        "Move color values into design tokens or use existing tokens.",
    ),
    Rule(
        "P2",
        "hardcoded-utility-token",
        re.compile(r"(?:!important|\bz-\[|\bw-\[|\bh-\[|\btext-\[|\brounded-\[)"),
        "Hardcoded utility value can drift from the design system.",
        "Replace with spacing/type/radius tokens or document the one-off constraint.",
    ),
]


def iter_scan_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(child for child in sorted(path.rglob("*")) if child.is_file() and child.suffix in SCAN_SUFFIXES)
        elif path.is_file():
            files.append(path)
    return files


def is_suppressed(line: str) -> bool:
    return bool(THEME_TOKEN_RE.search(line) or TOKEN_USE_RE.search(line) or "ui-lint-disable" in line)


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if is_suppressed(line):
            continue
        snippet = line.strip()
        for rule in RULES:
            if rule.pattern.search(line):
                findings.append(
                    Finding(
                        priority=rule.priority,
                        id=rule.id,
                        file=str(path),
                        line=line_number,
                        snippet=snippet[:180],
                        issue=rule.issue,
                        fix=rule.fix,
                    )
                )
    return findings


def scan(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_scan_files(paths):
        findings.extend(scan_file(path))
    return findings


def markdown(findings: list[Finding], paths: list[Path]) -> str:
    lines = [
        "## UI Artifact Lint",
        "",
        "### Scope",
        *[f"- {path}" for path in paths],
        "",
        "### Findings",
        "| Priority | ID | Evidence | Issue | Fix |",
        "|---|---|---|---|---|",
    ]
    if findings:
        for finding in findings:
            evidence = f"{finding.file}:{finding.line} `{finding.snippet}`"
            lines.append(f"| {finding.priority} | {finding.id} | {evidence} | {finding.issue} | {finding.fix} |")
    else:
        lines.append("| - | no-findings | - | No deterministic UI lint findings. | - |")
    lines.extend(
        [
            "",
            "### False positives checked",
            "- Suppressed CSS custom property token definitions and token usages.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan UI artifacts for deterministic AI slop and UI risk findings.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    findings = scan(args.paths)
    if args.format == "json":
        print(json.dumps({"findings": [asdict(finding) for finding in findings]}, ensure_ascii=False, indent=2))
    else:
        print(markdown(findings, args.paths), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple


URL_RE = re.compile(r"https?://[^\s)>'\"]+")


class SecretFinding(NamedTuple):
    kind: str
    line: int
    column: int
    match: str


class SecretFoundError(ValueError):
    def __init__(self, source: str, findings: list[SecretFinding]):
        self.source = source
        self.findings = findings
        summary = ", ".join(f"{item.kind}@{item.line}:{item.column}" for item in findings[:5])
        super().__init__(f"secret-like content found in {source}: {summary}")


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("credentialed_url", re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s:/@]+:[^\s@]+@[^\s]+")),
    (
        "assigned_secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret|client[_-]?secret)\b\s*[:=]\s*['\"]?([^\s,'\"]{12,})"
        ),
    ),
    (
        "natural_language_secret",
        re.compile(r"(?i)\b(?:the|this|production|prod)\s+(?:secret|password|token|api key)\s+(?:is|was|:)\s+([^\n]{12,})"),
    ),
)

HEX_RE = re.compile(r"\b[0-9a-fA-F]{32,}\b")
ALLOWED_HASH_CONTEXT_RE = re.compile(r"(?i)\b(?:commit|sha-?1|md5|sha-?256|checksum|digest|candidate|filename|sha256-)\b")
ASSIGNMENT_CONTEXT_RE = re.compile(r"(?i)\b(?:key|token|password|passwd|secret)\b\s*[:=]")

DEFAULT_SCAN_EXCLUDES = {
    ".git",
    ".long-loop",
    ".agent-state",
    ".venv",
    "node_modules",
    ".kilo/node_modules",
    "memory/.staging",
    "memory/.local",
    "scripts/tests",
    "scripts/spikes",
    "refs",
    "docs/refs-details",
}
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".mp4",
    ".mov",
    ".sqlite",
    ".db",
    ".npy",
}


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {char: value.count(char) for char in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def line_col(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    line_start = text.rfind("\n", 0, offset)
    column = offset + 1 if line_start == -1 else offset - line_start
    return line, column


def _finding(kind: str, text: str, start: int, value: str) -> SecretFinding:
    line, column = line_col(text, start)
    return SecretFinding(kind=kind, line=line, column=column, match=value[:80])


def _is_allowed_hash_context(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 40) : min(len(text), end + 40)]
    return bool(ALLOWED_HASH_CONTEXT_RE.search(window))


def _looks_like_assigned_secret(value: str) -> bool:
    if any(char in value for char in "{}()[]"):
        return False
    if value.startswith(("$", "<")):
        return False
    if len(value) < 16:
        return False
    return shannon_entropy(value) >= 3.5


def _looks_like_placeholder_credentialed_url(value: str) -> bool:
    lowered = value.lower()
    return any(item in lowered for item in ["username:password@", "user:pass@", "example.com"])


def find_secret_findings(text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for kind, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            if kind == "assigned_secret" and not _looks_like_assigned_secret(match.group(1)):
                continue
            if kind == "credentialed_url" and _looks_like_placeholder_credentialed_url(match.group(0)):
                continue
            findings.append(_finding(kind, text, match.start(), match.group(0)))

    for match in HEX_RE.finditer(text):
        if _is_allowed_hash_context(text, match.start(), match.end()):
            continue
        window = text[max(0, match.start() - 32) : match.start()]
        if ASSIGNMENT_CONTEXT_RE.search(window) or shannon_entropy(match.group(0)) >= 3.5:
            findings.append(_finding("high_entropy_hex", text, match.start(), match.group(0)))
    return findings


def assert_no_secrets(text: str, *, source: str = "<text>") -> None:
    findings = find_secret_findings(text)
    if findings:
        raise SecretFoundError(source, findings)


def redact(text: str) -> str:
    redacted = text
    for _kind, pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    redacted = HEX_RE.sub(lambda match: match.group(0) if _is_allowed_hash_context(redacted, match.start(), match.end()) else "[REDACTED_SECRET]", redacted)
    return URL_RE.sub("[REDACTED_URL]", redacted)


def _is_excluded(relative: Path, excludes: set[str]) -> bool:
    rel = relative.as_posix()
    parts = set(relative.parts)
    return any(rel == item or rel.startswith(f"{item}/") or item in parts for item in excludes)


def iter_scan_files(root: Path, excludes: set[str] | None = None):
    active_excludes = excludes or DEFAULT_SCAN_EXCLUDES
    for current_root, dirs, files in os.walk(root):
        current = Path(current_root)
        rel_dir = current.relative_to(root)
        dirs[:] = [name for name in dirs if not _is_excluded((rel_dir / name), active_excludes)]
        for name in files:
            path = current / name
            relative = path.relative_to(root)
            if _is_excluded(relative, active_excludes) or path.suffix.lower() in BINARY_SUFFIXES:
                continue
            yield path


def scan_repo(root: Path) -> tuple[list[tuple[Path, SecretFinding]], list[tuple[Path, str]]]:
    findings: list[tuple[Path, SecretFinding]] = []
    skipped: list[tuple[Path, str]] = []
    for path in iter_scan_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append((path, "decode"))
            continue
        except OSError as exc:
            skipped.append((path, exc.__class__.__name__))
            continue
        for finding in find_secret_findings(text):
            findings.append((path, finding))
    return findings, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared dotfiles redaction and secret scanning utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan-repo", help="Scan a repository with dotfiles exclusions.")
    scan.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    if args.command == "scan-repo":
        root = Path(args.root).resolve()
        findings, skipped = scan_repo(root)
        for path, finding in findings[:50]:
            sys.stderr.write(f"{path.relative_to(root)}:{finding.line}:{finding.column}: {finding.kind}\n")
        if skipped:
            sys.stderr.write(f"secret scan skipped {len(skipped)} undecodable/unreadable file(s)\n")
        if findings:
            sys.stderr.write(f"secret scan failed: {len(findings)} finding(s)\n")
            return 1
        sys.stdout.write("secret scan passed\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

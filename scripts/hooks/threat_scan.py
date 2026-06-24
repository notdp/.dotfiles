#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import asdict, dataclass


# Prompt-context memory blocks these categories because they can directly steer
# the next model turn or hide control characters; asset scans stay warn-only.
BLOCK_CATEGORIES = {"prompt-injection", "exfiltration", "destructive", "invisible-unicode"}
SENSITIVE_EVIDENCE_RE = re.compile(
    r"\b(?:api[-_ ]?keys?|secrets?|(?:access|auth|api)[-_ ]?tokens?|credentials?|env(?:ironment)?\s+vars?)\b",
    re.IGNORECASE,
)
INVISIBLE_UNICODE_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u202a-\u202e\u2066-\u2069]")
THREAT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "prompt-injection",
        re.compile(
            r"\b(?:ignore|disregard|bypass|override)\s+(?:all\s+)?(?:previous|prior|above|system|developer)\s+instructions?\b"
            r"|\breveal\s+(?:the\s+)?(?:system|developer)\s+prompt\b"
            r"|\bact\s+as\s+(?:a\s+)?(?:system|developer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "exfiltration",
        re.compile(
            r"\b(?:collect|read|dump|steal|exfiltrate|upload|send)\b.{0,80}\b(?:api[-_ ]?keys?|secrets?|(?:access|auth|api)[-_ ]?tokens?|credentials?|env(?:ironment)?\s+vars?)\b"
            r"|\b(?:api[-_ ]?keys?|secrets?|(?:access|auth|api)[-_ ]?tokens?|credentials?|env(?:ironment)?\s+vars?)\b.{0,80}\b(?:upload|send|post|exfiltrate|to\s+https?://)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "destructive",
        re.compile(
            r"\b(?:rm\s+-rf\s+/|format\s+(?:disk|drive)|wipe\s+(?:the\s+)?(?:machine|disk|drive)|destroy\s+(?:all\s+)?(?:data|files))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "persistence",
        re.compile(
            r"\b(?:install|create|add)\b.{0,80}\b(?:backdoor|startup|launch\s*agent|cron\s*job|persistent\s+agent)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "network",
        re.compile(
            r"\b(?:curl|wget)\s+https?://\S+\s*(?:\|\s*(?:sh|bash|python)|;\s*(?:sh|bash|python))?"
            r"|\b(?:fetch|download)\s+https?://\S+\s+and\s+(?:run|execute)",
            re.IGNORECASE,
        ),
    ),
    (
        "obfuscation",
        re.compile(
            r"\b(?:base64|encoded\s+payload|decode)\b.{0,80}\b(?:eval|exec|execute|payload)\b"
            r"|\beval\s*\(\s*(?:atob|base64|decode)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


@dataclass(frozen=True)
class ThreatFinding:
    category: str
    decision: str
    source: str
    line: int
    column: int
    evidence: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SanitizedText:
    text: str
    findings: list[ThreatFinding]

    @property
    def blocked(self) -> bool:
        return any(finding.decision == "block" for finding in self.findings)


def decision_for(category: str, trust_level: str) -> str:
    if trust_level == "strict":
        return "block"
    if trust_level == "prompt" and category in BLOCK_CATEGORIES:
        return "block"
    return "warn"


def location_for(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    line_start = text.rfind("\n", 0, index)
    column = index + 1 if line_start == -1 else index - line_start
    return line, column


def evidence_snippet(text: str, start: int, end: int, radius: int = 60) -> str:
    snippet = text[max(0, start - radius) : min(len(text), end + radius)]
    collapsed = re.sub(r"\s+", " ", snippet).strip()[:180]
    return SENSITIVE_EVIDENCE_RE.sub("[REDACTED]", collapsed)


def scan_text(text: str, source: str = "<memory>", trust_level: str = "skill") -> list[ThreatFinding]:
    findings: list[ThreatFinding] = []
    for category, pattern in THREAT_PATTERNS:
        for match in pattern.finditer(text):
            line, column = location_for(text, match.start())
            findings.append(
                ThreatFinding(
                    category=category,
                    decision=decision_for(category, trust_level),
                    source=source,
                    line=line,
                    column=column,
                    evidence=evidence_snippet(text, match.start(), match.end()),
                )
            )
    for match in INVISIBLE_UNICODE_RE.finditer(text):
        line, column = location_for(text, match.start())
        findings.append(
            ThreatFinding(
                category="invisible-unicode",
                decision=decision_for("invisible-unicode", trust_level),
                source=source,
                line=line,
                column=column,
                evidence=f"unicode U+{ord(match.group(0)):04X}",
            )
        )
    return findings


def sanitize_for_prompt(text: str, source: str = "<memory>") -> SanitizedText:
    findings = scan_text(text, source=source, trust_level="prompt")
    blocking = [finding for finding in findings if finding.decision == "block"]
    if not blocking:
        return SanitizedText(text=text, findings=findings)
    categories = ", ".join(sorted({finding.category for finding in blocking}))
    return SanitizedText(text=f"[BLOCKED] threat-scan blocked {source}: {categories}", findings=findings)

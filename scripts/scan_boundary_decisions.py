#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SINGLE_LINE_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "rejection",
        re.compile(
            r"\braise\s+HTTPException\(.*status_code\s*=\s*[45]|"
            r"\breturn\s+(?:JSONResponse|Response)\(.*status_code\s*=\s*[45]"
        ),
        "确认 spec 是否要求拒绝；若不是，先问用户或改为显式降级策略。",
    ),
    ("assert-guard", re.compile(r"\bassert\b"), "确认这是必要不变量，不是 spec 外新增防御。"),
    (
        "default-value",
        re.compile(r"\bor\s+(?:\[\]|\{\}|0\b|None\b)|\?\?\s*(?:\[\]|\{\}|0\b|null\b)"),
        "确认默认值不是越权填空；必要时列入 Boundary decisions。",
    ),
    (
        "retry-backoff",
        re.compile(r"\b(?:time\.sleep|asyncio\.sleep|retry|backoff)\b", re.I),
        "控制流、重试或 sleep 改动需要确认边界与成本影响。",
    ),
    (
        "schema-contract",
        re.compile(
            r"\b(?:response_model|BaseModel|interface\s+\w*Response\b|type\s+\w*Response\b|z\.object|"
            r"success.*data.*error)\b"
        ),
        "API schema/envelope/字段语义变化需要 contract case 或用户确认。",
    ),
)
METRIC_CUE_RE = re.compile(r"\b(?:StatsStore|metrics?\.|counter\(|gauge\(|histogram\(|emit\(|labels?\s*=)", re.I)
STRING_LITERAL_RE = re.compile(r"['\"][^'\"]+['\"]")
IF_BOUNDARY_RE = re.compile(
    r"^\s*if\s+(?:not\s+|len\(.*\)\s*[<>!=]|.*(?:is\s+None|==\s*None|!=\s*None)).*:\s*(?:#.*)?$"
)
EARLY_EXIT_RE = re.compile(r"^\s*(?:return\b|raise\b|continue\b|break\b)")
EXCEPT_RE = re.compile(r"^\s*except\b.*:")
SILENT_EXCEPT_RE = re.compile(r"^\s*(?:pass\b|return\b|continue\b)")


@dataclass(frozen=True)
class AddedLine:
    file: str
    line_number: int
    text: str


@dataclass(frozen=True)
class Finding:
    kind: str
    file: str
    line_number: int
    snippet: str
    suggestion: str


def is_default_excluded(file_path: str) -> bool:
    path = Path(file_path)
    parts = path.parts
    return (
        path.suffix.lower() in {".md", ".markdown", ".html", ".htm"}
        or parts[:2] == ("scripts", "tests")
        or parts[:2] == (".factory", "hooks")
        or parts[:1] == ("tests",)
        or file_path == "scripts/scan_boundary_decisions.py"
        or file_path == "scripts/hook_boundary_gate.py"
    )


def git_diff() -> str:
    chunks: list[str] = []
    for command in (
        ["git", "diff", "--cached", "--", ".", ":!refs/**"],
        ["git", "diff", "--", ".", ":!refs/**"],
    ):
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"{' '.join(command)} failed")
        chunks.append(result.stdout)
    chunks.append(untracked_diff())
    return "".join(chunks)


def untracked_diff() -> str:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")

    chunks: list[str] = []
    for raw_path in result.stdout.splitlines():
        path = Path(raw_path)
        if path.parts and path.parts[0] == "refs":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        chunks.extend(
            [
                f"diff --git a/{raw_path} b/{raw_path}",
                "--- /dev/null",
                f"+++ b/{raw_path}",
                f"@@ -0,0 +1,{len(lines)} @@",
            ]
        )
        chunks.extend(f"+{line}" for line in lines)
    return "\n".join(chunks) + ("\n" if chunks else "")


def parse_added_lines(diff_text: str) -> list[AddedLine]:
    current_file: str | None = None
    new_line: int | None = None
    added: list[AddedLine] = []

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            path = raw_line[4:].strip()
            if path == "/dev/null":
                current_file = None
            elif path.startswith("b/"):
                current_file = path[2:]
            else:
                current_file = path
            continue

        if raw_line.startswith("@@ "):
            match = re.search(r"\+(\d+)(?:,\d+)?", raw_line)
            new_line = int(match.group(1)) if match else None
            continue

        if current_file is None or new_line is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added.append(AddedLine(current_file, new_line, raw_line[1:]))
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        else:
            new_line += 1
    return added


def scan_added_lines(added_lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    lines_by_file: dict[str, list[AddedLine]] = {}

    for line in added_lines:
        if is_default_excluded(line.file):
            continue
        lines_by_file.setdefault(line.file, []).append(line)
        findings.extend(scan_single_line(line))

    for lines in lines_by_file.values():
        findings.extend(scan_sliding_windows(lines))
    return dedupe_findings(findings)


def scan_single_line(line: AddedLine) -> list[Finding]:
    findings: list[Finding] = []
    for kind, pattern, suggestion in SINGLE_LINE_PATTERNS:
        if pattern.search(line.text):
            findings.append(Finding(kind, line.file, line.line_number, line.text.strip(), suggestion))
    if METRIC_CUE_RE.search(line.text) and STRING_LITERAL_RE.search(line.text):
        findings.append(
            Finding(
                "observability-routing",
                line.file,
                line.line_number,
                line.text.strip(),
                "Metric name/label/path routing changes need a synthetic call or explicit route evidence.",
            )
        )
    return findings


def scan_sliding_windows(lines: list[AddedLine]) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines):
        window = lines[index + 1 : index + 4]
        if IF_BOUNDARY_RE.search(line.text) and any(EARLY_EXIT_RE.search(next_line.text) for next_line in window):
            findings.append(
                Finding(
                    "implicit-branch",
                    line.file,
                    line.line_number,
                    line.text.strip(),
                    "新增边界分支后接 early exit；确认这个行为在 spec 内。",
                )
            )
        if EXCEPT_RE.search(line.text) and any(SILENT_EXCEPT_RE.search(next_line.text) for next_line in window):
            findings.append(
                Finding(
                    "silent-catch",
                    line.file,
                    line.line_number,
                    line.text.strip(),
                    "silent catch/skip must be user-approved or recorded as a boundary decision.",
                )
            )
    return findings


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, int, str]] = set()
    deduped: list[Finding] = []
    for finding in findings:
        key = (finding.kind, finding.file, finding.line_number, finding.snippet)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def markdown_escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_findings(findings: list[Finding]) -> str:
    lines = [
        "## Boundary Decision Scan",
        "",
        "| 类型 | 文件 | 行 | 片段 | 建议 |",
        "|------|------|----|------|------|",
    ]
    for finding in findings:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape_cell(finding.kind),
                    markdown_escape_cell(finding.file),
                    str(finding.line_number),
                    f"`{markdown_escape_cell(finding.snippet)}`",
                    markdown_escape_cell(finding.suggestion),
                ]
            )
            + " |"
        )
    lines.extend(["", "## 总结", f"- 命中 {len(findings)} 条"])
    return "\n".join(lines) + "\n"


def render_hook_output(findings: list[Finding]) -> str:
    if not findings:
        return json.dumps({"suppressOutput": True})
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "Boundary decision scan found possible boundary changes:\n\n"
                + render_findings(findings),
            },
            "suppressOutput": True,
        },
        ensure_ascii=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan added diff lines for boundary decisions.")
    parser.add_argument("--stdin", action="store_true", help="Read unified diff from stdin.")
    parser.add_argument("--hook", action="store_true", help="Emit hook JSON and never block by exit code.")
    args = parser.parse_args()

    try:
        diff_text = sys.stdin.read() if args.stdin else git_diff()
    except RuntimeError as exc:
        if args.hook:
            print(json.dumps({"suppressOutput": True}))
            return 0
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = scan_added_lines(parse_added_lines(diff_text))
    if args.hook:
        print(render_hook_output(findings))
        return 0
    print(render_findings(findings), end="")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

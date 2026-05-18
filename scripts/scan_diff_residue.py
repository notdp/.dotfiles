#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


FINDING_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("TODO/FIXME", re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b"), "删除、改写，或转成 issue"),
    ("DEBUG 前缀", re.compile(r"\[DEBUG-[A-Za-z0-9_-]+\]"), "删除临时插桩"),
    ("调试打印", re.compile(r"\b(?:console\.log|print\(|dbg!|fmt\.Println|pp )"), "删除调试打印"),
    ("调试断点", re.compile(r"\b(?:debugger;|breakpoint\(\)|pdb\.set_trace)"), "删除断点"),
    (
        "疑似 secret",
        re.compile(r"\b(?:password|api[_-]?key|token|secret)\s*=\s*[\"'][^\"']{6,}[\"']", re.I),
        "确认不是凭据；若是凭据，立即移除并轮换",
    ),
    ("临时变量名", re.compile(r"\b(?:foo|bar|tmp1|test_xxx)\b"), "生产代码中改成有意图的名字"),
)


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
        path.suffix.lower() in {".md", ".markdown"}
        or parts[:2] == ("scripts", "tests")
        or parts[:2] == ("scripts", "hooks")
        or parts[:2] == (".factory", "hooks")
        or file_path == "scripts/scan_diff_residue.py"
        or file_path == "scripts/scan_operational_task_contract.py"
        or file_path == "scripts/scan_boundary_decisions.py"
    )


def git_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "--cached", "--", ".", ":!refs/**"],
        text=True,
        capture_output=True,
        check=False,
    )
    unstaged = subprocess.run(
        ["git", "diff", "--", ".", ":!refs/**"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff --cached failed")
    if unstaged.returncode != 0:
        raise RuntimeError(unstaged.stderr.strip() or "git diff failed")
    return result.stdout + unstaged.stdout + untracked_diff()


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
        except UnicodeDecodeError:
            continue
        except OSError:
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
    for added_line in added_lines:
        if is_default_excluded(added_line.file):
            continue
        for kind, pattern, suggestion in FINDING_PATTERNS:
            if pattern.search(added_line.text):
                findings.append(
                    Finding(
                        kind=kind,
                        file=added_line.file,
                        line_number=added_line.line_number,
                        snippet=added_line.text.strip(),
                        suggestion=suggestion,
                    )
                )
    return findings


def markdown_escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_findings(findings: list[Finding]) -> str:
    lines = [
        "## Diff Scan 结果",
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
                "additionalContext": "Diff residue scan found possible cleanup issues:\n\n" + render_findings(findings),
            },
            "suppressOutput": True,
        },
        ensure_ascii=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan added diff lines for debug residue.")
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

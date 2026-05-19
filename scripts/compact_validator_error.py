#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys


PY_FILE_LINE_RE = re.compile(r'File "([^"]+)", line (\d+)')
TS_ERROR_RE = re.compile(r"^([^()\s]+)\((\d+),(\d+)\):\s*(error\s+TS\d+:.+)$", re.I)
FAILED_TARGET_RE = re.compile(r"\bFAILED\s+(.+)")
ERROR_LINE_RE = re.compile(r"(\b(?:AssertionError|Error|Exception|Traceback|FAILED|error TS\d+)\b.*)", re.I)


def first_match(lines: list[str], pattern: re.Pattern[str]) -> re.Match[str] | None:
    for line in lines:
        match = pattern.search(line)
        if match:
            return match
    return None


def first_actionable_error(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        ts_match = TS_ERROR_RE.search(stripped)
        if ts_match:
            return ts_match.group(4)
        match = ERROR_LINE_RE.search(stripped)
        if match and stripped != "Traceback (most recent call last):":
            return stripped
    return "unknown"


def suspected_file(lines: list[str]) -> str:
    ts_match = first_match(lines, TS_ERROR_RE)
    if ts_match:
        return ts_match.group(1)
    py_match = first_match(lines, PY_FILE_LINE_RE)
    if py_match:
        return f"{py_match.group(1)}:{py_match.group(2)}"
    return "unknown"


def failing_target(lines: list[str]) -> str:
    match = first_match(lines, FAILED_TARGET_RE)
    return match.group(1).strip() if match else "unknown"


def render_summary(command: str, check: str, exit_code: str, log_text: str) -> str:
    lines = log_text.splitlines()
    return "\n".join(
        [
            "ValidatorErrorSummary:",
            f"- Command: `{command or 'unknown'}`",
            f"- Check: {check or 'unknown'}",
            f"- Exit: {exit_code or 'unknown'}",
            f"- First actionable error: {first_actionable_error(lines)}",
            f"- Suspected file: {suspected_file(lines)}",
            f"- Recent failing target: {failing_target(lines)}",
            "- Next probe: inspect the suspected file and rerun the narrowest failing check",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Compact validator failure logs into an actionable summary.")
    parser.add_argument("--command", default="")
    parser.add_argument("--check", default="")
    parser.add_argument("--exit-code", default="")
    args = parser.parse_args()
    sys.stdout.write(render_summary(args.command, args.check, args.exit_code, sys.stdin.read()) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

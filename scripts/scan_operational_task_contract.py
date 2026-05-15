#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


OPERATIONAL_PATH_RE = re.compile(r"(backfill|migration|migrate|sync|pipeline|batch|job|etl|repair|reconcile)", re.I)
CLI_RE = re.compile(r"\b(argparse|click|typer|commander|yargs|ArgumentParser|add_argument)\b")
RISK_RE = re.compile(
    r"(--dry-run|--apply|--run-until-empty|batch[-_ ]?size|concurrenc|backfill|migration|migrate|sync|pipeline|"
    r"reconcile|repair|cursor|checkpoint|while\s+True)",
    re.I,
)

CONTRACT_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "可观测性",
        re.compile(r"(progress|percent|percentage|eta\b|heartbeat|phase|current/.+total|tqdm|rich\.progress)", re.I),
        "长任务需要打印阶段、当前/总量、百分比、速率或 ETA，并有 heartbeat，避免看起来卡死。",
    ),
    (
        "可恢复性",
        re.compile(r"(checkpoint|cursor|resume|state[-_ ]?file|idempotenc|last[_-]?id|offset|processed[_-]?ids)", re.I),
        "批处理/数据任务需要 checkpoint、cursor、state file 或幂等键，中断后可继续。",
    ),
    (
        "dry-run 数据证据",
        re.compile(r"(count|sample|preview|diff|invariant|checksum|reconcile|row[_-]?count|planned)", re.I),
        "dry-run 需要输出计划变更数、样本、diff/聚合、不变量或失败样本，不只是 smoke run。",
    ),
    (
        "健壮性",
        re.compile(r"(retry|retries|backoff|failed[_-]?set|dead[-_ ]?letter|partial[_-]?failure|timeout)", re.I),
        "长任务需要重试/退避、部分失败记录或可诊断的失败集合。",
    ),
)

BOUNDED_CONCURRENCY_RE = re.compile(
    r"(Semaphore|bounded|rate[-_ ]?limit|backpressure|max_workers|worker[_-]?pool|--concurrency|concurrency)",
    re.I,
)
APPLY_CONFIRM_RE = re.compile(r"(--yes|--confirm|confirm|confirmation|force|requires.+apply|apply.+requires)", re.I)
DRY_RUN_RE = re.compile(r"(--dry-run|dry_run|dryRun)", re.I)
APPLY_RE = re.compile(r"(--apply|\bapply\b)", re.I)
CONCURRENCY_RE = re.compile(r"(concurrenc|asyncio|ThreadPoolExecutor|ProcessPoolExecutor|worker)", re.I)


@dataclass(frozen=True)
class AddedLine:
    file: str
    line_number: int
    text: str


@dataclass(frozen=True)
class FileChunk:
    file: str
    first_line: int
    text: str


@dataclass(frozen=True)
class Finding:
    kind: str
    file: str
    line_number: int
    evidence: str
    suggestion: str


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
        if path.parts and path.parts[0] in {"refs", ".factory"}:
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


def group_by_file(added_lines: list[AddedLine]) -> list[FileChunk]:
    grouped: dict[str, list[AddedLine]] = {}
    for line in added_lines:
        grouped.setdefault(line.file, []).append(line)
    return [
        FileChunk(file=file, first_line=lines[0].line_number, text="\n".join(line.text for line in lines))
        for file, lines in grouped.items()
        if lines
    ]


def is_excluded(file_path: str) -> bool:
    path = Path(file_path)
    parts = path.parts
    return (
        path.suffix.lower() in {".md", ".markdown", ".json", ".lock"}
        or parts[:2] == ("scripts", "tests")
        or file_path == "scripts/scan_operational_task_contract.py"
        or file_path == "scripts/scan_boundary_decisions.py"
    )


def is_operational_chunk(chunk: FileChunk) -> bool:
    if is_excluded(chunk.file):
        return False
    text = chunk.text
    return bool(OPERATIONAL_PATH_RE.search(chunk.file) or (CLI_RE.search(text) and RISK_RE.search(text)))


def scan_chunks(chunks: list[FileChunk]) -> list[Finding]:
    findings: list[Finding] = []
    for chunk in chunks:
        if not is_operational_chunk(chunk):
            continue

        for kind, pattern, suggestion in CONTRACT_PATTERNS:
            if kind == "dry-run 数据证据" and not DRY_RUN_RE.search(chunk.text):
                continue
            if not pattern.search(chunk.text):
                findings.append(Finding(kind, chunk.file, chunk.first_line, "operational-looking diff", suggestion))

        if CONCURRENCY_RE.search(chunk.text) and not BOUNDED_CONCURRENCY_RE.search(chunk.text):
            findings.append(
                Finding(
                    "有界并发",
                    chunk.file,
                    chunk.first_line,
                    "concurrency/worker cue without bound",
                    "并发任务需要显式上限、batch size、rate limit 或 backpressure。",
                )
            )

        if APPLY_RE.search(chunk.text) and not APPLY_CONFIRM_RE.search(chunk.text):
            findings.append(
                Finding(
                    "apply 安全确认",
                    chunk.file,
                    chunk.first_line,
                    "--apply/apply cue",
                    "`--apply` 或破坏性操作需要显式确认、preset 或 guard-gitops 升级路径。",
                )
            )
    return findings


def markdown_escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_findings(findings: list[Finding]) -> str:
    lines = [
        "## Operational Task Contract Scan",
        "",
        "| 类型 | 文件 | 行 | 证据 | 建议 |",
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
                    markdown_escape_cell(finding.evidence),
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
    context = (
        "Operational task contract scan found possible gaps. Load /dev-operational-task and address these before "
        "claiming the task is complete:\n\n"
        + render_findings(findings)
    )
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": context,
            },
            "suppressOutput": True,
        },
        ensure_ascii=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan diffs for long/data task operational contract gaps.")
    parser.add_argument("--stdin", action="store_true", help="Read unified diff from stdin.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when findings exist.")
    parser.add_argument("--hook", action="store_true", help="Emit Droid hook JSON and never block by exit code.")
    args = parser.parse_args()

    try:
        diff_text = sys.stdin.read() if args.stdin else git_diff()
    except RuntimeError as exc:
        if args.hook:
            print(json.dumps({"suppressOutput": True}))
            return 0
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = scan_chunks(group_by_file(parse_added_lines(diff_text)))
    if args.hook:
        print(render_hook_output(findings))
        return 0

    print(render_findings(findings), end="")
    return 1 if findings and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""扫 git diff 新增行里的"脆弱点触点"——外部依赖调用/写入。

定位：advisory 弱信号，不是门禁。命中即提醒 agent 这段触及 fragility-types.md 的
高风险类型（SaaS 配额/契约/鉴权），确认相关不确定性已用 spike 验证过（打真实/sandbox
API、读官方 limits 页），而非把未验证假设直接放进系统试错。

强度上限：外部依赖触点可从 diff 高精度判定，但"是否已 spike 验证"无法从 diff 判定，
故只能 advisory。--hook 模式永不阻塞（fail-open），与 scan_boundary_decisions 同级。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# 已知 SaaS / 云 / 第三方平台触点——高精度（这些名字出现基本就是外部依赖）。
EXTERNAL_DEP_RE = re.compile(
    r"\b(?:feishu|lark|larksuite|bitable|notion|airtable|stripe|twilio|sendgrid|"
    r"dingtalk|wecom|dashscope|aliyun|oss2|boto3|firebase|supabase|mailgun|"
    r"sendcloud|paypal|alipay|wxpay)\b|飞书|钉钉|企业微信|多维表格",
    re.I,
)
# HTTP 客户端写操作——对外写请求是契约/配额/幂等脆弱点的直接信号。
HTTP_WRITE_RE = re.compile(
    r"\b(?:requests|httpx|aiohttp|session|http_client|client)\.(?:post|put|patch|delete)\s*\(|"
    r"\baxios\.(?:post|put|patch|delete)\s*\(|"
    r"\.(?:batch_create|create_record|add_record|append_row|insert_rows?)\s*\(",
    re.I,
)

SUGGESTION = (
    "外部依赖触点（fragility-types #1/#2/#3：SaaS 配额-满载 / 第三方契约 / 鉴权回调）。"
    "确认相关不确定性已 spike 验证（打真实/sandbox API、读官方 limits 页、连发两次验幂等），"
    "而非把未验证假设直接放进系统试错。"
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


def is_excluded(file_path: str) -> bool:
    path = Path(file_path)
    parts = path.parts
    return (
        path.suffix.lower() in {".md", ".markdown", ".html", ".htm", ".txt", ".json", ".lock"}
        or parts[:2] == ("scripts", "tests")
        or parts[:2] == ("scripts", "hooks")
        or parts[:2] == (".factory", "hooks")
        or parts[:1] == ("tests",)
        or path.name.startswith("scan_")
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
    for line in added_lines:
        if is_excluded(line.file):
            continue
        if EXTERNAL_DEP_RE.search(line.text) or HTTP_WRITE_RE.search(line.text):
            findings.append(
                Finding("fragility-touchpoint", line.file, line.line_number, line.text.strip(), SUGGESTION)
            )
    return dedupe_findings(findings)


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, int]] = set()
    deduped: list[Finding] = []
    for finding in findings:
        key = (finding.kind, finding.file, finding.line_number)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def markdown_escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_findings(findings: list[Finding]) -> str:
    lines = [
        "## Fragility Touchpoint Scan",
        "",
        "| 文件 | 行 | 片段 | 建议 |",
        "|------|----|------|------|",
    ]
    for finding in findings:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape_cell(finding.file),
                    str(finding.line_number),
                    f"`{markdown_escape_cell(finding.snippet)}`",
                    markdown_escape_cell(finding.suggestion),
                ]
            )
            + " |"
        )
    lines.extend(["", "## 总结", f"- 命中 {len(findings)} 条（advisory，非门禁）"])
    return "\n".join(lines) + "\n"


def render_hook_output(findings: list[Finding]) -> str:
    if not findings:
        return json.dumps({"suppressOutput": True})
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "Fragility touchpoints in this change — confirm each was spiked before "
                "implementing (docs/software-engineering-research/fragility-types.md):\n\n"
                + render_findings(findings),
            },
            "suppressOutput": True,
        },
        ensure_ascii=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan added diff lines for external-dependency fragility touchpoints.")
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

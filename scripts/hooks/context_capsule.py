#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


CRITICAL_OPERATION_ACTION_RE = r"(关掉|停掉|回收|释放|降配|不用了|降成本|停止计费|stop|shutdown|release|destroy|decommission|downsize|cut cost)"
CRITICAL_OPERATION_RISK_RE = r"(GPU|ECS|云|实例|计费|费用|账单|生产|数据库|权限|RDS|OSS|Kafka|aliyun|阿里云|aws|k8s|delete|destroy)"
CRITICAL_OPERATION_PROMPT_RE = re.compile(
    rf"(?=.*{CRITICAL_OPERATION_ACTION_RE})(?=.*{CRITICAL_OPERATION_RISK_RE})",
    re.I,
)
OPERATIONAL_PROMPT_RE = re.compile(
    r"(刷数据|同步|迁移|回填|修复数据|批处理|"
    r"(?<![A-Za-z0-9_])(?:dry-?run|apply|run-until-empty|concurrenc\w*|"
    r"backfill|migration|migrate|sync|pipeline|batch|etl|repair|reconcile)(?![A-Za-z0-9_]))",
    re.I,
)
CODE_FENCE_RE = re.compile(r"```.*?```", re.S)
CAPSULE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "security-gitops.md",
        re.compile(
            r"(prod|生产|deploy|部署|ssh|scp|push|release|secret|token|auth|permission|权限|db|database|数据库|kubectl|terraform|helm|"
            r"发布|上线|下线|回滚|env|gitignore|凭据|密钥|"
            r"external target|exploit|c2|phishing|credential access|lateral movement|brute[- ]?force|auth bypass)",
            re.I,
        ),
    ),
    ("operational-task.md", re.compile(rf"(?:{OPERATIONAL_PROMPT_RE.pattern})|(?:{CRITICAL_OPERATION_PROMPT_RE.pattern})", re.I)),
    (
        "debug-task.md",
        re.compile(
            r"(bug|error|fail|failed|flaky|traceback|exception|报错|失败|异常|复现|incident|"
            r"原因分析|根因|排查|定位|不符合预期|不一致|不对|为何|为什么|搞丢|丢失|没生效|不生效)",
            re.I,
        ),
    ),
    (
        "ui-task.md",
        re.compile(r"(ui|css|react|vue|svelte|tsx|jsx|页面|视觉|截图|figma|overflow|mobile|desktop|布局|对齐|间距|留白|空白|样式|配色|按钮|弹窗)", re.I),
    ),
    (
        "scope-task.md",
        re.compile(
            r"(新增|增加|加一个|加个|添加|实现|做一个|做个|改成|换成|重构|优化|implement|refactor|optimi[sz]e|feature)",
            re.I,
        ),
    ),
    (
        "planning-task.md",
        re.compile(r"(方案|计划|架构|怎么做|approach|architecture|plan|options|phase|spec)", re.I),
    ),
    (
        "boundary-decision.md",
        re.compile(
            r"(封装|wrap|wrapper|包装|包一层|接入|对接|集成|adapter|integration|service\s+wrap|"
            r"schema|response_model|metric|metrics|埋点|指标|data source|数据源|canonical|snapshot|"
            r"sampling|limit|context|hook|CLAUDE\.md|AGENTS\.md)",
            re.I,
        ),
    ),
)
MAX_PROMPT_CONTEXT_CHARS = 2200
MATCH_HEAD_CHARS = 240  # 长 prompt 只用首段做 capsule 匹配, 避免尾部粘贴内容/日志/上下文撞词(FP 71% 来源)


def config_root() -> Path:
    return Path(__file__).resolve().parents[2]


def project_root() -> Path:
    return Path(os.environ.get("FACTORY_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def read_capsule(name: str) -> str:
    path = config_root() / "agents" / "context-capsules" / name
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def capsule_heading(capsule: str) -> str:
    for line in capsule.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return ""


def prompt_for_matching(prompt: str) -> str:
    stripped = CODE_FENCE_RE.sub("", prompt)
    # 长 prompt(任务描述/粘贴日志/背景上下文)尾部是 FP 撞词重灾区——只用首段匹配。
    return stripped[:MATCH_HEAD_CHARS] if len(stripped) > MATCH_HEAD_CHARS else stripped


def matching_capsules(prompt: str) -> list[tuple[str, re.Pattern[str], str]]:
    searchable_prompt = prompt_for_matching(prompt)
    return [
        (name, pattern, capsule)
        for name, pattern in CAPSULE_RULES
        if pattern.search(searchable_prompt)
        for capsule in [read_capsule(name)]
        if capsule
    ]


def json_context(event_name: str, context: str) -> str:
    if not context:
        return json.dumps({"suppressOutput": True})
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": context,
            },
            "suppressOutput": True,
        },
        ensure_ascii=False,
    )


def load_hook_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def session_context(event_name: str) -> str:
    return json.dumps({"suppressOutput": True})


def prompt_context(hook_input: dict) -> str:
    prompt = str(hook_input.get("prompt") or "")
    matches = matching_capsules(prompt)
    if not matches:
        return json.dumps({"suppressOutput": True})
    capsules = [capsule for _, _, capsule in matches]
    context = join_capsules(capsules)
    return json_context("UserPromptSubmit", context)


def join_capsules(capsules: list[str]) -> str:
    separator = "\n\n---\n\n"
    context = separator.join(capsules)
    if len(context) <= MAX_PROMPT_CONTEXT_CHARS:
        return context
    budget = MAX_PROMPT_CONTEXT_CHARS - (len(separator) * (len(capsules) - 1))
    per_capsule_budget = max(1, budget // len(capsules))
    return separator.join(capsule[:per_capsule_budget].rstrip() for capsule in capsules)[:MAX_PROMPT_CONTEXT_CHARS]


def markdown_escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_prompt_preview(prompt: str) -> str:
    matches = matching_capsules(prompt)
    matched_names = {name for name, _, _ in matches}
    context = "\n\n---\n\n".join(capsule for _, _, capsule in matches)[:MAX_PROMPT_CONTEXT_CHARS]
    lines = [
        "## Context Capsule Preview",
        "",
        f"Prompt: `{markdown_escape_cell(prompt)}`",
        f"Final context chars: {len(context)} / {MAX_PROMPT_CONTEXT_CHARS}",
        "",
    ]
    if not matches:
        lines.extend(["No capsules matched.", ""])
    lines.extend(
        [
            "| Capsule | Status | Heading | Rule |",
            "|---|---|---|---|",
        ]
    )
    for name, pattern in CAPSULE_RULES:
        capsule = read_capsule(name)
        status = "matched" if name in matched_names else "not matched"
        heading = capsule_heading(capsule) if capsule else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape_cell(name),
                    status,
                    markdown_escape_cell(heading),
                    f"`{markdown_escape_cell(pattern.pattern)}`",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def post_tool_context(root: Path) -> str:
    contexts: list[str] = []
    for script_name in ["scan_operational_task_contract.py", "scan_diff_residue.py", "scan_boundary_decisions.py"]:
        scanner = config_root() / "scripts" / script_name
        if not scanner.exists():
            continue
        result = subprocess.run(
            ["python3", str(scanner), "--hook"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if not result.stdout.strip():
            continue
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        context = payload.get("hookSpecificOutput", {}).get("additionalContext")
        if context:
            contexts.append(str(context))
    if contexts:
        return json_context("PostToolUse", "\n\n---\n\n".join(contexts))
    return json.dumps({"suppressOutput": True})


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject short Droid context capsules.")
    parser.add_argument("--event", choices=["session-start", "pre-compact", "prompt", "post-tool"], required=True)
    parser.add_argument("--preview", action="store_true", help="Print a Markdown capsule routing preview.")
    parser.add_argument("--prompt-text", default="", help="Prompt text for --preview mode.")
    args = parser.parse_args()

    root = project_root()
    hook_input = load_hook_input()
    if args.preview:
        prompt = args.prompt_text or str(hook_input.get("prompt") or "")
        sys.stdout.write(render_prompt_preview(prompt) + "\n")
    elif args.event == "session-start":
        print(session_context("SessionStart"))
    elif args.event == "pre-compact":
        print(session_context("PreCompact"))
    elif args.event == "prompt":
        print(prompt_context(hook_input))
    else:
        print(post_tool_context(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

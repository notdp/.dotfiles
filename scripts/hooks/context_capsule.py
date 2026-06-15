#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
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
            r"发布|上线|下线|回滚|env|gitignore|凭据|密钥|推到远端|git\s*push|推送到\s*\w+|"
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
CAPSULE_SHORT: dict[str, str] = {
    "scope-task.md": "scope",
    "planning-task.md": "planning",
    "debug-task.md": "debug",
    "security-gitops.md": "security",
    "ui-task.md": "ui",
    "boundary-decision.md": "boundary",
    "operational-task.md": "operational",
}
MAX_PROMPT_CONTEXT_CHARS = 2200
MATCH_HEAD_CHARS = 240  # 长 prompt 只用首段做正则 fallback 匹配, 避免尾部粘贴内容撞词(FP 71% 来源)

# deepseek 主路由: 三平台 300 样本实测 F1 54% vs 正则 27%, 跨平台稳(正则 kilo 崩到 30%)。
# 失败(无 key/超时/异常/CAPSULE_NO_LLM)一律 fallback 正则, hook 永不阻塞。
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_TIMEOUT = 6  # 秒; hook timeout 10s, 留余量给 fallback
DEEPSEEK_KEYFILE = "~/.config/deepseek/apikey"
DEEPSEEK_SYSTEM = (
    "你是 capsule 路由分类器。判断用户 prompt 理想情况下应注入哪些 context capsule"
    "(给 AI 编程助手的纪律提醒)。\n\n"
    "7 个 capsule(只在与主要意图真正相关时选, 宁缺勿滥):\n"
    "1. \"Scope Alignment Capsule\" — 要新增/修改/优化/重构功能但问题未锚定(没说清要解决什么问题); "
    "需求已具体到文件级或纯机械操作则不选。\n"
    "2. \"Planning Task Capsule\" — 明确要方案/计划/架构/阶段拆分/技术选型。\n"
    "3. \"Debug Task Capsule\" — 故障/异常/bug/行为不符预期/排查/定位/原因分析。注意:code review、"
    "审查代码变更、看 review 结论不是 debug。\n"
    "4. \"Security / GitOps Capsule\" — 生产/部署/远程机器/数据库/secret凭据/权限/推送发布上线下线/供应链/外部安全测试。\n"
    "5. \"UI Task Capsule\" — 前端/CSS/页面/组件/视觉/截图/布局。\n"
    "6. \"Boundary-Decision Capsule\" — 改动产生边界决策: service/wrapper/adapter/schema/API契约/"
    "metric埋点/数据源/采样/上限/hook/CLAUDE.md/AGENTS.md。\n"
    "7. \"Operational Task Capsule\" — 长耗时批处理/数据同步/回填/迁移脚本/dry-run/apply/可中断长任务。\n\n"
    "原则: 按主要意图判断, 不是碰到关键词就算(如\"符合原有设计吗\"是诊断不是 planning); "
    "只选真正相关的; 多数日常 prompt 是空或单个; 选 4+ 个几乎一定过度。\n\n"
    "正反示例(学边界, 非穷举):\n"
    "- \"再 review 一下\" → [] (要求审查代码, 不是 debug/planning/scope)\n"
    "- \"看 review 意见\" → [] (阅读已有 review 结论)\n"
    "- \"commit 一下\" → [] (简单执行操作)\n"
    "- \"这个 bug 怎么修\" → [\"Debug Task Capsule\"]\n"
    "- \"帮我看看为什么报错\" → [\"Debug Task Capsule\"]\n"
    "- \"加一个缓存层\" → [\"Scope Alignment Capsule\"]\n"
    "- \"这个改动需要改 schema 吗\" → [\"Boundary-Decision Capsule\"]\n"
    "- \"帮我设计一下方案\" → [\"Planning Task Capsule\"]\n"
    "- \"推到远端\" → [\"Security / GitOps Capsule\"]\n"
    "- \"跑一下迁移脚本\" → [\"Operational Task Capsule\"]\n"
    "- \"按钮样式不对\" → [\"UI Task Capsule\", \"Debug Task Capsule\"]\n\n"
    "只输出一个 JSON 对象 {\"capsules\": [\"名称\", ...]}:\n"
    "- capsules 是字符串数组, 每个元素必须是上面 7 个 capsule 的精确名称之一\n"
    "- 禁止任何其他字段, 元素必须是字符串不能是对象\n"
    "- 都不相关则 {\"capsules\": []}\n"
    "示例: {\"capsules\": [\"Debug Task Capsule\"]}"
)


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


def deepseek_api_key() -> str | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key and key.strip():
        return key.strip()
    try:
        return Path(DEEPSEEK_KEYFILE).expanduser().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def heading_to_name() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for name, _ in CAPSULE_RULES:
        heading = capsule_heading(read_capsule(name))
        if heading:
            mapping[heading] = name
    return mapping


def classify_with_deepseek(prompt: str) -> set[str] | None:
    """deepseek 主分类, 返回 capsule 文件名集合; 任何失败返回 None(caller fallback 正则)。"""
    if os.environ.get("CAPSULE_NO_LLM") or not prompt.strip():
        return None
    key = deepseek_api_key()
    if not key:
        return None
    body = json.dumps(
        {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": DEEPSEEK_SYSTEM},
                {"role": "user", "content": prompt[:2000]},
            ],
            "temperature": 0,
            "max_tokens": 200,
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    try:
        request = urllib.request.Request(
            DEEPSEEK_URL,
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=DEEPSEEK_TIMEOUT) as response:
            payload = json.loads(response.read())
        content = payload["choices"][0]["message"]["content"]
        headings = json.loads(content).get("capsules", [])
    except Exception:
        return None
    name_map = heading_to_name()
    return {name_map[h] for h in headings if isinstance(h, str) and h in name_map}


def resolve_capsule_names(prompt: str) -> list[str]:
    """决定注入哪些 capsule: deepseek 主, 失败 fallback 正则。返回按 CAPSULE_RULES 顺序的文件名。"""
    selected = classify_with_deepseek(prompt)
    if selected is None:
        searchable = prompt_for_matching(prompt)
        selected = {name for name, pattern in CAPSULE_RULES if pattern.search(searchable)}
    return [name for name, _ in CAPSULE_RULES if name in selected]


def json_context(event_name: str, context: str, system_message: str | None = None) -> str:
    payload: dict = {"suppressOutput": True}
    if context:
        payload["hookSpecificOutput"] = {"hookEventName": event_name, "additionalContext": context}
    if system_message:
        payload["systemMessage"] = system_message  # CC/Droid 终端通知形式显示, 不进 transcript
    return json.dumps(payload, ensure_ascii=False)


def load_hook_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def session_context(event_name: str) -> str:
    return json.dumps({"suppressOutput": True})


def current_time_note() -> str:
    # 每条 prompt 注入当前时间, 给 agent 时间感知(LLM 无内置时钟;
    # session 级注入会在长会话/compact 后过期, 故每条都带最新时间)。
    return f"[system] Current time: {datetime.now().astimezone().isoformat(timespec='seconds')}"


def prompt_context(hook_input: dict) -> str:
    prompt = str(hook_input.get("prompt") or "")
    names = resolve_capsule_names(prompt)
    capsules = [capsule for name in names for capsule in [read_capsule(name)] if capsule]
    # 时间行独立 prepend, 不占 capsule 的 MAX_PROMPT_CONTEXT_CHARS 截断预算(它短且必要)。
    context = current_time_note()
    if capsules:
        context += "\n\n---\n\n" + join_capsules(capsules)
    # 可观测: 有 capsule 时给用户一行摘要(systemMessage 在 CC/Droid 终端显示, 不进 transcript、不打扰模型)。
    system_message = "↳ capsules: " + ", ".join(CAPSULE_SHORT.get(n, n) for n in names) if names else None
    return json_context("UserPromptSubmit", context, system_message)


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

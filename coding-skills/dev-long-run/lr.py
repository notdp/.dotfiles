#!/usr/bin/env python3
"""dev-long-run 控制核心(纯逻辑部分)。

薄 wrapper，多 pane 调度脑在 loop orchestrator(LLM)里，本文件只放可单测的纯逻辑：
config schema 校验、variant→effort 按 backend 分流(L17)、SESSIONS.md 表读写、
state.json 扩字段、worktree/分支命名。spec: docs/specs/dev-long-run/overview.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def slugify(name: str) -> str:
    """自由任务名 → git-branch + 文件系统安全 slug(小写, 非字母数字折成单连字符)。"""
    slug = try_slugify(name)
    if not slug:
        raise ValueError(f"cannot derive slug from {name!r}")
    return slug


def try_slugify(name: str) -> str | None:
    """slugify 的非抛错版本, 用于 CLI 先给可恢复提示。"""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or None


BACKENDS = ("kilo", "claude_cli", "droid", "custom")
AUTONOMY = ("off", "low", "medium", "high")
# 双路 reviewer (L-dual): _a + _b 并发审查。旧单路 config 仍接受（向后兼容）。
REQUIRED_ROLES_DUAL = (
    "scaffold_orchestrator",
    "scaffold_reviewer_a", "scaffold_reviewer_b",
    "loop_orchestrator",
    "phase_planner",
    "phase_coder",
    "phase_reviewer_a", "phase_reviewer_b",
)
REQUIRED_ROLES_LEGACY = (
    "scaffold_orchestrator",
    "scaffold_reviewer",
    "loop_orchestrator",
    "phase_planner",
    "phase_coder",
    "phase_reviewer",
)
REVIEWER_SUFFIXES = ("_a", "_b")
READY_MARKERS = {
    "kilo": ("Ask anything", "? for shortcuts"),
    "claude_cli": ("bypass permissions", "? for shortcuts"),
}
ERROR_MARKERS = {
    "kilo": ("API error", "rate limit", "network error", "ECONNRESET", "request failed"),
    "claude_cli": ("API Error", "rate limit", "overloaded_error", "Connection error"),
    "droid": (),
    "codex": (),
}
CONFIRM_MARKERS = {
    "kilo": ("[y/N]", "(y/n)", "Do you want to proceed", "Approve", "1. Yes"),
    "claude_cli": ("Do you want to proceed", "❯ 1. Yes", "[y/n]"),
    "droid": (),
    "codex": (),
}
SAFE_LAUNCH_BOXES = [
    {"name": "omzsh_update", "all_of": ("Would you like to update", "[Y/n]"), "keys": ("n", "Enter")},
    {"name": "claude_trust", "any_of": ("trust this folder", "Is this a project"), "keys": ("Enter",)},
]
DISPATCH_TIMEOUT = 45
DISPATCH_BLOCKED_EXIT = 7
OBSERVE_FRAME_GAP = 1.0
DISPATCH_BLOCKED_MIN_AGE_S = 5.0
AWAIT_ALL_INTERVAL = 5
AWAIT_ALL_ATTENTION_EXIT = 10
AWAIT_ALL_ACTIONABLE_CLASSES = ("ready_idle", "errored", "awaiting_input", "dispatch_blocked", "blocked", "dead", "compact")
REMEDIABLE_CLASSES = ("ready_idle", "dispatch_blocked", "errored")
MAX_AUTO_REMEDIATE = 3
ERROR_RETRY_TRANSIENT = {
    "rate limit",
    "network error",
    "overloaded",
    "overloaded_error",
    "econnreset",
    "connection error",
    "timeout",
    "temporarily unavailable",
}
READY_IDLE_REMEDIATE_MIN_AGE_S = DISPATCH_BLOCKED_MIN_AGE_S
REMEDIATE_EXIT = 0
REMEDIATE_ESCALATE_EXIT = 11
STATUS_REPROMPT = "请把结论写进你启动时 [PHASE DIR] 给的目录下 <role>.status 首行(done / blocked <reason>)，不要写文件名或 =。"
ERROR_RETRY_PROMPT = "上一步瞬时报错(网络/限流)，请重试上一步骤。"


def aggregate_await_all(pane_states: list[dict]) -> dict:
    total = len(pane_states)
    done_count = sum(1 for state in pane_states if state.get("screen_class") == "done")
    triggering = [state.get("pane") for state in pane_states
                  if _pane_state_actionable(state)]
    triggering = [pane for pane in triggering if pane]
    if total > 0 and done_count == total:
        verdict = "all_done"
    elif triggering:
        verdict = "attention"
    else:
        verdict = "waiting"
    return {
        "verdict": verdict,
        "triggering": triggering,
        "done_count": done_count,
        "total": total,
    }


def _pane_state_actionable(state: dict) -> bool:
    screen_class = state.get("screen_class")
    if screen_class == "ready_idle":
        return float(state.get("age_s", 0) or 0) >= READY_IDLE_REMEDIATE_MIN_AGE_S
    return screen_class in AWAIT_ALL_ACTIONABLE_CLASSES


def agent_ready(screen: str, backend: str) -> bool:
    """Whether a launch screen shows the backend's prompt-ready marker.
    Unknown backends keep the historical best-effort behavior: treat as ready."""
    markers = READY_MARKERS.get(backend)
    if markers is None:
        return True
    return any(marker in screen for marker in markers)


def match_safe_launch_box(screen: str) -> tuple[str, tuple[str, ...]] | None:
    """Match launch-time prompts that are safe to answer automatically."""
    for box in SAFE_LAUNCH_BOXES:
        all_of = box.get("all_of")
        any_of = box.get("any_of")
        if all_of and not all(token in screen for token in all_of):
            continue
        if any_of and not any(token in screen for token in any_of):
            continue
        return str(box["name"]), tuple(box["keys"])
    return None


def classify_launch(screen: str, backend: str) -> str:
    if agent_ready(screen, backend):
        return "ready"
    match = match_safe_launch_box(screen)
    if match:
        return f"safe_box:{match[0]}"
    return "pending"


def screen_tail(screen: str, n: int = 15) -> str:
    return "\n".join(screen.splitlines()[-n:])


def screen_frozen(screen: str, prev_screen: str | None) -> bool:
    """两帧逐字相同才算冻结；首帧不轻易判成可行动静态状态。"""
    return prev_screen is not None and screen == prev_screen


FOOTER_CHROME_MARKERS = {
    "kilo": ("? for shortcuts",),
    "claude_cli": ("bypass permissions", "? for shortcuts"),
}


def strip_footer_chrome(screen: str, backend: str) -> str:
    """去掉 TUI 常驻页脚行，避免 footer ready/chrome 标记污染运行期分类。"""
    markers = FOOTER_CHROME_MARKERS.get(backend, ())
    lines = screen.splitlines()
    while lines and any(marker in lines[-1] for marker in markers):
        lines.pop()
    return "\n".join(lines)


def classify_prompt_shape(screen: str, backend: str) -> str:
    tail = screen_tail(screen)
    low = tail.lower()
    if "yes to all" in low:
        return "yes_to_all"
    if re.search(r"\[(?:y/n|y/N|Y/n|Y/N)\]|\([yY]/[nN]\)", tail):
        return "binary_yn"
    if re.search(r"(?m)^\s*1\.\s+\S+.*\n\s*2\.\s+\S+", tail):
        return "numbered"
    if _has_marker(tail, CONFIRM_MARKERS.get(backend, ())) and "yes" in low and "no" in low:
        return "binary_yn"
    if "❯" in tail:
        return "arrow_select"
    if re.search(r"(?m)(:\s*$|>\s*$)", tail):
        return "free_text"
    return "unknown"


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _has_confirm_marker(text: str, backend: str) -> bool:
    shape = classify_prompt_shape(text, backend)
    return _has_marker(text, CONFIRM_MARKERS.get(backend, ())) or shape in {
        "binary_yn", "numbered", "arrow_select", "yes_to_all"
    }


def classify_screen(screen: str, prev_screen: str | None, backend: str,
                    status_state: str | None, age_s: float) -> str:
    """运行期 pane 屏幕分类；done/blocked/compact 只信 status_state。"""
    if status_state in {"done", "blocked", "compact"}:
        return status_state
    if not screen_frozen(screen, prev_screen):
        return "working"
    if status_state is None and age_s >= DISPATCH_BLOCKED_MIN_AGE_S and match_safe_launch_box(screen):
        return "dispatch_blocked"

    tail = screen_tail(screen)
    has_confirm = _has_confirm_marker(tail, backend)
    if has_confirm and status_state != "done":
        return "awaiting_input"
    idle = pane_looks_idle(screen)

    backend_errors = ERROR_MARKERS.get(backend, ())
    if _has_marker(tail, backend_errors):
        return "errored"
    if idle:
        return "ready_idle"
    if _FAIL_LINE_RE.search(tail) and not has_confirm:
        return "errored"
    without_footer = strip_footer_chrome(screen, backend)
    if pane_looks_idle(without_footer) and not has_confirm:
        return "ready_idle"
    return "unknown"


def is_transient_error(screen: str, backend: str) -> bool:
    """报错屏是否含可重试瞬态标记；语义/断言/语法错误不自动重试。"""
    if not screen:
        return False
    low = screen.lower()
    semantic_errors = ("assertionerror", "syntaxerror")
    if any(marker in low for marker in semantic_errors):
        return False
    return any(marker in low for marker in ERROR_RETRY_TRANSIENT)


def plan_remediation(screen_class: str, screen: str, backend: str, retry_count: int, age_s: float = 0) -> dict:
    """纯函数：按 P4 type(a) 边界决定是否可幂等自动补救。"""
    if screen_class == "awaiting_input":
        return {"action": "escalate", "reason": "confirmation_needs_p5"}
    if retry_count >= MAX_AUTO_REMEDIATE:
        return {"action": "escalate", "reason": "intervention_loop"}
    if screen_class not in REMEDIABLE_CLASSES:
        return {"action": "escalate", "reason": "non_remediable_class"}
    if screen_class == "ready_idle":
        if age_s < READY_IDLE_REMEDIATE_MIN_AGE_S:
            return {"action": "escalate", "reason": "ready_idle_not_stale"}
        return {"action": "resend_status_prompt", "reason": "missing_status"}
    if screen_class == "dispatch_blocked":
        if match_safe_launch_box(screen):
            return {"action": "resolve_safe_box", "reason": "safe_launch_box"}
        return {"action": "escalate", "reason": "unsafe_dispatch_block"}
    if screen_class == "errored":
        if not is_transient_error(screen, backend):
            return {"action": "escalate", "reason": "non_transient_error"}
        if not pane_looks_idle(screen):
            return {"action": "escalate", "reason": "worker_not_idle"}
        return {"action": "retry_errored", "reason": "transient_error"}
    return {"action": "escalate", "reason": "non_remediable_class"}


def is_dual_review_config(roles: dict) -> bool:
    return "phase_reviewer_a" in roles


def validate_config(config: dict) -> dict:
    """校验已解析的 config.yaml(缺字段/错 enum/未知 backend 都拒)。返回原 config。
    向后兼容：接受旧单路 role 名（phase_reviewer / scaffold_reviewer）。"""
    if config.get("version") != 2:
        raise ValueError(f"config version must be 2, got {config.get('version')!r}")
    roles = config.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("config.roles must be a mapping")
    required = REQUIRED_ROLES_DUAL if is_dual_review_config(roles) else REQUIRED_ROLES_LEGACY
    missing = [r for r in required if r not in roles]
    if missing:
        raise ValueError(f"config.roles missing: {', '.join(missing)}")
    for name, role in roles.items():
        if role.get("backend") not in BACKENDS:
            raise ValueError(f"role {name}: unknown backend {role.get('backend')!r}")
        if role.get("autonomy") not in AUTONOMY:
            raise ValueError(f"role {name}: bad autonomy {role.get('autonomy')!r}")
        if role["backend"] == "claude_cli" and not role.get("cmd"):
            raise ValueError(f"role {name}: claude_cli backend requires 'cmd'")
    return config


def branch_name(slug: str) -> str:
    """L16: 专用开发分支名。"""
    return f"lr/{slug}"


def worktree_path(repo_root: Path, slug: str) -> Path:
    """L16: worktree 放 repo 同级目录 <repo>-lr-<slug>。"""
    repo_root = Path(repo_root)
    return repo_root.parent / f"{repo_root.name}-lr-{slug}"


def plan_worktree(repo_root: Path, slug: str, in_place: bool, current_branch: str) -> dict:
    """决定用新 worktree+分支(隔离)还是当前 worktree+分支(接着做)。
    in_place 时 L16 守卫: 拒绝在 main/master/detached 上开发。"""
    if in_place:
        if current_branch in ("main", "master", ""):
            raise ValueError(
                f"--in-place 拒绝在 {current_branch or 'detached HEAD'!r} 上开发(L16)；"
                f"先切到 feature 分支，或去掉 --in-place 新建 worktree"
            )
        return {"worktree_path": str(Path(repo_root)), "branch": current_branch, "create": False}
    return {"worktree_path": str(worktree_path(repo_root, slug)), "branch": branch_name(slug), "create": True}


SESSION_COLUMNS = ("role", "phase", "pane_id", "started_at", "last_seen", "status")


def parse_sessions(text: str) -> list[dict[str, str]]:
    """解析 SESSIONS.md 的 markdown 表为 row dict 列表(忽略标题/分隔行)。"""
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells == list(SESSION_COLUMNS):  # header
            continue
        if all(set(c) <= {"-", ":"} and c for c in cells):  # separator row
            continue
        if len(cells) != len(SESSION_COLUMNS):
            # 故障导向安全: 不静默丢像数据行但列数不符的行(可能是 SSOT 损坏)
            raise ValueError(f"malformed SESSIONS row, expected {len(SESSION_COLUMNS)} cols: {stripped!r}")
        rows.append(dict(zip(SESSION_COLUMNS, cells)))
    return rows


def render_sessions(rows: list[dict[str, str]]) -> str:
    """渲染 SESSIONS.md(机器+人都可读, 与 parse_sessions round-trip)。"""
    header = "| " + " | ".join(SESSION_COLUMNS) + " |"
    sep = "|" + "|".join(["---"] * len(SESSION_COLUMNS)) + "|"
    lines = ["# Sessions", "", header, sep]
    for row in rows:
        lines.append("| " + " | ".join(row[col] for col in SESSION_COLUMNS) + " |")
    return "\n".join(lines) + "\n"


def upsert_session(rows: list[dict[str, str]], session: dict[str, str]) -> list[dict[str, str]]:
    """按 pane_id 落盘一个 session：已存在则整行替换(更新 phase/last_seen/status)，否则追加。"""
    missing = [col for col in SESSION_COLUMNS if col not in session]
    if missing:
        raise ValueError(f"session missing columns: {', '.join(missing)}")
    entry = {col: session[col] for col in SESSION_COLUMNS}
    updated = [dict(r) for r in rows]
    for index, row in enumerate(updated):
        if row["pane_id"] == entry["pane_id"]:
            updated[index] = entry
            return updated
    updated.append(entry)
    return updated


# ---------------------------------------------------------------------------
# YAML 严格子集 loader(stdlib-only, 只认 config.yaml 的 schema 形状: 2-space 缩进、
# `key:` 开 map、`key: scalar`、# 注释、单/双引号标量; 不支持 list/多行)。跑偏即 fail-fast。
# ---------------------------------------------------------------------------
def _yaml_scalar(val: str):
    if val[:1] in ("'", '"'):
        quote = val[0]
        end = val.rfind(quote)
        if end <= 0:
            raise ValueError(f"unterminated quoted scalar: {val!r}")
        return val[1:end]
    val = val.split("#", 1)[0].strip()
    if val.isdigit():
        return int(val)
    if val in ("true", "false"):
        return val == "true"
    return val


def load_yaml(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, sep, val = raw.strip().partition(":")
        if not sep:
            raise ValueError(f"bad yaml line (no ':'): {raw!r}")
        key = key.strip()
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if val.strip() == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _yaml_scalar(val.strip())
    return root


# ---------------------------------------------------------------------------
# tmux / pane 命令构造(纯函数, 与执行分离, 可单测)
# ---------------------------------------------------------------------------
SPLIT_FLAG = {"split-right": "-h", "split-down": "-v"}


def split_window_args(cwd: str, mode: str, command: str | None, target: str | None = None) -> list[str]:
    """构造 tmux split-window(在当前 window split 当前 pane), 捕获新 pane_id。
    target=当前 $TMUX_PANE → 确保 pane 出现在用户当前 tab,不进别的 session/tab。
    command=None → 默认交互 shell(claude 路径用)。"""
    if mode not in SPLIT_FLAG:
        raise ValueError(f"bad split mode {mode!r}; valid: {', '.join(SPLIT_FLAG)}")
    args = ["split-window"]
    if target:
        args += ["-t", target]
    args += [SPLIT_FLAG[mode], "-P", "-F", "#{pane_id}", "-c", cwd]
    if command:
        args.append(command)
    return args


def paste_buffer_args(pane: str, buf: str) -> list[str]:
    """构造 tmux bracketed paste(`-p`)命令: 把 buffer 多行内容贴进 pane 输入框且不提前提交。
    实测(spike): kilo/claude TUI 收多行不 submit, 之后单次 Enter 提交为一条消息。"""
    return ["paste-buffer", "-p", "-b", buf, "-t", pane]


def pane_is_alive(list_panes_output: str, pane_id: str) -> bool:
    """从 `tmux list-panes -aF '#{pane_id}'` 输出判断某 pane 是否还在。"""
    return pane_id in list_panes_output.split()


WORKER_STATES = ("coding", "done", "blocked", "compact")


def parse_worker_status(text: str) -> tuple[str, str]:
    """解析 worker 写的 status 文件首行 → (state, detail)。
    机器可读的完成信号, 取代"grep prose 字符串"那种脆弱轮询。未知 state 一律 unknown。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ("unknown", "")
    first = lines[0]
    # 容错: worker 常把 prompt 里的 `phase_coder.status = done ...`(或 `status: done`)整行
    # 写进文件 → 剥掉 `<…status> = / :` 赋值左边, 用右边判 state(右边非法仍回落 unknown)。
    assign = re.match(r"(?i)^[\w./-]*status\s*[:=]\s*(\S.*)$", first)
    if assign:
        first = assign.group(1).strip()
    parts = first.split(None, 1)
    state = parts[0].lower()
    detail = parts[1].strip() if len(parts) > 1 else ""
    if state not in WORKER_STATES:
        return ("unknown", lines[0])
    return (state, detail)


# TUI worker"完成"=回到就绪输入框(pane 不死)。这些标识表示 pane 在等输入而非在干活。
IDLE_READY_MARKERS = ("? for shortcuts", "Ask anything", "bypass permissions")


def pane_looks_idle(screen: str) -> bool:
    """pane 当前是否停在就绪输入框(等输入, 不在生成)。"""
    return any(marker in screen for marker in IDLE_READY_MARKERS)


def update_idle(prev_screen: str, screen: str, strikes: int) -> int:
    """idle 兜底计数(纯逻辑): pane 停在就绪框且画面与上一轮完全相同 → strike+1, 否则清零。
    画面还在变(spinner/出 token)说明在干活, 不算 idle —— 杜绝把'在思考'误判成'卡住'。"""
    if pane_looks_idle(screen) and screen == prev_screen:
        return strikes + 1
    return 0


# ---------------------------------------------------------------------------
# 完成闸门(gate): 把"phase 完成 / run completed"从 prose 声明变成机器可检查的状态转换。
# 背景: 首次实战(00167-00173)中 phase 标 [x] 完成时验证从没真跑、reviewer blocker 被
# 静默放行、acceptance verifier 仅写在文档里没执行 → 半成品被当成完成品交付。
# ---------------------------------------------------------------------------
def verify_summary(exit_code: int, output: str) -> dict:
    """把一次 verify.sh / acceptance.sh 执行归一成机器可读结果。
    ok 完全由 exit code 决定(故障导向: 非 0 即未过), output_tail 留作证据(截尾防爆)。"""
    tail = "\n".join(output.splitlines()[-100:])
    return {"ok": exit_code == 0, "exit": exit_code, "output_tail": tail}


_BLOCKER_TAG = re.compile(r"\[blocker(?:\s+([A-Za-z][A-Za-z0-9_-]*))?\]", re.IGNORECASE)


def parse_review_blockers(review_text: str) -> list[tuple[str | None, str]]:
    """抽出 review.md 里 `[blocker <ID>]` / `[blocker]` 条目 → (id, 描述) 列表。
    reviewer 契约要求顺序编号 `[blocker B1]`(见 phase_reviewer.md): 带 ID 时门禁按 ID
    对账——同一 ID 重复提及不重复计数、ack 缺哪条报哪条、多写 [fixed] 行凑数也对不上;
    无 ID(历史 review)回落计数对账。`[should]`/`[nit]` 不算 blocker。"""
    out: list[tuple[str | None, str]] = []
    for raw in review_text.splitlines():
        desc = raw.strip().lstrip("#").strip()
        match = _BLOCKER_TAG.search(desc)
        if match:
            out.append((match.group(1), desc[match.end():].strip()))
    return out


def parse_ack_resolutions(ack_text: str) -> dict:
    """统计 ack.md 里 `## Blocker Resolutions` 段内的 `[fixed]` / `[rejected]` / `[deferred]` 数量,
    并保留 fixed_lines 和 rejected_lines 原文(供按 blocker ID 对账)。
    只认这一段, 防止 Findings 段里的 `[agree] [blocker]` 叙述被误计。
    双路 reviewer 下 coder 用 `[rejected] A:B2 理由` 表示不认同,门禁视为已裁决(不阻塞)。"""
    counts: dict = {"fixed": 0, "rejected": 0, "deferred": 0, "fixed_lines": [], "rejected_lines": []}
    in_section = False
    for raw in ack_text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_section = "blocker resolutions" in line.lower()
            continue
        if not in_section:
            continue
        low = line.lower()
        if "[fixed]" in low:
            counts["fixed"] += 1
            counts["fixed_lines"].append(line)
        elif "[rejected]" in low:
            counts["rejected"] += 1
            counts["rejected_lines"].append(line)
        elif "[deferred]" in low:
            counts["deferred"] += 1
    return counts


def phase_gate(verify: dict | None, review_text, ack_text: str) -> dict:
    """phase 完成的硬门(纯谓词)。

    review_text: str (单路旧格式) 或 dict[str, str] (双路, {"a": "...", "b": "..."})。
    双路时每份 review 的 blocker 加来源前缀 (A:B1, B:B2)，coder ack 按前缀对账。
    一路为空(降级) = 跳过该路, 但至少一路要有产出。
    [rejected] 视为已裁决(不阻塞), [deferred] 仍禁止。

    三条:
    (a) verify 必须真跑且过(verify 为 None/未 ok → 阻塞)。
    (b) review 必须产出(全空 → 阻塞)。
    (c) review 的每个 [blocker] 必须在 ack 标 [fixed] 或 [rejected](缺裁决 → 阻塞)。"""
    reasons: list[str] = []
    if not verify or not verify.get("ok"):
        reasons.append("验证未跑或失败：先 `lr.py verify --phase <id>`，verify.json.ok 必须为真")

    # 归一化 review_text 为 dict
    if isinstance(review_text, str):
        review_texts: dict[str, str] = {"": review_text}
    else:
        review_texts = review_text

    has_any_review = any(t.strip() for t in review_texts.values())
    if not has_any_review:
        reasons.append("review 未产出：review 文件缺失或为空 —— reviewer 环节不可跳过")

    # 从所有 review 中收集 blocker，双路时加来源前缀
    all_blockers: list[tuple[str | None, str]] = []
    for source, text in review_texts.items():
        if not text.strip():
            continue
        for bid, desc in parse_review_blockers(text):
            if source and bid:
                prefixed_id = f"{source.upper()}:{bid}"
            elif source and not bid:
                prefixed_id = None
            else:
                prefixed_id = bid
            all_blockers.append((prefixed_id, desc))

    res = parse_ack_resolutions(ack_text)
    # [rejected] 必须有理由（ID 后至少有非空文本），空理由 = 静默丢弃 blocker
    _rejected_no_reason = re.compile(r"^\s*-\s*\[rejected\]\s*[A-Za-z0-9:_-]*\s*$", re.IGNORECASE)
    bad_rejects = [ln for ln in res.get("rejected_lines", []) if _rejected_no_reason.match(ln)]
    if bad_rejects:
        reasons.append(f"[rejected] 缺理由（必须写明不认同原因）：{bad_rejects[0]!r}")
    resolved_lines = res["fixed_lines"] + res.get("rejected_lines", [])
    if all_blockers:
        ids = [bid for bid, _ in all_blockers]
        if all(ids):
            unique = list(dict.fromkeys(ids))
            missing = [bid for bid in unique
                       if not any(re.search(rf"\b{re.escape(bid)}\b", ln) for ln in resolved_lines)]
            problems = []
            if missing:
                problems.append(f"{', '.join(missing)} 未在 ack `## Blocker Resolutions` 标 [fixed] 或 [rejected]")
            if res["deferred"] > 0:
                problems.append(f"出现 {res['deferred']} 个 [deferred]（blocker 不允许 deferred）")
            if problems:
                reasons.append("blocker 未裁决：" + "；".join(problems))
        elif (res["fixed"] + res["rejected"]) < len(all_blockers) or res["deferred"] > 0:
            reasons.append(
                f"blocker 未裁决：review 有 {len(all_blockers)} 个 [blocker]，"
                f"ack 仅 fixed={res['fixed']} rejected={res['rejected']} deferred={res['deferred']}"
                f"（blocker 不允许 deferred）"
            )
    return {"ok": not reasons, "reasons": reasons}


def parse_status_commit(status_text: str) -> str | None:
    """从 worker status 文件取收口 commit hash(`done commit=<hash>`)。
    非 done / `done impl`(两段式的中间态) / 无合法 hash → None。
    L14 机器证据: complete-phase 据此要求 coder 声明的 commit 真实存在, 不收口头声明。"""
    state, detail = parse_worker_status(status_text)
    if state != "done":
        return None
    match = re.search(r"commit=([0-9a-fA-F]{6,40})\b", detail)
    return match.group(1) if match else None


def unchecked_phases(fix_plan_text: str) -> list[str]:
    """fix_plan.md 里仍未勾选的 phase id(`- [ ] <id> ...` 的首 token)。
    complete-run 用它拦"还有 phase 没过门禁就收尾"。"""
    out: list[str] = []
    for line in fix_plan_text.splitlines():
        match = re.match(r"^\s*-\s*\[ \]\s+(\S+)", line)
        if match:
            out.append(match.group(1))
    return out


def mark_phase_done(fix_plan_text: str, phase_id: str) -> str:
    """把 fix_plan.md 里 `- [ ] <phase_id> ...` 行翻成 `- [x] ...`,其它行原样。
    phase_id 必须是 checkbox 后第一个 token(`01` 不误匹配 `012`)。找不到则原样返回
    (调用方负责报"未知 phase"错误)。仅此一处可改完成态, 不许 orchestrator 手翻。"""
    pat = re.compile(r"^(\s*-\s*\[) \](\s+" + re.escape(phase_id) + r"\b)")
    out = [pat.sub(r"\1x]\2", line) for line in fix_plan_text.splitlines(keepends=True)]
    return "".join(out)


def acceptance_gate(acceptance: dict | None) -> dict:
    """run 收尾(state=completed)的硬门:必须真跑过 acceptance.sh 且过。
    acceptance 为 None(没跑)/未 ok → 阻塞。杜绝"acceptance verifier 只写在文档没执行"。"""
    if not acceptance or not acceptance.get("ok"):
        return {"ok": False, "reasons": [
            "acceptance 未跑或失败：完成前必须 `lr.py verify --acceptance` 跑通端到端验收，"
            "acceptance.json.ok 必须为真"
        ]}
    return {"ok": True, "reasons": []}


# ---------------------------------------------------------------------------
# 卡死检测(L26): 把"连续 N 次验证失败"从 orchestrator 记忆里的计数变成磁盘可计算信号。
# 背景: SKILL 停止条件写了"连续 2 次验证失败"但谁来数? 是对话 agent 凭记忆数——跨 compact /
# resume 必丢(全局红线"记忆不可信")。借 Ralph circuit_breaker 思路: 跨轮持久化失败计数 + 错误
# 指纹比对, 同一指纹反复出现才累加, 指纹变了说明错误在演化(还在推进)→ 重置, 不误判卡死。
# ---------------------------------------------------------------------------
STUCK_THRESHOLD = 2  # 连续同指纹失败达此数即判 stuck(对齐 SKILL "连续 2 次验证失败")

_FAIL_LINE_RE = re.compile(
    r"(FAIL|FAILED|Error|error:|Traceback|assert|Exception|panic|\bnot ok\b|✗|✕)", re.IGNORECASE
)


def _normalize_noise(text: str) -> str:
    """把易变噪声(行号/耗时/计数/temp 路径/内存地址)归一, 让"同一个失败"在多次跑之间指纹稳定。
    注: 数字全折成 N 是刻意激进——若两次失败只差一个数字(行号/计数), 大概率仍是同一个卡点。"""
    text = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", text)
    text = re.sub(r"/tmp/[^\s:]+", "/tmp/PATH", text)
    text = re.sub(r"\d+", "N", text)
    return text


def verify_fingerprint(verify: dict | None) -> str | None:
    """从一次 verify 执行结果取"失败指纹"。verify 通过(或缺失)→ None(无失败可指纹)。
    取 output_tail 里命中失败模式的行(没有则回落末 20 行) + exit code, 归一噪声后 sha1 截断。
    纯函数: 同样的失败输出 → 同样的指纹, 供 update_stuck 跨轮比对。"""
    if not verify or verify.get("ok"):
        return None
    tail = str(verify.get("output_tail", ""))
    lines = [ln.strip() for ln in tail.splitlines() if ln.strip()]
    salient = [ln for ln in lines if _FAIL_LINE_RE.search(ln)]
    basis = [f"exit={verify.get('exit')}"] + (salient or lines[-20:])
    norm = _normalize_noise("\n".join(basis))
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def update_stuck(prev: dict | None, fingerprint: str | None) -> dict:
    """纯转换: 据本轮 verify 指纹更新失败计数器。
    - 通过(fingerprint None) → 清零。
    - 同上轮指纹 → consecutive_fail+1(原地打转)。
    - 换了指纹 → 重置为 1(错误在演化=还在推进, 不算卡死; 直接抄 Ralph)。"""
    prev = prev or {}
    prev_fp = prev.get("fingerprint")
    prev_n = int(prev.get("consecutive_fail", 0) or 0)
    if fingerprint is None:
        return {"consecutive_fail": 0, "fingerprint": None}
    if fingerprint == prev_fp:
        return {"consecutive_fail": prev_n + 1, "fingerprint": fingerprint}
    return {"consecutive_fail": 1, "fingerprint": fingerprint}


def summarize_metrics(records: list[dict]) -> dict:
    """纯聚合 metrics.jsonl 的事件流 → run 级 + per-phase 汇总。stats 命令用它出人话报告。"""
    summary: dict = {
        "verify_attempts": 0, "verify_passes": 0, "verify_fails": 0,
        "phases_completed": 0, "run_completed": False, "per_phase": {},
    }
    for rec in records:
        event = rec.get("event")
        phase = str(rec.get("phase", "")) if rec.get("phase") is not None else ""
        if event == "verify":
            summary["verify_attempts"] += 1
            ph = summary["per_phase"].setdefault(phase, {"verify_attempts": 0, "passes": 0, "fails": 0,
                                                         "fail_streak": 0, "completed": False})
            ph["verify_attempts"] += 1
            if rec.get("ok"):
                summary["verify_passes"] += 1
                ph["passes"] += 1
            else:
                summary["verify_fails"] += 1
                ph["fails"] += 1
            ph["fail_streak"] = int(rec.get("fail_streak", ph["fail_streak"]) or 0)
        elif event == "complete_phase":
            summary["phases_completed"] += 1
            ph = summary["per_phase"].setdefault(phase, {"verify_attempts": 0, "passes": 0, "fails": 0,
                                                         "fail_streak": 0, "completed": False})
            ph["completed"] = True
        elif event == "complete_run":
            summary["run_completed"] = True
    return summary


def pane_registered(rows: list[dict[str, str]], pane_id: str) -> bool:
    """pane 是否出现在 SESSIONS.md 注册表(任意状态行)。send 的护栏:
    orchestrator 只该给 lr 自己 launch 的 worker pane 发消息, 防止编错 pane id
    把 prompt 灌进用户正在用的 pane(alive 检查挡不住这种——用户 pane 也是活的)。"""
    return any(r["pane_id"] == pane_id for r in rows)


def find_live_role_pane(rows: list[dict[str, str]], role: str, list_panes_output: str) -> str | None:
    """找某 role 仍存活的 running pane(L6 改:每 phase 开始时据此关掉上一个 coder)。"""
    for row in rows:
        if row["role"] == role and row["status"] == "running" and pane_is_alive(list_panes_output, row["pane_id"]):
            return row["pane_id"]
    return None


def panes_to_close(rows: list[dict[str, str]], roles, list_panes_output: str) -> list[str]:
    """该关哪些 pane(纯逻辑): SESSIONS 里 status==running 且 pane 仍 alive 且 role∈roles 的 pane_id。
    teardown 据此决定关谁 — phase 收口传 PHASE_TRANSIENT_ROLES(不含 coder), run 收尾传 WORKER_ROLES。"""
    roleset = set(roles)
    return [r["pane_id"] for r in rows
            if r["role"] in roleset and r["status"] == "running"
            and pane_is_alive(list_panes_output, r["pane_id"])]


def reconcile_dead_sessions(rows: list[dict[str, str]], list_panes_output: str, now: str) -> tuple[list[dict[str, str]], list[str]]:
    """SSOT 自愈(纯逻辑): SESSIONS 里 status==running 但 pane 已不在 tmux 的行 → 标 closed。
    这类行来自非 lr 路径的关闭(worker 进程自退 / 用户手关 pane) —— teardown 的 _close_roles
    只更新它亲手 kill 的行, 不会碰这些, 否则它们永远 stale 在 running, 误导任何信 status 的消费方。
    now 由调用方传(不在纯函数里取时间, 便于测试)。返回 (新 rows, 被 reconcile 的 pane_id 列表)。"""
    reconciled: list[str] = []
    new_rows: list[dict[str, str]] = []
    for r in rows:
        if r["status"] == "running" and not pane_is_alive(list_panes_output, r["pane_id"]):
            reconciled.append(r["pane_id"])
            new_rows.append(dict(r, status="closed", last_seen=now))
        else:
            new_rows.append(r)
    return new_rows, reconciled


def launch_command(role_cfg: dict) -> str | None:
    """role 的 pane 启动命令。kilo → `kilo -m <model>`(TUI 直接 exec, L19 用默认 effort);
    claude_cli → None(走默认交互 zsh, 再 send-keys cfg['cmd'], 以拿 .zshrc 的 token)。"""
    backend = role_cfg["backend"]
    if backend == "kilo":
        return f"kilo -m {shlex.quote(role_cfg['model'])}"
    if backend == "claude_cli":
        return None  # 交互 zsh pane, cmd 通过 send-keys 注入(见 launch_role)
    if backend == "custom":
        return role_cfg.get("cmd")
    raise ValueError(f"launch undefined for backend {role_cfg['backend']!r}")


def launch_resend_after_box(role_cfg: dict, command: str | None) -> dict[str, str] | None:
    resend_cmd = role_cfg.get("cmd") if role_cfg["backend"] == "claude_cli" else command
    return {"omzsh_update": resend_cmd} if resend_cmd else None


# ---------------------------------------------------------------------------
# state.json
# ---------------------------------------------------------------------------
def load_state(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_state(path: Path, state: dict) -> None:
    Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 执行层(side effects): tmux / git。CLI 入口下使用。
# ---------------------------------------------------------------------------
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tmux(args: list[str], capture: bool = False) -> str:
    result = subprocess.run(["tmux", *args], text=True, capture_output=True)
    if result.returncode != 0 and not capture:
        raise RuntimeError(f"tmux {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", "-C", str(repo_root), *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def pane_title(role: str, phase: str) -> str:
    # `phase {n} {身份}`(用户决策 2026-06-06): 比 lr:slug:role:phase 更易调试; 不含任务名(太长)。
    # 身份去掉 phase_ 前缀 → planner/coder/reviewer；双路 reviewer 保留后缀 → reviewer_a/reviewer_b。
    identity = role[len("phase_"):] if role.startswith("phase_") else role
    return f"phase {phase} {identity}"


def capture_pane(pane: str) -> str:
    return _tmux(["capture-pane", "-t", pane, "-p"], capture=True)


def send_to_pane(pane: str, text: str, enter: bool = True) -> None:
    """把(可多行)文本 bracketed-paste 进 pane 输入框, 再单次 Enter 提交为一条消息。
    多行 prompt 在窗口里按原排版可读(不再是 send-keys 单行一坨)。"""
    buf = "lrdispatch"
    subprocess.run(["tmux", "load-buffer", "-b", buf, "-"], input=text, text=True, capture_output=True)
    _tmux(paste_buffer_args(pane, buf))
    time.sleep(0.5)
    if enter:
        _tmux(["send-keys", "-t", pane, "Enter"])
        time.sleep(0.4)
    subprocess.run(["tmux", "delete-buffer", "-b", buf], capture_output=True)


def send_keys_to_pane(pane: str, keys: tuple[str, ...]) -> None:
    for key in keys:
        _tmux(["send-keys", "-t", pane, key])
        time.sleep(0.4)


def verify_dispatch(
    pane: str,
    backend: str,
    timeout_s: int = DISPATCH_TIMEOUT,
    recover_budget: int = 2,
    interval_s: float = 1,
    resend_after_box: dict[str, str] | None = None,
) -> tuple[str, str | None]:
    """Wait until the launched agent is ready, or return blocked with pane tail."""
    deadline = time.monotonic() + timeout_s
    last_screen = ""
    while time.monotonic() < deadline:
        last_screen = capture_pane(pane)
        state = classify_launch(last_screen, backend)
        if state == "ready":
            return "ready", None
        if state.startswith("safe_box:"):
            if recover_budget <= 0:
                return "blocked", screen_tail(last_screen)
            match = match_safe_launch_box(last_screen)
            if match is None:
                return "blocked", screen_tail(last_screen)
            _box_name, keys = match
            send_keys_to_pane(pane, keys)
            if resend_after_box and _box_name in resend_after_box:
                time.sleep(1)
                send_to_pane(pane, resend_after_box[_box_name])
            recover_budget -= 1
            continue
        time.sleep(interval_s)
    return "blocked", screen_tail(last_screen or capture_pane(pane))


# 薄 wrapper: launch_role 已改用 verify_dispatch(P1), 但 dev-complete 的 dc.py 仍直接
# 调 lr.consume_claude_trust / lr.wait_kilo_ready(独立 cmd_launch)。spec L57 允许保留为
# thin wrapper 以保现调用不破; 委托 P1 的 match_safe_launch_box/agent_ready 不重复逻辑。
def consume_claude_trust(pane: str, timeout_s: int = 20) -> bool:
    """claude 首次进目录的 trust 对话框: 检测到则发 Enter 接受, 否则就绪即返回。"""
    for _ in range(timeout_s):
        time.sleep(1)
        screen = capture_pane(pane)
        match = match_safe_launch_box(screen)
        if match and match[0] == "claude_trust":
            send_keys_to_pane(pane, match[1])
            time.sleep(1)
            return True
        if agent_ready(screen, "claude_cli"):
            return False
    return False


def wait_kilo_ready(pane: str, timeout_s: int = 30) -> bool:
    """轮询 kilo TUI 直到就绪, 防止 prompt 在加载完前抢跑丢失。"""
    for _ in range(timeout_s):
        time.sleep(1)
        screen = capture_pane(pane)
        if agent_ready(screen, "kilo"):
            return True
    sys.stderr.write(f"WARN: kilo pane {pane} 未在 {timeout_s}s 内就绪,仍尝试发送\n")
    return False


FRESH_PER_PHASE_ROLES = ("phase_coder",)  # L6(改): 每 phase 关掉上一个、开 fresh 的角色
# L24(pane 生命周期收尾): phase 收口该清的临时角色。coder 不在内 — 不是复用(L6 已反转为
# fresh-per-phase), 而是它由下一 phase 的 fresh launch 负责关; run 收尾清全部 worker。
# 双路 reviewer: _a/_b + 旧单路都列出，close/teardown 按 role 名匹配。
PHASE_TRANSIENT_ROLES = ("phase_planner", "phase_reviewer", "phase_reviewer_a", "phase_reviewer_b")
WORKER_ROLES = ("phase_planner", "phase_coder", "phase_reviewer", "phase_reviewer_a", "phase_reviewer_b")


def _close_roles(workspace: Path, roles) -> list[str]:
    """关掉这些 role 所有 running+alive pane, 在 SESSIONS.md 标 closed, 写回。返回被关的 pane_id 列表。
    teardown 兜底: 无 tmux / 无 SESSIONS / 没有可关的 → 静默返回 [](best-effort, 不阻断门禁)。"""
    if not os.environ.get("TMUX"):
        return []
    sessions_path = workspace / "SESSIONS.md"
    if not sessions_path.exists():
        return []
    rows = parse_sessions(sessions_path.read_text(encoding="utf-8"))
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    # SSOT 自愈: 先把"已死但仍记 running"的行标 closed —— 它们不进 panes_to_close(alive 检查为假),
    # 不在这里收口就永远 stale。reconcile 后再算该 kill 哪些活 pane。
    rows, reconciled = reconcile_dead_sessions(rows, live, _now())
    pids = panes_to_close(rows, roles, live)
    for pid in pids:
        _tmux(["kill-pane", "-t", pid], capture=True)
    closed = set(pids)
    rows = [dict(r, status="closed", last_seen=_now()) if r["pane_id"] in closed else r for r in rows]
    if pids or reconciled:
        sessions_path.write_text(render_sessions(rows), encoding="utf-8")
    return pids


def _close_role_pane(workspace: Path, role: str) -> str | None:
    """关掉某 role 上一个仍存活的 pane 并在 SESSIONS.md 标 closed。返回被关的 pane_id。"""
    pids = _close_roles(workspace, (role,))
    return pids[0] if pids else None


def resolve_phase_dir(workspace: Path, phase: str) -> Path:
    """把 phase id 解析到真实目录, 桥接 SSOT 不一致(命令里用数字 `03`, scaffold 建的是全名
    `03_<slug>`)。优先级:
    - `phases/<phase>` 精确存在 → 用它(显式传全名 slug, 或历史数字目录)
    - 否则唯一 `phases/<phase>_*`(scaffold 的 `<NN>_<slug>`) → 用它
    - 多个匹配 → 报歧义, 不静默猜(L: 边界决策不自决)
    - 都没有 → 回落 `phases/<phase>`, 让调用方按原路径暴露 not found(不掩盖缺失)"""
    phases = workspace / "phases"
    exact = phases / phase
    if exact.is_dir():
        return exact
    matches = sorted(d for d in phases.glob(f"{phase}_*") if d.is_dir()) if phases.is_dir() else []
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"phase {phase!r} 匹配到多个目录 {[m.name for m in matches]} —— id 有歧义, 请用更具体的 id")
    return exact


def _reviewer_suffix(role: str) -> str | None:
    """双路 reviewer 的后缀(_a/_b)。非 reviewer 或旧单路返回 None。"""
    for sfx in REVIEWER_SUFFIXES:
        if role.endswith(sfx):
            return sfx
    return None


def _prompt_file_for(role: str) -> Path:
    """role → prompt 文件。双路 reviewer (_a/_b) 共享去掉后缀的 prompt。"""
    sfx = _reviewer_suffix(role)
    base = role[:-len(sfx)] if sfx else role
    return PROMPTS_DIR / f"{base}.md"


def _reviewer_output_files(role: str, phase: str, workspace: Path) -> tuple[str, str] | None:
    """双路 reviewer 的 (review_file, status_file) 绝对路径。非双路返回 None。
    pane cwd 是 worktree（不是 workspace），所以必须返回绝对路径。"""
    sfx = _reviewer_suffix(role)
    if not sfx:
        return None
    label = sfx.lstrip("_")  # "a" or "b"
    if role.startswith("scaffold_reviewer"):
        return (str(workspace / f"SCAFFOLD_REVIEW_{label.upper()}.md"),
                str(workspace / f"scaffold_reviewer_{label}.status"))
    if role.startswith("phase_reviewer"):
        pdir = resolve_phase_dir(workspace, phase)
        return (str(pdir / f"review_{label}.md"), str(pdir / f"phase_reviewer_{label}.status"))
    return None


def _role_intro(role: str, phase: str, workspace: Path, brief: str | None) -> str:
    """worker pane 的初始 prompt(多行结构化, 经 bracketed paste 注入, 窗口可读)。
    phase 角色才注入 [PHASE DIR]; scaffold_reviewer 等非 phase 角色(phase=0)不注入 —
    否则会把不存在的 phases/0 当成产出目录, 与其角色契约(写工作区根)冲突。
    双路 reviewer: 共享 prompt 文件，但注入不同的 OUTPUT FILE 和 STATUS FILE。"""
    prompt_file = _prompt_file_for(role)
    is_phase_role = role in WORKER_ROLES and phase != "0"
    header = (f"You are the {role} for phase {phase}." if is_phase_role else f"You are the {role}.")
    parts = [
        header + " Do your role's job, then STOP when your output files are written.",
        f"[ROLE CONTRACT] {prompt_file}",
        f"[TASK BRIEF] {brief}" if brief else "",
        f"[MUST READ — workspace SSOT] {workspace}/REQUIREMENT.md ; {workspace}/SPEC_OVERVIEW.md ; {workspace}/fix_plan.md",
        (f"[PHASE DIR — this exact directory holds your spec; read it here and write ALL your phase outputs "
         f"(status/verify.sh/qa/ack/...) here, do not invent phases/{phase}] {resolve_phase_dir(workspace, phase)}")
        if is_phase_role else "",
    ]
    # 双路 reviewer: 注入具体产出文件名(覆盖 prompt 里的默认名)
    rv_files = _reviewer_output_files(role, phase, workspace)
    if rv_files:
        review_file, status_file = rv_files
        parts.append(f"[OUTPUT FILE — write your review here, NOT the default name] {review_file}")
        parts.append(f"[STATUS FILE — write 'done' here when finished] {status_file}")
    parts.extend([
        "[EVALUATE] whether /think-map or /think-research helps (per your role contract; evaluate, not forced).",
        "[RULES] Workspace files are the SSOT, your memory is not. Stay within your role's allowed outputs; do not touch files outside them.",
    ])
    return "\n".join(p for p in parts if p)


def launch_role(workspace: Path, role: str, role_cfg: dict, phase: str, mode: str, brief: str | None = None) -> tuple[str, str, str | None]:
    """在用户当前 tmux window split 出一个 role pane(就在当前 tab,不新建 session/tab),
    确认 agent 就绪后注入初始 prompt, 注册 SESSIONS.md。返回 (pane_id, status, tail)。
    phase_coder 走 fresh-per-phase(L6 反转): 先关上一个 coder pane 再开新的。"""
    if not os.environ.get("TMUX"):
        raise RuntimeError("不在 tmux 里 — worker pane 必须在用户当前 tmux window 内 split;请先在 tmux 中运行")
    worktree = Path(load_state(workspace / "state.json").get("worktree_path", workspace))
    intro = _role_intro(role, phase, workspace, brief)

    # L6(改, 用户决策 2026-05-29): 每 phase 开始先关掉上一个 coder, 再开 fresh(不复用),
    # 续接靠 coder 读 HANDOFF.md, 不靠长驻 context。
    if role in FRESH_PER_PHASE_ROLES:
        _close_role_pane(workspace, role)

    command = launch_command(role_cfg)
    # 关键: target = 当前 $TMUX_PANE → split 用户正在的 pane, pane 出现在当前 tab(不进别的 session/tab)
    current_pane = os.environ.get("TMUX_PANE")
    pane = _tmux(split_window_args(str(worktree), mode, command, target=current_pane), capture=True)
    if not pane:
        raise RuntimeError(f"failed to obtain pane_id for role {role}")
    title = pane_title(role, phase)
    _tmux(["select-pane", "-t", pane, "-T", title])
    # notify-tmux-title.sh hook 的 pane-border-format 显示 @notify_tmux_title_pane_name(不是 -T 标题),
    # 且只在该选项为空时才分配水浒传随机名 → 这里先占住, hook 就不会覆盖, border 直接显示 phase 名。
    _tmux(["set-option", "-pt", pane, "@notify_tmux_title_pane_name", title])
    time.sleep(1)
    if role_cfg["backend"] == "claude_cli":
        send_to_pane(pane, role_cfg["cmd"])
    elif role_cfg["backend"] not in READY_MARKERS:
        time.sleep(1)
    resend_after_box = launch_resend_after_box(role_cfg, command)
    status, tail = verify_dispatch(pane, role_cfg["backend"], resend_after_box=resend_after_box)
    if status == "blocked":
        _register(workspace, role, phase, pane, status="dispatch_blocked")
        return pane, "dispatch_blocked", tail
    send_to_pane(pane, intro)
    _register(workspace, role, phase, pane)
    return pane, "running", None


def _register(workspace: Path, role: str, phase: str, pane: str, status: str = "running") -> None:
    sessions_path = workspace / "SESSIONS.md"
    text = sessions_path.read_text(encoding="utf-8") if sessions_path.exists() else render_sessions([])
    rows = parse_sessions(text)
    # 每次注册新 pane 时顺手收口已死的 stale running 行(常见写入路径自愈, 不必等到下次 teardown)。
    if os.environ.get("TMUX"):
        live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
        rows, _ = reconcile_dead_sessions(rows, live, _now())
    rows = upsert_session(
        rows,
        {"role": role, "phase": phase, "pane_id": pane, "started_at": _now(), "last_seen": _now(), "status": status},
    )
    sessions_path.write_text(render_sessions(rows), encoding="utf-8")


# ---------------------------------------------------------------------------
# 模板
# ---------------------------------------------------------------------------
def default_config_yaml(slug: str) -> str:
    # 双路 reviewer: 检测 orchestrator 运行时, a/b backend 互补。
    # CC 环境 → a=kilo b=cc；非 CC 环境 → a=cc b=kilo。
    is_cc = bool(os.environ.get("CLAUDECODE"))
    if is_cc:
        rev_a_backend, rev_a_model = "kilo", "cliproxy/gpt-5.5"
        rev_a_extra = ""
        rev_b_backend, rev_b_model = "claude_cli", "claude-opus-4-6"
        rev_b_extra = "\n    cmd: 'claude --dangerously-skip-permissions'"
    else:
        rev_a_backend, rev_a_model = "claude_cli", "claude-opus-4-6"
        rev_a_extra = "\n    cmd: 'claude --dangerously-skip-permissions'"
        rev_b_backend, rev_b_model = "kilo", "cliproxy/gpt-5.5"
        rev_b_extra = ""

    return f"""version: 2

# dev-long-run 角色配置(双路 reviewer)。
# 双路 reviewer: _a + _b 并发审查, 两份 review 原样交 coder 仲裁。
# orchestrator 检测: {'CC → a=kilo b=cc' if is_cc else 'kilo/other → a=cc b=kilo'}
roles:
  scaffold_orchestrator:
    backend: kilo
    model: cliproxy/gpt-5.5     # 不生效(orchestrator = 对话 agent)
    autonomy: medium
  scaffold_reviewer_a:
    backend: {rev_a_backend}
    model: {rev_a_model}{rev_a_extra}
    autonomy: off
  scaffold_reviewer_b:
    backend: {rev_b_backend}
    model: {rev_b_model}{rev_b_extra}
    autonomy: off
  loop_orchestrator:
    backend: kilo
    model: cliproxy/gpt-5.5     # 不生效(orchestrator = 对话 agent)
    autonomy: medium
  phase_planner:
    backend: kilo
    model: cliproxy/gpt-5.5     # effort=high(模型默认)
    autonomy: low
  phase_coder:
    backend: kilo
    model: cliproxy/gpt-5.5     # effort=high(模型默认)
    autonomy: high
  phase_reviewer_a:
    backend: {rev_a_backend}
    model: {rev_a_model}{rev_a_extra}
    autonomy: off
  phase_reviewer_b:
    backend: {rev_b_backend}
    model: {rev_b_model}{rev_b_extra}
    autonomy: off

policy:
  review_loop: one_round_with_ack
  arbitration: coder_self_judge
  cleanup_strategy: propose_only
  pause_between_phases: true
  commit_per_phase: true
  wrapup_backlog_triage: true

tmux:
  default_split: split-right
  reviewer_split: split-down
  pane_title_prefix: lr:{slug}
"""


WORKSPACE_FILES = {
    "SPEC_OVERVIEW.md": "# Spec Overview\n\n(scaffold orchestrator 产出: Task Understanding / Code Facts / 边界)\n\n## Coverage Matrix\n\n| Req ID | REQUIREMENT 目标 | 覆盖 Phase | 备注 |\n|--------|-----------------|-----------|------|\n| R1     |                 |           |      |\n",
    "fix_plan.md": "# Fix Plan\n\n(phase 清单, scaffold orchestrator 产出。格式: `- [ ] 01 <phase>`)\n",
    "SCAFFOLD_REVIEW.md": "# Scaffold Review\n\n(scaffold reviewer 产出: blocker / should / nit)\n",
    "HANDOFF.md": "# Handoff\n\n(phase coder 每轮交接: 做了什么 / 下一步 / 验证证据)\n",
    "BACKLOG.md": "# Backlog\n\n(非阻塞 + 高成本未做 + disputed 项)\n",
    "CLEANUP_PROPOSAL.md": "# Cleanup Proposal\n\n(收尾产出, 建议清单, 不自动删)\n",
    "qa.md": "# Acceptance / QA\n\n(端到端验收契约 + evidence)\n",
    "logs.md": "# Logs (append-only)\n",
}


def append_git_exclude(repo_root: Path) -> None:
    """L18: 把 .long-loop/ 加进 .git/info/exclude(本地忽略, 不改 tracked .gitignore)。"""
    exclude = repo_root / ".git" / "info" / "exclude"
    if not exclude.parent.exists():
        return
    line = ".long-loop/"
    current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if line not in current.splitlines():
        exclude.write_text(current + ("" if current.endswith("\n") or not current else "\n") + line + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI 子命令
# ---------------------------------------------------------------------------
def cmd_scaffold(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    requirement = Path(args.requirement).expanduser().resolve()
    if not requirement.exists():
        sys.stderr.write(f"REQUIREMENT not found: {requirement}\n")
        return 1
    name = args.name or args.goal or requirement.stem
    current_branch = _git(repo_root, ["branch", "--show-current"])
    slug = try_slugify(name)
    # 强制显式选择 worktree 模式: 不默认, 逼 agent 先问用户(L16/L20)
    if args.new == args.in_place:  # 都没给 或 同时给, 都拒绝
        conflict = args.new and args.in_place
        if conflict:
            sys.stderr.write("both --new and --in-place given; pick one\n")
            return 2
        slug_hint = slug or "<slug-from---name>"
        name_hint = "" if slug else "  注意: 当前任务名无法生成 git-safe slug；重跑时请加 --name <ascii-slug>\n"
        sys.stderr.write(
            "worktree 模式未指定 — 请先把下面信息给用户、让用户选,再带 --new 或 --in-place 重跑:\n"
            + f"  当前分支: {current_branch or 'detached HEAD'}\n"
            f"  --new      : 新建隔离 worktree(../<repo>-lr-{slug_hint}) + 分支 lr/{slug_hint}\n"
            f"  --in-place : 在当前分支 '{current_branch}' 接着做(main/master 会被拒)\n"
            f"{name_hint}"
        )
        return 2
    if not slug:
        sys.stderr.write(
            f"cannot derive git-safe slug from {name!r}; "
            "use --name <ascii-slug>, e.g. --name commit-submission-config-optimization\n"
        )
        return 2
    date = datetime.now().strftime("%Y%m%d")
    workspace = repo_root / ".long-loop" / f"{date}_{slug}"
    if workspace.exists():
        sys.stderr.write(f"workspace exists: {workspace}\n")
        return 1
    # L16: 新建 worktree+分支(隔离) 或 在当前 worktree+分支接着做(--in-place)
    dirty = _git(repo_root, ["status", "--porcelain"])
    try:
        plan = plan_worktree(repo_root, slug, args.in_place, current_branch)
    except ValueError as error:
        sys.stderr.write(f"refusing: {error}\n")
        return 1
    wt = Path(plan["worktree_path"])
    branch = plan["branch"]
    if plan["create"]:
        # 友好拒绝撞名(同名任务二跑/上次残留), 不让 git 裸 traceback 出去
        if wt.exists():
            sys.stderr.write(
                f"refusing: worktree 路径已存在: {wt}\n"
                f"  上次残留 → 确认无用后 `git worktree remove {wt}`；要续做该分支改用 --in-place(先切过去)\n")
            return 1
        probe = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet",
                                f"refs/heads/{branch}"], capture_output=True)
        if probe.returncode == 0:
            sys.stderr.write(
                f"refusing: 分支 {branch} 已存在 —— 续做请先切到它再用 --in-place；"
                f"或删旧分支；或 `--name <别名>` 换个 slug\n")
            return 1
        _git(repo_root, ["worktree", "add", "-b", branch, str(wt)])
    workspace.mkdir(parents=True)
    append_git_exclude(repo_root)
    (workspace / "config.yaml").write_text(default_config_yaml(slug), encoding="utf-8")
    validate_config(load_yaml((workspace / "config.yaml").read_text(encoding="utf-8")))
    (workspace / "REQUIREMENT.md").write_text(requirement.read_text(encoding="utf-8"), encoding="utf-8")
    for fname, body in WORKSPACE_FILES.items():
        (workspace / fname).write_text(body, encoding="utf-8")
    (workspace / "SESSIONS.md").write_text(render_sessions([]), encoding="utf-8")
    (workspace / "ORCHESTRATOR.md").write_text((PROMPTS_DIR / "loop_orchestrator.md").read_text(encoding="utf-8"), encoding="utf-8")
    (workspace / "phases").mkdir()
    state = {
        "skill": "dev-long-run",
        "state": "scaffold", "phase": 0, "role_in_flight": "agent_orchestrator",
        "worktree_path": str(wt), "branch": branch, "goal": args.goal or name,
        "repo_root": str(repo_root), "slug": slug, "dirty_main_at_start": bool(dirty),
        "in_place": bool(args.in_place),
    }
    save_state(workspace / "state.json", state)
    mode = "in-place(当前 worktree+分支,接着做)" if args.in_place else "new(新建隔离 worktree+分支)"
    # 不 spawn orchestrator pane: 调用本命令的 agent 自己就是 orchestrator(SKILL 控制循环)。
    sys.stdout.write(
        f"scaffold ready (no orchestrator pane spawned — you the agent are the orchestrator).\n"
        f"  mode     : {mode}\n"
        f"  workspace: {workspace}\n  worktree : {wt}\n  branch   : {branch}\n\n"
        f"Next (act as scaffold orchestrator yourself):\n"
        f"  1. Read {workspace}/REQUIREMENT.md and the repo (cwd={wt}).\n"
        f"  2. Write SPEC_OVERVIEW.md (with Coverage Matrix) / fix_plan.md / qa.md / phases/<NN>_<slug>/spec.md into {workspace}.\n"
        f"  3. (L2, mandatory) launch dual scaffold reviewers:\n"
        f"       python3 {Path(__file__).resolve()} launch --workspace {workspace} --role scaffold_reviewer_a\n"
        f"       python3 {Path(__file__).resolve()} launch --workspace {workspace} --role scaffold_reviewer_b\n"
        f"  4. Tell the user the phase plan in chat; on approval, start the develop loop (see ORCHESTRATOR.md).\n"
        f"  resume: python3 {Path(__file__).resolve()} resume --workspace {workspace}\n"
    )
    if dirty:
        sys.stdout.write("  WARN: main 有未提交改动(已记录), 本流程不会碰 main\n")
    return 0


def cmd_develop(args: argparse.Namespace) -> int:
    """标记进入 develop。不 spawn pane: 调用方 agent 自己跑 develop 循环(见 ORCHESTRATOR.md)。"""
    workspace = Path(args.workspace).resolve()
    state = load_state(workspace / "state.json")
    state["state"] = "develop"
    state["role_in_flight"] = "agent_orchestrator"
    save_state(workspace / "state.json", state)
    sys.stdout.write(
        f"develop state set. You (agent) drive the loop: per phase →\n"
        f"  1. planner → {{research,plan,qa,verify_plan}}.md\n"
        f"  2. coder → impl + verify.sh (before done impl, no commit yet)\n"
        f"  3. dual reviewer → Verification Coverage + Debugger + Refactor\n"
        f"  4. send review to coder → ack+fix → commit (L14)\n"
        f"  5. lr.py verify + complete-phase, then ask user: next/done/block\n"
        f"  See {workspace}/ORCHESTRATOR.md\n"
    )
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    state = load_state(workspace / "state.json")
    config = load_yaml((workspace / "config.yaml").read_text(encoding="utf-8"))
    if args.role not in config["roles"]:
        sys.stderr.write(f"unknown role {args.role}\n")
        return 1
    mode = args.mode or ("split-down" if "reviewer" in args.role else "split-right")
    pane, status, tail = launch_role(workspace, args.role, config["roles"][args.role], args.phase, mode, brief=args.brief)
    if status == "dispatch_blocked":
        sys.stdout.write(f"DISPATCH_BLOCKED role={args.role} pane={pane}\n")
        if tail:
            sys.stdout.write("--- pane tail ---\n")
            sys.stdout.write(tail + "\n")
        return DISPATCH_BLOCKED_EXIT
    sys.stdout.write(pane + "\n")
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    # 故障导向安全: 打到不存在的 pane 必须明确报错, 不静默打空
    # (常见错误: 自己编 pane id, 或没先 launch。pane id 必须来自 launch 的输出。)
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    if not pane_is_alive(live, args.pane):
        sys.stderr.write(
            f"refusing: pane {args.pane} 不存在(别自己编 pane id;先 `launch --role <r>` 拿它打印的 id)。"
            f"当前活着的 pane: {live.split() or '无'}\n"
        )
        return 1
    # 注册表护栏: 带 --workspace 时 pane 必须是本工作区 launch 过的 worker pane,
    # 防止编错 id 把 prompt 灌进用户自己的 pane(它也 alive, 上面的检查挡不住)。
    if args.workspace:
        sessions_path = Path(args.workspace).resolve() / "SESSIONS.md"
        rows = parse_sessions(sessions_path.read_text(encoding="utf-8")) if sessions_path.exists() else []
        if not pane_registered(rows, args.pane):
            sys.stderr.write(
                f"refusing: pane {args.pane} 活着但不在 {sessions_path} 注册表里 —— "
                f"它可能是用户自己的 pane。只给 `launch` 打印的 worker pane 发消息。\n"
            )
            return 1
    send_to_pane(args.pane, args.text)
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    # 故障导向安全: 不在 tmux 里就没 pane 可关, 明确报错(与 cmd_send 一致)。
    if not os.environ.get("TMUX"):
        sys.stderr.write("refusing: 不在 tmux 里, 无 pane 可关\n")
        return 1
    workspace = Path(args.workspace).resolve()
    pids = _close_roles(workspace, (args.role,))
    if pids:
        sys.stdout.write(f"closed {args.role}: {' '.join(pids)}\n")
    else:
        sys.stdout.write(f"no live pane for role {args.role}\n")  # 幂等: 已关过/没开过都算成功
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    text = (workspace / "SESSIONS.md").read_text(encoding="utf-8")
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    sys.stdout.write(text + "\n")
    for row in parse_sessions(text):
        alive = pane_is_alive(live, row["pane_id"])
        sys.stdout.write(f"  {row['role']:18} {row['pane_id']:6} {'ALIVE' if alive else 'DEAD'}\n")
    return 0


def _role_backends(workspace: Path) -> dict[str, str]:
    config_path = workspace / "config.yaml"
    if not config_path.exists():
        return {}
    config = load_yaml(config_path.read_text(encoding="utf-8"))
    roles = config.get("roles", {}) if isinstance(config, dict) else {}
    return {role: cfg.get("backend", "custom") for role, cfg in roles.items() if isinstance(cfg, dict)}


def _status_state_for_observe(workspace: Path, row: dict[str, str]) -> str | None:
    role = row["role"]
    phase = row["phase"]
    if role.startswith("phase_"):
        status_path = resolve_phase_dir(workspace, phase) / f"{role}.status"
    else:
        status_path = workspace / f"{role}.status"
    if not status_path.exists():
        return None
    state, _detail = parse_worker_status(status_path.read_text(encoding="utf-8"))
    return None if state == "unknown" else state


def _session_age_s(row: dict[str, str], now: datetime | None = None) -> float:
    ts = row.get("last_seen") or row.get("started_at") or ""
    try:
        seen = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    return max(0.0, (now - seen).total_seconds())


def observe_running_panes(workspace: Path) -> list[dict]:
    sessions_path = workspace / "SESSIONS.md"
    rows = parse_sessions(sessions_path.read_text(encoding="utf-8")) if sessions_path.exists() else []
    running = [row for row in rows if row["status"] == "running"]
    if not running:
        return []

    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    backends = _role_backends(workspace)
    out = []
    for row in running:
        role = row["role"]
        pane = row["pane_id"]
        alive = pane_is_alive(live, pane)
        if not alive:
            out.append({
                "role": role,
                "pane": pane,
                "alive": False,
                "screen_class": "dead",
                "status_state": _status_state_for_observe(workspace, row),
                "age_s": _session_age_s(row),
                "prompt_shape": None,
                "tail": "",
            })
            continue
        frame1 = capture_pane(pane)
        time.sleep(OBSERVE_FRAME_GAP)
        frame2 = capture_pane(pane)
        backend = backends.get(role, "custom")
        status_state = _status_state_for_observe(workspace, row)
        age_s = _session_age_s(row)
        screen_class = classify_screen(frame2, frame1, backend, status_state, age_s)
        out.append({
            "role": role,
            "pane": pane,
            "alive": True,
            "screen_class": screen_class,
            "status_state": status_state,
            "age_s": age_s,
            "prompt_shape": classify_prompt_shape(frame2, backend) if screen_class == "awaiting_input" else None,
            "tail": screen_tail(frame2),
        })
    return out


def _read_remediate_counts(workspace: Path) -> dict[str, int]:
    path = workspace / "remediate.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): int(v) for k, v in data.items()}


def _write_remediate_counts(workspace: Path, counts: dict[str, int]) -> None:
    (workspace / "remediate.json").write_text(
        json.dumps(counts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _set_session_status(workspace: Path, pane: str, status: str) -> None:
    sessions_path = workspace / "SESSIONS.md"
    rows = parse_sessions(sessions_path.read_text(encoding="utf-8")) if sessions_path.exists() else []
    changed = False
    now = _now()
    for row in rows:
        if row["pane_id"] == pane and row["status"] != status:
            row["status"] = status
            row["last_seen"] = now
            changed = True
    if changed:
        sessions_path.write_text(render_sessions(rows), encoding="utf-8")


def _session_for_pane(workspace: Path, pane: str) -> dict[str, str] | None:
    sessions_path = workspace / "SESSIONS.md"
    rows = parse_sessions(sessions_path.read_text(encoding="utf-8")) if sessions_path.exists() else []
    for row in rows:
        if row["pane_id"] == pane:
            return row
    return None


def _observe_one_pane(workspace: Path, row: dict[str, str]) -> dict:
    pane = row["pane_id"]
    backends = _role_backends(workspace)
    backend = backends.get(row["role"], "custom")
    age_s = _session_age_s(row)
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    if not pane_is_alive(live, pane):
        return {
            "role": row["role"],
            "pane": pane,
            "alive": False,
            "backend": backend,
            "age_s": age_s,
            "screen": "",
            "screen_class": "dead",
            "tail": "",
        }
    frame1 = capture_pane(pane)
    time.sleep(OBSERVE_FRAME_GAP)
    frame2 = capture_pane(pane)
    status_state = _status_state_for_observe(workspace, row)
    screen_class = classify_screen(frame2, frame1, backend, status_state, age_s)
    return {
        "role": row["role"],
        "pane": pane,
        "alive": True,
        "backend": backend,
        "age_s": age_s,
        "screen": frame2,
        "screen_class": screen_class,
        "tail": screen_tail(frame2),
    }


def _role_config(workspace: Path, role: str) -> dict:
    config_path = workspace / "config.yaml"
    if not config_path.exists():
        return {"backend": "custom"}
    config = load_yaml(config_path.read_text(encoding="utf-8"))
    return config.get("roles", {}).get(role, {"backend": "custom"})


def _emit_remediate_metric(workspace: Path, row: dict[str, str] | None, pane: str,
                           screen_class: str, action: str, attempt: int | None = None,
                           reason: str | None = None) -> None:
    record = {
        "event": "remediate",
        "pane": pane,
        "role": row.get("role") if row else None,
        "screen_class": screen_class,
        "action": action,
    }
    if attempt is not None:
        record["attempt"] = attempt
    if reason:
        record["reason"] = reason
    append_metric(workspace, record)


def cmd_remediate(args: argparse.Namespace) -> int:
    """对 P4 type(a) 幂等场景做有界自动补救；其他情况 escalate。"""
    workspace = Path(args.workspace).resolve()
    row = _session_for_pane(workspace, args.pane)
    if row is None:
        _emit_remediate_metric(workspace, None, args.pane, "unknown", "escalate", reason="unregistered_pane")
        sys.stdout.write("ESCALATE unregistered_pane\n")
        return REMEDIATE_ESCALATE_EXIT

    observed = _observe_one_pane(workspace, row)
    if not observed["alive"]:
        _emit_remediate_metric(workspace, row, args.pane, "dead", "escalate", reason="pane_dead")
        sys.stdout.write("ESCALATE pane_dead\n")
        return REMEDIATE_ESCALATE_EXIT

    counts = _read_remediate_counts(workspace)
    retry_count = counts.get(args.pane, 0)
    plan = plan_remediation(
        observed["screen_class"], observed["screen"], observed["backend"], retry_count,
        age_s=observed.get("age_s", 0),
    )
    action = plan["action"]
    reason = plan.get("reason")
    if action == "escalate":
        _emit_remediate_metric(workspace, row, args.pane, observed["screen_class"], action, reason=reason)
        sys.stdout.write(f"ESCALATE {reason}\n")
        if observed["tail"]:
            sys.stdout.write(f"--- pane tail ---\n{observed['tail']}\n")
        return REMEDIATE_ESCALATE_EXIT

    if action == "resend_status_prompt":
        send_to_pane(args.pane, STATUS_REPROMPT)
    elif action == "resolve_safe_box":
        match = match_safe_launch_box(observed["screen"])
        if match is None:
            _emit_remediate_metric(workspace, row, args.pane, observed["screen_class"], "escalate", reason="unsafe_dispatch_block")
            sys.stdout.write("ESCALATE unsafe_dispatch_block\n")
            return REMEDIATE_ESCALATE_EXIT
        box_name, keys = match
        send_keys_to_pane(args.pane, keys)
        role_cfg = _role_config(workspace, row["role"])
        resend_after_box = launch_resend_after_box(role_cfg, launch_command(role_cfg))
        if resend_after_box and box_name in resend_after_box:
            send_to_pane(args.pane, resend_after_box[box_name])
        _set_session_status(workspace, args.pane, "running")
    elif action == "retry_errored":
        send_to_pane(args.pane, ERROR_RETRY_PROMPT)
    else:
        _emit_remediate_metric(workspace, row, args.pane, observed["screen_class"], "escalate", reason="unknown_action")
        sys.stdout.write("ESCALATE unknown_action\n")
        return REMEDIATE_ESCALATE_EXIT

    attempt = retry_count + 1
    counts[args.pane] = attempt
    _write_remediate_counts(workspace, counts)
    _emit_remediate_metric(workspace, row, args.pane, observed["screen_class"], action, attempt=attempt, reason=reason)
    sys.stdout.write(f"REMEDIATED {action} attempt={attempt}\n")
    return REMEDIATE_EXIT


def cmd_observe(args: argparse.Namespace) -> int:
    """只读观察所有 running pane，输出给协调者消费的结构化 JSON。"""
    workspace = Path(args.workspace).resolve()
    out = observe_running_panes(workspace)
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


def _await_all_payload(agg: dict, panes: list[dict], *, verdict: str | None = None) -> dict:
    return {
        "verdict": verdict or agg["verdict"],
        "triggering": agg["triggering"],
        "done_count": agg["done_count"],
        "total": agg["total"],
        "panes": panes,
    }


def cmd_await_all(args: argparse.Namespace) -> int:
    """有界循环观察所有 running pane；任一可行动、全部 done 或超时即返回 JSON。"""
    workspace = Path(args.workspace).resolve()
    deadline = time.monotonic() + args.timeout
    last_panes: list[dict] = []
    while time.monotonic() < deadline:
        panes = observe_running_panes(workspace)
        last_panes = panes
        if not panes:
            payload = _await_all_payload(aggregate_await_all([]), [], verdict="all_done")
            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            return 0
        agg = aggregate_await_all(panes)
        if agg["verdict"] == "all_done":
            sys.stdout.write(json.dumps(_await_all_payload(agg, panes), ensure_ascii=False) + "\n")
            return 0
        if agg["verdict"] == "attention":
            sys.stdout.write(json.dumps(_await_all_payload(agg, panes), ensure_ascii=False) + "\n")
            return AWAIT_ALL_ATTENTION_EXIT
        time.sleep(args.interval)
    agg = aggregate_await_all(last_panes)
    sys.stdout.write(json.dumps(_await_all_payload(agg, last_panes, verdict="timeout"), ensure_ascii=False) + "\n")
    return 4


def cmd_pane_alive(args: argparse.Namespace) -> int:
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    return 0 if pane_is_alive(live, args.pane) else 1


def _pane_tail(pane: str | None, n: int = 15) -> str:
    """抓 pane 末 n 行(供 IDLE/TIMEOUT 诊断: orchestrator 不必再单独 capture-pane 看现场)。"""
    if not pane:
        return "(无 pane)"
    screen = capture_pane(pane)
    return "\n".join(screen.splitlines()[-n:])


def cmd_await(args: argparse.Namespace) -> int:
    """健壮地等 worker 完成: 轮询 status 文件 token + 查 pane 死活 + idle 兜底 + 有界超时。
    退出码: 0 DONE / 2 BLOCKED / 3 DEAD(pane 没了) / 4 TIMEOUT / 5 COMPACT / 6 IDLE(停在
    就绪框却没写 status)。idle/timeout 附 pane tail 便于诊断。不 grep prose 判完成。

    status 路径二选一: 直接 `--status <path>`(裸路径); 或 `--workspace+--phase+--role`,
    由 lr `resolve_phase_dir` 解析真实 phase 目录再拼 `<role>.status` —— 后者推荐, 避免
    orchestrator 用数字 id 拼出 `phases/03` 而 worker 实际写在 `phases/03_<slug>` 的错位。"""
    if args.status:
        status_path = Path(args.status)
    elif args.workspace and args.phase and args.role:
        status_path = resolve_phase_dir(Path(args.workspace).resolve(), args.phase) / f"{args.role}.status"
    else:
        sys.stderr.write("await: 需要 --status, 或 --workspace+--phase+--role(由 lr 解析 phase 目录构造 status 路径)\n")
        return 2
    deadline = time.monotonic() + args.timeout
    prev_screen = ""
    idle_strikes = 0
    while time.monotonic() < deadline:
        if args.pane:
            live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
            if not pane_is_alive(live, args.pane):
                sys.stdout.write(f"DEAD {args.pane} (status 未达 done; pane 没了)\n")
                return 3
        text = status_path.read_text(encoding="utf-8") if status_path.exists() else ""
        state, detail = parse_worker_status(text)
        if state == "done":
            sys.stdout.write(f"DONE {detail}\n")
            return 0
        if state == "blocked":
            sys.stdout.write(f"BLOCKED {detail}\n")
            return 2
        if state == "compact":
            sys.stdout.write(f"COMPACT {detail}\n")
            return 5
        # idle 兜底: TUI worker 干完回到输入框却忘写/写错 status, pane 不死、status 不变 →
        # 不该死等到 timeout。连续 idle 超过 idle_timeout 即返回 6, 让 orchestrator 立即介入。
        if args.pane and args.idle_timeout > 0:
            screen = capture_pane(args.pane)
            idle_strikes = update_idle(prev_screen, screen, idle_strikes)
            prev_screen = screen
            if idle_strikes * args.interval >= args.idle_timeout:
                sys.stdout.write(
                    f"IDLE {args.pane} (停在就绪输入框 ~{idle_strikes * args.interval}s 未写 status)\n"
                    f"--- pane tail ---\n{_pane_tail(args.pane)}\n"
                )
                return 6
        time.sleep(args.interval)
    sys.stdout.write(
        f"TIMEOUT after {args.timeout}s (status={status_path})\n"
        f"--- pane tail ---\n{_pane_tail(args.pane)}\n"
    )
    return 4


def cmd_reset_status(args: argparse.Namespace) -> int:
    """把某 role 的 status 文件重置成 `coding`。orchestrator 给 coder 发 review 前必跑:
    清掉两段式信号残留的 `done impl`, 否则下一次 await 读到 stale done 立即误判修复完成。"""
    pdir = resolve_phase_dir(Path(args.workspace).resolve(), args.phase)
    status_file = pdir / f"{args.role}.status"
    status_file.write_text("coding\n", encoding="utf-8")
    sys.stdout.write(f"reset → coding: {status_file}\n")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    state = load_state(workspace / "state.json")
    wt = Path(state.get("worktree_path", ""))
    wt_ok = wt.exists()
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    sys.stdout.write(
        f"resume: state={state.get('state')} phase={state.get('phase')} branch={state.get('branch')}\n"
        f"  worktree {'OK' if wt_ok else 'MISSING'}: {wt}\n"
    )
    if not wt_ok:
        sys.stdout.write(f"  worktree 丢失 → 重建: git worktree add {wt} {state.get('branch')}\n")
    fp = workspace / "fix_plan.md"
    if fp.exists():
        pending = unchecked_phases(fp.read_text(encoding="utf-8"))
        sys.stdout.write(f"  未完成 phase: {', '.join(pending) if pending else '无(fix_plan 全勾)'}\n")
    for row in parse_sessions((workspace / "SESSIONS.md").read_text(encoding="utf-8")):
        alive = pane_is_alive(live, row["pane_id"])
        sys.stdout.write(f"  {row['role']:18} {row['pane_id']:6} {'ALIVE' if alive else 'DEAD(重开 fresh 读 HANDOFF / 标 failed)'}\n")
    # L26: 卡死计数从磁盘恢复(不靠记忆)——崩溃重启后仍能看到"哪个 phase 在同一失败上反复栽"。
    phases_dir = workspace / "phases"
    if phases_dir.is_dir():
        for sj in sorted(phases_dir.glob("*/stuck.json")):
            data = json.loads(sj.read_text(encoding="utf-8"))
            n = int(data.get("consecutive_fail", 0) or 0)
            if n >= STUCK_THRESHOLD:
                sys.stdout.write(
                    f"  STUCK: {sj.parent.name} 连续 {n} 次相同失败(指纹 {data.get('fingerprint')}) "
                    f"—— 续做前先 /think-unstuck, 别盲目重试\n"
                )
    return 0


def _append_log(workspace: Path, msg: str) -> None:
    p = workspace / "logs.md"
    prev = p.read_text(encoding="utf-8") if p.exists() else "# Logs\n"
    p.write_text(prev + f"- {_now()}: {msg}\n", encoding="utf-8")


def append_metric(workspace: Path, record: dict) -> None:
    """向 <ws>/metrics.jsonl 追加一行结构化事件(机器可读运行流水, append-only)。
    自动补 ts; 喂 `lr.py stats` 出汇总, 也是 stuck 计数的派生来源。纯增量、零回改, 不阻断任何门禁。"""
    p = workspace / "metrics.jsonl"
    with p.open("a", encoding="utf-8") as fh:
        if p.stat().st_size == 0:
            fh.write(json.dumps({"_schema": "dotfiles.long_loop.metrics", "_version": 1}, ensure_ascii=False) + "\n")
        line = json.dumps({"ts": _now(), **record}, ensure_ascii=False)
        fh.write(line + "\n")


def cmd_verify(args: argparse.Namespace) -> int:
    """在 worktree 里真跑验证脚本, 把执行证据(exit code + 输出)落成 verify.json/acceptance.json。
    这是"测试只写没跑"的解药: 完成门禁只认这个文件, 不认 coder 自己在 qa.md 的口头声明。"""
    workspace = Path(args.workspace).resolve()
    state = load_state(workspace / "state.json")
    cwd = Path(state.get("worktree_path") or workspace)
    if args.acceptance:
        script, out_path, label = workspace / "acceptance.sh", workspace / "acceptance.json", "acceptance"
    else:
        pdir = resolve_phase_dir(workspace, args.phase)
        script, out_path, label = pdir / "verify.sh", pdir / "verify.json", f"phase {args.phase}"
    if not script.exists():
        sys.stderr.write(f"refusing: {script} 不存在 —— 先写 {label} 的可执行验证脚本(真跑测试/端到端验收)\n")
        return 2
    try:
        result = subprocess.run(["bash", str(script)], cwd=str(cwd), text=True, capture_output=True,
                                timeout=args.timeout)
        summary = verify_summary(result.returncode, (result.stdout or "") + (result.stderr or ""))
    except subprocess.TimeoutExpired as err:
        # 挂起脚本(误启常驻服务等)不能无限阻塞 orchestrator: 按失败落证据, exit 124 惯例
        partial = (err.stdout or b"") if isinstance(err.stdout, (bytes, type(None))) else err.stdout
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "replace")
        summary = verify_summary(124, (partial or "") + f"\n[lr] TIMEOUT: {label} 超过 {args.timeout}s 未结束(挂起按失败处理)")
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"{'OK' if summary['ok'] else 'FAIL'} {label} exit={summary['exit']} → {out_path.name}\n")
    if args.acceptance:
        # acceptance 是端到端验收(非 phase 内 rework 回合), 只记一条 metric, 不参与 stuck 计数。
        append_metric(workspace, {"event": "acceptance", "ok": summary["ok"], "exit": summary["exit"]})
    else:
        # L26 卡死检测: 持久化失败计数 + 错误指纹(磁盘 SSOT, 不靠 orchestrator 记忆)。
        stuck_path = pdir / "stuck.json"
        prev = json.loads(stuck_path.read_text(encoding="utf-8")) if stuck_path.exists() else {}
        new = update_stuck(prev, verify_fingerprint(summary))
        stuck_path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        append_metric(workspace, {"event": "verify", "phase": args.phase, "ok": summary["ok"],
                                  "exit": summary["exit"], "fail_streak": new["consecutive_fail"],
                                  "fingerprint": new["fingerprint"]})
        if new["consecutive_fail"] >= STUCK_THRESHOLD:
            sys.stdout.write(
                f"STUCK: phase {args.phase} 连续 {new['consecutive_fail']} 次相同失败"
                f"(指纹 {new['fingerprint']}) —— 原地打转, 别再盲改, 调 /think-unstuck 结构化排查或问用户\n"
            )
    return 0 if summary["ok"] else 2


def _commit_evidence(workspace: Path, phase: str) -> str | None:
    """L14 机器证据: coder status 声明的 `done commit=<hash>` 必须真实存在且是 worktree HEAD
    的祖先(in-place/新建分支两种模式都成立)。返回 BLOCK 原因; 通过返回 None。"""
    pdir = resolve_phase_dir(workspace, phase)
    status_file = pdir / "phase_coder.status"
    text = status_file.read_text(encoding="utf-8") if status_file.exists() else ""
    commit = parse_status_commit(text)
    if not commit:
        return ("缺 commit 证据：phase_coder.status 须为 `done commit=<hash>`"
                "（L14 收口必须 commit，口头声明不算）")
    worktree = load_state(workspace / "state.json").get("worktree_path") or str(workspace)
    probe = subprocess.run(["git", "-C", worktree, "merge-base", "--is-ancestor", commit, "HEAD"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        return (f"commit 证据无效：{commit} 不存在或不在 worktree 当前分支上"
                f"（git merge-base --is-ancestor 失败：{probe.stderr.strip() or 'non-zero'}）")
    return None


def _phase_gate_for(workspace: Path, phase: str) -> dict:
    pdir = resolve_phase_dir(workspace, phase)
    vj = pdir / "verify.json"
    verify = json.loads(vj.read_text(encoding="utf-8")) if vj.exists() else None
    # 双路 reviewer: review_a.md + review_b.md；旧单路: review.md
    review_a = (pdir / "review_a.md").read_text(encoding="utf-8") if (pdir / "review_a.md").exists() else ""
    review_b = (pdir / "review_b.md").read_text(encoding="utf-8") if (pdir / "review_b.md").exists() else ""
    review_legacy = (pdir / "review.md").read_text(encoding="utf-8") if (pdir / "review.md").exists() else ""
    if review_a or review_b:
        review_text: dict[str, str] | str = {"a": review_a, "b": review_b}
    else:
        review_text = review_legacy
    ack = (pdir / "ack.md").read_text(encoding="utf-8") if (pdir / "ack.md").exists() else ""
    gate = phase_gate(verify, review_text, ack)
    commit_reason = _commit_evidence(workspace, phase)
    if commit_reason:
        return {"ok": False, "reasons": gate["reasons"] + [commit_reason]}
    return gate


def cmd_gate(args: argparse.Namespace) -> int:
    """只读检查某 phase 是否过完成门禁(verify 过 + 每个 blocker 都 [fixed])。不改文件。"""
    g = _phase_gate_for(Path(args.workspace).resolve(), args.phase)
    for r in g["reasons"]:
        sys.stdout.write(f"BLOCK: {r}\n")
    if g["ok"]:
        sys.stdout.write(f"GATE OK: phase {args.phase} 可标完成\n")
    return 0 if g["ok"] else 2


def cmd_complete_phase(args: argparse.Namespace) -> int:
    """过门禁才翻 fix_plan [x] + 记 log。不过 → exit 2 拒绝, 不动 fix_plan。
    唯一允许把 phase 标完成的入口; orchestrator 不许手改 fix_plan(否则又回到静默放行)。"""
    workspace = Path(args.workspace).resolve()
    g = _phase_gate_for(workspace, args.phase)
    if not g["ok"]:
        for r in g["reasons"]:
            sys.stderr.write(f"BLOCK: {r}\n")
        sys.stderr.write(f"refusing: phase {args.phase} 未过门禁, 不标完成\n")
        return 2
    fp = workspace / "fix_plan.md"
    text = fp.read_text(encoding="utf-8")
    new = mark_phase_done(text, args.phase)
    if new == text:
        sys.stderr.write(f"refusing: fix_plan.md 找不到 phase {args.phase} 的 `- [ ]` 行\n")
        return 1
    fp.write_text(new, encoding="utf-8")
    # 记录进度到 state.json, resume 时不再永远显示 phase=0
    state = load_state(workspace / "state.json")
    state["phase"] = args.phase
    save_state(workspace / "state.json", state)
    _append_log(workspace, f"phase {args.phase} gate passed → marked complete")
    append_metric(workspace, {"event": "complete_phase", "phase": args.phase})
    # L24 teardown 兜底: 门禁已过, 清掉该 phase 残留的 planner/reviewer。coder 不在这里关 —
    # 它由下一 phase 的 fresh launch 关闭(L6), run 收尾时 complete-run 兜底全关。
    closed = _close_roles(workspace, PHASE_TRANSIENT_ROLES)
    if closed:
        _append_log(workspace, f"phase {args.phase} teardown: closed {' '.join(closed)}")
    sys.stdout.write(f"phase {args.phase} 完成(门禁已过, fix_plan 已勾)\n")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """只读: 读 metrics.jsonl 出 run 级 + per-phase 汇总。orchestrator 用它给用户报进度,
    不靠记忆复述(呼应红线: 无证据不算数)。无 metrics 文件 → 提示尚无事件, 退出 0(非错误)。"""
    workspace = Path(args.workspace).resolve()
    mp = workspace / "metrics.jsonl"
    if not mp.exists():
        sys.stdout.write("(尚无 metrics.jsonl —— 还没跑过 verify/complete-phase)\n")
        return 0
    records = [json.loads(ln) for ln in mp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    s = summarize_metrics(records)
    sys.stdout.write(
        f"run: phases_completed={s['phases_completed']} run_completed={s['run_completed']} "
        f"verify={s['verify_passes']}/{s['verify_attempts']} pass (fails={s['verify_fails']})\n"
    )
    for phase in sorted(s["per_phase"]):
        ph = s["per_phase"][phase]
        flag = "✓" if ph["completed"] else " "
        stuck = f" STUCK×{ph['fail_streak']}" if ph["fail_streak"] >= STUCK_THRESHOLD else ""
        sys.stdout.write(
            f"  [{flag}] phase {phase}: verify {ph['passes']}/{ph['verify_attempts']} pass, "
            f"fails={ph['fails']}, streak={ph['fail_streak']}{stuck}\n"
        )
    return 0


def cmd_complete_run(args: argparse.Namespace) -> int:
    """过 acceptance 门禁(真跑过 acceptance.sh 且过) + fix_plan 全勾, 才置 state=completed。否则拒绝。"""
    workspace = Path(args.workspace).resolve()
    fp = workspace / "fix_plan.md"
    pending = unchecked_phases(fp.read_text(encoding="utf-8")) if fp.exists() else []
    if pending:
        sys.stderr.write(
            f"BLOCK: fix_plan 仍有未完成 phase: {', '.join(pending)} —— "
            f"先逐个过 `complete-phase` 门禁再收尾(acceptance 过了也不能跳 phase)\n")
        return 2
    aj = workspace / "acceptance.json"
    acceptance = json.loads(aj.read_text(encoding="utf-8")) if aj.exists() else None
    g = acceptance_gate(acceptance)
    if not g["ok"]:
        for r in g["reasons"]:
            sys.stderr.write(f"BLOCK: {r}\n")
        return 2
    state = load_state(workspace / "state.json")
    state["state"] = "completed"
    save_state(workspace / "state.json", state)
    _append_log(workspace, "run completed: acceptance gate passed")
    append_metric(workspace, {"event": "complete_run"})
    # L24 teardown: run 结束清掉所有 worker(含跨 phase 的 coder); --keep-panes 保留现场调试。
    if args.keep_panes:
        _append_log(workspace, "teardown skipped (--keep-panes)")
    else:
        closed = _close_roles(workspace, WORKER_ROLES)
        if closed:
            _append_log(workspace, f"run teardown: closed {' '.join(closed)}")
    sys.stdout.write("run completed(acceptance 门禁已过)\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lr", description="dev-long-run multi-pane orchestration harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scaffold", help="建 worktree+workspace, 进入 scaffold 流程")
    p.add_argument("--requirement", required=True)
    p.add_argument("--goal")
    p.add_argument("--name")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--new", action="store_true", help="新建隔离 worktree + lr/<slug> 分支")
    p.add_argument("--in-place", action="store_true", help="在当前 worktree+分支接着做(L16:当前在 main/master 则拒绝)")
    p.set_defaults(func=cmd_scaffold)

    p = sub.add_parser("develop", help="进入逐 phase 开发循环")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_develop)

    p = sub.add_parser("resume", help="读 state, 校验 worktree + pane 存活")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("launch", help="(orchestrator 调用) 起一个 role pane")
    p.add_argument("--workspace", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--phase", default="0")
    p.add_argument("--mode")
    p.add_argument("--brief")
    p.set_defaults(func=cmd_launch)

    p = sub.add_parser("send", help="(orchestrator 调用) literal send-keys 到 pane")
    p.add_argument("--pane", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--workspace", help="给了就校验 pane 在该工作区 SESSIONS.md 注册过(推荐;防把 prompt 灌进用户 pane)")
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("close", help="(orchestrator 调用) 关掉某 role 的 worker pane, 标 closed(幂等)")
    p.add_argument("--workspace", required=True)
    p.add_argument("--role", required=True)
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("await", help="(orchestrator 调用) 健壮等 worker 完成: 轮询 status 文件 + 查 pane 死活")
    p.add_argument("--status", help="status 文件裸路径; 或改用 --workspace+--phase+--role 让 lr 解析 phase 目录")
    p.add_argument("--workspace", help="配合 --phase+--role: lr resolve_phase_dir 解析真实目录再拼 <role>.status")
    p.add_argument("--phase", help="配合 --workspace+--role 构造 status 路径(数字 id 即可, 会解析到 <NN>_<slug>)")
    p.add_argument("--role", help="配合 --workspace+--phase 构造 status 路径(如 phase_coder)")
    p.add_argument("--pane", help="worker pane id; 给了就每轮查死活+idle 兜底, 死了立即 DEAD 退出")
    p.add_argument("--timeout", type=int, default=600, help="有界超时秒数(默认 600)")
    p.add_argument("--interval", type=int, default=5, help="轮询间隔秒(默认 5)")
    p.add_argument("--idle-timeout", type=int, default=120,
                   help="pane 停在就绪框且画面不变多少秒判 IDLE(退出码 6, 需 --pane; 0=禁用, 默认 120)")
    p.set_defaults(func=cmd_await)

    p = sub.add_parser("sessions", help="打印 SESSIONS.md + pane 存活")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_sessions)

    p = sub.add_parser("observe", help="只读观察所有 running pane, 输出 JSON 分类")
    p.add_argument("--workspace", required=True)
    p.add_argument("--json", action="store_true", default=True, help="输出 JSON(默认; 保留给未来兼容)")
    p.add_argument("--once", action="store_true", default=True, help="单次观察(默认; 预留给未来循环接口)")
    p.set_defaults(func=cmd_observe)

    p = sub.add_parser("await-all", help="(orchestrator 调用) 等所有 running pane: 任一可行动/全 done/超时返回 JSON")
    p.add_argument("--workspace", required=True)
    p.add_argument("--timeout", type=int, default=600, help="有界超时秒数(默认 600)")
    p.add_argument("--interval", type=int, default=AWAIT_ALL_INTERVAL, help="轮询间隔秒(默认 5)")
    p.set_defaults(func=cmd_await_all)

    p = sub.add_parser("remediate", help="(orchestrator 调用) 对 type(a) 幂等故障做有界自动补救")
    p.add_argument("--workspace", required=True)
    p.add_argument("--pane", required=True)
    p.set_defaults(func=cmd_remediate)

    p = sub.add_parser("pane-alive", help="exit 0 if pane alive else 1")
    p.add_argument("--pane", required=True)
    p.set_defaults(func=cmd_pane_alive)

    p = sub.add_parser("verify", help="在 worktree 真跑 verify.sh/acceptance.sh, 记录执行证据 verify.json")
    p.add_argument("--workspace", required=True)
    p.add_argument("--phase", default="0")
    p.add_argument("--acceptance", action="store_true", help="跑根 acceptance.sh(端到端验收)而非某 phase verify.sh")
    p.add_argument("--timeout", type=int, default=900, help="脚本最长运行秒数(默认 900; 挂起按失败记证据)")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("reset-status", help="(orchestrator 调用) 把 role status 重置为 coding(发 review 前清 stale done)")
    p.add_argument("--workspace", required=True)
    p.add_argument("--phase", required=True)
    p.add_argument("--role", required=True)
    p.set_defaults(func=cmd_reset_status)

    p = sub.add_parser("gate", help="只读检查某 phase 是否过完成门禁(verify 过 + blocker 全 fixed)")
    p.add_argument("--workspace", required=True)
    p.add_argument("--phase", required=True)
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("complete-phase", help="过门禁才翻 fix_plan [x](唯一标完成入口); 不过 exit 2 拒绝")
    p.add_argument("--workspace", required=True)
    p.add_argument("--phase", required=True)
    p.set_defaults(func=cmd_complete_phase)

    p = sub.add_parser("stats", help="只读: 读 metrics.jsonl 出 run/per-phase 进度 + 卡死汇总")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("complete-run", help="过 acceptance 门禁才置 state=completed")
    p.add_argument("--workspace", required=True)
    p.add_argument("--keep-panes", action="store_true", help="收尾不关 worker pane(保留现场调试)")
    p.set_defaults(func=cmd_complete_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

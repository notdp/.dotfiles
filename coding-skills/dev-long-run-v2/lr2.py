#!/usr/bin/env python3
"""dev-long-run-v2 控制核心(纯逻辑部分)。

薄 wrapper，多 pane 调度脑在 loop orchestrator(LLM)里，本文件只放可单测的纯逻辑：
config schema 校验、variant→effort 按 backend 分流(L17)、SESSIONS.md 表读写、
state.json 扩字段、worktree/分支命名。spec: docs/specs/dev-long-run-v2/overview.md
"""
from __future__ import annotations

import argparse
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
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive slug from {name!r}")
    return slug


BACKENDS = ("kilo", "claude_cli", "droid", "custom")
AUTONOMY = ("off", "low", "medium", "high")
REQUIRED_ROLES = (
    "scaffold_orchestrator",
    "scaffold_reviewer",
    "loop_orchestrator",
    "phase_planner",
    "phase_coder",
    "phase_reviewer",
)


def validate_config(config: dict) -> dict:
    """校验已解析的 config.yaml(缺字段/错 enum/未知 backend 都拒)。返回原 config。"""
    if config.get("version") != 2:
        raise ValueError(f"config version must be 2, got {config.get('version')!r}")
    roles = config.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("config.roles must be a mapping")
    missing = [r for r in REQUIRED_ROLES if r not in roles]
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


# L7: wait_confirm 下的用户命令 → 下一个持久化 state(数据驱动, 见 state.json enum)
CONFIRM_TRANSITIONS = {
    "confirm next": "develop",
    "confirm done": "wrapup",
    "block": "blocked",
}


def apply_confirm(state: str, command: str) -> str:
    """L7: 用户在 orch pane 输入的 confirm 命令只在 wait_confirm 合法, 返回下一个 state。"""
    if state != "wait_confirm":
        raise ValueError(f"confirm command only valid at wait_confirm, not {state!r}")
    if command not in CONFIRM_TRANSITIONS:
        raise ValueError(f"unknown command {command!r}; valid: {', '.join(CONFIRM_TRANSITIONS)}")
    return CONFIRM_TRANSITIONS[command]


def branch_name(slug: str) -> str:
    """L16: 专用开发分支名。"""
    return f"lr2/{slug}"


def worktree_path(repo_root: Path, slug: str) -> Path:
    """L16: worktree 放 repo 同级目录 <repo>-lr2-<slug>。"""
    repo_root = Path(repo_root)
    return repo_root.parent / f"{repo_root.name}-lr2-{slug}"


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
    parts = lines[0].split(None, 1)
    state = parts[0].lower()
    detail = parts[1].strip() if len(parts) > 1 else ""
    if state not in WORKER_STATES:
        return ("unknown", lines[0])
    return (state, detail)


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


def parse_review_blockers(review_text: str) -> list[str]:
    """抽出 review.md 里标 `[blocker]` 的条目描述(标题行 `### [blocker] ...` 或行内皆可)。
    `[should]`/`[nit]` 不算 blocker, 不阻塞 phase 完成(它们走 fix-now-or-backlog)。"""
    out: list[str] = []
    for raw in review_text.splitlines():
        line = raw.strip()
        low = line.lower()
        if "[blocker]" in low:
            desc = line.lstrip("#").strip()
            idx = desc.lower().find("[blocker]")
            desc = desc[idx + len("[blocker]"):].strip()
            out.append(desc)
    return out


def parse_ack_resolutions(ack_text: str) -> dict:
    """统计 ack.md 里 `## Blocker Resolutions` 段内的 `[fixed]` / `[deferred]` 数量。
    只认这一段, 防止 Findings 段里的 `[agree] [blocker]` 叙述被误计。"""
    counts = {"fixed": 0, "deferred": 0}
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
        elif "[deferred]" in low:
            counts["deferred"] += 1
    return counts


def phase_gate(verify: dict | None, review_text: str, ack_text: str) -> dict:
    """phase 完成的硬门(纯谓词)。两条:
    (a) verify 必须真跑且过(verify 为 None/未 ok → 阻塞) —— 杜绝"测试只写没跑"。
    (b) review 的每个 [blocker] 必须在 ack 标 [fixed](fixed<blocker数 或 有 deferred → 阻塞)
        —— 杜绝 reviewer 开了 blocker 却被静默放行。
    全过才 ok。reasons 给人看, 调用方据 ok 决定是否拒绝完成。"""
    reasons: list[str] = []
    if not verify or not verify.get("ok"):
        reasons.append("验证未跑或失败：先 `lr2.py verify --phase <id>`，verify.json.ok 必须为真")
    blockers = parse_review_blockers(review_text)
    res = parse_ack_resolutions(ack_text)
    if blockers and (res["fixed"] < len(blockers) or res["deferred"] > 0):
        reasons.append(
            f"blocker 未解决：review 有 {len(blockers)} 个 [blocker]，"
            f"ack 仅 fixed={res['fixed']} deferred={res['deferred']}（blocker 不允许 deferred）"
        )
    return {"ok": not reasons, "reasons": reasons}


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
            "acceptance 未跑或失败：完成前必须 `lr2.py verify --acceptance` 跑通端到端验收，"
            "acceptance.json.ok 必须为真"
        ]}
    return {"ok": True, "reasons": []}


def find_live_role_pane(rows: list[dict[str, str]], role: str, list_panes_output: str) -> str | None:
    """找某 role 仍存活的 running pane(L6 改:每 phase 开始时据此关掉上一个 coder)。"""
    for row in rows:
        if row["role"] == role and row["status"] == "running" and pane_is_alive(list_panes_output, row["pane_id"]):
            return row["pane_id"]
    return None


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
RUNTIME_ROOT = Path(__file__).resolve().parents[2]
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


def pane_title(slug: str, role: str, phase: str) -> str:
    return f"lr2:{slug}:{role}:{phase}"


def capture_pane(pane: str) -> str:
    return _tmux(["capture-pane", "-t", pane, "-p"], capture=True)


def send_to_pane(pane: str, text: str, enter: bool = True) -> None:
    """把(可多行)文本 bracketed-paste 进 pane 输入框, 再单次 Enter 提交为一条消息。
    多行 prompt 在窗口里按原排版可读(不再是 send-keys 单行一坨)。"""
    buf = "lr2dispatch"
    subprocess.run(["tmux", "load-buffer", "-b", buf, "-"], input=text, text=True, capture_output=True)
    _tmux(paste_buffer_args(pane, buf))
    time.sleep(0.5)
    if enter:
        _tmux(["send-keys", "-t", pane, "Enter"])
        time.sleep(0.4)
    subprocess.run(["tmux", "delete-buffer", "-b", buf], capture_output=True)


def consume_claude_trust(pane: str, timeout_s: int = 20) -> bool:
    """claude 首次进目录的 trust 对话框: 检测到则发 Enter 接受(spec step1 finding)。"""
    for _ in range(timeout_s):
        time.sleep(1)
        screen = capture_pane(pane)
        if "trust this folder" in screen or "Is this a project" in screen:
            _tmux(["send-keys", "-t", pane, "Enter"])
            time.sleep(1)
            return True
        if "bypass permissions" in screen or "? for shortcuts" in screen:
            return False  # 已就绪, 无对话框
    return False


FRESH_PER_PHASE_ROLES = ("phase_coder",)  # L6(改): 每 phase 关掉上一个、开 fresh 的角色


def _close_role_pane(workspace: Path, role: str) -> str | None:
    """关掉某 role 上一个仍存活的 pane 并在 SESSIONS.md 标 closed。返回被关的 pane_id。"""
    sessions_path = workspace / "SESSIONS.md"
    if not sessions_path.exists():
        return None
    rows = parse_sessions(sessions_path.read_text(encoding="utf-8"))
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    pid = find_live_role_pane(rows, role, live)
    if not pid:
        return None
    _tmux(["kill-pane", "-t", pid], capture=True)
    rows = [dict(r, status="closed", last_seen=_now()) if r["pane_id"] == pid else r for r in rows]
    sessions_path.write_text(render_sessions(rows), encoding="utf-8")
    return pid


def _role_intro(role: str, phase: str, workspace: Path, brief: str | None) -> str:
    """worker pane 的初始 prompt(多行结构化, 经 bracketed paste 注入, 窗口可读)。"""
    prompt_file = PROMPTS_DIR / f"{role}.md"
    parts = [
        f"You are the {role} for phase {phase}. Do your role's job, then STOP when your output files are written.",
        f"[ROLE CONTRACT] {prompt_file}",
        f"[TASK BRIEF] {brief}" if brief else "",
        f"[MUST READ — workspace SSOT] {workspace}/REQUIREMENT.md ; {workspace}/SPEC_OVERVIEW.md ; {workspace}/fix_plan.md ; your phase spec under {workspace}/phases/",
        "[EVALUATE] whether /think-map or /think-research helps (per your role contract; evaluate, not forced).",
        "[RULES] Workspace files are the SSOT, your memory is not. Stay within your role's allowed outputs; do not touch files outside them.",
    ]
    return "\n".join(p for p in parts if p)


def launch_role(workspace: Path, slug: str, role: str, role_cfg: dict, phase: str, mode: str, brief: str | None = None) -> str:
    """在用户当前 tmux window split 出一个 role pane(就在当前 tab,不新建 session/tab),
    注入初始 prompt, 注册 SESSIONS.md。返回 pane_id。phase_coder 已存活则复用(L6)。"""
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
    _tmux(["select-pane", "-t", pane, "-T", pane_title(slug, role, phase)])
    time.sleep(1)
    if role_cfg["backend"] == "claude_cli":
        send_to_pane(pane, role_cfg["cmd"])
        consume_claude_trust(pane)
    time.sleep(1)
    send_to_pane(pane, intro)
    _register(workspace, role, phase, pane)
    return pane


def _register(workspace: Path, role: str, phase: str, pane: str, status: str = "running") -> None:
    sessions_path = workspace / "SESSIONS.md"
    text = sessions_path.read_text(encoding="utf-8") if sessions_path.exists() else render_sessions([])
    rows = parse_sessions(text)
    rows = upsert_session(
        rows,
        {"role": role, "phase": phase, "pane_id": pane, "started_at": _now(), "last_seen": _now(), "status": status},
    )
    sessions_path.write_text(render_sessions(rows), encoding="utf-8")


# ---------------------------------------------------------------------------
# 模板
# ---------------------------------------------------------------------------
def default_config_yaml(slug: str) -> str:
    return f"""version: 2

# dev-long-run-v2 角色配置。模型只有 gpt-5.5 + claude-opus-4-8 两个;思考档由模型默认承载:
#   - kilo worker(planner/coder): cliproxy/gpt-5.5, 默认 effort=high(模型默认; kilo TUI 无 --variant flag, 非交互启动用默认)。
#   - claude_cli reviewer: cmd 不传 --model/--effort → claude CLI 默认(Opus 4.8 @ high, 自动跟最新);下方 model 仅记录。
#   - scaffold/loop orchestrator = 用户对话的 agent(无 pane),model 仅占位不生效。
roles:
  scaffold_orchestrator:
    backend: kilo
    model: cliproxy/gpt-5.5     # 不生效(orchestrator = 对话 agent)
    autonomy: medium
  scaffold_reviewer:
    backend: claude_cli
    cmd: 'claude --dangerously-skip-permissions'
    model: claude-opus-4-8      # 仅记录;实际用 claude CLI 默认(Opus 4.8 @ high)
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
  phase_reviewer:
    backend: claude_cli
    cmd: 'claude --dangerously-skip-permissions'
    model: claude-opus-4-8      # 仅记录;实际用 claude CLI 默认(Opus 4.8 @ high)
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
  pane_title_prefix: lr2:{slug}
"""


WORKSPACE_FILES = {
    "SPEC_OVERVIEW.md": "# Spec Overview\n\n(scaffold orchestrator 产出: Task Understanding / Code Facts / 边界)\n",
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
    slug = slugify(name)
    current_branch = _git(repo_root, ["branch", "--show-current"])
    # 强制显式选择 worktree 模式: 不默认, 逼 agent 先问用户(L16/L20)
    if args.new == args.in_place:  # 都没给 或 同时给, 都拒绝
        conflict = args.new and args.in_place
        sys.stderr.write(
            ("both --new and --in-place given; pick one\n" if conflict else
             "worktree 模式未指定 — 请先把下面信息给用户、让用户选,再带 --new 或 --in-place 重跑:\n")
            + f"  当前分支: {current_branch or 'detached HEAD'}\n"
            f"  --new      : 新建隔离 worktree(../<repo>-lr2-{slug}) + 分支 lr2/{slug}\n"
            f"  --in-place : 在当前分支 '{current_branch}' 接着做(main/master 会被拒)\n"
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
        f"  2. Write SPEC_OVERVIEW.md / fix_plan.md / phases/<NN>_<slug>/spec.md into {workspace}.\n"
        f"  3. (optional) launch a reviewer pane: python3 {Path(__file__).resolve()} launch --workspace {workspace} --role scaffold_reviewer\n"
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
        f"  launch planner/coder/reviewer panes via `lr2.py launch --role <r>`,\n"
        f"  send review to coder via `lr2.py send`, commit per phase (L14),\n"
        f"  then ask the user in chat: confirm next / done / block.  See {workspace}/ORCHESTRATOR.md\n"
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
    pane = launch_role(workspace, state["slug"], args.role, config["roles"][args.role], args.phase, mode, brief=args.brief)
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
    send_to_pane(args.pane, args.text)
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


def cmd_pane_alive(args: argparse.Namespace) -> int:
    live = _tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
    return 0 if pane_is_alive(live, args.pane) else 1


def cmd_await(args: argparse.Namespace) -> int:
    """健壮地等 worker 完成: 轮询 status 文件 token + 查 pane 死活 + 有界超时 + 短间隔。
    退出码: 0 DONE / 2 BLOCKED / 3 DEAD(pane 没了) / 4 TIMEOUT / 5 COMPACT。不 grep prose。"""
    status_path = Path(args.status)
    deadline = time.monotonic() + args.timeout
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
        time.sleep(args.interval)
    sys.stdout.write(f"TIMEOUT after {args.timeout}s (status={status_path})\n")
    return 4


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
    for row in parse_sessions((workspace / "SESSIONS.md").read_text(encoding="utf-8")):
        alive = pane_is_alive(live, row["pane_id"])
        sys.stdout.write(f"  {row['role']:18} {row['pane_id']:6} {'ALIVE' if alive else 'DEAD(重开 fresh 读 HANDOFF / 标 failed)'}\n")
    return 0


def _append_log(workspace: Path, msg: str) -> None:
    p = workspace / "logs.md"
    prev = p.read_text(encoding="utf-8") if p.exists() else "# Logs\n"
    p.write_text(prev + f"- {_now()}: {msg}\n", encoding="utf-8")


def cmd_verify(args: argparse.Namespace) -> int:
    """在 worktree 里真跑验证脚本, 把执行证据(exit code + 输出)落成 verify.json/acceptance.json。
    这是"测试只写没跑"的解药: 完成门禁只认这个文件, 不认 coder 自己在 qa.md 的口头声明。"""
    workspace = Path(args.workspace).resolve()
    state = load_state(workspace / "state.json")
    cwd = Path(state.get("worktree_path") or workspace)
    if args.acceptance:
        script, out_path, label = workspace / "acceptance.sh", workspace / "acceptance.json", "acceptance"
    else:
        pdir = workspace / "phases" / args.phase
        script, out_path, label = pdir / "verify.sh", pdir / "verify.json", f"phase {args.phase}"
    if not script.exists():
        sys.stderr.write(f"refusing: {script} 不存在 —— 先写 {label} 的可执行验证脚本(真跑测试/端到端验收)\n")
        return 2
    result = subprocess.run(["bash", str(script)], cwd=str(cwd), text=True, capture_output=True)
    summary = verify_summary(result.returncode, (result.stdout or "") + (result.stderr or ""))
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"{'OK' if summary['ok'] else 'FAIL'} {label} exit={summary['exit']} → {out_path.name}\n")
    return 0 if summary["ok"] else 2


def _phase_gate_for(workspace: Path, phase: str) -> dict:
    pdir = workspace / "phases" / phase
    vj = pdir / "verify.json"
    verify = json.loads(vj.read_text(encoding="utf-8")) if vj.exists() else None
    review = (pdir / "review.md").read_text(encoding="utf-8") if (pdir / "review.md").exists() else ""
    ack = (pdir / "ack.md").read_text(encoding="utf-8") if (pdir / "ack.md").exists() else ""
    return phase_gate(verify, review, ack)


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
    _append_log(workspace, f"phase {args.phase} gate passed → marked complete")
    sys.stdout.write(f"phase {args.phase} 完成(门禁已过, fix_plan 已勾)\n")
    return 0


def cmd_complete_run(args: argparse.Namespace) -> int:
    """过 acceptance 门禁(真跑过 acceptance.sh 且过)才置 state=completed。否则拒绝。"""
    workspace = Path(args.workspace).resolve()
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
    sys.stdout.write("run completed(acceptance 门禁已过)\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lr2", description="dev-long-run-v2 multi-pane orchestration harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scaffold", help="建 worktree+workspace, 启动 scaffold orchestrator")
    p.add_argument("--requirement", required=True)
    p.add_argument("--goal")
    p.add_argument("--name")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--new", action="store_true", help="新建隔离 worktree + lr2/<slug> 分支")
    p.add_argument("--in-place", action="store_true", help="在当前 worktree+分支接着做(L16:当前在 main/master 则拒绝)")
    p.set_defaults(func=cmd_scaffold)

    p = sub.add_parser("develop", help="启动 loop orchestrator 进入开发循环")
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
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("await", help="(orchestrator 调用) 健壮等 worker 完成: 轮询 status 文件 + 查 pane 死活")
    p.add_argument("--status", required=True, help="worker 写的 status 文件路径(phases/<id>/<role>.status)")
    p.add_argument("--pane", help="worker pane id; 给了就每轮查死活, 死了立即 DEAD 退出")
    p.add_argument("--timeout", type=int, default=1800, help="有界超时秒数(默认 1800)")
    p.add_argument("--interval", type=int, default=5, help="轮询间隔秒(默认 5)")
    p.set_defaults(func=cmd_await)

    p = sub.add_parser("sessions", help="打印 SESSIONS.md + pane 存活")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_sessions)

    p = sub.add_parser("pane-alive", help="exit 0 if pane alive else 1")
    p.add_argument("--pane", required=True)
    p.set_defaults(func=cmd_pane_alive)

    p = sub.add_parser("verify", help="在 worktree 真跑 verify.sh/acceptance.sh, 记录执行证据 verify.json")
    p.add_argument("--workspace", required=True)
    p.add_argument("--phase", default="0")
    p.add_argument("--acceptance", action="store_true", help="跑根 acceptance.sh(端到端验收)而非某 phase verify.sh")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("gate", help="只读检查某 phase 是否过完成门禁(verify 过 + blocker 全 fixed)")
    p.add_argument("--workspace", required=True)
    p.add_argument("--phase", required=True)
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("complete-phase", help="过门禁才翻 fix_plan [x](唯一标完成入口); 不过 exit 2 拒绝")
    p.add_argument("--workspace", required=True)
    p.add_argument("--phase", required=True)
    p.set_defaults(func=cmd_complete_phase)

    p = sub.add_parser("complete-run", help="过 acceptance 门禁才置 state=completed")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_complete_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

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
        if role.get("variant") not in VARIANTS:
            raise ValueError(f"role {name}: bad variant {role.get('variant')!r}")
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


# variant 词表(L13)。决策(2026-05-29): TUI 长驻 pane 用默认思考等级, 不按 role 注入 variant;
# 本表仅用于 config 的 variant 字段 enum 校验(意图标注 + typo 卫生), 不再驱动 launch effort。
VARIANTS = ("low", "medium", "high", "xhigh", "max")


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


def split_window_args(target: str, cwd: str, mode: str, command: str | None) -> list[str]:
    """构造 tmux split-window, 捕获新 pane_id。command=None → 默认交互 shell(claude 路径用)。"""
    if mode not in SPLIT_FLAG:
        raise ValueError(f"bad split mode {mode!r}; valid: {', '.join(SPLIT_FLAG)}")
    args = ["split-window", "-t", target, SPLIT_FLAG[mode], "-P", "-F", "#{pane_id}", "-c", cwd]
    if command:
        args.append(command)
    return args


def send_keys_arglists(pane: str, text: str) -> list[list[str]]:
    """L4/send-keys: 先用 -l literal 发文本(防止 $()/反引号被 shell 解释), 再单独发 Enter。

    残余风险见 spec S4(已否决): literal 仍是降暴露而非根除。"""
    return [["send-keys", "-t", pane, "-l", text], ["send-keys", "-t", pane, "Enter"]]


def pane_is_alive(list_panes_output: str, pane_id: str) -> bool:
    """从 `tmux list-panes -aF '#{pane_id}'` 输出判断某 pane 是否还在。"""
    return pane_id in list_panes_output.split()


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


def tmux_session(slug: str) -> str:
    return f"lr2-{slug}"


def pane_title(slug: str, role: str, phase: str) -> str:
    return f"lr2:{slug}:{role}:{phase}"


def capture_pane(pane: str) -> str:
    return _tmux(["capture-pane", "-t", pane, "-p"], capture=True)


def send_to_pane(pane: str, text: str) -> None:
    for arglist in send_keys_arglists(pane, text):
        _tmux(arglist)
        time.sleep(0.4)


def ensure_session(slug: str, cwd: Path, command: str | None) -> str:
    """没有 session 则 new-session(第一个 pane), 返回 pane_id。"""
    sess = tmux_session(slug)
    exists = subprocess.run(["tmux", "has-session", "-t", sess], capture_output=True).returncode == 0
    if exists:
        return ""  # 已存在, 调用方改用 split
    args = ["new-session", "-d", "-P", "-F", "#{pane_id}", "-s", sess, "-x", "220", "-y", "50", "-c", str(cwd)]
    if command:
        args.append(command)
    return _tmux(args, capture=True)


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


def launch_role(workspace: Path, slug: str, role: str, role_cfg: dict, phase: str, mode: str) -> str:
    """起一个 role pane, 注入初始 prompt, 注册 SESSIONS.md。返回 pane_id。"""
    worktree = Path(load_state(workspace / "state.json").get("worktree_path", workspace))
    command = launch_command(role_cfg)
    sess = tmux_session(slug)
    exists = subprocess.run(["tmux", "has-session", "-t", sess], capture_output=True).returncode == 0
    if not exists:
        pane = ensure_session(slug, worktree, command)
    else:
        pane = _tmux(split_window_args(sess, str(worktree), mode, command), capture=True)
    if not pane:
        raise RuntimeError(f"failed to obtain pane_id for role {role}")
    _tmux(["select-pane", "-t", pane, "-T", pane_title(slug, role, phase)])
    time.sleep(1)
    if role_cfg["backend"] == "claude_cli":
        send_to_pane(pane, role_cfg["cmd"])
        consume_claude_trust(pane)
    # 初始 prompt: 让 role 读自己的 prompt 文件 + workspace 上下文
    prompt_file = PROMPTS_DIR / f"{role}.md"
    intro = (
        f"Read {prompt_file} and {workspace}/ORCHESTRATOR.md (if you are an orchestrator) "
        f"or your role section, then act as the {role} for workspace {workspace}. "
        f"Workspace files are the SSOT; your memory is not."
    )
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

# dev-long-run-v2 角色配置。L19: TUI 用默认思考等级, variant 仅意图标注不注入。
roles:
  scaffold_orchestrator:
    backend: kilo
    model: cliproxy/gpt-5.5
    variant: xhigh
    autonomy: medium
  scaffold_reviewer:
    backend: claude_cli
    cmd: 'claude --dangerously-skip-permissions'
    model: claude-opus-4-7
    variant: max
    autonomy: off
  loop_orchestrator:
    backend: kilo
    model: cliproxy/gpt-5.5-fast
    variant: low
    autonomy: medium
  phase_planner:
    backend: kilo
    model: cliproxy/gpt-5.5
    variant: xhigh
    autonomy: low
  phase_coder:
    backend: kilo
    model: cliproxy/gpt-5.5
    variant: high
    autonomy: high
  phase_reviewer:
    backend: claude_cli
    cmd: 'claude --dangerously-skip-permissions'
    model: claude-opus-4-7
    variant: max
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
    date = datetime.now().strftime("%Y%m%d")
    workspace = repo_root / ".long-loop" / f"{date}_{slug}"
    if workspace.exists():
        sys.stderr.write(f"workspace exists: {workspace}\n")
        return 1
    # L16: worktree + 分支; 拒绝在脏 main 上开
    dirty = _git(repo_root, ["status", "--porcelain"])
    branch = branch_name(slug)
    wt = worktree_path(repo_root, slug)
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
        "state": "scaffold", "phase": 0, "role_in_flight": "scaffold_orchestrator",
        "worktree_path": str(wt), "branch": branch, "goal": args.goal or name,
        "repo_root": str(repo_root), "slug": slug, "dirty_main_at_start": bool(dirty),
    }
    save_state(workspace / "state.json", state)
    config = load_yaml((workspace / "config.yaml").read_text(encoding="utf-8"))
    pane = launch_role(workspace, slug, "scaffold_orchestrator", config["roles"]["scaffold_orchestrator"], "0", "split-right")
    sys.stdout.write(
        f"scaffold ready.\n  workspace: {workspace}\n  worktree : {wt}\n  branch   : {branch}\n"
        f"  orch pane: {pane} (tmux attach -t {tmux_session(slug)})\n"
        f"  resume   : lr2.py resume --workspace {workspace}\n"
    )
    if dirty:
        sys.stdout.write("  WARN: main 有未提交改动(已记录), 本流程不会碰 main\n")
    return 0


def cmd_develop(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    state = load_state(workspace / "state.json")
    config = load_yaml((workspace / "config.yaml").read_text(encoding="utf-8"))
    pane = launch_role(workspace, state["slug"], "loop_orchestrator", config["roles"]["loop_orchestrator"], "0", "split-right")
    state["state"] = "develop"
    state["role_in_flight"] = "loop_orchestrator"
    save_state(workspace / "state.json", state)
    sys.stdout.write(f"develop started. loop orch pane: {pane}\n")
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    state = load_state(workspace / "state.json")
    config = load_yaml((workspace / "config.yaml").read_text(encoding="utf-8"))
    if args.role not in config["roles"]:
        sys.stderr.write(f"unknown role {args.role}\n")
        return 1
    mode = args.mode or ("split-down" if "reviewer" in args.role else "split-right")
    pane = launch_role(workspace, state["slug"], args.role, config["roles"][args.role], args.phase, mode)
    sys.stdout.write(pane + "\n")
    return 0


def cmd_send(args: argparse.Namespace) -> int:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lr2", description="dev-long-run-v2 multi-pane orchestration harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scaffold", help="建 worktree+workspace, 启动 scaffold orchestrator")
    p.add_argument("--requirement", required=True)
    p.add_argument("--goal")
    p.add_argument("--name")
    p.add_argument("--repo-root", default=".")
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
    p.set_defaults(func=cmd_launch)

    p = sub.add_parser("send", help="(orchestrator 调用) literal send-keys 到 pane")
    p.add_argument("--pane", required=True)
    p.add_argument("--text", required=True)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("sessions", help="打印 SESSIONS.md + pane 存活")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_sessions)

    p = sub.add_parser("pane-alive", help="exit 0 if pane alive else 1")
    p.add_argument("--pane", required=True)
    p.set_defaults(func=cmd_pane_alive)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

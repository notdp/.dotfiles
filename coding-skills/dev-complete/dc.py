#!/usr/bin/env python3
"""dev-complete 控制核心：dev-long-run 的单 pass 精简版。

import lr 复用 pane 管理（bracketed paste、idle detection、session tracking），
自有 scaffold/verify/complete 逻辑。spec: 见 SKILL.md。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# lr.py 复用
_LR_DIR = Path(__file__).resolve().parent.parent / "dev-long-run"
sys.path.insert(0, str(_LR_DIR))
import lr  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = SKILL_DIR / "prompts"

ROLES = ("coder", "reviewer_a", "reviewer_b")
REVIEWER_ROLES = ("reviewer_a", "reviewer_b")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
def default_config_yaml() -> str:
    return """version: 2

# dev-complete: 单 pass 完备开发。coder=kilo+gpt, reviewer=kilo(A)+CC(B)。
roles:
  coder:
    backend: kilo
    model: cliproxy/gpt-5.5
    autonomy: high
  reviewer_a:
    backend: kilo
    model: cliproxy/gpt-5.5
    autonomy: off
  reviewer_b:
    backend: claude_cli
    model: claude-opus-4-6
    autonomy: off
    cmd: 'claude --dangerously-skip-permissions'
"""


def validate_config(config: dict) -> dict:
    if config.get("version") != 2:
        raise ValueError(f"config version must be 2, got {config.get('version')!r}")
    roles = config.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("config.roles must be a mapping")
    missing = [r for r in ROLES if r not in roles]
    if missing:
        raise ValueError(f"config.roles missing: {', '.join(missing)}")
    for name, role in roles.items():
        if role.get("backend") not in lr.BACKENDS:
            raise ValueError(f"role {name}: unknown backend {role.get('backend')!r}")
        if role.get("autonomy") not in lr.AUTONOMY:
            raise ValueError(f"role {name}: bad autonomy {role.get('autonomy')!r}")
        if role["backend"] == "claude_cli" and not role.get("cmd"):
            raise ValueError(f"role {name}: claude_cli backend requires 'cmd'")
    return config


# ---------------------------------------------------------------------------
# workspace 模板
# ---------------------------------------------------------------------------
WORKSPACE_FILES: dict[str, str] = {
    "REQUIREMENT.md": "",
    "spec.md": "# Spec\n\n(orchestrator 写)\n",
    "qa.md": "# QA\n\n## 自动化验证\n\n## 人工验证\n",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# scaffold
# ---------------------------------------------------------------------------
def cmd_scaffold(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    req_path = Path(args.requirement).resolve()
    if not req_path.exists():
        sys.stderr.write(f"REQUIREMENT 文件不存在: {req_path}\n")
        return 1
    name = args.name or req_path.stem
    slug = lr.slugify(name)

    if args.new and args.in_place:
        sys.stderr.write("--new 和 --in-place 互斥，只能选一个\n")
        return 2

    if not args.new and not args.in_place:
        branch = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "--show-current"],
            text=True, capture_output=True,
        ).stdout.strip()
        sys.stderr.write(
            f"请选择工作模式:\n"
            f"  当前分支: {branch or '(detached HEAD)'}\n"
            f"  --new      : 新建隔离 worktree(../<repo>-lr-{slug}) + 分支 lr/{slug}\n"
            f"  --in-place : 在当前分支 + 当前目录接着做\n"
        )
        return 2

    plan = lr.plan_worktree(repo_root, slug, in_place=args.in_place,
                            current_branch=subprocess.run(
                                ["git", "-C", str(repo_root), "branch", "--show-current"],
                                text=True, capture_output=True,
                            ).stdout.strip())

    ws_dir = repo_root / ".long-loop" / f"{datetime.now().strftime('%Y%m%d')}_{slug}"
    ws_dir.mkdir(parents=True, exist_ok=True)

    if plan["create"]:
        wt = Path(plan["worktree_path"])
        if not wt.exists():
            subprocess.run(["git", "-C", str(repo_root), "worktree", "add",
                            "-b", plan["branch"], str(wt)], check=True, capture_output=True)

    state = {
        "skill": "dev-complete",
        "state": "scaffold",
        "slug": slug,
        "repo_root": str(repo_root),
        "worktree_path": plan["worktree_path"],
        "branch": plan["branch"],
        "workspace": str(ws_dir),
        "created_at": _now(),
    }
    lr.save_state(ws_dir / "state.json", state)

    (ws_dir / "config.yaml").write_text(default_config_yaml(), encoding="utf-8")
    (ws_dir / "SESSIONS.md").write_text(lr.render_sessions([]), encoding="utf-8")

    req_content = req_path.read_text(encoding="utf-8")
    (ws_dir / "REQUIREMENT.md").write_text(req_content, encoding="utf-8")
    for name_f, content in WORKSPACE_FILES.items():
        p = ws_dir / name_f
        if not p.exists():
            p.write_text(content, encoding="utf-8")

    goal = args.goal or "(见 REQUIREMENT.md)"
    sys.stdout.write(
        f"workspace: {ws_dir}\n"
        f"worktree:  {plan['worktree_path']}\n"
        f"branch:    {plan['branch']}\n"
        f"goal:      {goal}\n"
        f"\nNext (act as orchestrator yourself):\n"
        f"  1. Write spec.md + qa.md in workspace\n"
        f"  2. Show user for approval\n"
        f"  3. dc.py launch --workspace {ws_dir} --role coder\n"
    )
    return 0


# ---------------------------------------------------------------------------
# launch
# ---------------------------------------------------------------------------
def _prompt_file(role: str) -> Path:
    base = role.replace("_a", "").replace("_b", "") if role in REVIEWER_ROLES else role
    return PROMPTS_DIR / f"{base}.md"


def _role_intro(role: str, workspace: Path, brief: str | None) -> str:
    prompt_file = _prompt_file(role)
    header = f"You are the {role} for this task."
    parts = [
        header + " Do your role's job, then STOP when your output files are written.",
        f"[ROLE CONTRACT] {prompt_file}",
        f"[TASK BRIEF] {brief}" if brief else "",
        f"[MUST READ — workspace SSOT] {workspace}/REQUIREMENT.md ; {workspace}/spec.md ; {workspace}/qa.md",
        f"[WORKSPACE] {workspace}",
    ]
    if role in REVIEWER_ROLES:
        label = role.split("_")[-1]  # "a" or "b"
        parts.append(f"[OUTPUT FILE — write your review here] {workspace}/review_{label}.md")
        parts.append(f"[STATUS FILE — write 'done' here when finished] {workspace}/reviewer_{label}.status")
    elif role == "coder":
        parts.append(f"[STATUS FILE] {workspace}/coder.status")
    parts.extend([
        "[EVALUATE] whether /think-map or /think-research helps (evaluate, not forced).",
        "[RULES] Workspace files are the SSOT, your memory is not. Stay within your role's allowed outputs.",
    ])
    return "\n".join(p for p in parts if p)


def _load_config(workspace: Path) -> dict:
    text = (workspace / "config.yaml").read_text(encoding="utf-8")
    return validate_config(lr.load_yaml(text))


def cmd_launch(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    role = args.role
    if role not in ROLES:
        sys.stderr.write(f"unknown role {role!r}, expected one of {ROLES}\n")
        return 1
    config = _load_config(workspace)
    role_cfg = config["roles"][role]
    state = lr.load_state(workspace / "state.json")
    worktree = Path(state.get("worktree_path", workspace))

    intro = _role_intro(role, workspace, args.brief if hasattr(args, "brief") else None)

    if not os.environ.get("TMUX"):
        raise RuntimeError("不在 tmux 里")

    command = lr.launch_command(role_cfg)
    current_pane = os.environ.get("TMUX_PANE")
    mode = args.mode if hasattr(args, "mode") and args.mode else "split-right"
    pane = lr._tmux(lr.split_window_args(str(worktree), mode, command, target=current_pane), capture=True)
    if not pane:
        raise RuntimeError(f"failed to obtain pane_id for role {role}")

    title = f"dc {role}"
    lr._tmux(["select-pane", "-t", pane, "-T", title])
    lr._tmux(["set-option", "-pt", pane, "@notify_tmux_title_pane_name", title])
    time.sleep(1)

    if role_cfg["backend"] == "claude_cli":
        lr.send_to_pane(pane, role_cfg["cmd"])
        lr.consume_claude_trust(pane)
    elif role_cfg["backend"] == "kilo":
        lr.wait_kilo_ready(pane)
    else:
        time.sleep(1)

    lr.send_to_pane(pane, intro)
    _register(workspace, role, pane)
    sys.stdout.write(f"pane={pane} role={role}\n")
    return 0


def _register(workspace: Path, role: str, pane: str) -> None:
    sessions_path = workspace / "SESSIONS.md"
    text = sessions_path.read_text(encoding="utf-8") if sessions_path.exists() else lr.render_sessions([])
    rows = lr.parse_sessions(text)
    if os.environ.get("TMUX"):
        live = lr._tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
        rows, _ = lr.reconcile_dead_sessions(rows, live, _now())
    rows = lr.upsert_session(rows, {
        "role": role, "phase": "0", "pane_id": pane,
        "started_at": _now(), "last_seen": _now(), "status": "running",
    })
    sessions_path.write_text(lr.render_sessions(rows), encoding="utf-8")


# ---------------------------------------------------------------------------
# send / close / await / sessions / reset-status
# ---------------------------------------------------------------------------
def cmd_send(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    sessions_path = workspace / "SESSIONS.md"
    rows = lr.parse_sessions(sessions_path.read_text(encoding="utf-8")) if sessions_path.exists() else []
    if not lr.pane_registered(rows, args.pane):
        sys.stderr.write(f"pane {args.pane} 不在 SESSIONS.md 注册表\n")
        return 1
    lr.send_to_pane(args.pane, args.text)
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    closed = lr._close_roles(workspace, (args.role,))
    sys.stdout.write(f"closed: {closed}\n")
    return 0


def cmd_await(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    role = args.role
    status_path = workspace / f"{role}.status"
    pane = args.pane
    timeout = getattr(args, "timeout", 600)
    idle_timeout = getattr(args, "idle_timeout", 120)

    deadline = time.time() + timeout
    last_change = time.time()
    prev_screen = ""

    while time.time() < deadline:
        if not lr.pane_is_alive(
            lr._tmux(["list-panes", "-aF", "#{pane_id}"], capture=True), pane
        ):
            tail = lr.capture_pane(pane) if False else "(pane dead)"
            sys.stderr.write(f"DEAD: {role} pane {pane} 已退出\n{tail}\n")
            return 3

        if status_path.exists():
            raw = status_path.read_text(encoding="utf-8").strip().split("\n")[0].strip()
            state, detail = lr.parse_worker_status(raw)
            if state == "done":
                sys.stdout.write(f"DONE: {role} {raw}\n")
                return 0
            if state == "blocked":
                sys.stderr.write(f"BLOCKED: {role} {raw}\n")
                return 2
            if state == "compact":
                sys.stderr.write(f"COMPACT: {role} 需要 fresh pane\n")
                return 5

        screen = lr.capture_pane(pane)
        if screen != prev_screen:
            prev_screen = screen
            last_change = time.time()
        elif lr.pane_looks_idle(screen) and time.time() - last_change > idle_timeout:
            tail = screen[-500:] if screen else ""
            sys.stderr.write(f"IDLE: {role} pane {pane} 静默超过 {idle_timeout}s\npane tail:\n{tail}\n")
            return 6

        time.sleep(5)

    screen = lr.capture_pane(pane)
    tail = screen[-500:] if screen else ""
    sys.stderr.write(f"TIMEOUT: {role} 超过 {timeout}s\npane tail:\n{tail}\n")
    return 4


def cmd_sessions(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    sessions_path = workspace / "SESSIONS.md"
    if not sessions_path.exists():
        sys.stdout.write("(no sessions)\n")
        return 0
    rows = lr.parse_sessions(sessions_path.read_text(encoding="utf-8"))
    if os.environ.get("TMUX"):
        live = lr._tmux(["list-panes", "-aF", "#{pane_id}"], capture=True)
        rows, reconciled = lr.reconcile_dead_sessions(rows, live, _now())
        if reconciled:
            sessions_path.write_text(lr.render_sessions(rows), encoding="utf-8")
    for r in rows:
        sys.stdout.write(f"  {r['role']:20s} pane={r['pane_id']}  {r['status']}\n")
    return 0


def cmd_reset_status(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    status_path = workspace / f"{args.role}.status"
    status_path.write_text("coding\n", encoding="utf-8")
    return 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
def cmd_verify(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    state = lr.load_state(workspace / "state.json")
    worktree = Path(state.get("worktree_path", workspace))
    verify_sh = workspace / "verify.sh"
    if not verify_sh.exists():
        sys.stderr.write(f"verify.sh 不存在: {verify_sh}\n")
        return 1

    result = subprocess.run(
        ["bash", str(verify_sh)],
        cwd=str(worktree),
        text=True,
        capture_output=True,
        timeout=getattr(args, "timeout", 300),
    )
    output = (result.stdout or "") + (result.stderr or "")
    summary = lr.verify_summary(result.returncode, output)

    json_path = workspace / "verify.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if summary["ok"]:
        sys.stdout.write("verify: PASS\n")
        return 0
    else:
        sys.stderr.write(f"verify: FAIL (exit {result.returncode})\n")
        sys.stderr.write(output[-1000:] + "\n")
        return 1


# ---------------------------------------------------------------------------
# complete (gate)
# ---------------------------------------------------------------------------
def _parse_ack_resolutions(ack_text: str, review_texts: dict[str, str]) -> tuple[list[str], list[str]]:
    """从 ack.md 解析 blocker 裁决，对照 review 中的 blocker ID。
    复用 lr.parse_ack_resolutions（限定 ## Blocker Resolutions section）。
    返回 (unresolved_ids, errors)。"""
    blocker_ids: list[str] = []
    for label, text in review_texts.items():
        for m in re.finditer(r"\[blocker\s+(B\d+)\]", text, re.IGNORECASE):
            bid = f"{label}:{m.group(1)}"
            if bid not in blocker_ids:
                blocker_ids.append(bid)

    res = lr.parse_ack_resolutions(ack_text)
    errors: list[str] = []

    _rejected_no_reason = re.compile(r"^\s*-\s*\[rejected\]\s*[A-Za-z0-9:_-]*\s*$", re.IGNORECASE)
    for ln in res.get("rejected_lines", []):
        if _rejected_no_reason.match(ln):
            errors.append(f"[rejected] 缺理由: {ln.strip()!r}")

    resolved_lines = res["fixed_lines"] + res.get("rejected_lines", [])
    unresolved = [bid for bid in blocker_ids
                  if not any(re.search(rf"\b{re.escape(bid)}\b", ln) for ln in resolved_lines)]
    return unresolved, errors


def cmd_complete(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    state = lr.load_state(workspace / "state.json")
    blocks: list[str] = []

    # 1. verify.json
    vj = workspace / "verify.json"
    if not vj.exists():
        blocks.append("verify.json 不存在：先跑 dc.py verify")
    else:
        vdata = json.loads(vj.read_text(encoding="utf-8"))
        if not vdata.get("ok"):
            blocks.append("verify.json.ok=false：verify.sh 未通过")

    # 2. review 存在
    review_a = workspace / "review_a.md"
    review_b = workspace / "review_b.md"
    has_review = (review_a.exists() and review_a.stat().st_size > 10) or \
                 (review_b.exists() and review_b.stat().st_size > 10)
    if not has_review:
        blocks.append("review_a.md 和 review_b.md 都不存在或为空")

    # 3. ack + blocker 裁决
    ack_path = workspace / "ack.md"
    if has_review:
        if not ack_path.exists():
            blocks.append("ack.md 不存在")
        else:
            ack_text = ack_path.read_text(encoding="utf-8")
            review_texts = {}
            if review_a.exists():
                review_texts["A"] = review_a.read_text(encoding="utf-8")
            if review_b.exists():
                review_texts["B"] = review_b.read_text(encoding="utf-8")
            unresolved, errors = _parse_ack_resolutions(ack_text, review_texts)
            for uid in unresolved:
                blocks.append(f"blocker {uid} 未裁决(ack.md 缺 [fixed] 或 [rejected])")
            for err in errors:
                blocks.append(err)

    # 4. commit 证据
    status_path = workspace / "coder.status"
    if status_path.exists():
        raw = status_path.read_text(encoding="utf-8").strip().split("\n")[0].strip()
        m = re.search(r"commit=([0-9a-fA-F]{6,40})\b", raw)
        commit_hash = m.group(1) if m else None
        if not commit_hash:
            blocks.append("coder.status 缺 commit=<hash>")
        else:
            worktree = Path(state.get("worktree_path", workspace))
            ret = subprocess.run(
                ["git", "-C", str(worktree), "rev-parse", "--verify", commit_hash],
                capture_output=True,
            )
            if ret.returncode != 0:
                blocks.append(f"commit {commit_hash} 不在 worktree 分支上")
    else:
        blocks.append("coder.status 不存在")

    if blocks:
        sys.stderr.write("BLOCKED — 门禁未通过:\n")
        for b in blocks:
            sys.stderr.write(f"  • {b}\n")
        return 2

    state["state"] = "completed"
    state["completed_at"] = _now()
    lr.save_state(workspace / "state.json", state)

    # teardown: 关所有 worker pane
    lr._close_roles(workspace, ROLES)

    sys.stdout.write("COMPLETE — 门禁通过, state=completed\n")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dc", description="dev-complete: 单 pass 完备开发 harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scaffold", help="建 workspace, 进入 scaffold 流程")
    p.add_argument("--requirement", required=True)
    p.add_argument("--goal")
    p.add_argument("--name")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--new", action="store_true")
    p.add_argument("--in-place", action="store_true")
    p.set_defaults(func=cmd_scaffold)

    p = sub.add_parser("launch", help="开 role pane")
    p.add_argument("--workspace", required=True)
    p.add_argument("--role", required=True, choices=ROLES)
    p.add_argument("--mode", default="split-right")
    p.add_argument("--brief")
    p.set_defaults(func=cmd_launch)

    p = sub.add_parser("send", help="发消息到 pane")
    p.add_argument("--workspace", required=True)
    p.add_argument("--pane", required=True)
    p.add_argument("--text", required=True)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("close", help="关 role pane")
    p.add_argument("--workspace", required=True)
    p.add_argument("--role", required=True)
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("await", help="等 role 完成")
    p.add_argument("--workspace", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--pane", required=True)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--idle-timeout", type=int, default=120)
    p.set_defaults(func=cmd_await)

    p = sub.add_parser("sessions", help="查看 pane 注册表")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_sessions)

    p = sub.add_parser("reset-status", help="重置 role status")
    p.add_argument("--workspace", required=True)
    p.add_argument("--role", required=True)
    p.set_defaults(func=cmd_reset_status)

    p = sub.add_parser("verify", help="跑 verify.sh")
    p.add_argument("--workspace", required=True)
    p.add_argument("--timeout", type=int, default=300)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("complete", help="门禁 gate")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=cmd_complete)

    parsed = parser.parse_args(argv)
    return parsed.func(parsed)


if __name__ == "__main__":
    sys.exit(main())

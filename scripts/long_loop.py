#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DIR = ".long-loop"
STATE_VERSION = 1


@dataclass(frozen=True)
class LoopPaths:
    root: Path

    @property
    def prompt(self) -> Path:
        return self.root / "PROMPT.md"

    @property
    def spec(self) -> Path:
        return self.root / "SPEC.md"

    @property
    def plan(self) -> Path:
        return self.root / "IMPLEMENTATION_PLAN.md"

    @property
    def assert_file(self) -> Path:
        return self.root / "ASSERT.md"

    @property
    def progress(self) -> Path:
        return self.root / "progress.md"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def state(self) -> Path:
        return self.root / "state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_log_path(paths: LoopPaths) -> Path:
    return paths.logs / f"{datetime.now().strftime('%Y-%m-%d')}.md"


def read_state(paths: LoopPaths) -> dict:
    if not paths.state.exists():
        raise RuntimeError(f"missing state file: {paths.state}")
    return json.loads(paths.state.read_text(encoding="utf-8"))


def write_state(paths: LoopPaths, state: dict) -> None:
    paths.state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(paths: LoopPaths, title: str, body: str) -> None:
    paths.logs.mkdir(parents=True, exist_ok=True)
    entry = f"\n## {now_iso()} — {title}\n\n{body.strip()}\n"
    log_path = today_log_path(paths)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def require_workspace(paths: LoopPaths) -> None:
    missing = [
        path
        for path in [paths.prompt, paths.spec, paths.plan, paths.assert_file, paths.progress, paths.state]
        if not path.exists()
    ]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise RuntimeError(f"long-loop workspace incomplete: {names}")


def initial_state(goal: str) -> dict:
    return {
        "version": STATE_VERSION,
        "goal": goal,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "iterations": 0,
        "failure_count": 0,
        "status": "awaiting_approval",
        "approval": "pending",
        "current_item": None,
        "last_event": "planned",
        "paused_reason": None,
        "stop_reason": None,
        "last_exit_code": None,
        "last_validation": None,
    }


def template_prompt(goal: str) -> str:
    return f"""# Long Loop Prompt

Goal: {goal}

Read these files before acting:

- `.long-loop/IMPLEMENTATION_PLAN.md`
- `.long-loop/ASSERT.md`
- `.long-loop/progress.md`

Rules:

0. Do not execute unless `.long-loop/state.json` is approved.
1. Pick exactly one highest-priority unchecked item from `IMPLEMENTATION_PLAN.md`.
2. Before editing, search the repository; do not assume the item is not already implemented.
3. Implement the item fully. Do not add placeholder or toy implementations.
4. Run the smallest relevant validation from `ASSERT.md`.
5. Update `IMPLEMENTATION_PLAN.md` and `progress.md` with what changed.
6. Do not push. If remote side effects are needed, stop and ask for `guard-gitops`.
7. Do not put status reports into this file.
"""


def template_spec(goal: str) -> str:
    return f"""# Long Loop Spec

## Goal

{goal}

## Boundaries

- Do not expand scope beyond the implementation plan.
- Do not push, deploy, modify databases, or touch third-party systems without explicit approval.

## Acceptance

- Required checks in `.long-loop/ASSERT.md` pass.
- Each completed item updates `.long-loop/progress.md`.

## Budget

- Default max iterations: 1
- Default max minutes: 30
"""


def template_plan(goal: str) -> str:
    return f"""# Implementation Plan

Goal: {goal}

## Todo

- [ ] Replace this item with the first concrete task.

## Notes

- Keep each item independently verifiable.
- One loop may complete only one item.
"""


def template_assert() -> str:
    return """# Assertions

## Budget

- approval_required: true
- max_iterations: 1
- max_minutes: 30
- default_push: false

## Required validation

- `scripts/run-verify.sh`
- `scripts/scan_diff_residue.py`

## Boundaries

- Do not push by default.
- Do not modify production, deployment, databases, secrets, or third-party systems.
- Stop if product judgment or external authorization is required.
"""


def template_progress(goal: str) -> str:
    return f"""# Progress

Goal: {goal}

## Current status

- State: awaiting_approval
- Last loop: none
- Next step: review `SPEC.md`, `IMPLEMENTATION_PLAN.md`, and `ASSERT.md`; then run `approve`.
"""


def init_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    if paths.root.exists() and any(paths.root.iterdir()) and not args.force:
        raise RuntimeError(f"{paths.root} already exists and is not empty; use --force to overwrite")
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(parents=True, exist_ok=True)
    paths.prompt.write_text(template_prompt(args.goal), encoding="utf-8")
    paths.spec.write_text(template_spec(args.goal), encoding="utf-8")
    paths.plan.write_text(template_plan(args.goal), encoding="utf-8")
    paths.assert_file.write_text(template_assert(), encoding="utf-8")
    paths.progress.write_text(template_progress(args.goal), encoding="utf-8")
    write_state(paths, initial_state(args.goal))
    append_log(paths, "planned", f"Goal: {args.goal}")
    sys.stdout.write(f"planned long-loop workspace at {paths.root}; run approve before run\n")
    return 0


def format_status(paths: LoopPaths, state: dict) -> str:
    remaining, done = count_todos(paths)
    return "\n".join(
        [
            "## Long Loop Status",
            "",
            f"- workspace: `{paths.root}`",
            f"- goal: {state.get('goal')}",
            f"- status: {state.get('status')}",
            f"- approval: {state.get('approval')}",
            f"- iterations: {state.get('iterations')}",
            f"- failure_count: {state.get('failure_count')}",
            f"- remaining_todo: {remaining}",
            f"- done_todo: {done}",
            f"- current_item: {state.get('current_item')}",
            f"- last_event: {state.get('last_event')}",
            f"- stop_reason: {state.get('stop_reason')}",
            f"- paused_reason: {state.get('paused_reason')}",
            f"- last_validation: {state.get('last_validation')}",
        ]
    )


def count_todos(paths: LoopPaths) -> tuple[int, int]:
    plan_text = paths.plan.read_text(encoding="utf-8") if paths.plan.exists() else ""
    remaining = sum(1 for line in plan_text.splitlines() if line.strip().startswith("- [ ]"))
    done = sum(1 for line in plan_text.splitlines() if line.strip().startswith("- [x]"))
    return remaining, done


def status_payload(paths: LoopPaths, state: dict) -> dict:
    remaining, done = count_todos(paths)
    return {
        "workspace": str(paths.root),
        "goal": state.get("goal"),
        "status": state.get("status"),
        "approval": state.get("approval"),
        "iterations": state.get("iterations"),
        "failure_count": state.get("failure_count"),
        "remaining_todo": remaining,
        "done_todo": done,
        "current_item": state.get("current_item"),
        "last_event": state.get("last_event"),
        "last_validation": state.get("last_validation"),
        "stop_reason": state.get("stop_reason"),
        "paused_reason": state.get("paused_reason"),
    }


def status_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    require_workspace(paths)
    state = read_state(paths)
    if args.json:
        sys.stdout.write(json.dumps(status_payload(paths, state), ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(format_status(paths, state) + "\n")
    return 0


def next_command_for_state(state: dict) -> str:
    status = state.get("status")
    if status == "awaiting_approval":
        return "scripts/long_loop.py approve"
    if status == "approved":
        return 'scripts/long_loop.py run --once --agent-cmd "..."'
    if status == "running":
        return "scripts/long_loop.py status"
    if status == "paused":
        return "edit .long-loop files, then scripts/long_loop.py approve"
    if status == "stopped":
        return "scripts/long_loop.py status"
    if status == "done":
        return "none"
    return "scripts/long_loop.py status"


def format_current_state(paths: LoopPaths) -> str:
    if not paths.state.exists():
        return ""
    state = read_state(paths)
    return f"""## Current workspace

- Current state: {state.get("status")}
- Approval: {state.get("approval")}
- Remaining todo: {count_todos(paths)[0] if paths.plan.exists() else "unknown"}
- Next command: `{next_command_for_state(state)}`

"""


def format_help_guide(paths: LoopPaths) -> str:
    return f"""# Long Loop Help

{format_current_state(paths)}
## Most common path

1. plan: create `.long-loop/` files
2. edit/review: check `SPEC.md`, `IMPLEMENTATION_PLAN.md`, `ASSERT.md`
3. approve: unlock execution
4. run: execute bounded iterations
5. status/tail/watch: observe progress
6. pause: intervene, edit files, approve again

## State Flow

```text
plan -> awaiting_approval -> approve -> approved -> run -> running
running -> stopped     [max iterations, max minutes, validation failure]
running -> done        [no remaining todo]
running -> pause -> paused -> edit plan -> approve -> approved
stopped -> approve -> approved -> resume -> running
```

## Command map

| Need | Command |
|---|---|
| Start a long task | `scripts/long_loop.py plan --goal "..."` |
| Unlock execution | `scripts/long_loop.py approve` |
| Run one bounded loop | `scripts/long_loop.py run --once --agent-cmd "..."` |
| Check state | `scripts/long_loop.py status` |
| Machine-readable state | `scripts/long_loop.py status --json` |
| Read recent logs | `scripts/long_loop.py tail --lines 80` |
| Watch progress | `scripts/long_loop.py watch --interval 10` |
| Intervene | `scripts/long_loop.py pause --reason "..."` |
| Stop | `scripts/long_loop.py stop --reason "..."` |
"""


def help_workspace(args: argparse.Namespace) -> int:
    sys.stdout.write(format_help_guide(LoopPaths(Path(args.dir))))
    return 0


def tail_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    require_workspace(paths)
    log_files = sorted(paths.logs.glob("*.md"))
    if not log_files:
        return 0
    lines: list[str] = []
    for log_file in log_files:
        lines.extend(log_file.read_text(encoding="utf-8").splitlines())
    output = "\n".join(lines[-args.lines :])
    sys.stdout.write(output + ("\n" if output else ""))
    return 0


def watch_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    require_workspace(paths)
    index = 0
    while args.iterations is None or index < args.iterations:
        if index:
            time.sleep(args.interval)
        state = read_state(paths)
        sys.stdout.write(format_status(paths, state) + "\n")
        log_files = sorted(paths.logs.glob("*.md"))
        if log_files:
            recent_lines = log_files[-1].read_text(encoding="utf-8").splitlines()[-5:]
            sys.stdout.write("\n## Recent Log\n\n" + "\n".join(recent_lines) + "\n")
        index += 1
    return 0


def stop_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    require_workspace(paths)
    state = read_state(paths)
    state.update(
        {
            "status": "stopped",
            "stop_reason": args.reason,
            "updated_at": now_iso(),
        }
    )
    write_state(paths, state)
    append_log(paths, "stopped", args.reason)
    sys.stdout.write(f"stopped: {args.reason}\n")
    return 0


def approve_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    require_workspace(paths)
    state = read_state(paths)
    state.update(
        {
            "status": "approved",
            "approval": "approved",
            "paused_reason": None,
            "stop_reason": None,
            "last_event": "approved",
            "updated_at": now_iso(),
        }
    )
    write_state(paths, state)
    append_log(paths, "approved", "Plan approved for execution.")
    sys.stdout.write("approved long-loop plan\n")
    return 0


def pause_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    require_workspace(paths)
    state = read_state(paths)
    state.update(
        {
            "status": "paused",
            "approval": "pending",
            "paused_reason": args.reason,
            "last_event": "paused",
            "updated_at": now_iso(),
        }
    )
    write_state(paths, state)
    append_log(paths, "paused", args.reason)
    sys.stdout.write(f"paused: {args.reason}\n")
    return 0


def run_shell(command: str, *, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, input=stdin, text=True, shell=True, capture_output=True, check=False)


def run_validation(repo_root: Path) -> tuple[bool, str]:
    verify = run_shell(f'"{repo_root / "scripts/run-verify.sh"}" "{repo_root}"')
    if verify.returncode != 0:
        return False, verify.stdout + verify.stderr
    residue = run_shell(f'"{repo_root / "scripts/scan_diff_residue.py"}"')
    if residue.returncode != 0:
        return False, residue.stdout + residue.stderr
    return True, verify.stdout + "\n" + residue.stdout


def run_loop(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    require_workspace(paths)
    if not args.agent_cmd:
        raise RuntimeError("run requires --agent-cmd")

    repo_root = Path.cwd()
    max_iterations = 1 if args.once else args.max_iterations
    if max_iterations < 1:
        raise RuntimeError("--max-iterations must be >= 1")

    state = read_state(paths)
    if state.get("approval") != "approved" or state.get("status") not in {"approved", "running"}:
        raise RuntimeError("long-loop plan is not approved; run approve before run")

    state["status"] = "running"
    state["last_event"] = "run_started"
    state["stop_reason"] = None
    state["updated_at"] = now_iso()
    write_state(paths, state)

    started_at = time.monotonic()
    for _ in range(max_iterations):
        remaining, _done = count_todos(paths)
        if remaining == 0:
            state = read_state(paths)
            state["status"] = "done"
            state["stop_reason"] = "plan complete"
            state["last_event"] = "done"
            state["updated_at"] = now_iso()
            write_state(paths, state)
            append_log(paths, "done", "No unchecked plan items remain.")
            sys.stdout.write(format_status(paths, state) + "\n")
            return 0
        if args.max_minutes is not None and time.monotonic() - started_at >= args.max_minutes * 60:
            state = read_state(paths)
            state["status"] = "stopped"
            state["stop_reason"] = "max minutes reached"
            state["last_event"] = "stopped"
            state["updated_at"] = now_iso()
            write_state(paths, state)
            append_log(paths, "stopped", "max minutes reached")
            sys.stdout.write(format_status(paths, state) + "\n")
            return 0
        prompt = paths.prompt.read_text(encoding="utf-8")
        result = run_shell(args.agent_cmd, stdin=prompt)
        state = read_state(paths)
        state["iterations"] = int(state.get("iterations", 0)) + 1
        state["last_exit_code"] = result.returncode
        state["last_event"] = "iteration_finished"
        state["updated_at"] = now_iso()
        append_log(
            paths,
            f"iteration {state['iterations']}",
            f"agent_cmd: `{args.agent_cmd}`\n\nexit_code: {result.returncode}\n\nstdout:\n\n```text\n{result.stdout[-4000:]}\n```\n\nstderr:\n\n```text\n{result.stderr[-4000:]}\n```",
        )

        if result.returncode != 0:
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["status"] = "stopped"
            state["stop_reason"] = "agent command failed"
            state["last_event"] = "stopped"
            write_state(paths, state)
            sys.stdout.write("agent command failed\n")
            return result.returncode or 1

        ok, validation_output = run_validation(repo_root)
        state["last_validation"] = "pass" if ok else "fail"
        append_log(paths, "judge", validation_output[-6000:])
        if not ok:
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["status"] = "stopped"
            state["stop_reason"] = "judge validation failed"
            state["last_event"] = "stopped"
            write_state(paths, state)
            sys.stdout.write(validation_output)
            return 1

        state["failure_count"] = 0
        state["status"] = "running"
        write_state(paths, state)

    state["status"] = "stopped"
    state["stop_reason"] = "max iterations reached"
    state["last_event"] = "stopped"
    state["updated_at"] = now_iso()
    write_state(paths, state)
    sys.stdout.write(format_status(paths, state) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a .long-loop workspace.")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="Long-loop workspace directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a long-loop workspace.")
    init.add_argument("--goal", required=True)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=init_workspace)

    plan = subparsers.add_parser("plan", help="Create an approval-gated long-loop plan.")
    plan.add_argument("--goal", required=True)
    plan.add_argument("--force", action="store_true")
    plan.set_defaults(func=init_workspace)

    status = subparsers.add_parser("status", help="Print workspace status.")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=status_workspace)

    help_parser = subparsers.add_parser("help", help="Print long-loop workflow help.")
    help_parser.set_defaults(func=help_workspace)

    tail = subparsers.add_parser("tail", help="Print recent append-only log lines.")
    tail.add_argument("--lines", type=int, default=80)
    tail.set_defaults(func=tail_workspace)

    watch = subparsers.add_parser("watch", help="Refresh status and recent logs.")
    watch.add_argument("--interval", type=float, default=10)
    watch.add_argument("--iterations", type=int, default=None)
    watch.set_defaults(func=watch_workspace)

    stop = subparsers.add_parser("stop", help="Mark workspace stopped.")
    stop.add_argument("--reason", required=True)
    stop.set_defaults(func=stop_workspace)

    approve = subparsers.add_parser("approve", help="Approve a long-loop plan for execution.")
    approve.set_defaults(func=approve_workspace)

    pause = subparsers.add_parser("pause", help="Pause execution for human intervention.")
    pause.add_argument("--reason", required=True)
    pause.set_defaults(func=pause_workspace)

    run = subparsers.add_parser("run", help="Run one or more bounded iterations.")
    run.add_argument("--agent-cmd")
    run.add_argument("--once", action="store_true")
    run.add_argument("--max-iterations", type=int, default=1)
    run.add_argument("--max-minutes", type=int, default=None)
    run.set_defaults(func=run_loop)

    resume = subparsers.add_parser("resume", help="Alias for run after re-approval.")
    resume.add_argument("--agent-cmd")
    resume.add_argument("--once", action="store_true")
    resume.add_argument("--max-iterations", type=int, default=1)
    resume.add_argument("--max-minutes", type=int, default=None)
    resume.set_defaults(func=run_loop)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

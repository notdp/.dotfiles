#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
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
    def specs(self) -> Path:
        return self.root / "specs"

    @property
    def main_spec(self) -> Path:
        return self.specs / "main.md"

    @property
    def plan(self) -> Path:
        return self.root / "IMPLEMENTATION_PLAN.md"

    @property
    def fix_plan(self) -> Path:
        return self.root / "fix_plan.md"

    @property
    def assert_file(self) -> Path:
        return self.root / "ASSERT.md"

    @property
    def validator(self) -> Path:
        return self.root / "validator.md"

    @property
    def validator_results(self) -> Path:
        return self.root / "validator-results.json"

    @property
    def progress(self) -> Path:
        return self.root / "progress.md"

    @property
    def events(self) -> Path:
        return self.root / "events.jsonl"

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


def append_event(paths: LoopPaths, event: dict) -> None:
    payload = {"ts": now_iso(), **event}
    with paths.events.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_log_block(paths: LoopPaths, *, iteration: int, event: str, summary: str, body: str) -> None:
    paths.logs.mkdir(parents=True, exist_ok=True)
    title = f"{now_iso()} | iteration-{iteration} | {event} | {summary}"
    with today_log_path(paths).open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {title}\n\n{body.strip()}\n")


def require_workspace(paths: LoopPaths) -> None:
    if not paths.state.exists():
        raise RuntimeError(f"missing state file: {paths.state}")
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

- `.long-loop/specs/main.md`
- `.long-loop/fix_plan.md`
- `.long-loop/validator.md`
- `.long-loop/progress.md`

Rules:

0. Do not execute unless `.long-loop/state.json` is approved.
1. Pick exactly one highest-priority item from `fix_plan.md`.
2. Before editing, search the repository; do not assume the item is not already implemented.
3. Implement the item fully. Do not add placeholder or toy implementations.
4. Run the item validator from `validator.md`; if it fails, fix it in the same iteration.
5. Update `fix_plan.md` and `progress.md` with what changed.
6. End each iteration with a concise stage summary: plan item, action, validation, state, next step.
7. Do not push. If remote side effects are needed, stop and ask for `guard-gitops`.
8. Do not put status reports into this file.
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


def template_fix_plan(goal: str) -> str:
    return f"""# Fix Plan

Goal: {goal}

## Active

### P0: Replace this item with the first concrete task.
- Status: pending
- Why: Initial placeholder created by `plan`; replace before running a real loop.
- Evidence needed: Item-specific validator passes.
- Validator: `.long-loop/validator.md`
- Notes: Keep learnings here, not in status reports.

## Backlog

- Empty.
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


def template_validator() -> str:
    return """# Validator

## Purpose

Validate the selected `fix_plan.md` item with the smallest meaningful command before full guards run.

## Item validator

- `scripts/run-verify.sh`

## Full guard

- `scripts/run-verify.sh`
- `scripts/scan_diff_residue.py`

## Evidence format

- command
- exit_code
- duration_sec
- stdout_tail
- stderr_tail
"""


def template_progress(goal: str) -> str:
    return f"""# Progress

Goal: {goal}

## Current status

- State: awaiting_approval
- Last loop: none
- Next step: review `SPEC.md`, `IMPLEMENTATION_PLAN.md`, and `ASSERT.md`; then run `approve`.

## Stage summaries

- No iterations yet.
"""


def append_stage_summary(paths: LoopPaths, summary: str) -> None:
    with paths.progress.open("a", encoding="utf-8") as handle:
        handle.write("\n" + summary.strip() + "\n")
    append_log(paths, "stage summary", summary)


def format_iteration_summary(
    *,
    iteration: int,
    plan_item: str,
    agent_ok: bool,
    verify_ok: bool | None,
    status: str,
    next_step: str,
) -> str:
    verify_text = "not run" if verify_ok is None else ("pass" if verify_ok else "fail")
    return "\n".join(
        [
            f"## Iteration {iteration} Summary",
            "",
            f"- Plan item: {plan_item}",
            f"- Agent: {'pass' if agent_ok else 'fail'}",
            f"- Verify: {verify_text}",
            f"- State: {status}",
            f"- Next: {next_step}",
        ]
    )


def init_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(Path(args.dir))
    if paths.root.exists() and any(paths.root.iterdir()) and not args.force:
        raise RuntimeError(f"{paths.root} already exists and is not empty; use --force to overwrite")
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.specs.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(parents=True, exist_ok=True)
    paths.prompt.write_text(template_prompt(args.goal), encoding="utf-8")
    paths.spec.write_text(template_spec(args.goal), encoding="utf-8")
    paths.main_spec.write_text(template_spec(args.goal), encoding="utf-8")
    paths.plan.write_text(template_plan(args.goal), encoding="utf-8")
    paths.fix_plan.write_text(template_fix_plan(args.goal), encoding="utf-8")
    paths.assert_file.write_text(template_assert(), encoding="utf-8")
    paths.validator.write_text(template_validator(), encoding="utf-8")
    paths.validator_results.write_text("[]\n", encoding="utf-8")
    paths.events.write_text("", encoding="utf-8")
    paths.progress.write_text(template_progress(args.goal), encoding="utf-8")
    write_state(paths, initial_state(args.goal))
    append_event(paths, {"iteration": 0, "event": "plan-created", "item": None, "summary": args.goal})
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
    if paths.fix_plan.exists():
        text = paths.fix_plan.read_text(encoding="utf-8")
        remaining = len(re.findall(r"(?m)^- Status: (pending|in_progress|blocked)$", text))
        done = len(re.findall(r"(?m)^- Status: done$", text))
        return remaining, done
    plan_text = paths.plan.read_text(encoding="utf-8") if paths.plan.exists() else ""
    remaining = sum(1 for line in plan_text.splitlines() if line.strip().startswith("- [ ]"))
    done = sum(1 for line in plan_text.splitlines() if line.strip().startswith("- [x]"))
    return remaining, done


def next_plan_item(paths: LoopPaths) -> str:
    if paths.fix_plan.exists():
        text = paths.fix_plan.read_text(encoding="utf-8")
        current_title = "none"
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("### "):
                current_title = stripped.removeprefix("### ").strip()
            if stripped in {"- Status: pending", "- Status: in_progress", "- Status: blocked"}:
                return current_title
        return "none"
    plan_text = paths.plan.read_text(encoding="utf-8") if paths.plan.exists() else ""
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            return stripped.removeprefix("- [ ]").strip()
    return "none"


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


def validator_commands(paths: LoopPaths) -> list[str]:
    if not paths.validator.exists():
        raise RuntimeError(f"missing validator file: {paths.validator}")
    commands: list[str] = []
    in_item_validator = False
    for line in paths.validator.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_item_validator = stripped == "## Item validator"
            continue
        if not in_item_validator:
            continue
        commands.extend(re.findall(r"`([^`]+)`", stripped))
    return commands


def append_validator_result(paths: LoopPaths, result: dict) -> None:
    payload = []
    if paths.validator_results.exists():
        text = paths.validator_results.read_text(encoding="utf-8").strip()
        payload = json.loads(text) if text else []
    payload.append(result)
    paths.validator_results.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_item_validator(paths: LoopPaths, *, iteration: int, item: str) -> tuple[bool, str]:
    commands = validator_commands(paths)
    if not commands:
        raise RuntimeError("missing item validator command in validator.md")
    outputs: list[str] = []
    ok = True
    for command in commands:
        started = time.monotonic()
        result = run_shell(command)
        duration = round(time.monotonic() - started, 3)
        command_ok = result.returncode == 0
        ok = ok and command_ok
        payload = {
            "ts": now_iso(),
            "iteration": iteration,
            "item": item,
            "command": command,
            "exit_code": result.returncode,
            "duration_sec": duration,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
        }
        append_validator_result(paths, payload)
        outputs.append(result.stdout + result.stderr)
        event = "validator-pass" if command_ok else "validator-fail"
        append_event(
            paths,
            {
                "iteration": iteration,
                "event": event,
                "item": item,
                "command": command,
                "exit_code": result.returncode,
                "duration_sec": duration,
            },
        )
        append_log_block(
            paths,
            iteration=iteration,
            event=event,
            summary=item[:80],
            body=f"command: `{command}`\n\nexit_code: {result.returncode}\n\nduration_sec: {duration}\n\nstdout_tail:\n\n```text\n{result.stdout[-2000:]}\n```\n\nstderr_tail:\n\n```text\n{result.stderr[-2000:]}\n```",
        )
    return ok, "\n".join(outputs)


def latest_stage_summary(paths: LoopPaths) -> str:
    if not paths.progress.exists():
        return "none"
    lines = paths.progress.read_text(encoding="utf-8").splitlines()
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].startswith("## Iteration "):
            return "\n".join(lines[index : index + 8])
    return "none"


def build_iteration_context(paths: LoopPaths, item: str) -> str:
    sections = [
        "# Fresh Iteration Context",
        "",
        "Use only this compact context plus fresh code search. Do not rely on prior conversation memory.",
        "",
        "## Runtime prompt",
        paths.prompt.read_text(encoding="utf-8"),
        "## Specs",
        paths.main_spec.read_text(encoding="utf-8") if paths.main_spec.exists() else paths.spec.read_text(encoding="utf-8"),
        "## Selected fix_plan.md item",
        item,
        "## fix_plan.md",
        paths.fix_plan.read_text(encoding="utf-8") if paths.fix_plan.exists() else paths.plan.read_text(encoding="utf-8"),
        "## validator.md",
        paths.validator.read_text(encoding="utf-8"),
        "## Previous stage summary",
        latest_stage_summary(paths),
        "## Mandatory fresh search",
        "Before editing, search the repository for the selected item and verify it is not already implemented.",
    ]
    return "\n".join(sections)


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
        plan_item = next_plan_item(paths)
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
        state = read_state(paths)
        state["current_item"] = plan_item
        state["updated_at"] = now_iso()
        write_state(paths, state)

        iteration = int(state.get("iterations", 0)) + 1
        append_event(paths, {"iteration": iteration, "event": "iteration-start", "item": plan_item})
        run_item_validator(paths, iteration=iteration, item=plan_item)

        context = build_iteration_context(paths, plan_item)
        result = run_shell(args.agent_cmd, stdin=context)
        state = read_state(paths)
        state["iterations"] = iteration
        state["last_exit_code"] = result.returncode
        state["last_event"] = "iteration_finished"
        state["updated_at"] = now_iso()
        append_event(
            paths,
            {
                "iteration": iteration,
                "event": "implementation-summary",
                "item": plan_item,
                "command": args.agent_cmd,
                "exit_code": result.returncode,
            },
        )
        append_log_block(
            paths,
            iteration=iteration,
            event="implementation-summary",
            summary=plan_item[:80],
            body=f"agent_cmd: `{args.agent_cmd}`\n\nexit_code: {result.returncode}\n\nstdout_tail:\n\n```text\n{result.stdout[-2000:]}\n```\n\nstderr_tail:\n\n```text\n{result.stderr[-2000:]}\n```",
        )

        if result.returncode != 0:
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["status"] = "stopped"
            state["stop_reason"] = "agent command failed"
            state["last_event"] = "stopped"
            write_state(paths, state)
            summary = format_iteration_summary(
                iteration=state["iterations"],
                plan_item=plan_item,
                agent_ok=False,
                verify_ok=None,
                status=state["status"],
                next_step="inspect agent failure, update plan, then approve before resume",
            )
            append_stage_summary(paths, summary)
            append_event(paths, {"iteration": iteration, "event": "iteration-summary", "item": plan_item, "verdict": "agent-fail"})
            sys.stdout.write(summary + "\n")
            sys.stdout.write("agent command failed\n")
            return result.returncode or 1

        item_ok, item_validation_output = run_item_validator(paths, iteration=iteration, item=plan_item)
        ok = item_ok
        validation_output = item_validation_output
        if ok:
            ok, validation_output = run_validation(repo_root)
        state["last_validation"] = "pass" if ok else "fail"
        append_log_block(
            paths,
            iteration=iteration,
            event="full-guard" if ok else "validator-fail",
            summary=plan_item[:80],
            body=validation_output[-4000:],
        )
        if not ok:
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["status"] = "stopped"
            state["stop_reason"] = "judge validation failed"
            state["last_event"] = "stopped"
            write_state(paths, state)
            summary = format_iteration_summary(
                iteration=iteration,
                plan_item=plan_item,
                agent_ok=True,
                verify_ok=False,
                status=state["status"],
                next_step="fix validation failure, update plan, then approve before resume",
            )
            append_stage_summary(paths, summary)
            append_event(paths, {"iteration": iteration, "event": "iteration-summary", "item": plan_item, "verdict": "validator-fail"})
            sys.stdout.write(summary + "\n")
            sys.stdout.write(validation_output)
            return 1

        state["failure_count"] = 0
        state["status"] = "running"
        write_state(paths, state)
        summary = format_iteration_summary(
            iteration=iteration,
            plan_item=plan_item,
            agent_ok=True,
            verify_ok=True,
            status=state["status"],
            next_step="continue if budget remains, otherwise inspect status",
        )
        append_stage_summary(paths, summary)
        append_event(paths, {"iteration": iteration, "event": "iteration-summary", "item": plan_item, "verdict": "pass"})
        sys.stdout.write(summary + "\n")

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

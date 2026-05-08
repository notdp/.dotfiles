#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import secrets
import selectors
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DIR = ".long-loop"
GITIGNORE_ENTRY = ".long-loop/"
STATE_VERSION = 1
V2_STATE_VERSION = 2
HARNESS_CREATED_BY = "dev-long-loop-harness"
VALID_PLAN_STATUSES = {"pending", "in_progress", "done", "blocked"}


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
    def spec_overview(self) -> Path:
        return self.root / "SPEC_OVERVIEW.md"

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
    def qa(self) -> Path:
        return self.root / "qa.md"

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
    def logs_md(self) -> Path:
        return self.root / "logs.md"

    @property
    def runtime_log(self) -> Path:
        return self.root / "runtime.log"

    @property
    def phases(self) -> Path:
        return self.root / "phases"

    @property
    def state(self) -> Path:
        return self.root / "state.json"


@dataclass(frozen=True)
class PlanItem:
    title: str
    status: str
    phase: str

    def as_context(self) -> str:
        return "\n".join(
            [
                f"### {self.title}",
                f"- Status: {self.status}",
                f"- Phase: {self.phase}",
            ]
        )


@dataclass(frozen=True)
class AgentRunResult:
    returncode: int
    output: str
    timed_out: bool = False


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_log_path(paths: LoopPaths) -> Path:
    return paths.logs / f"{datetime.now().strftime('%Y-%m-%d')}.md"


def slugify_goal(goal: str) -> str:
    parts: list[str] = []
    last_was_separator = False
    for char in goal.strip().lower():
        if char.isalnum():
            parts.append(char)
            last_was_separator = False
        elif char.isspace() or char in {"-", "_"}:
            if parts and not last_was_separator:
                parts.append("-")
                last_was_separator = True
    slug = "".join(parts).strip("-")
    return slug or "task"


def dated_workspace_name(goal: str) -> str:
    return f"{datetime.now().strftime('%Y-%m-%d')}_{slugify_goal(goal)}"


def next_available_workspace(base_dir: Path, goal: str, *, force: bool) -> Path:
    name = dated_workspace_name(goal)
    root = base_dir / name
    if force:
        return root
    candidate = root
    suffix = 2
    while candidate.exists() and any(candidate.iterdir()):
        candidate = base_dir / f"{name}-{suffix}"
        suffix += 1
    return candidate


def resolve_workspace_root(raw_dir: str) -> Path:
    root = Path(raw_dir)
    if (root / "state.json").exists():
        return root
    return root


def plan_workspace_root(args: argparse.Namespace) -> Path:
    base_dir = Path(args.dir)
    if args.dir == DEFAULT_DIR:
        return next_available_workspace(base_dir, args.goal, force=args.force)
    return base_dir


def gitignore_has_long_loop(lines: list[str]) -> bool:
    accepted = {".long-loop", ".long-loop/", "/.long-loop", "/.long-loop/"}
    return any(line.strip() in accepted for line in lines if not line.lstrip().startswith("#"))


def ensure_gitignore_ignores_long_loop(repo_root: Path) -> None:
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(GITIGNORE_ENTRY + "\n", encoding="utf-8")
        return
    text = gitignore.read_text(encoding="utf-8")
    lines = text.splitlines()
    if gitignore_has_long_loop(lines):
        return
    prefix = text
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    gitignore.write_text(prefix + GITIGNORE_ENTRY + "\n", encoding="utf-8")


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
        "status": "ready",
        "current_item": None,
        "last_event": "planned",
        "paused_reason": None,
        "stop_reason": None,
        "last_exit_code": None,
        "last_validation": None,
    }


def template_prompt(goal: str, workspace: str) -> str:
    return f"""# Long Loop Prompt

Goal: {goal}

Read these files before acting:

- `{workspace}/specs/main.md`
- `{workspace}/fix_plan.md`
- `{workspace}/validator.md`
- `{workspace}/progress.md`

Rules:

0. Execute only from a ready, paused, stopped, or running long-loop workspace.
1. Pick exactly one highest-priority item from `fix_plan.md`.
2. Before editing, search the repository; do not assume the item is not already implemented.
3. Implement the item fully. Do not add placeholder or toy implementations.
4. Run the item validator from `validator.md`; if it fails, fix it in the same iteration.
5. Update `fix_plan.md` and `progress.md` with what changed.
6. End each iteration with a concise stage summary: plan item, action, validation, state, next step.
7. Do not push. If remote side effects are needed, stop and ask for `guard-gitops`.
8. Do not put status reports into this file.
"""


def template_spec(goal: str, workspace: str) -> str:
    return f"""# Long Loop Spec

## Goal

{goal}

## Boundaries

- Do not expand scope beyond the implementation plan.
- Do not push, deploy, modify databases, or touch third-party systems without explicit approval.

## Acceptance

- Required checks in `{workspace}/ASSERT.md` pass.
- Each completed item updates `{workspace}/progress.md`.

## Budget

- Default max iterations: 1
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


def template_fix_plan(goal: str, workspace: str) -> str:
    return f"""# Fix Plan

Goal: {goal}

## Active

### P0: Replace this item with the first concrete task.
- Status: pending
- Why: Initial placeholder created by `plan`; replace before running a real loop.
- Evidence needed: Item-specific validator passes.
- Validator: `{workspace}/validator.md`
- Notes: Keep learnings here, not in status reports.

## Backlog

- Empty.
"""


def template_assert() -> str:
    return """# Assertions

## Budget

- max_iterations: 1
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

- State: ready
- Last loop: none
- Next step: review `SPEC.md`, `IMPLEMENTATION_PLAN.md`, and `ASSERT.md`; then run `run`.

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


def format_review_bundle(paths: LoopPaths) -> str:
    files = [
        ("SPEC.md", paths.spec),
        ("IMPLEMENTATION_PLAN.md", paths.plan),
        ("fix_plan.md", paths.fix_plan),
        ("ASSERT.md", paths.assert_file),
        ("validator.md", paths.validator),
    ]
    sections = [
        "# Long Loop Review",
        "",
        f"Workspace: `{paths.root}`",
        "",
        "Review the generated plan below. If it looks good, run the loop command directly.",
    ]
    for label, path in files:
        sections.extend(
            [
                "",
                f"## {label}",
                "",
                "```markdown",
                path.read_text(encoding="utf-8").strip(),
                "```",
            ]
        )
    sections.extend(
        [
            "",
            f"Next: review the plan above, then run `{harness_invocation()} run --dir {paths.root} --once --agent-cmd \"...\"`.",
            "",
        ]
    )
    return "\n".join(sections)


def init_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(plan_workspace_root(args))
    if paths.root.exists() and any(paths.root.iterdir()) and not args.force:
        raise RuntimeError(f"{paths.root} already exists and is not empty; use --force to overwrite")
    if args.dir == DEFAULT_DIR:
        ensure_gitignore_ignores_long_loop(Path.cwd())
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.specs.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(parents=True, exist_ok=True)
    workspace = str(paths.root)
    paths.prompt.write_text(template_prompt(args.goal, workspace), encoding="utf-8")
    paths.spec.write_text(template_spec(args.goal, workspace), encoding="utf-8")
    paths.main_spec.write_text(template_spec(args.goal, workspace), encoding="utf-8")
    paths.plan.write_text(template_plan(args.goal), encoding="utf-8")
    paths.fix_plan.write_text(template_fix_plan(args.goal, workspace), encoding="utf-8")
    paths.assert_file.write_text(template_assert(), encoding="utf-8")
    paths.validator.write_text(template_validator(), encoding="utf-8")
    paths.validator_results.write_text("[]\n", encoding="utf-8")
    paths.events.write_text("", encoding="utf-8")
    paths.progress.write_text(template_progress(args.goal), encoding="utf-8")
    write_state(paths, initial_state(args.goal))
    append_event(paths, {"iteration": 0, "event": "plan-created", "item": None, "summary": args.goal})
    append_log(paths, "planned", f"Goal: {args.goal}")
    sys.stdout.write(format_review_bundle(paths))
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


def parse_fix_plan_items(text: str) -> list[PlanItem]:
    items: list[PlanItem] = []
    title: str | None = None
    status = ""
    phase = ""

    def flush() -> None:
        if title:
            items.append(PlanItem(title=title, status=status, phase=phase))

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            flush()
            title = stripped.removeprefix("### ").strip()
            status = ""
            phase = ""
            continue
        if stripped.startswith("- Status:"):
            status = stripped.removeprefix("- Status:").strip()
            continue
        if stripped.startswith("- Phase:"):
            phase = stripped.removeprefix("- Phase:").strip()
    flush()
    return items


def plan_items(paths: LoopPaths) -> list[PlanItem]:
    if not paths.fix_plan.exists():
        return []
    return parse_fix_plan_items(paths.fix_plan.read_text(encoding="utf-8"))


def invalid_plan_statuses(paths: LoopPaths) -> list[str]:
    statuses = []
    for item in plan_items(paths):
        if item.status not in VALID_PLAN_STATUSES:
            statuses.append(f"{item.title}: {item.status or '<missing>'}")
    return statuses


def require_valid_plan_statuses(paths: LoopPaths) -> None:
    invalid = invalid_plan_statuses(paths)
    if invalid:
        raise RuntimeError(
            "invalid fix_plan status; allowed statuses are pending, in_progress, done, blocked: "
            + "; ".join(invalid)
        )


def count_todos(paths: LoopPaths) -> tuple[int, int]:
    if paths.fix_plan.exists():
        require_valid_plan_statuses(paths)
        items = plan_items(paths)
        remaining = sum(1 for item in items if item.status in {"pending", "in_progress", "blocked"})
        done = sum(1 for item in items if item.status == "done")
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
            if stripped in {"- Status: pending", "- Status: in_progress"}:
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
    paths = LoopPaths(resolve_workspace_root(args.dir))
    require_workspace(paths)
    state = read_state(paths)
    if args.json:
        sys.stdout.write(json.dumps(status_payload(paths, state), ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(format_status(paths, state) + "\n")
    return 0


def tail_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(resolve_workspace_root(args.dir))
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
    paths = LoopPaths(resolve_workspace_root(args.dir))
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
    paths = LoopPaths(resolve_workspace_root(args.dir))
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


def pause_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(resolve_workspace_root(args.dir))
    require_workspace(paths)
    state = read_state(paths)
    state.update(
        {
            "status": "paused",
            "paused_reason": args.reason,
            "last_event": "paused",
            "updated_at": now_iso(),
        }
    )
    write_state(paths, state)
    append_log(paths, "paused", args.reason)
    sys.stdout.write(f"paused: {args.reason}\n")
    return 0


def run_shell(command: str, *, stdin: str | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, input=stdin, text=True, shell=True, cwd=cwd, capture_output=True, check=False)


def run_agent_command(
    command: str,
    *,
    stdin: str,
    cwd: Path,
    paths: LoopPaths,
    idle_timeout_seconds: int,
) -> AgentRunResult:
    started = now_iso()
    paths.runtime_log.parent.mkdir(parents=True, exist_ok=True)
    runtime_input = paths.root / "runtime-input.md"
    runtime_input.write_text(stdin, encoding="utf-8")
    output_chunks: list[str] = []
    with paths.runtime_log.open("a", encoding="utf-8") as runtime:
        runtime.write(f"\n## {started} | agent command\n\n$ {command}\n\n")
        runtime.flush()
        input_handle = runtime_input.open("r", encoding="utf-8")
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdin=input_handle,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        selector = selectors.DefaultSelector()
        try:
            if process.stdout is not None:
                selector.register(process.stdout, selectors.EVENT_READ)
            last_output_at = time.monotonic()
            while True:
                if process.poll() is not None:
                    if process.stdout is not None:
                        remainder = process.stdout.read()
                        if remainder:
                            output_chunks.append(remainder)
                            runtime.write(remainder)
                    break
                events = selector.select(timeout=0.1)
                if events:
                    for key, _ in events:
                        line = key.fileobj.readline()
                        if not line:
                            continue
                        output_chunks.append(line)
                        runtime.write(line)
                        runtime.flush()
                        last_output_at = time.monotonic()
                        state = read_state(paths)
                        state["last_heartbeat_at"] = now_iso()
                        write_state(paths, state)
                    continue
                if idle_timeout_seconds > 0 and time.monotonic() - last_output_at > idle_timeout_seconds:
                    process.kill()
                    process.wait()
                    message = f"\nagent command idle timeout after {idle_timeout_seconds}s\n"
                    output_chunks.append(message)
                    runtime.write(message)
                    runtime.flush()
                    return AgentRunResult(returncode=124, output="".join(output_chunks), timed_out=True)
        finally:
            input_handle.close()
            selector.close()
    return AgentRunResult(returncode=process.returncode or 0, output="".join(output_chunks), timed_out=False)


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
    paths = LoopPaths(resolve_workspace_root(args.dir))
    require_workspace(paths)
    if not args.agent_cmd:
        raise RuntimeError("run requires --agent-cmd")

    repo_root = Path.cwd()
    max_iterations = 1 if args.once else args.max_iterations
    if max_iterations < 1:
        raise RuntimeError("--max-iterations must be >= 1")

    state = read_state(paths)
    if state.get("status") not in {"ready", "paused", "stopped", "running"}:
        raise RuntimeError("long-loop workspace is not runnable; create a plan first or inspect status")

    state["status"] = "running"
    state["last_event"] = "run_started"
    state["stop_reason"] = None
    state["updated_at"] = now_iso()
    write_state(paths, state)

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
                next_step="inspect agent failure, update plan, then resume",
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
                next_step="fix validation failure, update plan, then resume",
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


def v2_initial_state(goal: str, token_budget: str) -> dict:
    return {
        "version": V2_STATE_VERSION,
        "created_by": HARNESS_CREATED_BY,
        "state_schema": "dev-long-loop/v2",
        "workspace_token": secrets.token_urlsafe(16),
        "goal": goal,
        "status": "ready",
        "iterations": 0,
        "failure_count": 0,
        "token_budget": token_budget,
        "repo_root": str(Path.cwd().resolve()),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "iteration_started_at": None,
        "last_heartbeat_at": None,
        "last_exit_code": None,
        "last_validation": None,
        "stop_reason": None,
    }


def v2_template_prompt(goal: str, workspace: str, token_budget: str) -> str:
    return f"""# Long Loop Prompt

Goal: {goal}
Workspace: {workspace}
Token budget: {token_budget}

You are running a Ralph Loop style long task. The filesystem is the source of truth. Every loop starts fresh, so reread these files before acting:

- `SPEC_OVERVIEW.md`
- `fix_plan.md`
- `qa.md`
- recent `logs.md`

## Loop Rules

1. Pick exactly one highest-priority item from `fix_plan.md` with `Status: pending` or `Status: in_progress`. If the highest-priority item is blocked, stop and report the blocker instead of editing.
2. Before editing, search the repository and update the phase `research.md` using `/think-research` discipline: record code facts, uncertainty, and evidence paths.
3. Update the phase `plan.md` using `/think-plan` discipline: scope, files, steps, validation, and rollback notes.
4. Update the phase `qa.md`; the phase is not complete until this QA is satisfied.
5. Implement the item fully. Do not add placeholder, toy, or fake implementations.
6. Run the phase QA and then repository validators when available.
7. Use `/guard-close` discipline before ending: stop scope creep, move unrelated work to backlog, and decide whether this item is done.
8. Update `fix_plan.md` immediately after the item state changes.
9. Append a concise entry to `logs.md` with: item, actions, validation evidence, risks, and next step.
10. Do not write status reports into `PROMPT.md`.
11. Do not push, deploy, modify databases, or touch third-party systems.
"""


def v2_template_spec_overview(goal: str, token_budget: str) -> str:
    return f"""# Spec Overview

## Goal

{goal}

## Token Budget

- Budget: {token_budget}
- The budget is a pressure limit for focus. Prefer direct code evidence and staged execution over broad wandering.

## Task Understanding

- Replace this starter section with the full requirement after discussing or inferring the real task from user context.
- Challenge unreasonable requirements when code facts do not support them.

## Code Facts

- Pending research.

## Non-goals

- Do not expand scope beyond `fix_plan.md`.
- Do not push, deploy, modify databases, secrets, or third-party systems.

## Phases

1. `phases/01_initial/`: replace with the first concrete phase.

## Overall Verification

- Root `qa.md` must pass.
- Each completed phase must satisfy its own `phases/*/qa.md`.
"""


def v2_template_fix_plan(goal: str) -> str:
    return f"""# Fix Plan

Goal: {goal}

## Active

### P0: Replace this item with the first concrete phase.
- Status: pending
- Phase: phases/01_initial
- Evidence needed: Phase QA passes and logs.md records validation evidence.
- QA: phases/01_initial/qa.md

## Backlog

- Empty.
"""


def v2_template_qa() -> str:
    return """# Overall QA

## End-to-end checks

- [ ] Define at least one user-story or behavior-level acceptance path.
- [ ] Run repository validators when available.
- [ ] Confirm every done item in `fix_plan.md` has evidence in `logs.md`.
- [ ] Confirm no unrelated scope was implemented.

## Commands

- `scripts/run-verify.sh`
- `scripts/scan_diff_residue.py`
"""


def v2_template_logs(goal: str) -> str:
    return f"""# Logs

Append-only log for: {goal}

## {now_iso()} | plan-created

- Workspace created.
- Replace starter spec, QA, and phase files before trusting long-loop output.
"""


def v2_template_phase_file(title: str, body: str) -> str:
    return f"# {title}\n\n{body.strip()}\n"


def v2_format_review_bundle(paths: LoopPaths) -> str:
    files = [
        ("SPEC_OVERVIEW.md", paths.spec_overview),
        ("fix_plan.md", paths.fix_plan),
        ("qa.md", paths.qa),
        ("PROMPT.md", paths.prompt),
    ]
    sections = [
        "# Long Loop Review",
        "",
        f"Workspace: `{paths.root}`",
        "",
        "Review and enrich these files with code-aware context before running the loop.",
    ]
    for label, path in files:
        sections.extend(["", f"## {label}", "", "```markdown", path.read_text(encoding="utf-8").strip(), "```"])
    sections.extend(
        [
            "",
            f"Next: `{harness_invocation()} run --dir {paths.root} --repo-root {shlex.quote(str(Path.cwd().resolve()))} --max-iterations 3 --idle-timeout-seconds 300 --agent-cmd \"...\"`",
            "",
        ]
    )
    return "\n".join(sections)


def harness_invocation() -> str:
    script = Path(sys.argv[0]).resolve()
    return f"python3 {shlex.quote(str(script))}"


def v2_plan_workspace(args: argparse.Namespace) -> int:
    token_budget = args.token_budget
    paths = LoopPaths(plan_workspace_root(args))
    if paths.root.exists() and any(paths.root.iterdir()) and not args.force:
        raise RuntimeError(f"{paths.root} already exists and is not empty; use --force to overwrite")
    if args.dir == DEFAULT_DIR:
        ensure_gitignore_ignores_long_loop(Path.cwd())
    paths.root.mkdir(parents=True, exist_ok=True)
    phase = paths.phases / "01_initial"
    phase.mkdir(parents=True, exist_ok=True)
    paths.prompt.write_text(v2_template_prompt(args.goal, str(paths.root), token_budget), encoding="utf-8")
    paths.spec_overview.write_text(v2_template_spec_overview(args.goal, token_budget), encoding="utf-8")
    paths.fix_plan.write_text(v2_template_fix_plan(args.goal), encoding="utf-8")
    paths.qa.write_text(v2_template_qa(), encoding="utf-8")
    paths.logs_md.write_text(v2_template_logs(args.goal), encoding="utf-8")
    (phase / "spec.md").write_text(v2_template_phase_file("Phase Spec", "Replace with concrete phase task, boundaries, and todo checklist."), encoding="utf-8")
    (phase / "qa.md").write_text(v2_template_phase_file("Phase QA", "- [ ] Define phase acceptance checks.\n- [ ] Record validation evidence in root `logs.md`."), encoding="utf-8")
    (phase / "research.md").write_text(v2_template_phase_file("Phase Research", "Pending `/think-research` style code research."), encoding="utf-8")
    (phase / "plan.md").write_text(v2_template_phase_file("Phase Plan", "Pending `/think-plan` style implementation plan."), encoding="utf-8")
    write_state(paths, v2_initial_state(args.goal, token_budget))
    sys.stdout.write(v2_format_review_bundle(paths))
    return 0


def v2_require_workspace(paths: LoopPaths) -> None:
    missing = [
        path
        for path in [paths.prompt, paths.spec_overview, paths.fix_plan, paths.qa, paths.logs_md, paths.state, paths.phases]
        if not path.exists()
    ]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise RuntimeError(f"long-loop workspace incomplete: {names}")


def v2_require_harness_state(state: dict) -> None:
    if state.get("version") != V2_STATE_VERSION or state.get("created_by") != HARNESS_CREATED_BY or not state.get("workspace_token"):
        raise RuntimeError("long-loop workspace was not created by dev-long-loop plan")


STARTER_MARKERS = (
    "Replace this starter section",
    "Pending research.",
    "Replace this item with",
    "Define at least one user-story",
    "Replace with concrete phase",
    "Pending `/think-research`",
    "Pending `/think-plan`",
    "Define phase acceptance checks",
)


def v2_starter_placeholder_files(paths: LoopPaths) -> list[Path]:
    files = [
        paths.spec_overview,
        paths.fix_plan,
        paths.qa,
        paths.phases / "01_initial" / "spec.md",
        paths.phases / "01_initial" / "qa.md",
        paths.phases / "01_initial" / "research.md",
        paths.phases / "01_initial" / "plan.md",
    ]
    matches: list[Path] = []
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in STARTER_MARKERS):
            matches.append(path)
    return matches


def v2_require_ready_workspace(paths: LoopPaths) -> None:
    matches = v2_starter_placeholder_files(paths)
    if matches:
        names = ", ".join(str(path.relative_to(paths.root)) for path in matches)
        raise RuntimeError(f"long-loop workspace still contains starter placeholders: {names}")


def v2_status_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(resolve_workspace_root(args.dir))
    v2_require_workspace(paths)
    state = read_state(paths)
    v2_require_harness_state(state)
    require_valid_plan_statuses(paths)
    remaining, done = count_todos(paths)
    sys.stdout.write(
        "\n".join(
            [
                "## Long Loop Status",
                "",
                f"- workspace: `{paths.root}`",
                f"- goal: {state.get('goal')}",
                f"- status: {state.get('status')}",
                f"- iterations: {state.get('iterations')}",
                f"- failure_count: {state.get('failure_count')}",
                f"- token_budget: {state.get('token_budget')}",
                f"- remaining_todo: {remaining}",
                f"- done_todo: {done}",
                f"- last_exit_code: {state.get('last_exit_code')}",
                f"- last_validation: {state.get('last_validation')}",
                f"- stop_reason: {state.get('stop_reason')}",
                "",
            ]
        )
    )
    return 0


def v2_tail_workspace(args: argparse.Namespace) -> int:
    paths = LoopPaths(resolve_workspace_root(args.dir))
    v2_require_workspace(paths)
    v2_require_harness_state(read_state(paths))
    lines = paths.logs_md.read_text(encoding="utf-8").splitlines()
    output = "\n".join(lines[-args.lines :])
    sys.stdout.write(output + ("\n" if output else ""))
    return 0


def v2_logs_size(paths: LoopPaths) -> int:
    return paths.logs_md.stat().st_size if paths.logs_md.exists() else 0


def v2_print_logs_delta(paths: LoopPaths, offset: int) -> None:
    if not paths.logs_md.exists():
        return
    with paths.logs_md.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        delta = handle.read().strip()
    if delta:
        sys.stdout.write("\n## logs.md delta\n\n" + delta + "\n")
    else:
        sys.stdout.write("\n## logs.md delta\n\n(no new log entries)\n")


def v2_recent_logs(paths: LoopPaths, line_count: int = 120) -> str:
    if not paths.logs_md.exists():
        return ""
    return "\n".join(paths.logs_md.read_text(encoding="utf-8").splitlines()[-line_count:])


def v2_next_actionable_item(paths: LoopPaths) -> PlanItem | None:
    for item in plan_items(paths):
        if item.status in {"pending", "in_progress", "blocked"}:
            return item
    return None


def v2_item_by_title(paths: LoopPaths, title: str) -> PlanItem | None:
    for item in plan_items(paths):
        if item.title == title:
            return item
    return None


def v2_build_context(paths: LoopPaths, item: PlanItem) -> str:
    return "\n".join(
        [
            "# Long Loop Runtime Context",
            "",
            "Use this context plus fresh repository search. Do not rely on prior conversation memory.",
            "",
            "## PROMPT.md",
            paths.prompt.read_text(encoding="utf-8"),
            "## SPEC_OVERVIEW.md",
            paths.spec_overview.read_text(encoding="utf-8"),
            "## Selected fix_plan.md item",
            item.as_context(),
            "## fix_plan.md",
            paths.fix_plan.read_text(encoding="utf-8"),
            "## qa.md",
            paths.qa.read_text(encoding="utf-8"),
            "## recent logs.md",
            v2_recent_logs(paths),
        ]
    )


def script_from_repo_or_harness(repo_root: Path, name: str) -> Path | None:
    repo_script = repo_root / "scripts" / name
    if repo_script.exists():
        return repo_script
    harness_script = Path(__file__).resolve().parent / name
    if harness_script.exists():
        return harness_script
    dotfiles_script = Path(__file__).resolve().parents[2] / "scripts" / name
    if dotfiles_script.exists():
        return dotfiles_script
    return None


def v2_run_validation(repo_root: Path) -> tuple[bool, str]:
    outputs: list[str] = []
    ok = True
    verify = script_from_repo_or_harness(repo_root, "run-verify.sh")
    if verify:
        result = run_shell(f'bash "{verify}" "{repo_root}"', cwd=repo_root)
        outputs.append(result.stdout + result.stderr)
        ok = ok and result.returncode == 0
        if result.returncode == 2:
            outputs.append("validation structural gap: no runnable validators detected")
    else:
        outputs.append("validation structural gap: missing run-verify.sh")
        ok = False
    scan = script_from_repo_or_harness(repo_root, "scan_diff_residue.py")
    if scan:
        result = run_shell(f'python3 "{scan}"', cwd=repo_root)
        outputs.append(result.stdout + result.stderr)
        ok = ok and result.returncode == 0
    else:
        outputs.append("validation structural gap: missing scan_diff_residue.py")
        ok = False
    return ok, "\n".join(outputs).strip()


def v2_iteration_progress_ok(paths: LoopPaths, item: PlanItem, logs_offset: int, previous_status: str) -> tuple[bool, str]:
    if v2_logs_size(paths) <= logs_offset:
        return False, "logs.md did not update during iteration"
    current = v2_item_by_title(paths, item.title)
    if current is None:
        return False, f"fix_plan.md no longer contains selected item: {item.title}"
    if current.status == previous_status:
        return False, "fix_plan.md did not update selected item status"
    return True, "iteration progress recorded"


def v2_phase_complete(paths: LoopPaths, phase: str) -> bool:
    phase_items = [item for item in plan_items(paths) if item.phase == phase]
    return bool(phase_items) and all(item.status == "done" for item in phase_items)


def v2_git_status_porcelain(repo_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def v2_checkpoint_phase(repo_root: Path, phase: str) -> tuple[bool, str]:
    inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_root, text=True, capture_output=True, check=False)
    if inside.returncode != 0:
        return False, "checkpoint failed: not inside a git repository"
    subprocess.run(["git", "add", "-A"], cwd=repo_root, text=True, capture_output=True, check=False)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_root, text=True, capture_output=True, check=False)
    if staged.returncode == 0:
        return True, f"checkpoint skipped: no staged changes for {phase}"
    commit = subprocess.run(
        ["git", "commit", "-m", f"checkpoint(long-loop): complete {phase}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if commit.returncode != 0:
        return False, commit.stdout + commit.stderr
    return True, commit.stdout.strip()


def v2_repo_root_from_args(args: argparse.Namespace, state: dict) -> Path:
    raw = getattr(args, "repo_root", None) or state.get("repo_root") or str(Path.cwd())
    return Path(raw).expanduser().resolve()


def v2_run_loop(args: argparse.Namespace) -> int:
    paths = LoopPaths(resolve_workspace_root(args.dir))
    v2_require_workspace(paths)
    if not args.agent_cmd:
        raise RuntimeError("run requires --agent-cmd")
    if args.max_iterations < 1:
        raise RuntimeError("--max-iterations must be >= 1")
    if args.idle_timeout_seconds < 1:
        raise RuntimeError("--idle-timeout-seconds must be >= 1")
    v2_require_ready_workspace(paths)
    state = read_state(paths)
    v2_require_harness_state(state)
    require_valid_plan_statuses(paths)
    repo_root = v2_repo_root_from_args(args, state)
    if args.checkpoint_commits:
        dirty = v2_git_status_porcelain(repo_root)
        if dirty:
            state["status"] = "stopped"
            state["stop_reason"] = "checkpoint refused: dirty worktree before iteration"
            state["updated_at"] = now_iso()
            write_state(paths, state)
            sys.stdout.write("checkpoint refused: dirty worktree before iteration\n")
            return 1
    state["status"] = "running"
    state["stop_reason"] = None
    state["updated_at"] = now_iso()
    write_state(paths, state)

    for _ in range(args.max_iterations):
        item = v2_next_actionable_item(paths)
        if item is None:
            state = read_state(paths)
            state["status"] = "done"
            state["stop_reason"] = "plan complete"
            state["updated_at"] = now_iso()
            write_state(paths, state)
            sys.stdout.write("plan complete\n")
            return 0
        if item.status == "blocked":
            state = read_state(paths)
            state["status"] = "stopped"
            state["current_item"] = item.title
            state["stop_reason"] = "blocked item requires user action"
            state["updated_at"] = now_iso()
            write_state(paths, state)
            sys.stdout.write("blocked item requires user action\n")
            return 0
        iteration = int(state.get("iterations", 0)) + 1
        state = read_state(paths)
        state["current_item"] = item.title
        state["iteration_started_at"] = now_iso()
        state["last_heartbeat_at"] = state["iteration_started_at"]
        state["updated_at"] = now_iso()
        write_state(paths, state)
        logs_offset = v2_logs_size(paths)
        previous_status = item.status
        result = run_agent_command(
            args.agent_cmd,
            stdin=v2_build_context(paths, item),
            cwd=repo_root,
            paths=paths,
            idle_timeout_seconds=args.idle_timeout_seconds,
        )
        v2_print_logs_delta(paths, logs_offset)

        state = read_state(paths)
        state["iterations"] = iteration
        state["last_exit_code"] = result.returncode
        state["updated_at"] = now_iso()
        if result.timed_out:
            state["status"] = "stopped"
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["stop_reason"] = f"agent command idle timeout after {args.idle_timeout_seconds}s"
            write_state(paths, state)
            sys.stdout.write(result.output)
            return 1
        if result.returncode != 0:
            state["status"] = "stopped"
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["stop_reason"] = "agent command failed"
            write_state(paths, state)
            sys.stdout.write(result.output)
            return result.returncode or 1

        progress_ok, progress_message = v2_iteration_progress_ok(paths, item, logs_offset, previous_status)
        if not progress_ok:
            state["status"] = "stopped"
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["stop_reason"] = progress_message
            write_state(paths, state)
            sys.stdout.write(progress_message + "\n")
            return 1

        validation_ok, validation_output = v2_run_validation(repo_root)
        state["last_validation"] = "pass" if validation_ok else "fail"
        if not validation_ok:
            state["status"] = "stopped"
            state["failure_count"] = int(state.get("failure_count", 0)) + 1
            state["stop_reason"] = "validation failed"
            write_state(paths, state)
            if validation_output:
                sys.stdout.write(validation_output + "\n")
            return 1

        if args.checkpoint_commits and item.phase and v2_phase_complete(paths, item.phase):
            checkpoint_ok, checkpoint_output = v2_checkpoint_phase(repo_root, item.phase)
            if checkpoint_output:
                sys.stdout.write(checkpoint_output + "\n")
            if not checkpoint_ok:
                state["status"] = "stopped"
                state["failure_count"] = int(state.get("failure_count", 0)) + 1
                state["stop_reason"] = "checkpoint commit failed"
                write_state(paths, state)
                return 1

        state["failure_count"] = 0
        state["status"] = "running"
        write_state(paths, state)

    state = read_state(paths)
    state["status"] = "stopped"
    state["stop_reason"] = "max iterations reached"
    state["updated_at"] = now_iso()
    write_state(paths, state)
    sys.stdout.write("max iterations reached\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a .long-loop workspace.")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="Long-loop workspace directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_workspace_arg(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--dir", default=argparse.SUPPRESS, help="Long-loop workspace directory.")

    plan = subparsers.add_parser("plan", help="Create a ready long-loop plan.")
    plan.add_argument("--goal", required=True)
    plan.add_argument("--force", action="store_true")
    plan.add_argument("--token-budget", default="500K", choices=["500K", "1M", "2M"])
    add_workspace_arg(plan)
    plan.set_defaults(func=v2_plan_workspace)

    status = subparsers.add_parser("status", help="Print workspace status.")
    add_workspace_arg(status)
    status.set_defaults(func=v2_status_workspace)

    tail = subparsers.add_parser("tail", help="Print recent append-only log lines.")
    tail.add_argument("--lines", type=int, default=80)
    add_workspace_arg(tail)
    tail.set_defaults(func=v2_tail_workspace)

    run = subparsers.add_parser("run", help="Run one or more bounded iterations.")
    run.add_argument("--agent-cmd")
    run.add_argument("--max-iterations", type=int, default=1)
    run.add_argument("--idle-timeout-seconds", type=int, default=300)
    run.add_argument("--repo-root")
    run.add_argument("--checkpoint-commits", action="store_true")
    add_workspace_arg(run)
    run.set_defaults(func=v2_run_loop)

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

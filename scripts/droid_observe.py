#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ABS_WORKSPACE_RE = re.compile(r"(/[^\s`\"'<>]+/\.long-loop/[^\s`\"'<>]+)")
REL_WORKSPACE_RE = re.compile(r"(?<![\w/.-])(\.long-loop/[^\s`\"'<>]+)")
REPO_ROOT_RE = re.compile(r"--repo-root\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s`]+))")
CD_RE = re.compile(r"\bcd\s+\"([^\"]+)\"")
CWD_RE = re.compile(r"--cwd\s+\"([^\"]+)\"")


def session_files(sessions_dir: Path, prefix: str) -> list[Path]:
    matches = sorted(sessions_dir.glob(f"**/{prefix}*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise RuntimeError(f"no session found for prefix: {prefix}")
    return matches


def json_line_cwd(line: str) -> str | None:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    cwd = data.get("cwd")
    if isinstance(cwd, str):
        return cwd
    return None


def normalize_workspace_path(path: Path) -> Path:
    parts = path.parts
    if ".long-loop" not in parts:
        return path
    index = parts.index(".long-loop")
    if len(parts) <= index + 1:
        return path
    return Path(*parts[: index + 2])


def workspace_updated_at(workspace: Path) -> str:
    state = workspace / "state.json"
    if not state.exists():
        return ""
    try:
        payload = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("updated_at") or "")


def workspaces_under(root: Path) -> list[Path]:
    long_loop_dir = root / ".long-loop"
    if not long_loop_dir.exists():
        return []
    workspaces = [path for path in long_loop_dir.iterdir() if (path / "state.json").exists()]
    return sorted(workspaces, key=lambda path: (workspace_updated_at(path), path.stat().st_mtime), reverse=True)


def latest_workspace_under(root: Path) -> Path | None:
    workspaces = workspaces_under(root)
    return workspaces[0] if workspaces else None


def resolve_direct_target(target: str | None) -> Path | None:
    if not target:
        return latest_workspace_under(Path.cwd())
    path = Path(target).expanduser()
    if (path / "state.json").exists():
        return path
    if path.name == "state.json" and path.exists():
        return path.parent
    if path.exists() and path.is_dir():
        return latest_workspace_under(path)
    return None


def resolve_target_workspaces(target: str | None, sessions_dir: Path) -> list[Path]:
    workspace = resolve_direct_target(target)
    if workspace is not None:
        path = Path(target).expanduser() if target else Path.cwd()
        if path.exists() and path.is_dir() and not (path / "state.json").exists():
            return workspaces_under(path) or [workspace]
        return [workspace]
    if not target:
        return []
    sessions = session_files(sessions_dir, target)
    return extract_workspaces(sessions[0])


def print_workspace_list(workspaces: list[Path]) -> None:
    for index, workspace in enumerate(workspaces, start=1):
        state = workspace / "state.json"
        goal = ""
        status = ""
        updated_at = workspace_updated_at(workspace)
        try:
            payload = json.loads(state.read_text(encoding="utf-8"))
            goal = str(payload.get("goal") or "")
            status = str(payload.get("status") or "")
        except (OSError, json.JSONDecodeError):
            pass
        sys.stdout.write(f"{index}. {workspace}\n   status: {status or 'unknown'} updated_at: {updated_at or 'unknown'}\n   goal: {goal or 'unknown'}\n")


def extract_workspaces(session_path: Path) -> list[Path]:
    roots: list[Path] = []
    absolute_candidates: set[Path] = set()
    relative_candidates: set[str] = set()

    def add_root(raw: str | None) -> None:
        if raw:
            root = Path(raw).expanduser()
            if root not in roots:
                roots.append(root)

    with session_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            add_root(json_line_cwd(line))
            for match in REPO_ROOT_RE.finditer(line):
                add_root(next(group for group in match.groups() if group))
            for regex in (CD_RE, CWD_RE):
                for match in regex.finditer(line):
                    add_root(match.group(1))
            for match in ABS_WORKSPACE_RE.finditer(line):
                absolute_candidates.add(normalize_workspace_path(Path(match.group(1))))
            for match in REL_WORKSPACE_RE.finditer(line):
                relative_candidates.add(match.group(1))

    workspaces: set[Path] = set()
    for candidate in absolute_candidates:
        if (candidate / "state.json").exists():
            workspaces.add(candidate)
    for root in roots:
        for relative in relative_candidates:
            candidate = normalize_workspace_path(root / relative)
            if (candidate / "state.json").exists():
                workspaces.add(candidate)
    return sorted(workspaces, key=lambda path: (workspace_updated_at(path), path.stat().st_mtime), reverse=True)


def harness_path() -> Path:
    return Path(__file__).resolve().parents[1] / "skills" / "dev-long-loop" / "long_loop.py"


def dashboard_path() -> Path:
    return Path(__file__).resolve().parent / "longrun_dashboard.py"


def open_workspace(workspace: Path, *, dry_run: bool) -> int:
    html_path = workspace / "observe.html"
    if dry_run:
        sys.stdout.write(f"workspace: {workspace}\nopen: longrun --workspace {workspace}\n")
        return 0
    repo = workspace.parent.parent if workspace.parent.name == ".long-loop" else Path.cwd()
    return subprocess.call(["python3", str(dashboard_path()), str(repo), "--workspace", str(workspace)])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open the latest long-run observe page.")
    parser.add_argument(
        "target",
        nargs="?",
        help="Long-loop workspace path, repo/worktree path, or Droid session id prefix. Defaults to current directory.",
    )
    parser.add_argument("--sessions-dir", type=Path, default=Path.home() / ".factory" / "sessions")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved workspace and open command without opening a browser.")
    parser.add_argument("--list", action="store_true", help="List matching long-run workspaces instead of opening one.")
    parser.add_argument("--index", type=int, default=1, help="Open the Nth workspace from --list order. Default: 1 (latest).")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        workspaces = resolve_target_workspaces(args.target, args.sessions_dir)
        if not workspaces:
            target = args.target or "current directory"
            raise RuntimeError(f"no long-loop workspace found for: {target}")
        if args.list:
            print_workspace_list(workspaces)
            return 0
        if args.index < 1 or args.index > len(workspaces):
            raise RuntimeError(f"--index must be between 1 and {len(workspaces)}")
        workspace = workspaces[args.index - 1]
    except RuntimeError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2
    return open_workspace(workspace, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    kind: str
    pattern: re.Pattern[str]
    reason: str


SHELL_SEPARATORS = {"&&", "||", ";", "|"}
DB_WRITE_WORDS = {"delete", "insert", "update", "drop", "alter", "create", "truncate", "flush", "set", "del", "hset", "sadd", "zadd"}


def load_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def command_from_input(payload: dict) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    command = tool_input.get("command")
    return command if isinstance(command, str) else ""


def suppress() -> dict:
    return {"suppressOutput": True}


def deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "suppressOutput": True,
    }


def split_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def command_segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in SHELL_SEPARATORS:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def reason_for_segment(segment: list[str]) -> str | None:
    if not segment:
        return None
    cmd = PathLikeCommand(segment[0])
    args = [arg.lower() for arg in segment[1:]]
    all_words = re.findall(r"[a-z_]+", " ".join([cmd.name, *args]))

    if cmd.name == "git" and args[:1] == ["push"]:
        return "git push modifies remote repository state; route through /guard-gitops first."
    if cmd.name == "git" and args[:1] == ["clean"]:
        return "destructive git cleanup requires explicit user approval and safety review."
    if cmd.name == "gh" and (args[:2] == ["pr", "merge"] or args[:1] == ["release"]):
        return "GitHub merge/release changes remote state; route through /guard-gitops first."
    if cmd.name == "npm" and args[:1] == ["publish"]:
        return "Publishing changes package registry state; route through /guard-gitops first."
    if cmd.name in {"ssh", "scp", "rsync"}:
        return "remote machine command can change non-repository state; route through /guard-gitops first."
    if cmd.name == "kubectl" and args and args[0] in {"apply", "delete", "replace", "patch", "scale", "rollout", "set"}:
        return "cluster write command requires /guard-gitops first."
    if cmd.name == "helm" and args and args[0] in {"upgrade", "install", "uninstall", "delete"}:
        return "helm write command requires /guard-gitops first."
    if cmd.name == "terraform" and args and args[0] in {"apply", "destroy"}:
        return "terraform write command requires /guard-gitops first."
    if cmd.name == "rm" and any(arg.startswith("-") and "r" in arg and "f" in arg for arg in args):
        return "destructive file cleanup requires explicit user approval and safety review."
    if cmd.name == "find" and "-delete" in args:
        return "destructive find -delete requires explicit user approval and safety review."
    if cmd.name in {"psql", "mysql", "redis-cli"} and any(token in DB_WRITE_WORDS for token in all_words):
        return "database write command requires /guard-gitops or explicit data-operation approval first."
    if cmd.name in {"bash", "sh", "zsh"} and "-c" in args:
        index = args.index("-c")
        if index + 1 < len(segment):
            nested = evaluate_command(segment[index + 2])
            if nested:
                return nested
    return None


@dataclass(frozen=True)
class PathLikeCommand:
    raw: str

    @property
    def name(self) -> str:
        return self.raw.rsplit("/", 1)[-1].lower()


def evaluate_command(command: str) -> str | None:
    for segment in command_segments(split_tokens(command)):
        reason = reason_for_segment(segment)
        if reason:
            return reason
    return None


def evaluate(command: str) -> dict:
    reason = evaluate_command(command)
    return deny(reason) if reason else suppress()


def main() -> int:
    sys.stdout.write(json.dumps(evaluate(command_from_input(load_input())), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

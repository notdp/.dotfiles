#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Rule:
    kind: str
    pattern: re.Pattern[str]
    reason: str


DecisionKind = Literal["warn", "deny"]


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    reason: str


SHELL_SEPARATORS = {"&&", "||", ";", "|"}
DB_WARN_WORDS = {"delete", "insert", "update"}
DB_DENY_WORDS = {"drop", "alter", "create", "truncate", "flush"}
REDIS_WRITE_WORDS = {"del", "hset", "sadd", "set", "zadd"}
REMOTE_WRITE_COMMANDS = {
    "chmod",
    "chown",
    "cp",
    "kill",
    "mv",
    "pkill",
    "reboot",
    "rm",
    "service",
    "systemctl",
}
REMOTE_READ_COMMANDS = {
    "awk",
    "cat",
    "curl",
    "df",
    "du",
    "echo",
    "free",
    "grep",
    "head",
    "journalctl",
    "ps",
    "sed",
    "ss",
    "supervisorctl",
    "systemctl",
    "tail",
    "uptime",
}
SYSTEMCTL_READ_ARGS = {"is-active", "is-enabled", "show", "status"}
SUPERVISORCTL_READ_ARGS = {"status", "tail"}
PYTHON_COMMAND_RE = re.compile(r"^python(?:\d+(?:\.\d+)?)?$")
DB_PIPE_RE = re.compile(r"\|\s*(?:\S*/)?(?:psql|mysql)\b", re.I)
DYNAMIC_WIDE_CLEANUP_RE = re.compile(r"(?:\$\([^)]*\)|`[^`]+`)\s+-[^;&|]*[rf][^;&|]*\s+(?:/|~|\$HOME|\*)", re.I)


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


def warn(reason: str) -> dict:
    return {"systemMessage": f"Command guard advisory: {approval_request(reason)}"}


def approval_request(reason: str) -> str:
    return "\n".join(
        [
            reason,
            "",
            "ApprovalRequest:",
            "- Action: state the exact command or operation before running it",
            "- Target: name the remote, cluster, database, file path, package, or cloud resource",
            f"- External side effect: {reason}",
            "- Risk: explain data loss, outage, billing, remote state, or rollback risk",
            "- Dry-run / read-only evidence: provide status, plan, diff, or read-only check when available",
            "- Rollback: describe the concrete rollback or recovery path",
            "- Validation after apply: list the command or observation that proves the target state",
            "- User approval required: quote the explicit approval before proceeding",
        ]
    )


def split_tokens(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        return list(lexer)
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


def is_dry_run(args: list[str]) -> bool:
    return any(arg in {"-n", "--dry-run"} for arg in args)


def is_remote_ref(value: str) -> bool:
    if value.startswith(("/", "./", "../")):
        return False
    return bool(re.match(r"^(?:[^@\s:]+@)?[^/\s:]+:.+", value))


def option_operands(tokens: list[str], options_with_values: set[str]) -> list[str]:
    operands: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            operands.extend(tokens[index + 1 :])
            break
        if token in options_with_values:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        operands.append(token)
        index += 1
    return operands


def ssh_remote_command(segment: list[str]) -> str:
    tokens = segment[1:]
    options_with_values = {"-b", "-c", "-D", "-E", "-F", "-i", "-J", "-L", "-l", "-m", "-O", "-o", "-p", "-R", "-S", "-W", "-w"}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token in options_with_values:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        index += 1
        break
    return " ".join(tokens[index:]).strip()


def remote_segment_is_read_only(segment: list[str]) -> bool:
    if not segment:
        return True
    cmd = PathLikeCommand(segment[0])
    args = [arg.lower() for arg in segment[1:]]

    if cmd.name == "systemctl":
        return bool(args and args[0] in SYSTEMCTL_READ_ARGS)
    if cmd.name == "supervisorctl":
        return bool(args and args[0] in SUPERVISORCTL_READ_ARGS)
    if cmd.name == "curl":
        return any("localhost" in arg or "127.0.0.1" in arg or "[::1]" in arg for arg in args)
    if cmd.name == "sed" and any(arg == "-i" or arg.startswith("-i") for arg in args):
        return False
    if cmd.name in REMOTE_WRITE_COMMANDS:
        return False
    return cmd.name in REMOTE_READ_COMMANDS


def remote_command_is_read_only(command: str) -> bool:
    if remote_command_has_write_redirect(command):
        return False
    segments = command_segments(split_tokens(command))
    return bool(segments) and all(remote_segment_is_read_only(segment) for segment in segments)


def remote_command_has_write_redirect(command: str) -> bool:
    return bool(re.search(r"(?<!\d)>{1,2}|<<", command))


def scp_is_read_only_fetch(segment: list[str]) -> bool:
    operands = option_operands(segment[1:], {"-c", "-F", "-i", "-J", "-l", "-o", "-P", "-S"})
    if len(operands) < 2:
        return False
    sources = operands[:-1]
    target = operands[-1]
    return bool(sources) and all(is_remote_ref(source) for source in sources) and not is_remote_ref(target)


def rsync_is_read_only(segment: list[str]) -> bool:
    args = [arg.lower() for arg in segment[1:]]
    return "--list-only" in args or is_dry_run(args)


def db_command_decision(cmd_name: str, args: list[str], all_words: list[str]) -> Decision | None:
    if cmd_name == "redis-cli":
        if any(token in REDIS_WRITE_WORDS for token in all_words):
            return Decision("warn", "database write command; confirm scope, rollback, and validation before proceeding.")
        return None
    query = " ".join(args).lower()
    if cmd_name in {"psql", "mysql"} and any(
        arg in {"-f", "--file", "<"} or arg.startswith("<") or arg.startswith("--file=") for arg in args
    ):
        return Decision("warn", "database SQL file execution can write data or schema; confirm scope, rollback, and validation before proceeding.")
    if any(re.search(rf"\b{word}\b", query) for word in DB_DENY_WORDS):
        return Decision("deny", "database destructive schema command is too risky for automatic execution.")
    if any(re.search(rf"\b{word}\b", query) for word in DB_WARN_WORDS):
        return Decision("warn", "database write command; confirm scope, rollback, and validation before proceeding.")
    return None


def wide_path_operand(value: str) -> bool:
    return value in {"/", "~", "$HOME", "*"} or value.startswith(("/", "~/", "$HOME/", "/*"))


def embedded_text_decision(text: str) -> Decision | None:
    lowered = text.lower()
    if re.search(r"\brm\s+-[^;&|'\"]*[rf][^;&|'\"]*\s+(?:/|~|\$home|\*)", lowered):
        return Decision("deny", "wide destructive cleanup is too risky for automatic execution.")
    if re.search(r"\bgit\s+reset\s+--hard\b", lowered):
        return Decision("deny", "git reset --hard can discard working tree changes; do not run automatically.")
    if re.search(r"\baws\s+s3\s+rm\b.*\s--recursive\b", lowered):
        return Decision("deny", "recursive cloud object deletion is too risky for automatic execution.")
    if re.search(r"\bgh\s+repo\s+delete\b", lowered):
        return Decision("deny", "repository deletion is too risky for automatic execution.")
    nested = evaluate_command(text)
    return nested


def raw_command_decision(command: str) -> Decision | None:
    if DYNAMIC_WIDE_CLEANUP_RE.search(command):
        return Decision("deny", "wide destructive cleanup is too risky for automatic execution.")
    if DB_PIPE_RE.search(command):
        return Decision("warn", "database piped SQL input can write data or schema; confirm scope, rollback, and validation before proceeding.")
    return None


def option_value(args: list[str], name: str) -> str | None:
    prefix = f"{name}="
    for index, arg in enumerate(args):
        if arg == name and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith(prefix):
            return arg.removeprefix(prefix)
    return None


def aliyun_ecs_stop_instance_decision(args: list[str]) -> Decision | None:
    if len(args) < 2 or args[:2] != ["ecs", "stopinstance"]:
        return None
    stopped_mode = option_value(args, "--stoppedmode")
    if stopped_mode == "keepcharging":
        return Decision(
            "warn",
            "aliyun ecs StopInstance with KeepCharging can leave ECS/GPU compute billing active; confirm the cost goal, retained assets, rollback, and StoppedMode verification before proceeding.",
        )
    if stopped_mode == "stopcharging":
        return Decision(
            "warn",
            "aliyun ecs StopInstance with StopCharging changes remote resource and billing state; confirm retained assets, rollback, immediate validation, and delayed billing verification before proceeding.",
        )
    return Decision(
        "warn",
        "aliyun ecs StopInstance requires an explicit StoppedMode decision; confirm whether the goal is KeepCharging recoverability or StopCharging billing reduction before proceeding.",
    )


def aliyun_command_decision(args: list[str]) -> Decision | None:
    ecs_stop_decision = aliyun_ecs_stop_instance_decision(args)
    if ecs_stop_decision:
        return ecs_stop_decision
    if len(args) < 2:
        return Decision(
            "warn",
            "aliyun CLI command can change cloud resource state; confirm retained assets, rollback, billing impact, and validation before proceeding.",
        )
    action = args[1]
    if action.startswith(("describe", "list", "get")) or action in {"help", "version"}:
        return None
    if any(word in action for word in ("delete", "release", "remove", "destroy")):
        return Decision(
            "deny",
            "aliyun destructive cloud command is too risky for automatic execution.",
        )
    return Decision(
        "warn",
        "aliyun CLI command can change cloud resource state; confirm retained assets, rollback, billing impact, and validation before proceeding.",
    )


def env_inner_segment(segment: list[str]) -> list[str]:
    index = 1
    while index < len(segment):
        token = segment[index]
        if token == "--":
            return segment[index + 1 :]
        if token in {"-0", "-i", "-u"}:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            index += 1
            continue
        return segment[index:]
    return []


def xargs_inner_segment(segment: list[str]) -> list[str]:
    index = 1
    options_with_values = {"-a", "-E", "-I", "-n", "-P", "-s", "--arg-file", "--max-args", "--max-procs", "--max-chars"}
    while index < len(segment):
        token = segment[index]
        if token == "--":
            return segment[index + 1 :]
        if token in options_with_values:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return segment[index:]
    return []


def segment_decision(segment: list[str]) -> Decision | None:
    if not segment:
        return None
    cmd = PathLikeCommand(segment[0])
    args = [arg.lower() for arg in segment[1:]]
    all_words = re.findall(r"[a-z_]+", " ".join([cmd.name, *args]))

    if cmd.name == "git" and args[:1] == ["push"]:
        if any(arg in {"--force", "--force-with-lease", "-f"} for arg in args):
            return Decision("deny", "git force push can overwrite remote history; do not run automatically.")
        return Decision("deny", "git push modifies remote repository state; route through /guard-gitops and obtain explicit user approval before proceeding.")
    if cmd.name == "git" and args[:1] == ["clean"] and not is_dry_run(args):
        if any("x" in arg for arg in args if arg.startswith("-")):
            return Decision("deny", "destructive git cleanup including ignored files is too risky for automatic execution.")
        return Decision("warn", "destructive git cleanup requires explicit user approval and safety review.")
    if cmd.name == "git" and args[:1] == ["reset"] and "--hard" in args:
        return Decision("deny", "git reset --hard can discard working tree changes; do not run automatically.")
    if cmd.name == "gh" and (args[:2] == ["pr", "merge"] or args[:1] == ["release"]):
        return Decision("warn", "GitHub merge/release changes remote state; confirm target, checks, and rollback before proceeding.")
    if cmd.name == "gh" and args[:2] == ["repo", "delete"]:
        return Decision("deny", "repository deletion is too risky for automatic execution.")
    if cmd.name == "aws" and args[:2] == ["s3", "rm"] and "--recursive" in args:
        return Decision("deny", "recursive cloud object deletion is too risky for automatic execution.")
    if cmd.name == "aws" and args[:2] == ["s3"]:
        return Decision("warn", "cloud storage command can change remote state; confirm scope, rollback, and validation before proceeding.")
    if cmd.name == "aliyun":
        aliyun_decision = aliyun_command_decision(args)
        if aliyun_decision:
            return aliyun_decision
    if cmd.name == "docker" and args and args[0] in {"rm", "rmi"}:
        return Decision("warn", "container cleanup can remove local runtime state; confirm scope and rollback before proceeding.")
    if cmd.name == "docker" and args[:2] in (["volume", "rm"], ["system", "prune"]):
        return Decision("warn", "container cleanup can remove local runtime state; confirm scope and rollback before proceeding.")
    if cmd.name == "npm" and args[:1] == ["publish"]:
        return Decision("warn", "publishing changes package registry state; confirm package, version, and rollback before proceeding.")
    if cmd.name == "env":
        nested = segment_decision(env_inner_segment(segment))
        if nested:
            return nested
    if cmd.name == "xargs":
        nested = segment_decision(xargs_inner_segment(segment))
        if nested:
            return nested
    if cmd.name == "ssh" and not remote_command_is_read_only(ssh_remote_command(segment)):
        remote = ssh_remote_command(segment)
        if re.search(r"\brm\s+-[^;|&]*[rf][^;|&]*\s+(?:/|~|\$HOME|\*)", remote):
            return Decision("deny", "remote destructive cleanup is too risky for automatic execution.")
        if not remote:
            return Decision("deny", "interactive ssh session has unknown remote effects; do not run automatically.")
        return Decision("warn", "remote machine command can change non-repository state; confirm scope, rollback, and validation before proceeding.")
    if cmd.name == "scp" and not scp_is_read_only_fetch(segment):
        return Decision("warn", "remote file transfer can change non-repository state; confirm destination and rollback before proceeding.")
    if cmd.name == "rsync" and not rsync_is_read_only(segment):
        return Decision("warn", "remote sync can change non-repository state; confirm source, destination, dry-run, and rollback before proceeding.")
    if cmd.name == "kubectl" and args[:2] == ["rollout", "status"]:
        return None
    if cmd.name == "kubectl" and args and args[0] == "delete":
        return Decision("deny", "cluster delete command is too risky for automatic execution.")
    if cmd.name == "kubectl" and args and args[0] in {"apply", "delete", "replace", "patch", "scale", "rollout", "set"}:
        return Decision("warn", "cluster write command; confirm namespace, resources, rollback, and validation before proceeding.")
    if cmd.name == "helm" and args and args[0] in {"upgrade", "install", "uninstall", "delete"}:
        return Decision("warn", "helm write command; confirm release, namespace, rollback, and validation before proceeding.")
    if cmd.name == "terraform" and args and args[0] == "destroy":
        return Decision("deny", "terraform destroy is too risky for automatic execution.")
    if cmd.name == "terraform" and args and args[0] == "apply":
        return Decision("warn", "terraform apply changes infrastructure; confirm plan, scope, rollback, and validation before proceeding.")
    if cmd.name == "rm" and any(arg.startswith("-") and "r" in arg and "f" in arg for arg in args):
        if any(wide_path_operand(arg) for arg in segment[1:]):
            return Decision("deny", "wide destructive cleanup is too risky for automatic execution.")
        return Decision("warn", "destructive file cleanup requires explicit user approval and safety review.")
    if cmd.name == "find" and "-delete" in args:
        if any(arg in {"/", "~", "$HOME", "."} for arg in args):
            return Decision("deny", "wide find -delete is too risky for automatic execution.")
        return Decision("warn", "destructive find -delete requires explicit user approval and safety review.")
    if cmd.name == "find" and "-exec" in args:
        exec_index = args.index("-exec")
        exec_segment = segment[exec_index + 2 :]
        if exec_segment:
            nested = segment_decision(exec_segment)
            if nested and nested.kind == "deny":
                return nested
            if exec_segment[0].lower().rsplit("/", 1)[-1] == "rm" and any(
                wide_path_operand(arg) for arg in args[:exec_index]
            ):
                return Decision("deny", "wide destructive cleanup is too risky for automatic execution.")
            if nested:
                return nested
            return Decision("warn", "find -exec can apply changes across many files; confirm scope before proceeding.")
    if cmd.name in {"psql", "mysql", "redis-cli"}:
        db_decision = db_command_decision(cmd.name, args, all_words)
        if db_decision:
            return db_decision
    if cmd.name == "eval" and len(segment) > 1:
        return embedded_text_decision(" ".join(segment[1:]))
    if PYTHON_COMMAND_RE.fullmatch(cmd.name) and "-c" in args:
        index = args.index("-c")
        if index + 1 < len(segment):
            return embedded_text_decision(segment[index + 2])
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


def evaluate_command(command: str) -> Decision | None:
    raw_decision = raw_command_decision(command)
    if raw_decision:
        return raw_decision
    warning: Decision | None = None
    for segment in command_segments(split_tokens(command)):
        decision = segment_decision(segment)
        if not decision:
            continue
        if decision.kind == "deny":
            return decision
        warning = warning or decision
    return warning


def evaluate(command: str) -> dict:
    decision = evaluate_command(command)
    if not decision:
        return suppress()
    return deny(decision.reason) if decision.kind == "deny" else warn(decision.reason)


def main() -> int:
    sys.stdout.write(json.dumps(evaluate(command_from_input(load_input())), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

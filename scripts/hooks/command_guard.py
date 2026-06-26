#!/usr/bin/env python3
from __future__ import annotations

import ast
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
WRAPPER_COMMANDS = {"sudo", "doas", "timeout", "nice", "nohup", "command", "time", "ionice", "stdbuf", "setsid", "env"}
DB_CLIENT_COMMANDS = {"psql", "mysql", "mariadb"}
DB_INLINE_EXEC_FLAGS = {"-c", "-e", "--command", "--execute"}
SHELL_COMMANDS = {"bash", "sh", "zsh"}
DESTRUCTIVE_SQL_PATTERNS = [
    re.compile(r"\bdrop\s+(?:database|table)\b", re.I),
    re.compile(r"\btruncate\s+table\b", re.I),
    re.compile(r"\balter\s+table\b.*\bdrop\b", re.I),
    re.compile(r"\bdelete\s+from\b(?![^;]*\bwhere\b)", re.I),
]


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
        if any(token in {"flushall", "flushdb"} for token in all_words):
            return Decision("deny", "database destructive flush command is too risky for automatic execution.")
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


# os.system / os.popen and subprocess.* that take a command (string or argv list).
DANGEROUS_PY_CALL_NAMES = {"system", "popen", "run", "call", "Popen", "check_output", "check_call"}


def _ast_literal_command(node: ast.AST) -> str | None:
    """A string literal, or a list/tuple of string literals joined as a command."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        parts = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                parts.append(elt.value)
            else:
                return None
        return " ".join(parts)
    return None


def python_source_decision(text: str) -> Decision | None:
    """Scan `python -c` source. AST-detect literal os.system / subprocess calls and
    re-check their command — including the argv-LIST form (e.g. subprocess.run(["rm",
    "-rf", "/etc"])) that the plain text scan misses — then fall back to the text scan.
    ADVISORY only: python is Turing-complete, so non-literal argv, base64/eval and the
    like still pass. This is defense-in-depth against accidental destructive commands,
    NOT a hard security boundary."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return embedded_text_decision(text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
        if name not in DANGEROUS_PY_CALL_NAMES:
            continue
        command = _ast_literal_command(node.args[0])
        if command is not None:
            decision = embedded_text_decision(command)
            if decision and decision.kind == "deny":
                return decision
    return embedded_text_decision(text)


def raw_command_decision(command: str) -> Decision | None:
    if DYNAMIC_WIDE_CLEANUP_RE.search(command):
        return Decision("deny", "wide destructive cleanup is too risky for automatic execution.")
    if curl_pipe_shell_decision(command):
        return Decision("deny", "remote script piped into a shell is too risky for automatic execution.")
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


def wrapper_inner_segment(segment: list[str]) -> list[str]:
    cmd_name = PathLikeCommand(segment[0]).name if segment else ""
    if cmd_name == "env":
        return env_inner_segment(segment)
    index = 1
    options_with_values = {
        "sudo": {"-C", "-g", "-h", "-p", "-T", "-t", "-U", "-u"},
        "doas": {"-C", "-u"},
        "timeout": {"--signal", "-s", "--kill-after", "-k"},
        "nice": {"-n"},
        "ionice": {"-c", "-n", "-p"},
        "stdbuf": {"-i", "-o", "-e"},
    }
    value_options = options_with_values.get(cmd_name, set())
    if cmd_name == "timeout":
        while index < len(segment) and segment[index].startswith("-"):
            token = segment[index]
            if token in value_options and index + 1 < len(segment):
                index += 2
                continue
            index += 1
        if index < len(segment):
            index += 1
        return segment[index:]
    while index < len(segment):
        token = segment[index]
        if token == "--":
            return segment[index + 1 :]
        if token in value_options and index + 1 < len(segment):
            index += 2
            continue
        if cmd_name in {"sudo", "doas"} and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            index += 1
            continue
        if token.startswith("-"):
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


GIT_PUSH_PROTECTED_BRANCHES = {"main", "master"}
GIT_FORCE_PUSH_FLAGS = {"--force", "--force-with-lease", "-f"}
GIT_PUSH_VALUE_OPTIONS = {"-o", "--push-option", "--repo", "--exec", "--receive-pack"}
GIT_GLOBAL_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree"}
GIT_GLOBAL_FLAGS = {"--no-pager", "-p", "--paginate"}


def git_push_target_branches(push_args: list[str]) -> tuple[list[str], bool]:
    """Parse `git push` args (lowercased, without the leading 'push') into
    (explicit destination branch names, pushes_all_branches).

    `HEAD` and a bare remote resolve to the current branch, which the command
    string can't reveal, so they are treated as non-explicit (ambiguous)."""
    operands: list[str] = []
    pushes_all = False
    index = 0
    while index < len(push_args):
        token = push_args[index]
        if token == "--":
            operands.extend(push_args[index + 1 :])
            break
        if token in {"--all", "--mirror"}:
            pushes_all = True
            index += 1
            continue
        if token in GIT_PUSH_VALUE_OPTIONS:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        operands.append(token)
        index += 1
    refspecs = operands[1:]  # operands[0] is the remote
    branches: list[str] = []
    for spec in refspecs:
        spec = spec.lstrip("+")
        dst = spec.split(":", 1)[1] if ":" in spec else spec
        dst = dst.removeprefix("refs/heads/")
        if dst and dst != "head":
            branches.append(dst)
    return branches, pushes_all


def git_push_decision(push_args: list[str]) -> Decision | None:
    # Force is also expressed as --force-with-lease=<value> (= form) and as a
    # leading '+' on a refspec (e.g. `git push origin +feature`); match both.
    if any(
        arg in GIT_FORCE_PUSH_FLAGS
        or arg.startswith("--force-with-lease=")
        or arg.startswith("+")
        for arg in push_args
    ):
        return Decision("deny", "git force push can overwrite remote history; do not run automatically.")
    branches, pushes_all = git_push_target_branches(push_args)
    if pushes_all:
        return Decision("deny", "git push --all/--mirror can update protected branches (main/master); route through /guard-gitops and push feature branches explicitly.")
    if any(branch in GIT_PUSH_PROTECTED_BRANCHES for branch in branches):
        return Decision("deny", "pushing to a protected branch (main/master) modifies shared history; route through /guard-gitops and obtain explicit user approval before proceeding.")
    if not branches:
        return Decision("deny", "bare 'git push' has an ambiguous target branch; run 'git push <remote> <feature-branch>' so the guard can confirm it is not main/master. Route through /guard-gitops for protected branches.")
    return None


def git_command_args(segment: list[str]) -> list[str]:
    args = segment[1:]
    command_index = 0
    while command_index < len(args):
        token = args[command_index]
        if token == "--":
            command_index += 1
            break
        if token in GIT_GLOBAL_VALUE_OPTIONS:
            command_index += 2
            continue
        if any(token.startswith(f"{option}=") for option in GIT_GLOBAL_VALUE_OPTIONS if option.startswith("--")):
            command_index += 1
            continue
        if token in GIT_GLOBAL_FLAGS:
            command_index += 1
            continue
        break
    return [arg.lower() for arg in args[command_index:]]


def rm_decision(args: list[str]) -> Decision | None:
    has_recursive = False
    has_force = False
    operands: list[str] = []
    parsing_options = True
    for arg in args:
        if parsing_options and arg == "--":
            parsing_options = False
            continue
        if not parsing_options:
            operands.append(arg)
            continue
        if arg in {"--recursive", "-r", "-R"}:
            has_recursive = True
            continue
        if arg == "--force" or arg == "-f":
            has_force = True
            continue
        if arg.startswith("-") and not arg.startswith("--"):
            has_recursive = has_recursive or "r" in arg.lower()
            has_force = has_force or "f" in arg.lower()
            continue
        if arg.startswith("--"):
            continue
        operands.append(arg)
    if has_recursive and has_force:
        if any(wide_path_operand(arg) for arg in operands):
            return Decision("deny", "wide destructive cleanup is too risky for automatic execution.")
        return Decision("warn", "destructive file cleanup requires explicit user approval and safety review.")
    return None


def has_db_inline_execution(args: list[str]) -> bool:
    return any(arg in DB_INLINE_EXEC_FLAGS or any(arg.startswith(f"{flag}=") for flag in DB_INLINE_EXEC_FLAGS if flag.startswith("--")) for arg in args)


def destructive_sql_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in DESTRUCTIVE_SQL_PATTERNS)


def sql_content_decision(cmd_name: str, args: list[str], text: str) -> Decision | None:
    if cmd_name in DB_CLIENT_COMMANDS and has_db_inline_execution(args) and destructive_sql_text(text):
        return Decision("deny", "database destructive SQL command is too risky for automatic execution.")
    if cmd_name in {"drop", "truncate", "alter", "delete"} and destructive_sql_text(text):
        return Decision("deny", "database destructive SQL command is too risky for automatic execution.")
    return None


def curl_pipe_shell_decision(command: str) -> bool:
    tokens = split_tokens(command)
    for index, token in enumerate(tokens):
        if token != "|":
            continue
        left = tokens[index - 1 :: -1]
        source = []
        for left_token in left:
            if left_token in SHELL_SEPARATORS:
                break
            source.insert(0, left_token)
        sink = []
        for right_token in tokens[index + 1 :]:
            if right_token in SHELL_SEPARATORS:
                break
            sink.append(right_token)
        if not source or PathLikeCommand(source[0]).name != "curl":
            continue
        while sink and PathLikeCommand(sink[0]).name in WRAPPER_COMMANDS:
            next_sink = wrapper_inner_segment(sink)
            if next_sink == sink:
                break
            sink = next_sink
        if sink and PathLikeCommand(sink[0]).name in SHELL_COMMANDS:
            return True
    return False


def dangerous_verb_decision(cmd_name: str, args: list[str]) -> Decision | None:
    if cmd_name == "truncate":
        if any(arg in {"--help", "-h"} for arg in args):
            return None
        size = option_value(args, "-s") or option_value(args, "--size")
        if size == "0" or any(arg in {"-s0", "--size=0"} for arg in args):
            return Decision("deny", "file truncation is too risky for automatic execution.")
    if cmd_name == "dd":
        output = option_value(args, "of")
        if output and (output.startswith("/dev/") or output.startswith(("/etc/", "/bin/", "/sbin/", "/usr/", "/var/"))):
            return Decision("deny", "raw disk or system-path write is too risky for automatic execution.")
    if cmd_name == "shred":
        return Decision("deny", "secure file deletion is too risky for automatic execution.")
    if cmd_name.startswith("mkfs") or cmd_name == "wipefs":
        return Decision("deny", "filesystem destruction is too risky for automatic execution.")
    if cmd_name == "dropdb":
        return Decision("deny", "database deletion is too risky for automatic execution.")
    if cmd_name == "crontab" and "-r" in args:
        return Decision("deny", "crontab removal is too risky for automatic execution.")
    return None


def segment_decision(segment: list[str]) -> Decision | None:
    if not segment:
        return None
    cmd = PathLikeCommand(segment[0])
    args = [arg.lower() for arg in segment[1:]]
    all_words = re.findall(r"[a-z_]+", " ".join([cmd.name, *args]))

    if cmd.name in WRAPPER_COMMANDS:
        nested = segment_decision(wrapper_inner_segment(segment))
        if nested:
            return nested
    content_decision = sql_content_decision(cmd.name, args, " ".join(segment))
    if content_decision:
        return content_decision
    verb_decision = dangerous_verb_decision(cmd.name, args)
    if verb_decision:
        return verb_decision
    git_args = git_command_args(segment) if cmd.name == "git" else args
    if cmd.name == "git" and git_args[:1] == ["push"]:
        return git_push_decision(git_args[1:])
    if cmd.name == "git" and git_args[:1] == ["branch"]:
        original_args = segment[2:]
        has_combined_force_delete = any(
            a.startswith("-") and not a.startswith("--") and "d" in a and "f" in a for a in git_args
        )
        is_force_delete = (
            any(a == "-D" for a in original_args)
            or has_combined_force_delete
            or (any(a in {"-d", "--delete"} for a in git_args) and any(a in {"--force", "-f"} for a in git_args))
        )
        if is_force_delete:
            return Decision("warn", "git branch -D can lose unmerged commits; confirm the branch is fully merged or backed up before proceeding.")
    if cmd.name == "git" and git_args[:1] == ["checkout"] and "." in git_args:
        return Decision("warn", "git checkout . discards all unstaged changes; confirm no uncommitted work will be lost before proceeding.")
    if cmd.name == "git" and git_args[:1] == ["restore"] and "." in git_args:
        return Decision("warn", "git restore . discards unstaged changes; confirm no uncommitted work will be lost before proceeding.")
    if cmd.name == "git" and git_args[:1] == ["stash"] and git_args[1:2] == ["drop"]:
        return Decision("warn", "git stash drop permanently removes stashed work; confirm the stash is no longer needed before proceeding.")
    if cmd.name == "git" and git_args[:1] == ["clean"] and not is_dry_run(git_args):
        if any("x" in arg for arg in git_args if arg.startswith("-")):
            return Decision("deny", "destructive git cleanup including ignored files is too risky for automatic execution.")
        return Decision("warn", "destructive git cleanup requires explicit user approval and safety review.")
    if cmd.name == "git" and git_args[:1] == ["reset"] and "--hard" in git_args:
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
    if cmd.name == "rm":
        rm_cleanup_decision = rm_decision(segment[1:])
        if rm_cleanup_decision:
            return rm_cleanup_decision
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
            # AST + text scan of the -c source; advisory only (see python_source_decision).
            return python_source_decision(segment[index + 2])
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


def extract_command_substitutions(command: str) -> list[str]:
    """Return inner command strings from $(...) and backtick substitutions.

    Without this the tokenizer treats `$(git push origin main)` as opaque
    arguments, so a destructive command wrapped in a substitution would bypass
    the guard. Arithmetic expansion $(( ... )) is skipped."""
    results: list[str] = []
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if char == "$" and index + 1 < length and command[index + 1] == "(":
            if index + 2 < length and command[index + 2] == "(":
                index += 2  # arithmetic expansion $(( ... )), not a command
                continue
            depth = 0
            cursor = index + 1
            while cursor < length:
                if command[cursor] == "(":
                    depth += 1
                elif command[cursor] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                cursor += 1
            if depth == 0:
                results.append(command[index + 2 : cursor])
                index = cursor + 1
                continue
        if char == "`":
            end = command.find("`", index + 1)
            if end != -1:
                results.append(command[index + 1 : end])
                index = end + 1
                continue
        index += 1
    return results


def evaluate_command(command: str) -> Decision | None:
    raw_decision = raw_command_decision(command)
    if raw_decision:
        return raw_decision
    warning: Decision | None = None
    for inner in extract_command_substitutions(command):
        decision = evaluate_command(inner)
        if decision:
            if decision.kind == "deny":
                return decision
            warning = warning or decision
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

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


try:
    from scripts.hooks.memory_flags import memory_enabled
    from scripts.hooks.memory_telemetry import append_memory_telemetry
    from scripts.hooks.redact import SecretFoundError, assert_no_secrets, redact
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.hooks.memory_flags import memory_enabled
    from scripts.hooks.memory_telemetry import append_memory_telemetry
    from scripts.hooks.redact import SecretFoundError, assert_no_secrets, redact


ALLOWED_ROLES = {"user", "assistant"}
RAW_DIR = Path("memory") / ".staging" / "raw_memories"
TTL_DAYS = 14
CAPSULE_COMMENT_RE = re.compile(r"<!--\s*dotfiles-context-capsule\s*-->.*", re.I | re.S)
MEMORY_SEGMENT_RE = re.compile(r"<dotfiles-memory>.*?</dotfiles-memory>", re.I | re.S)
LEGACY_CAPSULE_RE = re.compile(r"<dotfiles-capsule>.*?</dotfiles-capsule>", re.I | re.S)
SIGNAL_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("preference", re.compile(r"(?i)\b(?:remember|prefer|preference|以后|偏好|约定)\b")),
    ("decision", re.compile(r"(?i)\b(?:decision|decided|use|choose|采用|决定)\b")),
    ("correction", re.compile(r"(?i)\b(?:correction|actually|不要再|更正|纠正)\b")),
    ("failure-mode", re.compile(r"(?i)\b(?:failure mode|lesson|avoid|教训|失败模式)\b")),
    ("fact", re.compile(r"(?i)\b(?:fact|stable|in this repo|事实|固定)\b")),
)
ANTI_SELF_POISONING_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "negative_tool_claim",
        re.compile(r"(?i)\b(?:cannot|can't|can not|unable to|does not work|doesn't work|broken|unusable|不能用|坏了)\b"),
    ),
    (
        "transient_environment_failure",
        re.compile(
            r"(?i)\b(?:command not found|no such file|missing binary|missing credential|credential.*missing|permission denied|PATH (?:not set|not configured)|not configured|缺二进制|缺凭证|未配置凭证|PATH 未配置)\b"
        ),
    ),
    ("one_time_task_narration", re.compile(r"(?i)\b(?:this session|one[- ]time|temporary todo|一次性任务|本轮任务)\b")),
)
TASK_NARRATION_RE = re.compile(r"(?i)\b(?:changed|ran tests|updated file|implemented|fixed|this session|本轮|临时|todo)\b")
# Harness/capsule machinery that an agent may echo back into a transcript. These
# strings are high-precision: they appear in skill prompts, boundary capsules,
# compact-recovery capsules and system reminders, never in a genuine user/agent
# memory exchange. Without this gate the noise passes the broad SIGNAL_RULES
# (it contains words like "use"/"decision") and pollutes the candidate pool —
# the junk candidate that broke consolidation gate 2.
CAPSULE_NOISE_RE = re.compile(
    r"(?i)(?:"
    r"###\s*Skill:"
    r"|Base directory for this skill"
    r"|Boundary facts:"
    r"|Boundary decisions:"
    r"|Risk types:"
    r"|Compact Recovery Capsule"
    r"|TaskCheckpoint:"
    r"|system-reminder"
    r"|This context may or may not be relevant"
    r"|dotfiles-context-capsule"
    r"|These instructions OVERRIDE"
    r"|Skill 路由"
    r")"
)


@dataclass(frozen=True)
class NormalizedRecord:
    role: str
    text: str


@dataclass
class AdapterStats:
    total: int = 0
    skipped_reasons: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.skipped_reasons[reason] = self.skipped_reasons.get(reason, 0) + 1


@dataclass(frozen=True)
class CaptureResult:
    status: str
    reason: str = ""
    path: Path | None = None
    candidate_id: str = ""
    skipped_reasons: dict[str, int] = field(default_factory=dict)


def emit_capture_telemetry(root: Path, result: CaptureResult, *, platform: str = "", duration_ms: int = 0) -> None:
    append_memory_telemetry(
        "capture",
        "memory_capture",
        {
            "duration_ms": max(0, duration_ms),
            "status": result.status,
            "reason": result.reason,
            "candidate_count": 1 if result.candidate_id else 0,
            "candidate_written": result.status == "written",
            "candidate_id": result.candidate_id,
            "platform": platform,
            "skipped_reasons": result.skipped_reasons,
        },
        root=root,
    )


def load_json_lines(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _role_and_text(record: dict[str, Any]) -> tuple[str, str, str | None]:
    if "payload" in record and isinstance(record["payload"], dict):
        payload = record["payload"]
        return str(payload.get("role") or "").lower(), _content_to_text(payload.get("content")), None
    message = record.get("message")
    if isinstance(message, dict):
        role = str(message.get("role") or record.get("role") or record.get("type") or "").lower()
        if role == "compaction_state" or "summaryText" in message:
            return role, "", "compaction_state"
        return role, _content_to_text(message.get("content")), None
    role = str(record.get("role") or record.get("type") or "").lower()
    return role, _content_to_text(record.get("content")), None


def normalize_records(platform: str, records: list[dict[str, Any]]) -> tuple[list[NormalizedRecord], AdapterStats]:
    stats = AdapterStats(total=len(records))
    normalized: list[NormalizedRecord] = []
    for record in records:
        role, text, forced_skip = _role_and_text(record)
        if forced_skip:
            stats.skip(forced_skip)
            continue
        if role not in ALLOWED_ROLES:
            stats.skip("unsupported_role")
            continue
        clean = strip_injected_segments(text).strip()
        if not clean:
            stats.skip("empty_text")
            continue
        normalized.append(NormalizedRecord(role=role, text=clean))
    return normalized, stats


def strip_injected_segments(text: str) -> str:
    text = MEMORY_SEGMENT_RE.sub("", text)
    text = LEGACY_CAPSULE_RE.sub("", text)
    text = CAPSULE_COMMENT_RE.sub("", text)
    return text


def _signal_for(text: str) -> str | None:
    for category, pattern in SIGNAL_RULES:
        if pattern.search(text):
            return category
    return None


def _anti_self_poisoning_reason(text: str) -> str | None:
    for reason, pattern in ANTI_SELF_POISONING_RULES:
        if pattern.search(text):
            return reason
    return None


def _origin_session(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "-", value).strip("-")
    return cleaned[:80] or "unknown-session"


def classify_origin_scope(directory: str, root: Path) -> tuple[str, str]:
    """Map the originating session's directory to (origin_project, scope).

    Scope is "project" for a real project repo (origin_project = its basename),
    and "user" for general work: the dotfiles repo itself, the home dir, or the
    agent config dirs (~/.claude, ~/.config). Home is derived as the dotfiles
    root's parent so this is testable with synthetic roots. Unknown/empty → user.
    """
    d = (directory or "").strip()
    if not d:
        return "", "user"
    try:
        p = Path(d).expanduser().resolve()
        root_r = root.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return "", "user"
    home = root_r.parent
    if p == root_r or p == home or p.is_relative_to(root_r):
        return "", "user"
    if p.is_relative_to(home / ".claude") or p.is_relative_to(home / ".config"):
        return "", "user"
    name = p.name
    if name in {"", ".dotfiles", "dotfiles"}:
        return "", "user"
    return name, "project"


def _summary_from(text: str, category: str) -> str:
    trimmed = re.sub(r"\s+", " ", text).strip()
    trimmed = re.sub(r"(?i)^\s*(remember|decision|correction)\s*[:：-]?\s*", "", trimmed).strip()
    return f"{category}: {trimmed[:160]}"


def _canonical_for_hash(candidate: dict[str, Any]) -> str:
    stable = {key: value for key, value in candidate.items() if key not in {"id", "created_at"}}
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _candidate_id(candidate: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_for_hash(candidate).encode("utf-8")).hexdigest()


def _build_candidate_with_skips(
    records: list[NormalizedRecord], *, platform: str, origin_session: str,
    origin_dir: str = "", root: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    skipped: dict[str, int] = {}
    origin_project, scope = classify_origin_scope(origin_dir, root or Path.cwd())

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    for record in records:
        text = strip_injected_segments(record.text).strip()
        if not text:
            skip("empty_text")
            continue
        if CAPSULE_NOISE_RE.search(text):
            skip("capsule_noise")
            continue
        category = _signal_for(text)
        if not category:
            skip("no_signal")
            continue
        if TASK_NARRATION_RE.search(text) and category not in {"preference", "decision", "correction"}:
            skip("task_narration")
            continue
        if _anti_self_poisoning_reason(text):
            skip("anti_self_poisoning")
            continue
        summary = redact(_summary_from(text, category))
        evidence_text = redact(text[:500])
        implication = redact(f"Future agents can apply this {category} when working in similar dotfiles memory tasks.")
        candidate: dict[str, Any] = {
            "summary": summary,
            "evidence": f"Evidence: {evidence_text}",
            "implication": implication,
            "category": category,
            "origin_session": _origin_session(origin_session),
            "origin_project": origin_project,
            "scope": scope,
            "source_platform": platform,
            "source_roles": [record.role],
            "created_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        try:
            assert_no_secrets(
                "\n".join([candidate["summary"], candidate["evidence"], candidate["implication"]]),
                source="raw_memory_candidate",
            )
        except SecretFoundError:
            skip("secret_rejected")
            continue
        candidate["id"] = _candidate_id(candidate)
        return candidate, skipped
    return None, skipped


def build_candidate(
    records: list[NormalizedRecord], *, platform: str, origin_session: str,
    origin_dir: str = "", root: Path | None = None,
) -> dict[str, Any] | None:
    candidate, _skipped = _build_candidate_with_skips(
        records, platform=platform, origin_session=origin_session, origin_dir=origin_dir, root=root
    )
    return candidate


def canonical_json(candidate: dict[str, Any]) -> str:
    return json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def same_stable_candidate(existing_text: str, candidate: dict[str, Any]) -> bool:
    try:
        existing = json.loads(existing_text)
    except json.JSONDecodeError:
        return False
    return isinstance(existing, dict) and _canonical_for_hash(existing) == _canonical_for_hash(candidate)


def candidate_secret_scan_text(candidate: dict[str, Any]) -> str:
    fields = ["summary", "evidence", "implication"]
    return "\n".join(str(candidate.get(field) or "") for field in fields)


def raw_dir(root: Path) -> Path:
    return root / RAW_DIR


def gitignore_allows_raw_staging(root: Path, target: Path) -> bool:
    relative = target.relative_to(root)
    result = subprocess.run(["git", "check-ignore", "-q", relative.as_posix()], cwd=root, check=False)
    return result.returncode == 0


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_raw_candidate(root: Path, candidate: dict[str, Any]) -> CaptureResult:
    root = root.resolve()
    target_dir = raw_dir(root)
    candidate_id = str(candidate.get("id") or _candidate_id(candidate))
    candidate = {**candidate, "id": candidate_id}
    target = target_dir / f"{candidate_id}.json"
    if not gitignore_allows_raw_staging(root, target):
        return CaptureResult(status="gitignore_refused", reason="memory/.staging/raw_memories is not ignored", candidate_id=candidate_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    text = canonical_json(candidate)
    assert_no_secrets(candidate_secret_scan_text(candidate), source=str(target.relative_to(root)))
    lock_path = target_dir / ".lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if target.exists():
            existing = target.read_text(encoding="utf-8", errors="replace")
            if same_stable_candidate(existing, candidate):
                return CaptureResult(status="deduped", path=target, candidate_id=candidate_id)
            remediation = target_dir / f"{target.name}.{int(time.time())}.bak"
            remediation.write_text(
                canonical_json({"status": "drift_refused", "candidate_id": candidate_id, "existing_size": len(existing)}),
                encoding="utf-8",
            )
            return CaptureResult(status="drift_refused", reason="target differs from canonical candidate", path=target, candidate_id=candidate_id)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{candidate_id}.", suffix=".tmp", dir=target_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
            _fsync_dir(target_dir)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink()
        return CaptureResult(status="written", path=target, candidate_id=candidate_id)


def resolve_codex_rollout(session_id: str, home: Path | None = None) -> Path | None:
    if not session_id:
        return None
    base = (home or Path.home()) / ".codex" / "sessions"
    if not base.exists():
        return None
    candidates = sorted(base.glob(f"**/rollout-*{session_id}*"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def capture_from_records(
    root: Path,
    *,
    platform: str,
    records: list[dict[str, Any]],
    origin_session: str,
    origin_dir: str = "",
    env: dict[str, str] | None = None,
) -> CaptureResult:
    if not memory_enabled(env):
        return CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
    normalized, stats = normalize_records(platform, records)
    candidate, candidate_skips = _build_candidate_with_skips(
        normalized, platform=platform, origin_session=origin_session, origin_dir=origin_dir, root=root
    )
    stats.skipped_reasons.update({key: stats.skipped_reasons.get(key, 0) + value for key, value in candidate_skips.items()})
    if not candidate:
        reason = "secret_rejected" if stats.skipped_reasons.get("secret_rejected") else "no memory-worthy candidate"
        return CaptureResult(status="skipped", reason=reason, skipped_reasons=stats.skipped_reasons)
    return write_raw_candidate(root, candidate)


def capture_from_hook_input(root: Path, hook_input: dict[str, Any], env: dict[str, str] | None = None) -> CaptureResult:
    started = time.monotonic()
    platform = str(hook_input.get("platform") or hook_input.get("agent") or "cc").lower()
    if os.environ.get("DOTFILES_MEMORY_CAPTURE_FORCE_ERROR"):
        raise RuntimeError("forced memory capture error")
    if not memory_enabled(env):
        result = CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
        emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
        return result
    transcript_path = str(hook_input.get("transcript_path") or "").strip()
    session_id = str(hook_input.get("session_id") or hook_input.get("sessionID") or "").strip()
    path = Path(transcript_path).expanduser() if transcript_path else None
    if not path or not path.exists():
        rollout = resolve_codex_rollout(session_id) if platform == "codex" else None
        path = rollout
    if not path:
        result = CaptureResult(status="unavailable", reason="transcript_unavailable")
        emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
        return result
    records = load_json_lines(path)
    origin_dir = str(hook_input.get("cwd") or hook_input.get("workspace") or "").strip()
    result = capture_from_records(root, platform=platform, records=records, origin_session=session_id or path.stem, origin_dir=origin_dir, env=env)
    emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
    return result


def _env_source(env: dict[str, str] | None) -> dict[str, str]:
    return dict(os.environ) if env is None else env


def sqlite_db_path(platform: str, env: dict[str, str] | None = None) -> Path:
    """安装版 kilo/opencode session 库路径;可经 DOTFILES_MEMORY_<PLATFORM>_DB 覆盖(测试用)。"""
    override = _env_source(env).get(f"DOTFILES_MEMORY_{platform.upper()}_DB", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / platform / f"{platform}.db"


def _sqlite_session_directory(con: sqlite3.Connection, sid: str) -> str:
    """Best-effort: the originating cwd for a kilo/opencode session (for scope
    tagging). The session table carries `directory`; if the schema differs or the
    row is absent, return "" so scope falls back to user (fail-open)."""
    try:
        row = con.execute("SELECT directory FROM session WHERE id = ?", (sid,)).fetchone()
        return str(row[0]) if row and row[0] else ""
    except sqlite3.Error:
        return ""


def read_sqlite_session_records(db: Path, session_id: str = "") -> tuple[list[dict[str, Any]], str, str]:
    """immutable 只读(零锁、不碰 live 写)抽指定/最近 session 的 {role,content} 记录。

    安装版 schema = message/part,role 在 message.data JSON、text 在 part.data JSON。
    role 白名单 / 注入剥离 / redact 由下游 capture_from_records pipeline 统一处理。
    返回 (records, sid, directory);directory 用于 scope 标记,取不到为 ""。
    """
    con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True, timeout=2)
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"message", "part"} <= tables:
            raise RuntimeError("unsupported_sqlite_schema")
        sid = session_id
        if not sid:
            row = con.execute("SELECT session_id FROM message ORDER BY time_created DESC LIMIT 1").fetchone()
            sid = row[0] if row else ""
        if not sid:
            return [], "", ""
        rows = con.execute(
            "SELECT json_extract(m.data,'$.role') AS role, json_extract(p.data,'$.text') AS text "
            "FROM part p JOIN message m ON p.message_id = m.id "
            "WHERE m.session_id = ? AND json_extract(p.data,'$.type') = 'text' "
            "ORDER BY p.time_created",
            (sid,),
        ).fetchall()
        records = [{"role": role, "content": text} for role, text in rows if role and text]
        return records, sid, _sqlite_session_directory(con, sid)
    finally:
        con.close()


def capture_from_sqlite(root: Path, *, platform: str, session_id: str = "", env: dict[str, str] | None = None) -> CaptureResult:
    """从 kilo/opencode 的 SQLite session 库捕获候选(替代旧的 unavailable 降级)。"""
    started = time.monotonic()
    if not memory_enabled(env):
        result = CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
        emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
        return result
    db = sqlite_db_path(platform, env)
    if not db.exists():
        result = CaptureResult(status="unavailable", reason="sqlite_db_not_found")
        emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
        return result
    try:
        records, origin, origin_dir = read_sqlite_session_records(db, session_id)
    except Exception as exc:  # noqa: BLE001 - 捕获 hook 必须 fail-open,绝不打断会话。
        result = CaptureResult(status="unavailable", reason=f"sqlite_read_failed:{exc.__class__.__name__}")
        emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
        return result
    if not records:
        result = CaptureResult(status="unavailable", reason="no_session_records")
        emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
        return result
    result = capture_from_records(root, platform=platform, records=records, origin_session=origin or session_id or db.stem, origin_dir=origin_dir, env=env)
    emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
    return result


def capture_sqlite_for_session(
    root: Path, *, session_id: str, env: dict[str, str] | None = None, platforms: tuple[str, ...] = ("opencode", "kilo")
) -> CaptureResult:
    """kilo/opencode 共用 .mjs、运行时分不清平台 → 按 session_id 在候选库里定位(session id 唯一)。"""
    started = time.monotonic()
    if not memory_enabled(env):
        result = CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
        emit_capture_telemetry(root, result, platform="sqlite", duration_ms=int((time.monotonic() - started) * 1000))
        return result
    if not session_id:
        result = CaptureResult(status="unavailable", reason="no_session_id")
        emit_capture_telemetry(root, result, platform="sqlite", duration_ms=int((time.monotonic() - started) * 1000))
        return result
    for platform in platforms:
        db = sqlite_db_path(platform, env)
        if not db.exists():
            continue
        try:
            records, origin, origin_dir = read_sqlite_session_records(db, session_id)
        except Exception:  # noqa: BLE001 - fail-open:某库读失败不阻断,试下一个。
            continue
        if records:
            result = capture_from_records(root, platform=platform, records=records, origin_session=origin or session_id, origin_dir=origin_dir, env=env)
            emit_capture_telemetry(root, result, platform=platform, duration_ms=int((time.monotonic() - started) * 1000))
            return result
    result = CaptureResult(status="unavailable", reason="session_not_found_in_any_sqlite")
    emit_capture_telemetry(root, result, platform="sqlite", duration_ms=int((time.monotonic() - started) * 1000))
    return result


def capture_from_platform(root: Path, *, platform: str, session_id: str = "", env: dict[str, str] | None = None) -> CaptureResult:
    if not memory_enabled(env):
        result = CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
        emit_capture_telemetry(root, result, platform=platform, duration_ms=0)
        return result
    if platform in {"opencode", "kilo"}:
        return capture_from_sqlite(root, platform=platform, session_id=session_id, env=env)
    result = CaptureResult(status="unavailable", reason="platform_capture_unavailable")
    emit_capture_telemetry(root, result, platform=platform, duration_ms=0)
    return result


def capture_best_effort(root: Path, hook_input: dict[str, Any], env: dict[str, str] | None = None) -> CaptureResult:
    try:
        return capture_from_hook_input(root, hook_input, env=env)
    except Exception as exc:  # noqa: BLE001 - hook side effect must be fail-open.
        if os.environ.get("DOTFILES_MEMORY_CAPTURE_LOG"):
            Path(os.environ["DOTFILES_MEMORY_CAPTURE_LOG"]).expanduser().write_text(f"memory capture failed: {exc}\n", encoding="utf-8")
        result = CaptureResult(status="error", reason=exc.__class__.__name__)
        emit_capture_telemetry(root, result, platform=str(hook_input.get("platform") or hook_input.get("agent") or "cc").lower(), duration_ms=0)
        return result


def gc_raw_memories(root: Path, ttl_days: int = TTL_DAYS) -> list[Path]:
    directory = raw_dir(root)
    if not directory.exists():
        return []
    cutoff = time.time() - ttl_days * 24 * 60 * 60
    removed: list[Path] = []
    candidates = sorted(list(directory.glob("*.json")) + list(directory.glob("*.bak")))
    for path in candidates:
        if path.stat().st_mtime >= cutoff:
            continue
        path.unlink()
        removed.append(path)
    return removed


def result_payload(result: CaptureResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "reason": result.reason,
        "path": str(result.path) if result.path else "",
        "candidate_id": result.candidate_id,
        "skipped_reasons": result.skipped_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture raw memory candidates from hook transcripts.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--hook-json", help="Path to hook JSON input, or '-' for stdin")
    parser.add_argument("--platform", choices=("cc", "droid", "codex", "opencode", "kilo"))
    parser.add_argument("--session-id", default="")
    parser.add_argument("--sqlite-session", default="", help="kilo/opencode 按 session_id 自动定位库捕获(.mjs idle 调用)")
    parser.add_argument("--gc", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.gc:
        removed = gc_raw_memories(root)
        print(json.dumps({"status": "gc", "removed": [str(path) for path in removed]}, ensure_ascii=False))
        return 0
    if args.sqlite_session:
        result = capture_sqlite_for_session(root, session_id=args.sqlite_session)
        if os.environ.get("DOTFILES_MEMORY_CAPTURE_DEBUG"):
            print(json.dumps(result_payload(result), ensure_ascii=False))
        return 0
    if args.platform in {"opencode", "kilo"}:
        print(json.dumps(result_payload(capture_from_platform(root, platform=args.platform, session_id=args.session_id)), ensure_ascii=False))
        return 0
    hook_input: dict[str, Any] = {}
    if args.hook_json:
        raw = sys.stdin.read() if args.hook_json == "-" else Path(args.hook_json).read_text(encoding="utf-8")
        hook_input = json.loads(raw) if raw.strip() else {}
    result = capture_best_effort(root, hook_input)
    if os.environ.get("DOTFILES_MEMORY_CAPTURE_DEBUG"):
        print(json.dumps(result_payload(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

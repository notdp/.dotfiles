#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


try:
    from scripts.hooks.memory_flags import memory_enabled
    from scripts.hooks.redact import SecretFoundError, assert_no_secrets, redact
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.hooks.memory_flags import memory_enabled
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
    records: list[NormalizedRecord], *, platform: str, origin_session: str
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    skipped: dict[str, int] = {}

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    for record in records:
        text = strip_injected_segments(record.text).strip()
        if not text:
            skip("empty_text")
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


def build_candidate(records: list[NormalizedRecord], *, platform: str, origin_session: str) -> dict[str, Any] | None:
    candidate, _skipped = _build_candidate_with_skips(records, platform=platform, origin_session=origin_session)
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
    env: dict[str, str] | None = None,
) -> CaptureResult:
    if not memory_enabled(env):
        return CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
    normalized, stats = normalize_records(platform, records)
    candidate, candidate_skips = _build_candidate_with_skips(normalized, platform=platform, origin_session=origin_session)
    stats.skipped_reasons.update({key: stats.skipped_reasons.get(key, 0) + value for key, value in candidate_skips.items()})
    if not candidate:
        reason = "secret_rejected" if stats.skipped_reasons.get("secret_rejected") else "no memory-worthy candidate"
        return CaptureResult(status="skipped", reason=reason, skipped_reasons=stats.skipped_reasons)
    return write_raw_candidate(root, candidate)


def capture_from_hook_input(root: Path, hook_input: dict[str, Any], env: dict[str, str] | None = None) -> CaptureResult:
    if os.environ.get("DOTFILES_MEMORY_CAPTURE_FORCE_ERROR"):
        raise RuntimeError("forced memory capture error")
    if not memory_enabled(env):
        return CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
    platform = str(hook_input.get("platform") or hook_input.get("agent") or "cc").lower()
    transcript_path = str(hook_input.get("transcript_path") or "").strip()
    session_id = str(hook_input.get("session_id") or hook_input.get("sessionID") or "").strip()
    path = Path(transcript_path).expanduser() if transcript_path else None
    if not path or not path.exists():
        rollout = resolve_codex_rollout(session_id) if platform == "codex" else None
        path = rollout
    if not path:
        return CaptureResult(status="unavailable", reason="transcript_unavailable")
    records = load_json_lines(path)
    return capture_from_records(root, platform=platform, records=records, origin_session=session_id or path.stem, env=env)


def capture_from_platform(root: Path, *, platform: str, session_id: str = "", env: dict[str, str] | None = None) -> CaptureResult:
    if not memory_enabled(env):
        return CaptureResult(status="disabled", reason="DOTFILES_MEMORY_ENABLED is not enabled")
    if platform in {"opencode", "kilo"}:
        return CaptureResult(status="unavailable", reason="assistant_text_unavailable")
    return CaptureResult(status="unavailable", reason="platform_capture_unavailable")


def capture_best_effort(root: Path, hook_input: dict[str, Any], env: dict[str, str] | None = None) -> CaptureResult:
    try:
        return capture_from_hook_input(root, hook_input, env=env)
    except Exception as exc:  # noqa: BLE001 - hook side effect must be fail-open.
        if os.environ.get("DOTFILES_MEMORY_CAPTURE_LOG"):
            Path(os.environ["DOTFILES_MEMORY_CAPTURE_LOG"]).expanduser().write_text(f"memory capture failed: {exc}\n", encoding="utf-8")
        return CaptureResult(status="error", reason=exc.__class__.__name__)


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
    parser.add_argument("--gc", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.gc:
        removed = gc_raw_memories(root)
        print(json.dumps({"status": "gc", "removed": [str(path) for path in removed]}, ensure_ascii=False))
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

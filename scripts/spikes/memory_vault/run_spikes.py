#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SECTION_IDS = ["S1", "S2", "S3", "S4", "S5", "S6"]
CURRENT_SECRET_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{8,}|(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+)"
)
TARGET_SECRET_RE = re.compile(
    r"(?is)("
    r"AKIA[0-9A-Z]{16}|"
    r"gh[pousr]_[A-Za-z0-9_]{30,}|"
    r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----|"
    r"(?:postgres|mysql|mongodb|redis)://[^\s'\"]+|"
    r"\b[a-f0-9]{32,}\b|"
    r"(?:api[_ -]?key|token|password|secret)\s+(?:is|=|:)\s*[^\s,;.]+"
    r")"
)


@dataclass
class Section:
    sid: str
    title: str
    status: str
    method: str
    conclusion: str
    evidence: list[str] = field(default_factory=list)
    plan_revision: str = ""
    data: dict[str, Any] = field(default_factory=dict)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl_records(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def stringify_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    if isinstance(value, dict):
        return stringify_content(value.get("text") or value.get("content") or "")
    return ""


def normalize_record(record: dict[str, Any]) -> tuple[dict[str, str] | None, str | None]:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else None
    message = record.get("message") if isinstance(record.get("message"), dict) else None
    source = payload or message or record
    role = source.get("role") or source.get("type")
    text = stringify_content(source.get("content"))
    if isinstance(role, str) and text.strip():
        return {"role": role, "text": text.strip()}, None
    return None, "unsupported record shape"


def probe_stop_payloads(evidence_dir: Path) -> Section:
    transcript = evidence_dir / "synthetic_transcript.jsonl"
    transcript.write_text(json.dumps({"role": "assistant", "content": "synthetic stop payload"}) + "\n", encoding="utf-8")
    payloads = {
        "cc": {"hook_event_name": "Stop", "transcript_path": str(transcript)},
        "droid": {"hook_event_name": "Stop", "transcript_path": str(transcript)},
        "codex": {"hook_event_name": "Stop", "session_id": "phase01-synthetic-session"},
    }
    payload_path = evidence_dir / "stop_payloads.synthetic.json"
    payload_path.write_text(json.dumps(payloads, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    started = time.perf_counter()
    codex_root = Path.home() / ".codex" / "sessions"
    candidates = sorted(codex_root.glob("*/*/*/rollout-*.jsonl")) if codex_root.exists() else []
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    readable = [str(path) for path in candidates[-5:] if path.is_file() and os.access(path, os.R_OK)]
    fallback = {
        "root": str(codex_root),
        "candidate_count": len(candidates),
        "readable_recent": readable,
        "elapsed_ms": elapsed_ms,
        "session_id_mapping_validated": False,
        "mapping_note": "Auto probe only proves bounded glob/readability; QA8 must validate real session_id -> rollout mapping.",
    }
    fallback_path = evidence_dir / "codex_rollout_fallback.json"
    fallback_path.write_text(json.dumps(fallback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    platform_status = {
        name: {
            "status": "PASS" if payload.get("transcript_path") or (name == "codex" and elapsed_ms < 10000) else "REVISION",
            "keys": sorted(payload.keys()),
            "has_transcript_path": isinstance(payload.get("transcript_path"), str),
        }
        for name, payload in payloads.items()
    }
    codex_ok = elapsed_ms < 10000 and bool(readable)
    status = "PASS" if codex_ok else "REVISION"
    return Section(
        "S1",
        "Stop Hook Payloads",
        status,
        "Generate synthetic cc/droid/codex Stop payloads and run a read-only codex rollout glob under ~/.codex/sessions.",
        "Auto evidence is synthetic shape only for cc/droid/codex payload keys; real hook stdin reachability is UNVALIDATED until manual QA8. Codex fallback only proves glob/readability under 10s, not session_id mapping. "
        + ("Readable rollout evidence exists." if codex_ok else "No readable rollout match was proven in this run; live payload smoke remains a gate."),
        [f"payloads={payload_path}", f"codex_fallback={fallback_path}", f"platform_status={json.dumps(platform_status, ensure_ascii=False)}"],
        "Codex Stop payload/fallback must be confirmed with a real session before later capture work is treated as unblocked." if not codex_ok else "",
        {"platform_status": platform_status, "fallback": fallback},
    )


def inspect_sqlite(db_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(db_path), "exists": db_path.exists(), "tables": [], "assistant_snippets": []}
    if not db_path.exists():
        return result
    uri = f"file:{db_path}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=1) as conn:
            tables = [row[0] for row in conn.execute("select name from sqlite_master where type='table' order by name")]
            result["tables"] = tables
            result["schemas"] = {
                name: [row[1] for row in conn.execute(f"pragma table_info({name})")]
                for name in tables
                if name in {"message", "message_v2", "part", "part_v2"}
            }
            for table in ["part", "part_v2", "message_v2", "message"]:
                if table not in tables:
                    continue
                columns = result["schemas"].get(table) or [row[1] for row in conn.execute(f"pragma table_info({table})")]
                text_col = next((col for col in ["text", "content", "body"] if col in columns), None)
                role_col = next((col for col in ["role", "type"] if col in columns), None)
                if not text_col:
                    continue
                where = f"where lower({role_col}) like '%assistant%'" if role_col else ""
                query = f"select {text_col} from {table} {where} order by rowid desc limit 3"
                for (text,) in conn.execute(query):
                    if isinstance(text, str) and text.strip():
                        result["assistant_snippets"].append({"table": table, "text": text.strip()[:160]})
                if result["assistant_snippets"]:
                    break
    except sqlite3.Error as exc:
        result["error"] = str(exc)
    return result


def probe_assistant_text(evidence_dir: Path, repo_root: Path) -> Section:
    plugin_path = repo_root / "scripts" / "opencode" / "dotfiles_hooks.mjs"
    plugin_text = plugin_path.read_text(encoding="utf-8", errors="replace") if plugin_path.exists() else ""
    transform_static = "experimental.chat.messages.transform" in plugin_text
    chat_message_static = '"chat.message"' in plugin_text or "'chat.message'" in plugin_text
    db_info = inspect_sqlite(Path.home() / ".local" / "share" / "opencode" / "opencode.db")
    evidence = {
        "plugin_path": str(plugin_path),
        "has_experimental_chat_messages_transform_static": transform_static,
        "has_chat_message_static": chat_message_static,
        "sqlite": db_info,
    }
    evidence_path = evidence_dir / "assistant_text_probe.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected = "sqlite" if db_info.get("assistant_snippets") else ""
    status = "PASS" if selected else "REVISION"
    return Section(
        "S2",
        "Kilo/Opencode Assistant Text Reachability",
        status,
        "Statically inspect plugin hook names and read-only inspect ~/.local/share/opencode/opencode.db schema/recent assistant rows if present.",
        ("SQLite contains recent assistant snippets and is the selected capture path." if selected else "No assistant text capture path was proven automatically; manual kilo/opencode runtime confirmation is required."),
        [f"assistant_probe={evidence_path}", f"selected_path={selected or 'none'}"],
        "If transform runtime and SQLite both remain unavailable in manual QA, downgrade to user-side capture or revise Phase 05 adapter plan." if not selected else "",
        evidence,
    )


def probe_transcript_adapter(evidence_dir: Path) -> Section:
    records = [
        {"payload": {"role": "assistant", "content": [{"type": "text", "text": "codex payload text"}]}},
        {"message": {"role": "user", "content": "droid message text"}},
        {"role": "assistant", "content": [{"text": "top level text"}]},
        {"payload": {"content": []}},
    ]
    normalized: list[dict[str, str]] = []
    skipped: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        row, reason = normalize_record(record)
        if row:
            normalized.append(row)
        else:
            skipped.append({"index": index, "reason": reason})
    path = evidence_dir / "adapter_fixture_results.json"
    path.write_text(json.dumps({"normalized": normalized, "skipped": skipped}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    required_ok = {("assistant", "codex payload text"), ("user", "droid message text")}.issubset(
        {(row["role"], row["text"]) for row in normalized}
    )
    return Section(
        "S3",
        "Transcript Adapter Normalization",
        "PASS" if required_ok and skipped else "FAIL",
        "Run codex-like payload, droid-like message, top-level, and unsupported fixture records through a minimal normalizer.",
        "Required codex-like and droid-like fixtures normalize to {role,text}; unsupported fixture is reported explicitly." if required_ok and skipped else "Required adapter fixture failed.",
        [f"adapter_results={path}", f"normalized_count={len(normalized)}", f"skipped_count={len(skipped)}"],
        data={"normalized": normalized, "skipped": skipped},
    )


def probe_redact(evidence_dir: Path) -> Section:
    samples = {
        "AWS": "aws_access_key_id=AKIAIOSFODNN7EXAMPLE",
        "GitHub": "token=ghp_abcdefghijklmnopqrstuvwxyz1234567890AB",
        "JWT": "jwt=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.sflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "PEM": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----",
        "connection string": "postgres://user:secretpass@localhost:5432/app",
        "bare hex/high entropy": "0123456789abcdef0123456789abcdef0123456789abcdef",
        "natural-language secret": "the api key is local-demo-secret",
    }
    rows = []
    for family, sample in samples.items():
        rows.append(
            {
                "family": family,
                "current_hit": bool(CURRENT_SECRET_RE.search(sample)),
                "target_hit": bool(TARGET_SECRET_RE.search(sample)),
            }
        )
    precision_samples = {
        "git SHA-1 40hex": "0123456789abcdef0123456789abcdef01234567",
        "MD5 checksum": "d41d8cd98f00b204e9800998ecf8427e",
        "SHA256 checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256 candidate filename": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08.json",
    }
    precision_rows = []
    for family, sample in precision_samples.items():
        precision_rows.append(
            {
                "family": family,
                "should_allow": True,
                "target_hit": bool(TARGET_SECRET_RE.search(sample)),
            }
        )
    path = evidence_dir / "redact_corpus_results.json"
    path.write_text(json.dumps({"positive_rows": rows, "precision_rows": precision_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    all_target = all(row["target_hit"] for row in rows)
    false_positive_count = sum(1 for row in precision_rows if row["target_hit"])
    return Section(
        "S4",
        "Redact Corpus And Target Regex",
        "PASS" if all_target else "FAIL",
        "Compare current context_state SECRET_RE with proposed target regex against required synthetic secret families, then run should-allow precision samples.",
        (
            "Target regex hits all required synthetic families, but precision samples prove the bare-hex branch false-positives on legitimate hashes. Phase 02 redact must add precision fixtures and narrow bare-hex before fail-closed tracked writes."
            if all_target and false_positive_count
            else "Target regex hits all required synthetic families; precision samples did not expose a false positive in this run."
            if all_target
            else "Target regex misses at least one required family."
        ),
        [f"redact_results={path}", "positive_families=" + ", ".join(samples.keys()), "precision_families=" + ", ".join(precision_samples.keys()), f"precision_false_positive_count={false_positive_count}"],
        data={"rows": rows, "precision_rows": precision_rows, "precision_false_positive_count": false_positive_count},
    )


def probe_dual_marker(evidence_dir: Path, repo_root: Path) -> Section:
    node = shutil.which("node")
    if not node:
        return Section("S5", "Opencode Dual-Marker Injection", "FAIL", "Run node synthetic dual-marker probe.", "node is unavailable.", ["node=missing"])
    script = repo_root / "scripts" / "spikes" / "memory_vault" / "dual_marker_probe.mjs"
    result = subprocess.run([node, str(script)], cwd=repo_root, text=True, capture_output=True, check=False, timeout=10)
    out_path = evidence_dir / "dual_marker_probe.json"
    payload: dict[str, Any] = {"returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    try:
        payload["parsed"] = json.loads(result.stdout)
    except json.JSONDecodeError:
        pass
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = result.returncode == 0 and payload.get("parsed", {}).get("ok") is True
    return Section(
        "S5",
        "Opencode Dual-Marker Injection",
        "PASS" if ok else "FAIL",
        "Run synthetic full-schema text part through a dual marker probe twice under node.",
        "Dual-marker idempotency and no-new-part behavior are verified. Budget enforcement is not covered by this spike and remains Phase 03 work." if ok else "Dual marker probe failed.",
        [f"dual_marker_probe={out_path}", f"returncode={result.returncode}"],
        data=payload,
    )


def write_candidate(directory: Path, text: str) -> Path:
    path = directory / f"{sha256_text(text)}.json"
    path.write_text(json.dumps({"text": text}, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def stale_guarded_write(path: Path, expected: str, replacement: str) -> dict[str, Any]:
    current = path.read_text(encoding="utf-8")
    if current != expected:
        bak = path.with_suffix(path.suffix + ".bak")
        bak.write_text(replacement, encoding="utf-8")
        return {"ok": False, "reason": "external-drift", "bak": str(bak), "current": current}
    path.write_text(replacement, encoding="utf-8")
    return {"ok": True}


def probe_staging_drift(evidence_dir: Path) -> Section:
    with tempfile.TemporaryDirectory(prefix="memory-vault-spike-") as tmp:
        tmp_path = Path(tmp)
        candidate_dir = tmp_path / "raw_memories"
        candidate_dir.mkdir()
        candidates = [f"candidate-{index}" for index in range(12)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(lambda text: write_candidate(candidate_dir, text), candidates))
        unique_files_ok = len({path.name for path in paths}) == len(candidates) == len(list(candidate_dir.glob("*.json")))

        drift_file = tmp_path / "topic.md"
        drift_file.write_text("base", encoding="utf-8")
        expected = drift_file.read_text(encoding="utf-8")
        drift_file.write_text("external change", encoding="utf-8")
        drift = stale_guarded_write(drift_file, expected, "replacement")
        snapshot = {
            "unique_files_ok": unique_files_ok,
            "candidate_file_count": len(list(candidate_dir.glob("*.json"))),
            "drift": drift,
            "temp_dir_removed_after_run": True,
        }
    path = evidence_dir / "staging_drift_results.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = unique_files_ok and drift.get("ok") is False and drift.get("reason") == "external-drift" and bool(drift.get("bak"))
    return Section(
        "S6",
        "Staging Concurrency And Drift-Detect",
        "PASS" if ok else "FAIL",
        "Use a temp raw_memories directory for content-fingerprint writes and simulate stale same-file write refusal with .bak remediation.",
        "Independent candidate files are race-free in the prototype; stale write is refused and a .bak remediation artifact is recorded." if ok else "Concurrency or drift prototype failed.",
        [f"staging_drift_results={path}"],
        data=snapshot,
    )


def markdown_table(rows: list[dict[str, Any]], keys: list[str]) -> list[str]:
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")).replace("\n", " ") for key in keys) + " |")
    return lines


def render_findings(sections: list[Section]) -> str:
    lines = ["# Phase 01 Findings — Spike Gate", "", "Generated by `scripts/spikes/memory_vault/run_spikes.py`.", ""]
    for section in sections:
        lines.extend(
            [
                f"## {section.sid} {section.title}",
                "",
                f"- Status: {section.status}",
                f"- Method: {section.method}",
                f"- Conclusion: {section.conclusion}",
                "- Evidence:",
            ]
        )
        lines.extend(f"  - {item}" for item in section.evidence)
        if section.sid == "S1":
            rows = [dict(platform=name, **value) for name, value in section.data.get("platform_status", {}).items()]
            lines.extend(["", "Platform status:"] + markdown_table(rows, ["platform", "status", "has_transcript_path", "keys"]))
            fallback = section.data.get("fallback", {})
            lines.extend(
                [
                    "",
                    "Scope note:",
                    "- auto=synthetic shape only; real Stop/idle hook payload reachability is UNVALIDATED and must pass manual QA8 before later capture work treats it as fact.",
                    f"- codex session_id -> rollout mapping validated: {fallback.get('session_id_mapping_validated', False)}; auto only proves glob/readability within {fallback.get('elapsed_ms')} ms.",
                ]
            )
        if section.sid == "S4":
            lines.extend(["", "Redact hit-rate table:"] + markdown_table(section.data.get("rows", []), ["family", "current_hit", "target_hit"]))
            lines.extend(["", "Redact precision table (should allow):"] + markdown_table(section.data.get("precision_rows", []), ["family", "should_allow", "target_hit"]))
            if section.data.get("precision_false_positive_count"):
                lines.extend(
                    [
                        "",
                        "Phase 02 redact warning:",
                        "- The bare-hex branch currently false-positives on legitimate hashes/checksums/candidate filenames. Phase 02 must carry precision fixtures and narrow this rule before fail-closed tracked writes, otherwise valid content can be silently redacted.",
                    ]
                )
        if section.sid == "S5" and section.status == "PASS":
            lines.extend(
                [
                    "",
                    "Scope note:",
                    "- This validates dual-marker idempotency and no-new-part behavior only. Overflow truncation, budget allocation, and dropped-context reporting are Phase 03 responsibilities and are not proven here.",
                ]
            )
        if section.plan_revision:
            lines.append(f"- PLAN-REVISION: {section.plan_revision}")
        lines.append("")
    lines.extend(
        [
            "## Manual Steps",
            "",
            "- S1: Temporarily wire the dump probe in an isolated cc/droid/codex session, trigger Stop/idle once, and compare raw payload keys with S1 platform_status. Do not run install_hooks from this phase.",
            "- S2: In kilo/opencode, send `phase01 assistant probe <timestamp>`, then rerun this verify script or inspect the SQLite evidence in S2 for the assistant snippet. If neither transform runtime nor SQLite shows assistant text, keep S2 as REVISION.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_sections(sections: list[Section]) -> list[str]:
    errors: list[str] = []
    by_id = {section.sid: section for section in sections}
    for sid in SECTION_IDS:
        section = by_id.get(sid)
        if not section:
            errors.append(f"missing {sid}")
            continue
        if section.status not in {"PASS", "FAIL", "REVISION"}:
            errors.append(f"{sid} invalid status {section.status}")
        if not section.method or not section.conclusion or not section.evidence:
            errors.append(f"{sid} missing method/conclusion/evidence")
        if section.status == "REVISION" and not section.plan_revision:
            errors.append(f"{sid} REVISION missing PLAN-REVISION")
    for sid in ["S3", "S4", "S5", "S6"]:
        if by_id.get(sid) and by_id[sid].status != "PASS":
            errors.append(f"{sid} must pass for the automated spike suite")
    return errors


def section_by_id(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("FINDINGS.json must be a list")
    sections: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        sid = item.get("sid")
        if isinstance(sid, str):
            sections[sid] = item
    return sections


def validate_findings_json(path: Path) -> list[str]:
    try:
        sections = section_by_id(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"FINDINGS.json unreadable: {exc}"]

    errors: list[str] = []
    for sid in SECTION_IDS:
        section = sections.get(sid)
        if not section:
            errors.append(f"missing {sid}")
            continue
        if section.get("status") not in {"PASS", "FAIL", "REVISION"}:
            errors.append(f"{sid} invalid status")
        for key in ["method", "conclusion", "evidence"]:
            if not section.get(key):
                errors.append(f"{sid} missing {key}")

    s1 = sections.get("S1", {}).get("data", {})
    platform_status = s1.get("platform_status", {})
    if set(platform_status) != {"cc", "droid", "codex"}:
        errors.append("S1 missing cc/droid/codex platform_status")
    fallback = s1.get("fallback", {})
    if not isinstance(fallback.get("elapsed_ms"), (int, float)) or fallback.get("elapsed_ms", 10000) >= 10000:
        errors.append("S1 missing codex fallback elapsed_ms < 10000")
    if fallback.get("session_id_mapping_validated") is not False:
        errors.append("S1 must explicitly mark session_id_mapping_validated=false for auto spike")

    s2 = sections.get("S2", {})
    s2_evidence = s2.get("evidence", [])
    selected_none = any(item == "selected_path=none" for item in s2_evidence if isinstance(item, str))
    if selected_none and not s2.get("plan_revision"):
        errors.append("S2 selected_path=none requires plan_revision")

    s3 = sections.get("S3", {}).get("data", {})
    if not s3.get("normalized") or not s3.get("skipped"):
        errors.append("S3 missing normalized/skipped adapter evidence")

    s4 = sections.get("S4", {}).get("data", {})
    required_positive = {"AWS", "GitHub", "JWT", "PEM", "connection string", "bare hex/high entropy", "natural-language secret"}
    positive_rows = s4.get("rows", [])
    if {row.get("family") for row in positive_rows if isinstance(row, dict)} != required_positive:
        errors.append("S4 missing required positive redact families")
    if not all(row.get("target_hit") is True for row in positive_rows if isinstance(row, dict)):
        errors.append("S4 target regex must hit all positive redact families")
    precision_rows = s4.get("precision_rows", [])
    required_precision = {"git SHA-1 40hex", "MD5 checksum", "SHA256 checksum", "sha256 candidate filename"}
    if {row.get("family") for row in precision_rows if isinstance(row, dict)} != required_precision:
        errors.append("S4 missing should-allow precision families")
    if not any(row.get("target_hit") is True for row in precision_rows if isinstance(row, dict)):
        errors.append("S4 precision probe must expose current bare-hex false positive")

    s5 = sections.get("S5", {}).get("data", {})
    parsed = s5.get("parsed", {})
    if parsed.get("ok") is not True or parsed.get("finalPartCount") != parsed.get("initialPartCount"):
        errors.append("S5 missing parsed no-new-part success")
    if parsed.get("capsuleCount") != 1 or parsed.get("memoryCount") != 1:
        errors.append("S5 marker counts must both be one")

    s6 = sections.get("S6", {}).get("data", {})
    drift = s6.get("drift", {})
    if s6.get("unique_files_ok") is not True or drift.get("ok") is not False or drift.get("reason") != "external-drift" or not drift.get("bak"):
        errors.append("S6 missing unique file success or external-drift refusal evidence")
    return errors


def run(repo_root: Path, phase_dir: Path) -> int:
    evidence_dir = phase_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    sections = [
        probe_stop_payloads(evidence_dir),
        probe_assistant_text(evidence_dir, repo_root),
        probe_transcript_adapter(evidence_dir),
        probe_redact(evidence_dir),
        probe_dual_marker(evidence_dir, repo_root),
        probe_staging_drift(evidence_dir),
    ]
    findings_json = phase_dir / "FINDINGS.json"
    findings_md = phase_dir / "FINDINGS.md"
    findings_json.write_text(json.dumps([section.__dict__ for section in sections], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    findings_md.write_text(render_findings(sections), encoding="utf-8")
    errors = validate_sections(sections) + validate_findings_json(findings_json)
    if errors:
        print("VERIFY FAIL: " + "; ".join(errors))
        return 1
    statuses = ", ".join(f"{section.sid}={section.status}" for section in sections)
    print(f"VERIFY PASS: {statuses}")
    print(f"FINDINGS: {findings_md}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--phase-dir", type=Path, required=True)
    args = parser.parse_args()
    return run(args.repo_root.resolve(), args.phase_dir.resolve())


if __name__ == "__main__":
    raise SystemExit(main())

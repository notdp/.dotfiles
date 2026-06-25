#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


# Contract ownership:
# - coding-skills/dev-long-run/lr.py is the emitter SSOT.
# - This validator is the enforcement SSOT for agentsview ingestion.
# - docs/agentsview-memory-vault-emitted-schema.md is the downstream handoff contract.
# Any {_schema,_version} or event-shape change must update all three surfaces.
METRICS_SCHEMA = "dotfiles.long_loop.metrics"
METRICS_VERSION = 1
METRIC_EVENT_FIELDS: dict[str, dict[str, tuple[type, ...]]] = {
    "verify": {
        "ts": (str,),
        "event": (str,),
        "phase": (str, int),
        "ok": (bool,),
        "exit": (int,),
        "fail_streak": (int,),
        "fingerprint": (str, type(None)),
    },
    "acceptance": {"ts": (str,), "event": (str,), "ok": (bool,), "exit": (int,)},
    "complete_phase": {"ts": (str,), "event": (str,), "phase": (str, int)},
    "complete_run": {"ts": (str,), "event": (str,)},
}


def _load_memory_index_module():
    script = Path(__file__).resolve().parent / "build_memory_index.py"
    spec = importlib.util.spec_from_file_location("build_memory_index", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def _require(data: dict[str, Any], path: Path, fields: dict[str, tuple[type, ...]]) -> None:
    for field, types in fields.items():
        if field not in data:
            raise ValueError(f"{path}: missing required field {field!r}")
        value = data[field]
        valid = any(
            isinstance(value, bool)
            if typ is bool
            else isinstance(value, int) and not isinstance(value, bool)
            if typ is int
            else isinstance(value, typ)
            for typ in types
        )
        if not valid:
            names = "/".join(t.__name__ for t in types)
            raise ValueError(f"{path}: field {field!r} expected {names}, got {type(value).__name__}")


def validate_state(path: Path) -> None:
    data = _load_json_object(path)
    # 按 skill 分流:dev-complete 是单 pass(无 phase/role_in_flight 概念),只校验其精简
    # schema;dev-long-run(skill 缺省或 "dev-long-run")按完整多-phase schema 校验。
    if data.get("skill") == "dev-complete":
        _require(
            data,
            path,
            {
                "skill": (str,),
                "state": (str,),
                "slug": (str,),
                "repo_root": (str,),
                "worktree_path": (str,),
                "branch": (str,),
            },
        )
        return
    _require(
        data,
        path,
        {
            "state": (str,),
            "phase": (str, int),
            "role_in_flight": (str,),
            "worktree_path": (str,),
            "branch": (str,),
            "goal": (str,),
            "repo_root": (str,),
            "slug": (str,),
            "dirty_main_at_start": (bool,),
            "in_place": (bool,),
        },
    )


def validate_result_snapshot(path: Path) -> None:
    data = _load_json_object(path)
    _require(data, path, {"ok": (bool,), "exit": (int,), "output_tail": (str,)})


def validate_stuck(path: Path) -> None:
    data = _load_json_object(path)
    _require(data, path, {"consecutive_fail": (int,)})
    fp = data.get("fingerprint")
    if fp is not None and not isinstance(fp, str):
        raise ValueError(f"{path}: field 'fingerprint' expected str/null, got {type(fp).__name__}")


def _load_jsonl_record(path: Path, line_no: int, line: str) -> dict[str, Any]:
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}:{line_no}: expected JSON object")
    return data


def validate_metric_record(path: Path, line_no: int, data: dict[str, Any]) -> None:
    event = data.get("event")
    fields = METRIC_EVENT_FIELDS.get(event)
    if fields is None:
        raise ValueError(f"{path}:{line_no}: unsupported metrics event {event!r}")
    _require(data, Path(f"{path}:{line_no}"), fields)


def validate_metrics(path: Path) -> tuple[int, str]:
    if not path.exists():
        return 0, "missing metrics accepted"
    records = 0
    schema_label = "legacy metrics accepted"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    start = 0
    if lines:
        first = _load_jsonl_record(path, 1, lines[0])
        if "_schema" in first or "_version" in first:
            if first != {"_schema": METRICS_SCHEMA, "_version": METRICS_VERSION}:
                raise ValueError(f"{path}:1: unsupported metrics schema header")
            schema_label = f"{METRICS_SCHEMA}@{METRICS_VERSION}"
            start = 1
    for offset, line in enumerate(lines[start:], start=start + 1):
        data = _load_jsonl_record(path, offset, line)
        validate_metric_record(path, offset, data)
        records += 1
    return records, schema_label


def validate_memory(memory_dir: Path) -> tuple[int, dict[str, list[str]]]:
    facets = {"problem_type": set(), "type": set(), "origin_session": set(), "status": set()}
    if not memory_dir.exists():
        return 0, {key: [] for key in facets}
    build_memory_index = _load_memory_index_module()
    count = 0
    for path in sorted(memory_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        try:
            meta = build_memory_index.parse_frontmatter(path)
        except Exception as exc:
            raise ValueError(str(exc)) from exc
        count += 1
        for key in facets:
            if meta.get(key):
                facets[key].add(meta[key])
    return count, {key: sorted(values) for key, values in facets.items()}


def validate_workspace(workspace: Path, memory_dir: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    memory_dir = memory_dir.resolve()
    summary: dict[str, Any] = {
        "state_files": 0,
        "metrics_records": 0,
        "metrics_schema": "missing metrics accepted",
        "verify_files": 0,
        "acceptance_files": 0,
        "stuck_files": 0,
        "memory_notes": 0,
        "memory_facets": {"problem_type": [], "type": [], "origin_session": [], "status": []},
    }

    state_path = workspace / "state.json"
    if not state_path.exists():
        raise ValueError(f"{state_path}: missing required state.json")
    validate_state(state_path)
    summary["state_files"] = 1

    metrics_records, metrics_schema = validate_metrics(workspace / "metrics.jsonl")
    summary["metrics_records"] = metrics_records
    summary["metrics_schema"] = metrics_schema

    acceptance = workspace / "acceptance.json"
    if acceptance.exists():
        validate_result_snapshot(acceptance)
        summary["acceptance_files"] = 1

    phases_dir = workspace / "phases"
    if phases_dir.exists():
        for phase_dir in sorted(p for p in phases_dir.iterdir() if p.is_dir()):
            verify = phase_dir / "verify.json"
            if verify.exists():
                validate_result_snapshot(verify)
                summary["verify_files"] += 1
            stuck = phase_dir / "stuck.json"
            if stuck.exists():
                validate_stuck(stuck)
                summary["stuck_files"] += 1

    memory_notes, memory_facets = validate_memory(memory_dir)
    summary["memory_notes"] = memory_notes
    summary["memory_facets"] = memory_facets
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dotfiles emitted schema for agentsview memory/vault ingestion.")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--memory-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = validate_workspace(args.workspace, args.memory_dir)
    except Exception as exc:
        sys.stderr.write(f"agentsview emitted schema validation failed: {exc}\n")
        return 1
    sys.stdout.write(
        "checked workspace={workspace} metrics_records={metrics_records} metrics_schema={metrics_schema}; "
        "state_files={state_files} verify_files={verify_files} acceptance_files={acceptance_files} "
        "stuck_files={stuck_files} memory_notes={memory_notes}\n".format(workspace=args.workspace, **summary)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

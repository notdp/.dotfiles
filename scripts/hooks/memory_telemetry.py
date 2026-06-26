from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "dotfiles.memory.telemetry.v1"


def config_root() -> Path:
    override = os.environ.get("DOTFILES_CONFIG_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def telemetry_path(root: Path | None = None) -> Path:
    override = os.environ.get("DOTFILES_MEMORY_TELEMETRY_PATH")
    if override:
        return Path(override).expanduser()
    return (root or config_root()) / "memory_telemetry.jsonl"


def append_memory_telemetry(event: str, source: str, fields: dict[str, Any], root: Path | None = None) -> None:
    """Best-effort local JSONL telemetry for memory hooks.

    This helper is deliberately fail-open because it runs inside hot hook paths:
    telemetry must never block prompt injection or memory capture.
    """
    try:
        record = {
            "schema": SCHEMA,
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "event": event,
            "source": source,
            **fields,
        }
        path = telemetry_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    except Exception:
        return

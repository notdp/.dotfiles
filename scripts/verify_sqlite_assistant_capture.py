#!/usr/bin/env python3
"""S2 验收探针:验证 kilo/opencode 的 SQLite session 库能否抽出 assistant 文本。

背景:Phase 01 spike 只做静态检查,无法证明 assistant 文本可达,故 Phase 05 把
kilo/opencode 的自动捕获降级为 unavailable(改走 /assist-consolidate 显式写入)。
本探针对【真实安装的库】验证 assistant 文本【确实可达】,为后续把捕获升级成 SQLite
读取(capture_from_sqlite + .mjs session.idle 接线)提供 de-risk 证据。

只读、immutable 打开(零锁、不碰 live 写)。退出码 0=可达(S2 PASS),1=不可达。
用法: python3 scripts/verify_sqlite_assistant_capture.py [--platform opencode|kilo]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

PLATFORMS = ("opencode", "kilo")


def db_path(platform: str) -> Path:
    override = os.environ.get(f"DOTFILES_MEMORY_{platform.upper()}_DB")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / platform / f"{platform}.db"


def _connect_ro(path: Path) -> sqlite3.Connection:
    # immutable=1:把库当只读快照,忽略 WAL/锁 → 快、零争用、绝不影响 live 写。
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, timeout=2)


def _tables(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def probe(platform: str) -> dict:
    path = db_path(platform)
    if not path.exists():
        return {"platform": platform, "ok": False, "reason": "db_not_found", "path": str(path)}
    try:
        con = _connect_ro(path)
    except Exception as exc:  # noqa: BLE001
        return {"platform": platform, "ok": False, "reason": f"open_failed:{exc.__class__.__name__}", "path": str(path)}
    try:
        tables = _tables(con)
        # 安装版 schema: message/part,role/text 在 data JSON 里(已实测 opencode+kilo 同构)。
        if {"message", "part"} <= tables:
            sid_row = con.execute("SELECT session_id FROM message ORDER BY time_created DESC LIMIT 1").fetchone()
            sid = sid_row[0] if sid_row else None
            n = con.execute(
                "SELECT count(*) FROM part p JOIN message m ON p.message_id=m.id "
                "WHERE m.session_id=? AND json_extract(m.data,'$.role')='assistant' "
                "AND json_extract(p.data,'$.type')='text' AND length(json_extract(p.data,'$.text'))>0",
                (sid,),
            ).fetchone()[0]
            sample = con.execute(
                "SELECT substr(json_extract(p.data,'$.text'),1,80) FROM part p JOIN message m ON p.message_id=m.id "
                "WHERE m.session_id=? AND json_extract(m.data,'$.role')='assistant' "
                "AND json_extract(p.data,'$.type')='text' AND length(json_extract(p.data,'$.text'))>20 LIMIT 1",
                (sid,),
            ).fetchone()
            return {
                "platform": platform, "ok": n > 0, "reason": "ok" if n > 0 else "no_assistant_text",
                "schema": "message/part+json", "latest_session": (sid or "")[:24],
                "assistant_text_parts": n, "sample": (sample[0] if sample else "")[:80],
            }
        # 新版源码 schema: message_v2 + role/content 列(预留)。
        if "message_v2" in tables:
            n = con.execute("SELECT count(*) FROM message_v2 WHERE role='assistant'").fetchone()[0]
            return {"platform": platform, "ok": n > 0, "reason": "ok" if n > 0 else "no_assistant_text",
                    "schema": "message_v2", "assistant_messages": n}
        return {"platform": platform, "ok": False, "reason": "unknown_schema", "tables": sorted(tables)[:12]}
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=PLATFORMS)
    args = parser.parse_args()
    targets = [args.platform] if args.platform else list(PLATFORMS)
    results = [probe(p) for p in targets]
    any_ok = False
    for r in results:
        status = "PASS" if r["ok"] else "MISS"
        print(f"[{status}] {r['platform']}: {r}")
        any_ok = any_ok or r["ok"]
    print("\nS2 结论:", "assistant 文本可达 → SQLite 捕获可行(可升级 unavailable→capture)" if any_ok
          else "未在任何平台抽到 assistant 文本(检查是否用过 kilo/opencode,或 schema 变化)")
    return 0 if any_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""TDD: kilo/opencode SQLite 自动捕获(capture_from_sqlite)。

安装版 opencode/kilo 库 schema = message/part,role 在 message.data JSON、
text 在 part.data JSON(已用真实库实测,见 scripts/verify_sqlite_assistant_capture.py)。
本测试用临时库验证捕获链路,不碰用户真实库。
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "hooks" / "memory_capture.py"

# 已验证能产出候选的 salient 文本(与 test_memory_capture 同源)。
SALIENT = "remember: prefer lexical memory recall before embeddings for this dotfiles MVP"


def load_capture_module():
    spec = importlib.util.spec_from_file_location("memory_capture", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["memory_capture"] = module
    spec.loader.exec_module(module)
    return module


class SqliteCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capture = load_capture_module()

    def init_repo(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        (root / ".gitignore").write_text("/memory/.staging/\n/memory/.local/\n", encoding="utf-8")

    def raw_dir(self, root: Path) -> Path:
        return root / "memory" / ".staging" / "raw_memories"

    def build_db(self, path: Path, session_id: str, turns: list[tuple[str, str]], *, base_t: int = 1000) -> None:
        """建安装版 message/part+JSON schema 的临时库。turns=[(role,text),...]"""
        con = sqlite3.connect(str(path))
        con.execute("CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER, time_updated INTEGER, data TEXT)")
        con.execute("CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT, time_created INTEGER, time_updated INTEGER, data TEXT)")
        t = base_t
        for i, (role, text) in enumerate(turns):
            mid = f"{session_id}-msg{i}"
            con.execute("INSERT INTO message VALUES (?,?,?,?,?)", (mid, session_id, t, t, json.dumps({"role": role})))
            con.execute("INSERT INTO part VALUES (?,?,?,?,?,?)", (f"{session_id}-part{i}", mid, session_id, t, t, json.dumps({"type": "text", "text": text})))
            t += 1
        con.commit()
        con.close()

    def env(self, db: Path, *, enabled: str = "1") -> dict[str, str]:
        return {"DOTFILES_MEMORY_ENABLED": enabled, "DOTFILES_MEMORY_KILO_DB": str(db)}

    def test_sqlite_capture_writes_candidate_from_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            db = root / "kilo.db"
            self.build_db(db, "ses_1", [("user", SALIENT), ("assistant", "好的,记下偏好。")])

            result = self.capture.capture_from_sqlite(root, platform="kilo", env=self.env(db))

            self.assertEqual(result.status, "written", f"got {result.status}/{result.reason}")
            files = list(self.raw_dir(root).glob("*.json"))
            self.assertEqual(len(files), 1)

    def test_picks_latest_session_when_no_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            db = root / "kilo.db"
            self.build_db(db, "ses_old", [("user", "remember: prefer tabs over spaces here")], base_t=1000)
            self.build_db_append(db, "ses_new", [("user", SALIENT)], base_t=5000)

            result = self.capture.capture_from_sqlite(root, platform="kilo", env=self.env(db))

            self.assertEqual(result.status, "written", f"got {result.status}/{result.reason}")
            payload = json.loads(next(self.raw_dir(root).glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(payload.get("origin_session"), "ses_new")

    def test_session_id_override_targets_that_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            db = root / "kilo.db"
            self.build_db(db, "ses_old", [("user", SALIENT)], base_t=1000)
            self.build_db_append(db, "ses_new", [("user", "just a throwaway hello")], base_t=5000)

            result = self.capture.capture_from_sqlite(root, platform="kilo", session_id="ses_old", env=self.env(db))

            self.assertEqual(result.status, "written", f"got {result.status}/{result.reason}")
            payload = json.loads(next(self.raw_dir(root).glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(payload.get("origin_session"), "ses_old")

    def test_missing_db_is_fail_open_unavailable_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            result = self.capture.capture_from_sqlite(root, platform="kilo", env=self.env(root / "nope.db"))
            self.assertEqual(result.status, "unavailable")
            self.assertEqual(result.reason, "sqlite_db_not_found")
            self.assertFalse(list(self.raw_dir(root).glob("*.json")))

    def test_flag_off_is_disabled_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            db = root / "kilo.db"
            self.build_db(db, "ses_1", [("user", SALIENT)])
            result = self.capture.capture_from_sqlite(root, platform="kilo", env=self.env(db, enabled=""))
            self.assertEqual(result.status, "disabled")
            self.assertFalse(list(self.raw_dir(root).glob("*.json")))

    def test_capture_from_platform_opencode_routes_to_sqlite(self) -> None:
        # 头条行为变更:opencode/kilo 不再返回 assistant_text_unavailable。
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            db = root / "kilo.db"
            self.build_db(db, "ses_1", [("user", SALIENT)])
            env = {"DOTFILES_MEMORY_ENABLED": "1", "DOTFILES_MEMORY_OPENCODE_DB": str(db)}
            result = self.capture.capture_from_platform(root, platform="opencode", env=env)
            self.assertNotEqual(result.reason, "assistant_text_unavailable")
            self.assertEqual(result.status, "written", f"got {result.status}/{result.reason}")

    def test_autodetect_captures_from_db_that_owns_the_session(self) -> None:
        # kilo/opencode 共用 .mjs 分不清平台 → 按 session_id 在两库里定位(session id 唯一)。
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            oc_db = root / "opencode.db"
            ki_db = root / "kilo.db"
            self.build_db(oc_db, "ses_other", [("user", "unrelated throwaway hello there")])
            self.build_db(ki_db, "ses_target", [("user", SALIENT)])
            env = {"DOTFILES_MEMORY_ENABLED": "1", "DOTFILES_MEMORY_OPENCODE_DB": str(oc_db), "DOTFILES_MEMORY_KILO_DB": str(ki_db)}

            result = self.capture.capture_sqlite_for_session(root, session_id="ses_target", env=env)

            self.assertEqual(result.status, "written", f"got {result.status}/{result.reason}")
            payload = json.loads(next(self.raw_dir(root).glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(payload.get("origin_session"), "ses_target")

    def test_autodetect_unavailable_when_session_in_no_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            ki_db = root / "kilo.db"
            self.build_db(ki_db, "ses_a", [("user", SALIENT)])
            env = {"DOTFILES_MEMORY_ENABLED": "1", "DOTFILES_MEMORY_KILO_DB": str(ki_db)}
            result = self.capture.capture_sqlite_for_session(root, session_id="ses_missing", env=env)
            self.assertEqual(result.status, "unavailable")
            self.assertFalse(list(self.raw_dir(root).glob("*.json")))

    def build_db_append(self, path: Path, session_id: str, turns: list[tuple[str, str]], *, base_t: int) -> None:
        con = sqlite3.connect(str(path))
        t = base_t
        for i, (role, text) in enumerate(turns):
            mid = f"{session_id}-msg{i}"
            con.execute("INSERT INTO message VALUES (?,?,?,?,?)", (mid, session_id, t, t, json.dumps({"role": role})))
            con.execute("INSERT INTO part VALUES (?,?,?,?,?,?)", (f"{session_id}-part{i}", mid, session_id, t, t, json.dumps({"type": "text", "text": text})))
            t += 1
        con.commit()
        con.close()


if __name__ == "__main__":
    unittest.main()

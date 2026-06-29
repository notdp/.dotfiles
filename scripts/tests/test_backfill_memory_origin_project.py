import sqlite3
import tempfile
import unittest
from pathlib import Path

import importlib.util
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "backfill_memory_origin_project.py"


def load_module():
    spec = importlib.util.spec_from_file_location("backfill_origin_project", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["backfill_origin_project"] = module
    spec.loader.exec_module(module)
    return module


class BackfillTests(unittest.TestCase):
    def _root_with_note(self, tmp: Path, name: str, origin_session: str,
                        origin_project: str | None = None) -> Path:
        user_dir = tmp / "memory" / "user"
        user_dir.mkdir(parents=True, exist_ok=True)
        op = "" if origin_project is None else f'origin_project: "{origin_project}"\n'
        path = user_dir / name
        path.write_text(
            "---\n"
            f"title: {name}\n"
            "date: 2026-06-29\n"
            "problem_type: knowledge\n"
            "type: semantic\n"
            "status: active\n"
            f"origin_session: \"{origin_session}\"\n"
            f"{op}"
            "applies_to: user\n"
            "---\n\n"
            "Body.\n",
            encoding="utf-8",
        )
        return path

    def _db(self, tmp: Path, rows: list[tuple[str, str, str]]) -> Path:
        db = tmp / "sessions.db"
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE sessions (id TEXT, source_session_id TEXT, project TEXT)"
        )
        conn.executemany(
            "INSERT INTO sessions (id, source_session_id, project) VALUES (?,?,?)", rows
        )
        conn.commit()
        conn.close()
        return db

    def test_atomic_note_gets_project_from_session_lookup(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "a.md", "sess-1")
            db = self._db(tmp, [("sess-1", "sess-1", "oss-atlas")])
            rc = mod.main(["--root", str(tmp), "--db", str(db)])
            self.assertEqual(rc, 0)
            text = note.read_text(encoding="utf-8")
            self.assertIn('origin_project: "oss-atlas"', text)
            self.assertIn('scope: "project"', text)

    def test_synthesized_topic_note_is_left_general(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "topic.md", "compact-memory:reflect-1")
            db = self._db(tmp, [("sess-1", "sess-1", "oss-atlas")])
            mod.main(["--root", str(tmp), "--db", str(db)])
            self.assertNotIn("origin_project:", note.read_text(encoding="utf-8"))

    def test_unmatched_atomic_is_left_general(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "x.md", "unknown-sess")
            db = self._db(tmp, [("sess-1", "sess-1", "oss-atlas")])
            mod.main(["--root", str(tmp), "--db", str(db)])
            self.assertNotIn("origin_project:", note.read_text(encoding="utf-8"))

    def test_dotfiles_origin_is_treated_as_general(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "a.md", "sess-df")
            db = self._db(tmp, [("sess-df", "sess-df", ".dotfiles")])
            mod.main(["--root", str(tmp), "--db", str(db)])
            # dotfiles SSOT repo = general, consistent with classify_origin_scope.
            self.assertNotIn("origin_project:", note.read_text(encoding="utf-8"))

    def test_existing_project_is_never_overwritten_and_idempotent(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "a.md", "sess-1", origin_project="manual-keep")
            db = self._db(tmp, [("sess-1", "sess-1", "oss-atlas")])
            mod.main(["--root", str(tmp), "--db", str(db)])
            self.assertIn('origin_project: "manual-keep"', note.read_text(encoding="utf-8"))
            # second run is a no-op
            before = note.read_text(encoding="utf-8")
            mod.main(["--root", str(tmp), "--db", str(db)])
            self.assertEqual(before, note.read_text(encoding="utf-8"))

    def test_dry_run_does_not_write(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "a.md", "sess-1")
            db = self._db(tmp, [("sess-1", "sess-1", "oss-atlas")])
            before = note.read_text(encoding="utf-8")
            mod.main(["--root", str(tmp), "--db", str(db), "--dry-run"])
            self.assertEqual(before, note.read_text(encoding="utf-8"))

    def test_missing_db_fails_open_to_general(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "a.md", "sess-1")
            rc = mod.main(["--root", str(tmp), "--db", str(tmp / "nope.db")])
            self.assertEqual(rc, 0)
            self.assertNotIn("origin_project:", note.read_text(encoding="utf-8"))

    def test_backfilled_note_still_parses_in_index(self) -> None:
        mod = load_module()
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            note = self._root_with_note(tmp, "a.md", "sess-1")
            db = self._db(tmp, [("sess-1", "sess-1", "oss-atlas")])
            mod.main(["--root", str(tmp), "--db", str(db)])
            # The build_memory_index parser must accept the inserted fields.
            spec = importlib.util.spec_from_file_location(
                "build_memory_index", REPO_ROOT / "scripts" / "build_memory_index.py"
            )
            bmi = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bmi)
            meta = bmi.parse_frontmatter(note)  # must not raise
            self.assertEqual(meta["origin_project"], "oss-atlas")


if __name__ == "__main__":
    unittest.main()

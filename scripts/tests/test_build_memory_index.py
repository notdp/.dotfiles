import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "build_memory_index.py"


def load_index_module():
    spec = importlib.util.spec_from_file_location("build_memory_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildMemoryIndexTests(unittest.TestCase):
    def run_script(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--root", str(root), *args],
            text=True,
            capture_output=True,
        )

    def write_note(self, root: Path, name: str, frontmatter: str, body: str = "Body\n") -> Path:
        user_dir = root / "memory" / "user"
        user_dir.mkdir(parents=True, exist_ok=True)
        path = user_dir / name
        path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")
        return path

    def test_generates_deterministic_index_from_allowed_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(
                root,
                "decision.md",
                "title: Prefer lexical memory recall\n"
                "date: 2026-06-23\n"
                "problem_type: decision\n"
                "type: semantic\n"
                "status: active\n"
                "keywords: [memory, lexical]\n"
                "origin_session: abc123def456\n",
            )

            result = self.run_script(root)
            verify = self.run_script(root, "--verify")
            index = (root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        self.assertIn("Prefer lexical memory recall", index)
        self.assertIn("decision.md", index)
        self.assertIn("memory, lexical", index)
        self.assertNotIn("level", index)

    def test_escapes_pipe_characters_in_index_table_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(
                root,
                "pipe.md",
                "title: A | B\n"
                "date: 2026-06-23\n"
                "problem_type: knowledge\n"
                "keywords: [alpha | beta]\n",
            )

            result = self.run_script(root)
            index = (root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(r"A \| B", index)
        self.assertIn(r"alpha \| beta", index)

    def test_verify_detects_stale_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(root, "note.md", "title: Stable note\ndate: 2026-06-23\nproblem_type: knowledge\n")
            self.run_script(root)
            (root / "memory" / "user" / "INDEX.md").write_text("stale\n", encoding="utf-8")

            result = self.run_script(root, "--verify")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale", result.stderr)

    def test_rejects_secret_frontmatter_and_level_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(
                root,
                "bad.md",
                "title: Secret note\n"
                "date: 2026-06-23\n"
                "problem_type: knowledge\n"
                "token: ghp_abcdefghijklmnopqrstuvwxyz1234567890AB\n",
            )
            secret_result = self.run_script(root)

        self.assertNotEqual(secret_result.returncode, 0)
        self.assertIn("secret", secret_result.stderr.lower())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(
                root,
                "bad.md",
                "title: Level note\n"
                "date: 2026-06-23\n"
                "problem_type: knowledge\n"
                "level: user\n",
            )
            level_result = self.run_script(root)

        self.assertNotEqual(level_result.returncode, 0)
        self.assertIn("level", level_result.stderr)

    def test_schema_fields_include_phase_02_without_level(self) -> None:
        module = load_index_module()
        for field in [
            "title",
            "date",
            "problem_type",
            "type",
            "created",
            "last_accessed",
            "status",
            "valid_from",
            "valid_to",
            "superseded_by",
            "trust",
            "keywords",
            "tags",
            "related",
            "origin_session",
            "verify",
            "applies_to",
        ]:
            self.assertIn(field, module.ALLOWED_FRONTMATTER_FIELDS)
        self.assertNotIn("level", module.ALLOWED_FRONTMATTER_FIELDS)


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_SCRIPT = REPO_ROOT / "scripts" / "scan_diff_residue.py"


class ScanDiffResidueTests(unittest.TestCase):
    def run_scan(self, diff: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCAN_SCRIPT), "--stdin"],
            input=diff,
            text=True,
            capture_output=True,
        )

    def run_hook_scan(self, diff: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCAN_SCRIPT), "--stdin", "--hook"],
            input=diff,
            text=True,
            capture_output=True,
        )

    def test_reports_added_debug_residue(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app.py b/src/app.py
            --- a/src/app.py
            +++ b/src/app.py
            @@ -10,2 +10,5 @@ def handler():
             keep()
            +print("debug")
            +logger.info("[DEBUG-a4f2] state=%s", state)
            +# TODO: remove this later
            +api_""" + """key="secret-value"
            """
        )

        result = self.run_scan(diff)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("| 调试打印 | src/app.py | 11 |", result.stdout)
        self.assertIn("| DEBUG 前缀 | src/app.py | 12 |", result.stdout)
        self.assertIn("| TODO/FIXME | src/app.py | 13 |", result.stdout)
        self.assertIn("| 疑似 secret | src/app.py | 14 |", result.stdout)

    def test_ignores_context_and_removed_lines(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app.py b/src/app.py
            --- a/src/app.py
            +++ b/src/app.py
            @@ -20,3 +20,3 @@ def handler():
             print("existing debug in context")
            -console.log("removed")
            +return "ok"
            """
        )

        result = self.run_scan(diff)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_hook_mode_returns_additional_context_without_blocking(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app.py b/src/app.py
            --- a/src/app.py
            +++ b/src/app.py
            @@ -1,1 +1,2 @@
             keep()
            +print("debug")
            """
        )

        result = self.run_hook_scan(diff)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("hookSpecificOutput", payload)
        self.assertIn("Diff residue scan", payload["hookSpecificOutput"]["additionalContext"])

    def test_scans_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            src = repo / "src"
            src.mkdir()
            (src / "new.py").write_text('print("debug")\n', encoding="utf-8")

            result = subprocess.run(
                ["python3", str(SCAN_SCRIPT)],
                cwd=repo,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("| 调试打印 | src/new.py | 1 |", result.stdout)

    def test_skips_docs_tests_and_scanner_source_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "docs").mkdir()
            (repo / "docs" / "note.md").write_text("TODO: example\n", encoding="utf-8")
            (repo / "scripts" / "tests").mkdir(parents=True)
            (repo / "scripts" / "tests" / "fixture.py").write_text('print("fixture")\n', encoding="utf-8")
            (repo / "scripts" / "scan_diff_residue.py").write_text('print("usage")\n', encoding="utf-8")
            (repo / "scripts" / "scan_operational_task_contract.py").write_text('print("json output")\n', encoding="utf-8")
            (repo / "scripts" / "scan_boundary_decisions.py").write_text('print("hook output")\n', encoding="utf-8")
            (repo / "scripts" / "hooks").mkdir()
            (repo / "scripts" / "hooks" / "context_capsule.py").write_text('print("preview output")\n', encoding="utf-8")
            (repo / ".factory" / "hooks").mkdir(parents=True)
            (repo / ".factory" / "hooks" / "context_capsule.py").write_text('print("hook output")\n', encoding="utf-8")

            result = subprocess.run(
                ["python3", str(SCAN_SCRIPT)],
                cwd=repo,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)


if __name__ == "__main__":
    unittest.main()

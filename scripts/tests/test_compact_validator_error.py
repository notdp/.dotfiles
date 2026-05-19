import subprocess
import textwrap
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "compact_validator_error.py"
RUN_VERIFY = REPO_ROOT / "scripts" / "run-verify.sh"


class CompactValidatorErrorTests(unittest.TestCase):
    def run_compactor(self, log: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            input=log,
            text=True,
            capture_output=True,
        )

    def test_extracts_python_traceback_actionable_error(self) -> None:
        log = textwrap.dedent(
            """\
            ============================= test session starts =============================
            Traceback (most recent call last):
              File "scripts/tests/test_sync.py", line 42, in test_sync
                self.assertEqual(result, 3)
            AssertionError: 2 != 3
            FAILED scripts/tests/test_sync.py::SyncTests::test_sync
            """
        )

        result = self.run_compactor(log, "--command", "pytest -q", "--check", "tests")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ValidatorErrorSummary:", result.stdout)
        self.assertIn("- Command: `pytest -q`", result.stdout)
        self.assertIn("- Check: tests", result.stdout)
        self.assertIn("AssertionError: 2 != 3", result.stdout)
        self.assertIn("scripts/tests/test_sync.py:42", result.stdout)
        self.assertIn("scripts/tests/test_sync.py::SyncTests::test_sync", result.stdout)

    def test_extracts_typescript_error(self) -> None:
        log = "src/app.ts(12,5): error TS2322: Type 'string' is not assignable to type 'number'.\n"

        result = self.run_compactor(log, "--command", "npm run typecheck", "--check", "typecheck", "--exit-code", "2")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("- Exit: 2", result.stdout)
        self.assertIn("TS2322", result.stdout)
        self.assertIn("src/app.ts", result.stdout)


class RunVerifyFailureSummaryTests(unittest.TestCase):
    def test_failed_check_evidence_has_no_trailing_brace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(
                '{"name":"smoke","scripts":{"test":"node -e \\"process.exit(2)\\""}}\n',
                encoding="utf-8",
            )
            scripts_dir = repo / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "compact_validator_error.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

            result = subprocess.run(
                ["bash", str(RUN_VERIFY), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            evidence_lines = [line for line in result.stdout.splitlines() if "tests (npm)" in line]
            self.assertEqual(len(evidence_lines), 1, result.stdout)
            self.assertNotIn("a} |", evidence_lines[0])


if __name__ == "__main__":
    unittest.main()

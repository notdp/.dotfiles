import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run-verify.sh"


class RunVerifyTests(unittest.TestCase):
    def test_runs_scripts_tests_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            test_dir = repo / "scripts" / "tests"
            test_dir.mkdir(parents=True)
            (test_dir / "test_sample.py").write_text(
                "import unittest\n\n"
                "class SampleTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["bash", str(SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("tests (scripts unittest)", result.stdout)
            self.assertIn("python3 -m unittest discover -s scripts/tests -p \"test_*.py\"", result.stdout)


if __name__ == "__main__":
    unittest.main()

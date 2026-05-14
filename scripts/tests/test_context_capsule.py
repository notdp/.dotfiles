import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".factory" / "hooks" / "context_capsule.py"


class ContextCapsuleTests(unittest.TestCase):
    def run_capsule(self, repo: Path, prompt: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo)}
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": prompt}
        return subprocess.run(
            ["python3", str(SCRIPT), "--event", "prompt"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            cwd=repo,
        )

    def test_prompt_can_match_multiple_capsules_with_risk_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), "prod dry-run apply backfill failed with auth permission bug")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Security / GitOps Capsule", context)
        self.assertIn("Operational Task Capsule", context)
        self.assertIn("Debug Task Capsule", context)
        self.assertLess(context.index("Security / GitOps Capsule"), context.index("Operational Task Capsule"))
        self.assertLessEqual(len(context), 2200)

    def test_non_matching_prompt_stays_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), "thanks")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])


if __name__ == "__main__":
    unittest.main()

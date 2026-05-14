import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hook_context_state.py"


class HookContextStateTests(unittest.TestCase):
    def run_script(self, repo: Path, payload: dict, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo)}
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            cwd=repo,
        )

    def test_precompact_saves_compact_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "src.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"role": "user", "content": "Fix the flaky sync bug"}) + "\n"
                + json.dumps({"role": "assistant", "content": "Ran `python3 scripts/run-verify.sh` pass"}) + "\n",
                encoding="utf-8",
            )

            result = self.run_script(repo, {"transcript_path": str(transcript)}, "--event", "pre-compact")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"])
            state = json.loads((repo / ".factory" / "scratch" / "compact-state.json").read_text())
            self.assertEqual(state["last_user_prompt"], "Fix the flaky sync bug")
            self.assertIn("src.py", state["changed_files"])
            self.assertIn("run-verify.sh", state["recent_validation"])

    def test_session_start_compact_injects_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            state_dir = repo / ".factory" / "scratch"
            state_dir.mkdir(parents=True)
            (state_dir / "compact-state.json").write_text(
                json.dumps(
                    {
                        "last_user_prompt": "Implement operational hook",
                        "changed_files": ["scripts/hook.py"],
                        "recent_validation": "python3 -m unittest pass",
                        "recent_todos": ["1. [in_progress] finish hook"],
                        "risks": ["unverified stop hook"],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_script(repo, {"source": "compact"}, "--event", "session-start")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            context = payload["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Compact Recovery Capsule", context)
            self.assertIn("Implement operational hook", context)
            self.assertIn("scripts/hook.py", context)

    def test_non_compact_session_start_stays_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            result = self.run_script(repo, {"source": "startup"}, "--event", "session-start")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"])


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "context_state.py"
WRAPPER_SCRIPT = REPO_ROOT / "scripts" / "hook_context_state.py"


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

    def run_wrapper(self, repo: Path, payload: dict, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo)}
        return subprocess.run(
            ["python3", str(WRAPPER_SCRIPT), *args],
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
                json.dumps(
                    {
                        "role": "user",
                        "content": "Fix the flaky sync bug with token sk-live-abc123 and https://secret.example.com/path",
                    }
                )
                + "\n"
                + json.dumps({"role": "assistant", "content": "Boundary decisions:\n- context-surface: compact recovery keeps state small"}) + "\n"
                + json.dumps({"role": "assistant", "content": "Blocked: waiting for failing fixture"}) + "\n"
                + json.dumps({"role": "assistant", "content": "Ran `python3 scripts/run-verify.sh` pass"}) + "\n",
                encoding="utf-8",
            )

            result = self.run_script(repo, {"transcript_path": str(transcript)}, "--event", "pre-compact")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"])
            states = list((repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            self.assertEqual(len(states), 1)
            state = json.loads(states[0].read_text())
            self.assertFalse((repo / ".factory" / "scratch" / "compact-state.json").exists())
            self.assertNotIn("sk-live-abc123", json.dumps(state))
            self.assertNotIn("secret.example.com", json.dumps(state))
            self.assertIn("[REDACTED_SECRET]", state["last_user_prompt"])
            self.assertIn("[REDACTED_URL]", state["last_user_prompt"])
            self.assertIn("src.py", state["changed_files"])
            self.assertIn("run-verify.sh", state["recent_validation"])
            self.assertIn("Fix the flaky sync bug", state["goal"])
            self.assertIn("waiting for failing fixture", state["blockers"])
            self.assertIn("context-surface", state["boundary_decisions"])
            self.assertIn("not inferred", state["next_action"])
            self.assertNotIn("recent_todos", state)

    def test_precompact_captures_chinese_blocker_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"role": "user", "content": "继续修复"}) + "\n"
                + json.dumps({"role": "assistant", "content": "阻塞：等待用户确认生产资源范围"}) + "\n",
                encoding="utf-8",
            )

            result = self.run_script(repo, {"transcript_path": str(transcript)}, "--event", "pre-compact")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state_file = next((repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            state = json.loads(state_file.read_text())
            self.assertIn("等待用户确认生产资源范围", state["blockers"])

    def test_precompact_does_not_treat_embedded_blocked_text_as_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"role": "user", "content": "review 当前 diff"}) + "\n"
                + json.dumps({"role": "assistant", "content": "Example text: Blocked: this is only a quoted review sample"}) + "\n",
                encoding="utf-8",
            )

            result = self.run_script(repo, {"transcript_path": str(transcript)}, "--event", "pre-compact")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state_file = next((repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            state = json.loads(state_file.read_text())
            self.assertEqual(state["blockers"], "")

    def test_precompact_ignores_todowrite_lines_as_recovery_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"role": "user", "content": "Current task"}) + "\n"
                + json.dumps({"role": "assistant", "content": "1. [completed] stale task\n2. [pending] unrelated task"})
                + "\n",
                encoding="utf-8",
            )

            result = self.run_script(repo, {"transcript_path": str(transcript)}, "--event", "pre-compact")
            state_file = next((repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            state = json.loads(state_file.read_text())

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("recent_todos", state)

    def test_session_start_compact_injects_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            state_dir = repo / ".agent-state" / "hooks" / "compact-state"
            state_dir.mkdir(parents=True)
            (state_dir / "agent-a.json").write_text(
                json.dumps(
                    {
                        "state_key": "agent-a",
                        "last_user_prompt": "Implement operational hook",
                        "changed_files": ["scripts/hook.py"],
                        "recent_validation": "python3 -m unittest pass",
                        "risks": ["unverified stop hook"],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_script(repo, {"source": "compact", "session_id": "agent-a"}, "--event", "session-start")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            context = payload["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Compact Recovery Capsule", context)
            self.assertIn("TaskCheckpoint", context)
            self.assertIn("Implement operational hook", context)
            self.assertIn("scripts/hook.py", context)
            self.assertIn("Next action", context)
            self.assertNotIn("Recent todos", context)
            self.assertFalse((state_dir / "agent-a.json").exists())

    def test_precompact_writes_gitignore_for_agent_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            transcript = self._write_transcript(repo, "session.jsonl", "Current task")

            result = self.run_script(repo, {"transcript_path": str(transcript)}, "--event", "pre-compact")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(".agent-state/", (repo / ".gitignore").read_text(encoding="utf-8"))

    def test_compact_state_uses_session_id_when_transcript_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

            first_save = self.run_script(
                repo,
                {"session_id": "agent-a"},
                "--event",
                "pre-compact",
            )
            second_save = self.run_script(
                repo,
                {"session_id": "agent-b"},
                "--event",
                "pre-compact",
            )
            self.assertEqual(first_save.returncode, 0, first_save.stdout + first_save.stderr)
            self.assertEqual(second_save.returncode, 0, second_save.stdout + second_save.stderr)
            state_files = sorted(path.name for path in (repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            self.assertEqual(state_files, ["agent-a.json", "agent-b.json"])

            first_restore = self.run_script(repo, {"source": "compact", "session_id": "agent-a"}, "--event", "session-start")
            second_restore = self.run_script(repo, {"source": "compact", "session_id": "agent-b"}, "--event", "session-start")
            first_context = json.loads(first_restore.stdout)["hookSpecificOutput"]["additionalContext"]
            second_context = json.loads(second_restore.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Compact Recovery Capsule", first_context)
            self.assertIn("Compact Recovery Capsule", second_context)
            state_files_after_restore = list((repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            self.assertEqual(state_files_after_restore, [])

    def test_compact_state_is_isolated_by_transcript_when_session_id_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            first = self._write_transcript(repo, "agent-a.jsonl", "Transcript A goal")
            second = self._write_transcript(repo, "agent-b.jsonl", "Transcript B goal")

            self.run_script(repo, {"transcript_path": str(first)}, "--event", "pre-compact")
            self.run_script(repo, {"transcript_path": str(second)}, "--event", "pre-compact")
            state_files = list((repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            self.assertEqual(len(state_files), 2)

            first_restore = self.run_script(
                repo,
                {"source": "compact", "transcript_path": str(first)},
                "--event",
                "session-start",
            )

            first_context = json.loads(first_restore.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Transcript A goal", first_context)
            self.assertNotIn("Transcript B goal", first_context)
            remaining_files = list((repo / ".agent-state" / "hooks" / "compact-state").glob("*.json"))
            self.assertEqual(len(remaining_files), 1)

    def test_session_start_without_matching_key_does_not_read_latest_other_agent_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            state_dir = repo / ".agent-state" / "hooks" / "compact-state"
            state_dir.mkdir(parents=True)
            (state_dir / "agent-a.json").write_text(
                json.dumps(
                    {
                        "state_key": "agent-a",
                        "last_user_prompt": "Private agent A state",
                        "changed_files": ["agent-a.py"],
                        "recent_validation": "python3 -m unittest pass",
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_script(repo, {"source": "compact", "session_id": "agent-b"}, "--event", "session-start")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["suppressOutput"])
            self.assertTrue((state_dir / "agent-a.json").exists())

    def test_transcript_key_survives_changed_session_id_across_compact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            transcript = self._write_transcript(repo, "same-transcript.jsonl", "Same transcript survives")

            save = self.run_script(
                repo,
                {"session_id": "before-compact", "transcript_path": str(transcript)},
                "--event",
                "pre-compact",
            )
            restore = self.run_script(
                repo,
                {"source": "compact", "session_id": "after-compact", "transcript_path": str(transcript)},
                "--event",
                "session-start",
            )

            self.assertEqual(save.returncode, 0, save.stdout + save.stderr)
            self.assertEqual(restore.returncode, 0, restore.stdout + restore.stderr)
            context = json.loads(restore.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Same transcript survives", context)

    def test_precompact_cleans_up_expired_compact_state_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            state_dir = repo / ".agent-state" / "hooks" / "compact-state"
            state_dir.mkdir(parents=True)
            expired = datetime.now(timezone.utc) - timedelta(days=30)
            fresh = datetime.now(timezone.utc)
            (state_dir / "expired.json").write_text(
                json.dumps({"updated_at": expired.replace(microsecond=0).isoformat(), "last_user_prompt": "old"}),
                encoding="utf-8",
            )
            (state_dir / "fresh.json").write_text(
                json.dumps({"updated_at": fresh.replace(microsecond=0).isoformat(), "last_user_prompt": "fresh"}),
                encoding="utf-8",
            )
            transcript = self._write_transcript(repo, "session.jsonl", "Current task")

            result = self.run_script(repo, {"transcript_path": str(transcript)}, "--event", "pre-compact")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((state_dir / "expired.json").exists())
            self.assertTrue((state_dir / "fresh.json").exists())

    def test_session_start_compact_reads_legacy_factory_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            state_dir = repo / ".factory" / "scratch"
            state_dir.mkdir(parents=True)
            (state_dir / "compact-state.json").write_text(
                json.dumps(
                    {
                        "last_user_prompt": "Continue from legacy state",
                        "changed_files": ["legacy.py"],
                        "recent_validation": "python3 -m unittest pass",
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_script(repo, {"source": "compact"}, "--event", "session-start")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Continue from legacy state", context)
            self.assertIn("legacy.py", context)
            self.assertFalse((state_dir / "compact-state.json").exists())

    def test_non_compact_session_start_stays_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            result = self.run_script(repo, {"source": "startup"}, "--event", "session-start")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_legacy_wrapper_delegates_to_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            result = self.run_wrapper(repo, {"source": "startup"}, "--event", "session-start")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def _write_transcript(self, repo: Path, name: str, prompt: str) -> Path:
        transcript = repo / name
        transcript.write_text(json.dumps({"role": "user", "content": prompt}) + "\n", encoding="utf-8")
        return transcript


if __name__ == "__main__":
    unittest.main()

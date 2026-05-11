import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "droid_observe.py"


class DroidObserveTests(unittest.TestCase):
    def write_workspace(self, root: Path, name: str, *, updated_at: str) -> Path:
        workspace = root / ".long-loop" / name
        workspace.mkdir(parents=True)
        (workspace / "state.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "created_by": "dev-long-loop-harness",
                    "workspace_token": "token",
                    "goal": name,
                    "status": "running",
                    "updated_at": updated_at,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return workspace

    def test_finds_latest_long_loop_workspace_from_session_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            old_workspace = self.write_workspace(repo, "old-run", updated_at="2026-05-10T01:00:00+00:00")
            new_workspace = self.write_workspace(repo, "new-run", updated_at="2026-05-10T02:00:00+00:00")
            sessions = root / "sessions" / "-tmp-repo"
            sessions.mkdir(parents=True)
            session = sessions / "1b14d3ae-0000-0000-0000-000000000000.jsonl"
            session.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "session_start", "id": "1b14d3ae-0000", "cwd": str(repo)}),
                        json.dumps({"type": "message", "message": {"content": [{"type": "text", "text": f"Workspace: `{old_workspace}`"}]}}),
                        json.dumps({"type": "message", "message": {"content": [{"type": "text", "text": f"Workspace: `{new_workspace}`"}]}}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(SCRIPT), "1b14d3ae", "--sessions-dir", str(root / "sessions"), "--dry-run"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(new_workspace), result.stdout)
            self.assertIn("open", result.stdout)
            self.assertNotIn(str(old_workspace), result.stdout)

    def test_resolves_relative_workspace_against_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            workspace = self.write_workspace(repo, "relative-run", updated_at="2026-05-10T01:00:00+00:00")
            sessions = root / "sessions" / "-tmp-repo"
            sessions.mkdir(parents=True)
            session = sessions / "abcd-0000.jsonl"
            session.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "session_start", "id": "abcd", "cwd": str(root / "other")}),
                        json.dumps({"type": "message", "message": {"content": [{"type": "text", "text": f"Next: `python3 long_loop.py run --dir .long-loop/relative-run --repo-root {repo}`"}]}}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(SCRIPT), "abcd", "--sessions-dir", str(root / "sessions"), "--dry-run"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(workspace), result.stdout)

    def test_accepts_workspace_path_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = self.write_workspace(root, "direct-run", updated_at="2026-05-10T01:00:00+00:00")

            result = subprocess.run(
                ["python3", str(SCRIPT), str(workspace), "--dry-run"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(workspace), result.stdout)

    def test_accepts_repo_path_and_uses_latest_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            old_workspace = self.write_workspace(repo, "old-run", updated_at="2026-05-10T01:00:00+00:00")
            new_workspace = self.write_workspace(repo, "new-run", updated_at="2026-05-10T02:00:00+00:00")

            result = subprocess.run(
                ["python3", str(SCRIPT), str(repo), "--dry-run"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(new_workspace), result.stdout)
            self.assertNotIn(str(old_workspace), result.stdout)

    def test_repo_path_with_multiple_workspaces_lists_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            old_workspace = self.write_workspace(repo, "old-run", updated_at="2026-05-10T01:00:00+00:00")
            new_workspace = self.write_workspace(repo, "new-run", updated_at="2026-05-10T02:00:00+00:00")

            result = subprocess.run(
                ["python3", str(SCRIPT), str(repo), "--list"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1", result.stdout)
            self.assertIn(str(new_workspace), result.stdout)
            self.assertIn("2", result.stdout)
            self.assertIn(str(old_workspace), result.stdout)

    def test_repo_path_can_open_nth_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            old_workspace = self.write_workspace(repo, "old-run", updated_at="2026-05-10T01:00:00+00:00")
            self.write_workspace(repo, "new-run", updated_at="2026-05-10T02:00:00+00:00")

            result = subprocess.run(
                ["python3", str(SCRIPT), str(repo), "--index", "2", "--dry-run"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(old_workspace), result.stdout)


if __name__ == "__main__":
    unittest.main()

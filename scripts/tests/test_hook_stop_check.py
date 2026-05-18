import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "stop_check.py"
WRAPPER_SCRIPT = REPO_ROOT / "scripts" / "hook_stop_check.py"


class HookStopCheckTests(unittest.TestCase):
    def run_stop_check(self, repo: Path, transcript: Path, script: Path = SCRIPT) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo)}
        payload = {"hook_event_name": "Stop", "transcript_path": str(transcript)}
        return subprocess.run(
            ["python3", str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=repo,
            env=env,
        )

    def test_warns_when_code_changed_without_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(json.dumps({"role": "assistant", "content": "I changed app.py"}) + "\n", encoding="utf-8")

            result = self.run_stop_check(repo, transcript)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("systemMessage", payload)
            self.assertIn("guard-verify", payload["systemMessage"])

    def test_stays_quiet_when_validation_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"role": "assistant", "content": "Ran python3 -m unittest discover -s tests OK"}) + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_old_validation_before_current_prompt_does_not_satisfy_stop_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"role": "assistant", "content": "Ran python3 -m unittest discover -s tests OK"}),
                        json.dumps({"role": "user", "content": "Now change app.py"}),
                        json.dumps({"role": "assistant", "content": "Changed app.py"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("guard-verify", json.loads(result.stdout)["systemMessage"])

    def test_bare_pass_is_not_validation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"role": "assistant", "content": "Changed app.py; pass"}) + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("systemMessage", payload)
            self.assertIn("guard-verify", payload["systemMessage"])

    def test_warns_for_ui_change_without_visual_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "App.tsx").write_text("export function App() { return <div /> }\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"role": "assistant", "content": "Ran npm test pass"}) + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("visual", payload["systemMessage"].lower())

    def test_old_visual_evidence_before_current_prompt_does_not_satisfy_ui_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "App.tsx").write_text("export function App() { return <div /> }\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"role": "assistant", "content": "Captured screenshot and checked overflow"}),
                        json.dumps({"role": "user", "content": "Now change App.tsx"}),
                        json.dumps({"role": "assistant", "content": "Ran npm test pass"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("visual", json.loads(result.stdout)["systemMessage"].lower())

    def test_warns_when_boundary_scan_found_without_assistant_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "user",
                                "message": {"content": "Spec says `Boundary decisions:` is required"},
                            }
                        ),
                        json.dumps(
                            {
                                "type": "user",
                                "message": {
                                    "content": "Boundary decision scan found possible boundary changes"
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "type": "assistant",
                                "message": {"content": "Ran python3 -m unittest discover -s tests OK"},
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("Boundary decisions", payload["systemMessage"])

    def test_legacy_wrapper_delegates_to_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            transcript = repo / "session.jsonl"
            transcript.write_text(json.dumps({"role": "assistant", "content": "No changes"}) + "\n", encoding="utf-8")

            result = self.run_stop_check(repo, transcript, script=WRAPPER_SCRIPT)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_ignores_user_or_capsule_boundary_manifest_when_assistant_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "user",
                                "message": {"content": "Boundary decisions:\n- rejection: example"},
                            }
                        ),
                        json.dumps(
                            {
                                "type": "assistant",
                                "message": {
                                    "content": "Boundary decision scan found possible boundary changes\nRan npm test pass"
                                },
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("Boundary decisions", payload["systemMessage"])

    def test_stays_quiet_when_assistant_boundary_manifest_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "assistant",
                                "message": {
                                    "content": (
                                        "Boundary decision scan found possible boundary changes\n"
                                        "Ran python3 -m unittest discover -s tests OK\n\n"
                                        "Boundary decisions:\n"
                                        "- rejection: added explicit 422 because user approved it (file:line, evidence: approved)"
                                    )
                                },
                            }
                        )
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_old_boundary_manifest_before_current_prompt_does_not_satisfy_stop_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "role": "assistant",
                                "content": (
                                    "Boundary decision scan found possible boundary changes\n"
                                    "Boundary decisions:\n- schema-contract: old task"
                                ),
                            }
                        ),
                        json.dumps({"role": "user", "content": "Now change app.py"}),
                        json.dumps(
                            {
                                "role": "assistant",
                                "content": "Boundary decision scan found possible boundary changes\nRan npm test pass",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Boundary decisions", json.loads(result.stdout)["systemMessage"])

    def test_boundary_decisions_none_does_not_satisfy_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": (
                                "Boundary decision scan found possible boundary changes\n"
                                "Ran npm test pass\n\n"
                                "Boundary decisions:\nnone"
                            )
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_stop_check(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("Boundary decisions", payload["systemMessage"])


if __name__ == "__main__":
    unittest.main()

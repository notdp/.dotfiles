import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hook_boundary_gate.py"


class HookBoundaryGateTests(unittest.TestCase):
    def run_gate(
        self,
        repo: Path,
        transcript: Path,
        tool_name: str = "Edit",
        mode: str = "advisory",
    ) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo), "BOUNDARY_GATE_MODE": mode}
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool_name, "transcript_path": str(transcript)}
        return subprocess.run(
            ["python3", str(SCRIPT)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=repo,
            env=env,
        )

    def write_transcript(self, path: Path, *records: dict) -> None:
        path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")

    def test_warns_before_edit_after_high_risk_prompt_without_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(transcript, {"type": "user", "message": {"content": "帮我封装这个服务"}})

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertIn("Boundary gate advisory", payload["systemMessage"])

    def test_blocks_in_block_mode_when_facts_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(transcript, {"type": "user", "message": {"content": "改 response_model"}})

            result = self.run_gate(repo, transcript, mode="block")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "block")
        self.assertIn("reason", payload)

    def test_stays_quiet_when_boundary_facts_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "帮我封装这个服务"}},
                {"type": "assistant", "message": {"content": "Boundary decisions:\n- schema-contract: keep envelope"}},
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_stays_quiet_for_non_edit_tools_and_low_risk_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(transcript, {"type": "user", "message": {"content": "thanks"}})

            low_risk = self.run_gate(repo, transcript)
            execute = self.run_gate(repo, transcript, tool_name="Execute")

        self.assertEqual(low_risk.returncode, 0, low_risk.stdout + low_risk.stderr)
        self.assertEqual(execute.returncode, 0, execute.stdout + execute.stderr)
        self.assertTrue(json.loads(low_risk.stdout)["suppressOutput"])
        self.assertTrue(json.loads(execute.stdout)["suppressOutput"])


if __name__ == "__main__":
    unittest.main()

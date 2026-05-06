import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LONG_LOOP_SCRIPT = REPO_ROOT / "scripts" / "long_loop.py"


class LongLoopTests(unittest.TestCase):
    def run_script(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(LONG_LOOP_SCRIPT), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )

    def test_plan_creates_approval_gated_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "plan", "--goal", "ship feature")

            self.assertEqual(result.returncode, 0, result.stderr)
            root = cwd / ".long-loop"
            self.assertTrue((root / "PROMPT.md").exists())
            self.assertTrue((root / "SPEC.md").exists())
            self.assertTrue((root / "IMPLEMENTATION_PLAN.md").exists())
            self.assertTrue((root / "ASSERT.md").exists())
            self.assertTrue((root / "progress.md").exists())
            self.assertTrue((root / "logs").exists())
            state = json.loads((root / "state.json").read_text())
            self.assertEqual(state["goal"], "ship feature")
            self.assertEqual(state["status"], "awaiting_approval")
            self.assertEqual(state["approval"], "pending")

    def test_init_is_approval_gated_alias_for_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "init", "--goal", "ship feature")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((cwd / ".long-loop" / "state.json").read_text())
            self.assertEqual(state["status"], "awaiting_approval")
            self.assertEqual(state["approval"], "pending")

    def test_status_reports_remaining_todo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "init", "--goal", "ship feature")
            result = self.run_script(cwd, "status")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("remaining_todo: 1", result.stdout)
            self.assertIn("status: awaiting_approval", result.stdout)

    def test_stop_records_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "init", "--goal", "ship feature")
            result = self.run_script(cwd, "stop", "--reason", "needs user")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((cwd / ".long-loop" / "state.json").read_text())
            self.assertEqual(state["status"], "stopped")
            self.assertEqual(state["stop_reason"], "needs user")

    def test_run_requires_agent_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "init", "--goal", "ship feature")
            result = self.run_script(cwd, "run", "--once")

            self.assertEqual(result.returncode, 2)
            self.assertIn("run requires --agent-cmd", result.stderr)

    def test_run_requires_approval_even_with_agent_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "run", "--once", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 2)
            self.assertIn("long-loop plan is not approved", result.stderr)

    def test_approve_allows_execution_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "approve")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((cwd / ".long-loop" / "state.json").read_text())
            self.assertEqual(state["status"], "approved")
            self.assertEqual(state["approval"], "approved")

    def test_pause_records_intervention_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "pause", "--reason", "adjust plan")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((cwd / ".long-loop" / "state.json").read_text())
            self.assertEqual(state["status"], "paused")
            self.assertEqual(state["paused_reason"], "adjust plan")
            self.assertEqual(state["approval"], "pending")

    def test_status_json_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "status", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "awaiting_approval")
            self.assertEqual(payload["remaining_todo"], 1)

    def test_tail_outputs_recent_log_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "tail", "--lines", "20")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("planned", result.stdout)
            self.assertIn("approved", result.stdout)

    def test_watch_can_run_for_one_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "watch", "--interval", "0", "--iterations", "1")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Long Loop Status", result.stdout)
            self.assertIn("awaiting_approval", result.stdout)

    def test_help_outputs_state_transition_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "help")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("State Flow", result.stdout)
            self.assertIn("plan -> awaiting_approval -> approve -> approved -> run -> running", result.stdout)
            self.assertIn("pause -> paused -> edit plan -> approve", result.stdout)
            self.assertIn("Most common path", result.stdout)

    def test_help_reports_current_state_when_workspace_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "help")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Current state: awaiting_approval", result.stdout)
            self.assertIn("Next command: `scripts/long_loop.py approve`", result.stdout)

    def test_approved_run_executes_one_iteration_and_judge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            scripts = cwd / "scripts"
            scripts.mkdir()
            run_verify = scripts / "run-verify.sh"
            run_verify.write_text("#!/usr/bin/env bash\necho verify ok\n", encoding="utf-8")
            scan = scripts / "scan_diff_residue.py"
            scan.write_text("#!/usr/bin/env python3\nprint('scan ok')\n", encoding="utf-8")
            run_verify.chmod(0o755)
            scan.chmod(0o755)

            self.run_script(cwd, "plan", "--goal", "ship feature")
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "run", "--once", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads((cwd / ".long-loop" / "state.json").read_text())
            self.assertEqual(state["iterations"], 1)
            self.assertEqual(state["last_validation"], "pass")
            self.assertEqual(state["stop_reason"], "max iterations reached")

    def test_run_respects_zero_minute_budget_before_agent_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "run", "--max-iterations", "3", "--max-minutes", "0", "--agent-cmd", "false")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads((cwd / ".long-loop" / "state.json").read_text())
            self.assertEqual(state["iterations"], 0)
            self.assertEqual(state["stop_reason"], "max minutes reached")


if __name__ == "__main__":
    unittest.main()

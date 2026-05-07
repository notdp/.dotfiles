import json
import subprocess
import tempfile
import unittest
from datetime import datetime
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

    def workspace(self, cwd: Path) -> Path:
        marker = cwd / ".long-loop" / "current"
        if marker.exists():
            return cwd / ".long-loop" / marker.read_text(encoding="utf-8").strip()
        return cwd / ".long-loop"

    def test_plan_creates_approval_gated_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "plan", "--goal", "ship feature")

            self.assertEqual(result.returncode, 0, result.stderr)
            root = self.workspace(cwd)
            self.assertEqual(root.parent, cwd / ".long-loop")
            self.assertTrue(root.name.startswith(datetime.now().strftime("%Y-%m-%d") + "_ship-feature"))
            self.assertFalse((cwd / ".long-loop" / "state.json").exists())
            self.assertTrue((root / "PROMPT.md").exists())
            self.assertTrue((root / "SPEC.md").exists())
            self.assertTrue((root / "specs" / "main.md").exists())
            self.assertTrue((root / "IMPLEMENTATION_PLAN.md").exists())
            self.assertTrue((root / "fix_plan.md").exists())
            self.assertTrue((root / "ASSERT.md").exists())
            self.assertTrue((root / "validator.md").exists())
            self.assertTrue((root / "validator-results.json").exists())
            self.assertTrue((root / "events.jsonl").exists())
            self.assertTrue((root / "progress.md").exists())
            self.assertTrue((root / "logs").exists())
            state = json.loads((root / "state.json").read_text())
            self.assertEqual(state["goal"], "ship feature")
            self.assertEqual(state["status"], "awaiting_approval")
            self.assertEqual(state["approval"], "pending")

    def test_plan_adds_long_loop_to_gitignore_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            gitignore = cwd / ".gitignore"
            gitignore.write_text("dist/\n", encoding="utf-8")

            first = self.run_script(cwd, "plan", "--goal", "ship feature")
            second = self.run_script(cwd, "plan", "--goal", "ship other feature")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            lines = gitignore.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines.count(".long-loop/"), 1)

    def test_plan_creates_gitignore_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "plan", "--goal", "ship feature")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((cwd / ".gitignore").read_text(encoding="utf-8"), ".long-loop/\n")

    def test_plan_prints_review_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "plan", "--goal", "ship feature")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# Long Loop Review", result.stdout)
            self.assertIn("## SPEC.md", result.stdout)
            self.assertIn("## IMPLEMENTATION_PLAN.md", result.stdout)
            self.assertIn("## fix_plan.md", result.stdout)
            self.assertIn("## ASSERT.md", result.stdout)
            self.assertIn("## validator.md", result.stdout)
            self.assertIn("Next: review the plan above, then run", result.stdout)

    def test_init_is_approval_gated_alias_for_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "init", "--goal", "ship feature")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((self.workspace(cwd) / "state.json").read_text())
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
            state = json.loads((self.workspace(cwd) / "state.json").read_text())
            self.assertEqual(state["status"], "stopped")
            self.assertEqual(state["stop_reason"], "needs user")

    def test_run_requires_agent_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "init", "--goal", "ship feature")
            result = self.run_script(cwd, "run", "--once")

            self.assertEqual(result.returncode, 2)
            self.assertIn("run requires --agent-cmd", result.stderr)

    def test_run_from_initial_plan_auto_approves_and_executes(self) -> None:
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
            result = self.run_script(cwd, "run", "--once", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads((self.workspace(cwd) / "state.json").read_text())
            self.assertEqual(state["approval"], "approved")
            self.assertEqual(state["iterations"], 1)
            self.assertIn("auto-approved long-loop plan via run", result.stdout)

    def test_approve_allows_execution_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "approve")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((self.workspace(cwd) / "state.json").read_text())
            self.assertEqual(state["status"], "approved")
            self.assertEqual(state["approval"], "approved")

    def test_pause_records_intervention_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "pause", "--reason", "adjust plan")

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads((self.workspace(cwd) / "state.json").read_text())
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
            self.assertFalse((cwd / ".long-loop").exists())
            self.assertIn("State Flow", result.stdout)
            self.assertIn("plan -> awaiting_approval -> approve -> approved -> run -> running", result.stdout)
            self.assertIn("pause -> paused -> edit plan -> approve", result.stdout)
            self.assertIn("Most common path", result.stdout)

    def test_status_does_not_create_workspace_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "status")

            self.assertEqual(result.returncode, 2)
            self.assertFalse((cwd / ".long-loop").exists())
            self.assertIn("missing state file", result.stderr)

    def test_help_reports_current_state_when_workspace_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "help")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Current state: awaiting_approval", result.stdout)
            self.assertIn('Next command: `scripts/long_loop.py run --once --agent-cmd "..."`', result.stdout)

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
            workspace = self.workspace(cwd)
            state = json.loads((workspace / "state.json").read_text())
            self.assertEqual(state["iterations"], 1)
            self.assertEqual(state["last_validation"], "pass")
            self.assertEqual(state["stop_reason"], "max iterations reached")
            self.assertIn("## Iteration 1 Summary", result.stdout)
            self.assertIn("Agent: pass", result.stdout)
            self.assertIn("Verify: pass", result.stdout)
            progress = (workspace / "progress.md").read_text(encoding="utf-8")
            self.assertIn("## Iteration 1 Summary", progress)
            events = (workspace / "events.jsonl").read_text(encoding="utf-8").splitlines()
            event_payloads = [json.loads(line) for line in events if line.strip()]
            self.assertTrue(any(event["event"] == "validator-pass" for event in event_payloads))
            self.assertTrue(any(event["event"] == "iteration-summary" for event in event_payloads))
            log_text = next((workspace / "logs").glob("*.md")).read_text(encoding="utf-8")
            self.assertRegex(log_text, r"## 20\\d\\d-\\d\\d-\\d\\dT.* \\| iteration-1 \\| validator-pass \\|")

    def test_run_uses_fresh_context_without_prior_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            scripts = cwd / "scripts"
            scripts.mkdir()
            run_verify = scripts / "run-verify.sh"
            run_verify.write_text("#!/usr/bin/env bash\necho verify ok\n", encoding="utf-8")
            scan = scripts / "scan_diff_residue.py"
            scan.write_text("#!/usr/bin/env python3\nprint('scan ok')\n", encoding="utf-8")
            capture = scripts / "capture_context.py"
            capture.write_text(
                "import pathlib, sys\npathlib.Path('context.txt').write_text(sys.stdin.read(), encoding='utf-8')\nprint('OLD_STDOUT_SHOULD_NOT_LEAK')\n",
                encoding="utf-8",
            )
            run_verify.chmod(0o755)
            scan.chmod(0o755)

            self.run_script(cwd, "plan", "--goal", "ship feature")
            self.run_script(cwd, "approve")
            first = self.run_script(cwd, "run", "--once", "--agent-cmd", "python3 scripts/capture_context.py")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.run_script(cwd, "approve")
            second = self.run_script(cwd, "run", "--once", "--agent-cmd", "python3 scripts/capture_context.py")

            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            context = (cwd / "context.txt").read_text(encoding="utf-8")
            self.assertIn("fix_plan.md", context)
            self.assertIn("validator.md", context)
            self.assertNotIn("OLD_STDOUT_SHOULD_NOT_LEAK", context)

    def test_run_requires_validator_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            (self.workspace(cwd) / "validator.md").unlink()
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "run", "--once", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 2)
            self.assertIn("missing validator file", result.stderr)

    def test_validator_failure_stops_before_marking_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            (self.workspace(cwd) / "validator.md").write_text(
                "# Validator\n\n## Item validator\n\n- `false`\n",
                encoding="utf-8",
            )
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "run", "--once", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 1)
            state = json.loads((self.workspace(cwd) / "state.json").read_text())
            self.assertEqual(state["status"], "stopped")
            self.assertEqual(state["last_validation"], "fail")
            self.assertIn("judge validation failed", state["stop_reason"])
            fix_plan = (self.workspace(cwd) / "fix_plan.md").read_text(encoding="utf-8")
            self.assertIn("Status: pending", fix_plan)

    def test_run_respects_zero_minute_budget_before_agent_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            self.run_script(cwd, "approve")
            result = self.run_script(cwd, "run", "--max-iterations", "3", "--max-minutes", "0", "--agent-cmd", "false")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads((self.workspace(cwd) / "state.json").read_text())
            self.assertEqual(state["iterations"], 0)
            self.assertEqual(state["stop_reason"], "max minutes reached")


if __name__ == "__main__":
    unittest.main()

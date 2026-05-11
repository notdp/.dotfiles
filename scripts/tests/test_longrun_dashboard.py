import importlib.util
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "longrun_dashboard.py"
LONGRUN_BIN = REPO_ROOT / "bin" / "longrun"


def load_module():
    spec = importlib.util.spec_from_file_location("longrun_dashboard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LongrunDashboardTests(unittest.TestCase):
    def write_workspace(
        self,
        root: Path,
        name: str,
        *,
        status: str,
        current_item: str,
        current_phase: str,
        updated_at: str,
        last_validation: str | None = None,
        stop_reason: str | None = None,
        last_heartbeat_at: str | None = None,
    ) -> Path:
        workspace = root / ".long-loop" / name
        workspace.mkdir(parents=True)
        (workspace / "state.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "created_by": "dev-long-loop-harness",
                    "workspace_token": "token",
                    "goal": name,
                    "status": status,
                    "updated_at": updated_at,
                    "current_item": current_item,
                    "current_phase": current_phase,
                    "last_validation": last_validation,
                    "stop_reason": stop_reason,
                    "last_heartbeat_at": last_heartbeat_at,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (workspace / "fix_plan.md").write_text(f"# Fix Plan\n\n### {current_item}\n- Status: {status}\n", encoding="utf-8")
        (workspace / "logs.md").write_text("# Logs\n\n## current work\n\n- P1 evidence\n", encoding="utf-8")
        (workspace / "runtime.log").write_text("old P0 log\n\n## latest command\n\nP1 started\n", encoding="utf-8")
        return workspace

    def test_snapshot_prefers_current_running_state_over_previous_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workspace = self.write_workspace(
                repo,
                "p1-run",
                status="running",
                current_item="P1: Run labels",
                current_phase="phases/02_phase2_labeling",
                updated_at="2026-05-10T02:00:00+00:00",
                last_validation="fail",
                last_heartbeat_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            )
            module = load_module()

            snapshot = module.build_snapshot(repo=repo, workspace=workspace)

            self.assertEqual(snapshot["selected"]["health"], "running")
            self.assertIn("P1: Run labels", snapshot["selected"]["headline"])
            self.assertEqual(snapshot["selected"]["last_validation_label"], "Previous validation")
            self.assertFalse(snapshot["selected"]["needs_user"])

    def test_snapshot_stopped_during_p1_does_not_look_like_phase1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workspace = self.write_workspace(
                repo,
                "p1-stopped",
                status="stopped",
                current_item="P1: Run Phase 2 Gemini labeling",
                current_phase="phases/02_phase2_labeling",
                updated_at="2026-05-10T02:00:00+00:00",
                stop_reason="agent command idle timeout after 300s",
            )
            module = load_module()

            snapshot = module.build_snapshot(repo=repo, workspace=workspace)

            self.assertEqual(snapshot["selected"]["health"], "needs_attention")
            self.assertIn("Stopped during P1", snapshot["selected"]["headline"])
            self.assertIn("idle timeout", snapshot["selected"]["next_action"])
            self.assertNotIn("Phase 1", snapshot["selected"]["headline"])

    def test_snapshot_treats_all_done_fix_plan_as_completed_even_if_state_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workspace = self.write_workspace(
                repo,
                "completed-after-timeout",
                status="stopped",
                current_item="P1: Run Phase 2 Gemini labeling",
                current_phase="phases/02_phase2_labeling",
                updated_at="2026-05-10T02:00:00+00:00",
                stop_reason="agent command idle timeout after 300s",
            )
            (workspace / "fix_plan.md").write_text(
                "# Fix Plan\n\n"
                "### P0: Monitor Phase 1\n- Status: done\n"
                "### P1: Run Phase 2 Gemini labeling\n- Status: done\n"
                "### P2: Produce final report\n- Status: done\n",
                encoding="utf-8",
            )
            module = load_module()

            snapshot = module.build_snapshot(repo=repo, workspace=workspace)

            self.assertEqual(snapshot["selected"]["health"], "done")
            self.assertIn("completed", snapshot["selected"]["headline"].lower())
            self.assertIn("fix_plan", snapshot["selected"]["why"])

    def test_html_is_dynamic_dashboard_not_static_log_dump(self) -> None:
        module = load_module()

        html = module.render_index_html()

        self.assertIn("Longrun Dashboard", html)
        self.assertIn("/api/snapshot", html)
        self.assertIn("Now", html)
        self.assertIn("Needs attention", html)
        self.assertIn("<details", html)

    def test_snapshot_cli_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            old_workspace = self.write_workspace(
                repo,
                "old",
                status="stopped",
                current_item="P0: Old",
                current_phase="phases/01_initial",
                updated_at="2026-05-10T01:00:00+00:00",
            )
            self.write_workspace(
                repo,
                "latest",
                status="running",
                current_item="P1: Run labels",
                current_phase="phases/02_phase2_labeling",
                updated_at="2026-05-10T02:00:00+00:00",
            )

            result = subprocess.run(
                ["python3", str(SCRIPT), str(repo), "--workspace", str(old_workspace), "--snapshot"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(Path(payload["selected_workspace"]).resolve(), old_workspace.resolve())
            self.assertEqual(payload["selected"]["state"]["workspace_token"], "<redacted>")

    def test_longrun_wrapper_exists(self) -> None:
        self.assertTrue(LONGRUN_BIN.exists())


if __name__ == "__main__":
    unittest.main()

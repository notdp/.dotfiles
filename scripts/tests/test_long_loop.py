import json
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LONG_LOOP_SCRIPT = REPO_ROOT / "skills" / "dev-long-loop" / "long_loop.py"
LONG_LOOP_SYMLINK = REPO_ROOT / "scripts" / "long_loop.py"


class LongLoopTests(unittest.TestCase):
    def run_script(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(LONG_LOOP_SCRIPT), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )

    def make_workspace_ready(self, root: Path, *, status: str = "pending") -> None:
        (root / "SPEC_OVERVIEW.md").write_text(
            "# Spec Overview\n\n## Task Understanding\n\nShip the concrete feature.\n\n## Code Facts\n\n- Verified existing files.\n",
            encoding="utf-8",
        )
        (root / "fix_plan.md").write_text(
            "# Fix Plan\n\n"
            "## Active\n\n"
            "### P0: Ship concrete feature\n"
            f"- Status: {status}\n"
            "- Phase: phases/01_initial\n"
            "- Evidence needed: logs.md records validation evidence.\n"
            "- QA: phases/01_initial/qa.md\n"
            "\n## Backlog\n\n- Empty.\n",
            encoding="utf-8",
        )
        (root / "qa.md").write_text("# Overall QA\n\n- [ ] Run validators.\n", encoding="utf-8")
        phase = root / "phases" / "01_initial"
        phase.mkdir(parents=True, exist_ok=True)
        (phase / "spec.md").write_text("# Phase Spec\n\nShip concrete feature.\n", encoding="utf-8")
        (phase / "qa.md").write_text("# Phase QA\n\n- [ ] Validate concrete feature.\n", encoding="utf-8")
        (phase / "research.md").write_text("# Phase Research\n\n- Existing code reviewed.\n", encoding="utf-8")
        (phase / "plan.md").write_text("# Phase Plan\n\n- Implement and verify.\n", encoding="utf-8")

    def install_passing_validators(self, cwd: Path) -> None:
        scripts = cwd / "scripts"
        scripts.mkdir(exist_ok=True)
        verify = scripts / "run-verify.sh"
        verify.write_text("#!/usr/bin/env bash\necho verify-pass\n", encoding="utf-8")
        verify.chmod(0o755)
        scan = scripts / "scan_diff_residue.py"
        scan.write_text("#!/usr/bin/env python3\nprint('scan-pass')\n", encoding="utf-8")
        scan.chmod(0o755)

    def workspace(self, cwd: Path) -> Path:
        workspaces = sorted(path for path in (cwd / ".long-loop").iterdir() if path.is_dir())
        self.assertEqual(len(workspaces), 1)
        return workspaces[0]

    def test_plan_creates_v2_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "plan", "--goal", "ship feature", "--token-budget", "1M")

            self.assertEqual(result.returncode, 0, result.stderr)
            root = self.workspace(cwd)
            self.assertTrue(root.name.startswith(datetime.now().strftime("%Y-%m-%d") + "_ship-feature"))
            self.assertFalse((cwd / ".long-loop" / "current").exists())
            self.assertTrue((root / "PROMPT.md").exists())
            self.assertTrue((root / "SPEC_OVERVIEW.md").exists())
            self.assertTrue((root / "fix_plan.md").exists())
            self.assertTrue((root / "qa.md").exists())
            self.assertTrue((root / "logs.md").exists())
            self.assertTrue((root / "state.json").exists())
            self.assertTrue((root / "phases" / "01_initial" / "spec.md").exists())
            self.assertTrue((root / "phases" / "01_initial" / "qa.md").exists())
            self.assertTrue((root / "phases" / "01_initial" / "research.md").exists())
            self.assertTrue((root / "phases" / "01_initial" / "plan.md").exists())
            self.assertFalse((root / "validator-results.json").exists())
            self.assertFalse((root / "events.jsonl").exists())
            self.assertFalse((root / "SPEC.md").exists())
            self.assertFalse((root / "IMPLEMENTATION_PLAN.md").exists())
            self.assertFalse((root / "ASSERT.md").exists())
            state = json.loads((root / "state.json").read_text())
            self.assertEqual(state["goal"], "ship feature")
            self.assertEqual(state["status"], "ready")
            self.assertEqual(state["token_budget"], "1M")
            self.assertEqual(state["created_by"], "dev-long-loop-harness")
            self.assertIn("workspace_token", state)

    def test_prompt_contains_ralph_workflow_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            prompt = (self.workspace(cwd) / "PROMPT.md").read_text(encoding="utf-8")

            self.assertIn("Ralph Loop", prompt)
            self.assertIn("/think-research", prompt)
            self.assertIn("/think-plan", prompt)
            self.assertIn("/guard-close", prompt)
            self.assertIn("Token budget: 500K", prompt)
            self.assertIn("Do not add placeholder", prompt)
            self.assertNotIn("Status: blocked", prompt)

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

    def test_plan_prints_review_bundle_with_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_script(cwd, "plan", "--goal", "ship feature")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# Long Loop Review", result.stdout)
            self.assertIn("## SPEC_OVERVIEW.md", result.stdout)
            self.assertIn("## fix_plan.md", result.stdout)
            self.assertIn("## qa.md", result.stdout)
            self.assertIn("## PROMPT.md", result.stdout)
            self.assertIn("--dir .long-loop/", result.stdout)
            self.assertIn(str(LONG_LOOP_SCRIPT.resolve()), result.stdout)
            self.assertNotIn("--max-minutes", result.stdout)

    def test_only_simple_commands_are_supported(self) -> None:
        for command in ["init", "watch", "pause", "stop", "resume", "approve", "help"]:
            with self.subTest(command=command), tempfile.TemporaryDirectory() as tmp:
                result = self.run_script(Path(tmp), command)
                self.assertEqual(result.returncode, 2)
                self.assertIn("invalid choice", result.stderr)

    def test_status_and_tail_read_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)

            status = self.run_script(cwd, "status", "--dir", str(workspace))
            tail = self.run_script(cwd, "tail", "--dir", str(workspace), "--lines", "20")

            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("status: ready", status.stdout)
            self.assertIn("token_budget: 500K", status.stdout)
            self.assertEqual(tail.returncode, 0, tail.stderr)
            self.assertIn("plan-created", tail.stdout)

    def test_run_builds_rich_context_and_prints_logs_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.install_passing_validators(cwd)
            scripts = cwd / "scripts"
            agent = scripts / "agent.py"
            agent.write_text(
                "import pathlib, sys\n"
                "ctx = sys.stdin.read()\n"
                "pathlib.Path('context.txt').write_text(ctx, encoding='utf-8')\n"
                "fix_plan = pathlib.Path('.long-loop/2026-PLACEHOLDER/fix_plan.md')\n"
                "fix_plan.write_text(fix_plan.read_text(encoding='utf-8').replace('- Status: pending', '- Status: done'), encoding='utf-8')\n"
                "with open('.long-loop/2026-PLACEHOLDER/logs.md', 'a', encoding='utf-8') as f:\n"
                "    f.write('\\n## agent-log\\n\\n- validation evidence\\n')\n",
                encoding="utf-8",
            )
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace)
            text = agent.read_text(encoding="utf-8").replace(".long-loop/2026-PLACEHOLDER", str(workspace))
            agent.write_text(text, encoding="utf-8")

            result = self.run_script(cwd, "run", "--dir", str(workspace), "--max-iterations", "1", "--agent-cmd", "python3 scripts/agent.py")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            context = (cwd / "context.txt").read_text(encoding="utf-8")
            self.assertIn("SPEC_OVERVIEW.md", context)
            self.assertIn("Selected fix_plan.md item", context)
            self.assertIn("P0: Ship concrete feature", context)
            self.assertIn("fix_plan.md", context)
            self.assertIn("qa.md", context)
            self.assertIn("logs.md", context)
            self.assertIn("logs.md delta", result.stdout)
            self.assertIn("validation evidence", result.stdout)
            state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["iterations"], 1)
            self.assertEqual(state["last_validation"], "pass")
            self.assertEqual(state["current_item"], "P0: Ship concrete feature")

    def test_run_rejects_starter_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "run", "--dir", str(self.workspace(cwd)), "--max-iterations", "1", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 2)
            self.assertIn("starter placeholders", result.stderr)

    def test_run_rejects_workspace_not_created_by_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            workspace = cwd / ".long-loop" / "manual"
            workspace.mkdir(parents=True)
            (workspace / "PROMPT.md").write_text("# Prompt\n", encoding="utf-8")
            (workspace / "logs.md").write_text("# Logs\n", encoding="utf-8")
            (workspace / "state.json").write_text(json.dumps({"version": 2, "status": "ready"}) + "\n", encoding="utf-8")
            self.make_workspace_ready(workspace)

            result = self.run_script(cwd, "run", "--dir", str(workspace), "--max-iterations", "1", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 2)
            self.assertIn("not created by dev-long-loop plan", result.stderr)

    def test_run_rejects_unknown_fix_plan_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace, status="active")

            result = self.run_script(cwd, "run", "--dir", str(workspace), "--max-iterations", "1", "--agent-cmd", "true")

            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid fix_plan status", result.stderr)
            self.assertIn("active", result.stderr)

    def test_run_requires_logs_and_fix_plan_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.install_passing_validators(cwd)
            scripts = cwd / "scripts"
            agent = scripts / "agent.py"
            agent.write_text(
                "with open('.long-loop/2026-PLACEHOLDER/logs.md', 'a', encoding='utf-8') as f:\n"
                "    f.write('\\n## agent-log\\n\\n- validation evidence\\n')\n",
                encoding="utf-8",
            )
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace)
            agent.write_text(agent.read_text(encoding="utf-8").replace(".long-loop/2026-PLACEHOLDER", str(workspace)), encoding="utf-8")

            result = self.run_script(cwd, "run", "--dir", str(workspace), "--max-iterations", "1", "--agent-cmd", "python3 scripts/agent.py")

            self.assertEqual(result.returncode, 1)
            self.assertIn("fix_plan.md did not update selected item status", result.stdout)

    def test_run_treats_missing_validation_as_structural_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            scripts = cwd / "scripts"
            scripts.mkdir()
            agent = scripts / "agent.py"
            agent.write_text(
                "import pathlib\n"
                "fix_plan = pathlib.Path('.long-loop/2026-PLACEHOLDER/fix_plan.md')\n"
                "fix_plan.write_text(fix_plan.read_text(encoding='utf-8').replace('- Status: pending', '- Status: done'), encoding='utf-8')\n"
                "with open('.long-loop/2026-PLACEHOLDER/logs.md', 'a', encoding='utf-8') as f:\n"
                "    f.write('\\n## agent-log\\n\\n- validation evidence\\n')\n",
                encoding="utf-8",
            )
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace)
            agent.write_text(agent.read_text(encoding="utf-8").replace(".long-loop/2026-PLACEHOLDER", str(workspace)), encoding="utf-8")

            result = self.run_script(cwd, "run", "--dir", str(workspace), "--max-iterations", "1", "--agent-cmd", "python3 scripts/agent.py")

            self.assertEqual(result.returncode, 1)
            self.assertIn("validation structural gap", result.stdout)

    def test_run_stops_on_blocked_item_without_running_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace, status="blocked")

            result = self.run_script(cwd, "run", "--dir", str(workspace), "--max-iterations", "1", "--agent-cmd", "false")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("blocked item requires user action", result.stdout)
            state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["iterations"], 0)
            self.assertEqual(state["stop_reason"], "blocked item requires user action")

    def test_run_uses_explicit_repo_root_for_agent_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo = parent / "repo"
            other = parent / "other"
            repo.mkdir()
            other.mkdir()
            self.install_passing_validators(repo)
            agent = repo / "scripts" / "agent.py"
            agent.write_text(
                "import pathlib, sys\n"
                "pathlib.Path('cwd.txt').write_text(str(pathlib.Path.cwd()), encoding='utf-8')\n"
                "fix_plan = pathlib.Path('.long-loop/2026-PLACEHOLDER/fix_plan.md')\n"
                "fix_plan.write_text(fix_plan.read_text(encoding='utf-8').replace('- Status: pending', '- Status: done'), encoding='utf-8')\n"
                "with open('.long-loop/2026-PLACEHOLDER/logs.md', 'a', encoding='utf-8') as f:\n"
                "    f.write('\\n## agent-log\\n\\n- validation evidence\\n')\n",
                encoding="utf-8",
            )
            self.run_script(repo, "plan", "--goal", "ship feature")
            workspace = self.workspace(repo)
            self.make_workspace_ready(workspace)
            agent.write_text(agent.read_text(encoding="utf-8").replace(".long-loop/2026-PLACEHOLDER", str(workspace)), encoding="utf-8")

            result = self.run_script(
                other,
                "run",
                "--dir",
                str(workspace),
                "--repo-root",
                str(repo),
                "--max-iterations",
                "1",
                "--agent-cmd",
                "python3 scripts/agent.py",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((repo / "cwd.txt").read_text(encoding="utf-8"), str(repo.resolve()))

    def test_run_stops_idle_agent_and_writes_runtime_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            scripts = cwd / "scripts"
            scripts.mkdir()
            agent = scripts / "agent.py"
            agent.write_text("import time\nprint('agent-start', flush=True)\ntime.sleep(2)\n", encoding="utf-8")
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace)

            result = self.run_script(
                cwd,
                "run",
                "--dir",
                str(workspace),
                "--max-iterations",
                "1",
                "--idle-timeout-seconds",
                "1",
                "--agent-cmd",
                "python3 scripts/agent.py",
            )

            self.assertEqual(result.returncode, 1)
            state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
            self.assertIn("idle timeout", state["stop_reason"])
            self.assertTrue((workspace / "runtime.log").exists())
            self.assertIn("agent-start", (workspace / "runtime.log").read_text(encoding="utf-8"))

    def test_checkpoint_commits_when_phase_is_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=cwd, check=True)
            self.install_passing_validators(cwd)
            scripts = cwd / "scripts"
            agent = scripts / "agent.py"
            agent.write_text(
                "import pathlib\n"
                "pathlib.Path('feature.txt').write_text('done\\n', encoding='utf-8')\n"
                "fix_plan = pathlib.Path('.long-loop/2026-PLACEHOLDER/fix_plan.md')\n"
                "fix_plan.write_text(fix_plan.read_text(encoding='utf-8').replace('- Status: pending', '- Status: done'), encoding='utf-8')\n"
                "with open('.long-loop/2026-PLACEHOLDER/logs.md', 'a', encoding='utf-8') as f:\n"
                "    f.write('\\n## agent-log\\n\\n- validation evidence\\n')\n",
                encoding="utf-8",
            )
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace)
            agent.write_text(agent.read_text(encoding="utf-8").replace(".long-loop/2026-PLACEHOLDER", str(workspace)), encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore", "scripts"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "baseline"], cwd=cwd, check=True, capture_output=True)

            result = self.run_script(
                cwd,
                "run",
                "--dir",
                str(workspace),
                "--max-iterations",
                "1",
                "--checkpoint-commits",
                "--agent-cmd",
                "python3 scripts/agent.py",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            log = subprocess.run(["git", "log", "--oneline", "-1"], cwd=cwd, text=True, capture_output=True, check=True)
            self.assertIn("checkpoint(long-loop): complete phases/01_initial", log.stdout)

    def test_checkpoint_refuses_dirty_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=cwd, check=True)
            self.install_passing_validators(cwd)
            subprocess.run(["git", "add", "scripts"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "baseline"], cwd=cwd, check=True, capture_output=True)
            (cwd / "unrelated.txt").write_text("do not include\n", encoding="utf-8")
            agent = cwd / "scripts" / "agent.py"
            agent.write_text(
                "import pathlib\n"
                "pathlib.Path('feature.txt').write_text('done\\n', encoding='utf-8')\n"
                "fix_plan = pathlib.Path('.long-loop/2026-PLACEHOLDER/fix_plan.md')\n"
                "fix_plan.write_text(fix_plan.read_text(encoding='utf-8').replace('- Status: pending', '- Status: done'), encoding='utf-8')\n"
                "with open('.long-loop/2026-PLACEHOLDER/logs.md', 'a', encoding='utf-8') as f:\n"
                "    f.write('\\n## agent-log\\n\\n- validation evidence\\n')\n",
                encoding="utf-8",
            )
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace)
            agent.write_text(agent.read_text(encoding="utf-8").replace(".long-loop/2026-PLACEHOLDER", str(workspace)), encoding="utf-8")

            result = self.run_script(
                cwd,
                "run",
                "--dir",
                str(workspace),
                "--max-iterations",
                "1",
                "--checkpoint-commits",
                "--agent-cmd",
                "python3 scripts/agent.py",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("checkpoint refused: dirty worktree before iteration", result.stdout)

    def test_scripts_path_is_relative_symlink_to_skill_harness(self) -> None:
        self.assertTrue(LONG_LOOP_SYMLINK.is_symlink())
        target = Path(LONG_LOOP_SYMLINK).readlink()
        self.assertFalse(target.is_absolute(), f"symlink target must be relative, got {target}")
        self.assertEqual(LONG_LOOP_SYMLINK.resolve(), LONG_LOOP_SCRIPT.resolve())

    def test_run_requires_agent_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "run", "--dir", str(self.workspace(cwd)))

            self.assertEqual(result.returncode, 2)
            self.assertIn("run requires --agent-cmd", result.stderr)

    def test_run_rejects_max_minutes_option(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            result = self.run_script(cwd, "run", "--dir", str(self.workspace(cwd)), "--max-iterations", "3", "--max-minutes", "0", "--agent-cmd", "false")

            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments: --max-minutes", result.stderr)


if __name__ == "__main__":
    unittest.main()

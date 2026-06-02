import json
import os
import subprocess
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LONG_LOOP_SCRIPT = REPO_ROOT / "coding-skills" / "dev-long-loop" / "long_loop.py"
LONG_LOOP_SYMLINK = REPO_ROOT / "scripts" / "long_loop.py"


class LongLoopTests(unittest.TestCase):
    def run_script(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(LONG_LOOP_SCRIPT), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )

    def run_script_with_env(self, cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(LONG_LOOP_SCRIPT), *args],
            cwd=cwd,
            env=env,
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

    def install_fake_tmux(self, cwd: Path) -> tuple[Path, dict[str, str]]:
        bindir = cwd / "bin"
        bindir.mkdir()
        log = cwd / "tmux.log"
        tmux = bindir / "tmux"
        tmux.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['TMUX_LOG']).open('a', encoding='utf-8').write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if len(sys.argv) > 1 and sys.argv[1] in {'split-window', 'new-window'}:\n"
            "    print('%999')\n",
            encoding="utf-8",
        )
        tmux.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = f"{bindir}{os.pathsep}{env.get('PATH', '')}"
        env["TMUX"] = "/tmp/fake-tmux"
        env["TMUX_PANE"] = "%1"
        env["TMUX_LOG"] = str(log)
        return log, env

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
            self.assertTrue((root / "ORCHESTRATOR.md").exists())
            self.assertTrue((root / "WORKER_PROMPT.md").exists())
            self.assertTrue((root / "HANDOFF.md").exists())
            self.assertTrue((root / "WORKER_CONFIG.json").exists())
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

    def test_plan_creates_agent_orchestration_contract_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            root = self.workspace(cwd)

            orchestrator = (root / "ORCHESTRATOR.md").read_text(encoding="utf-8")
            worker_prompt = (root / "WORKER_PROMPT.md").read_text(encoding="utf-8")
            handoff = (root / "HANDOFF.md").read_text(encoding="utf-8")
            worker_config = json.loads((root / "WORKER_CONFIG.json").read_text(encoding="utf-8"))

            self.assertIn("Current agent", orchestrator)
            self.assertIn("Do not use Hive as a required dependency", orchestrator)
            self.assertIn("Use `long_loop.py launch-worker`", orchestrator)
            self.assertIn("Do not hand-write `tmux new-session`", orchestrator)
            self.assertIn("HANDOFF.md + fix_plan.md + phase QA", orchestrator)
            self.assertIn("handoff complete but worker process still running", orchestrator)
            self.assertIn("one worker round", worker_prompt)
            self.assertIn("HANDOFF.md", worker_prompt)
            self.assertIn("Do not start the next round", worker_prompt)
            self.assertIn("state file", worker_prompt)
            self.assertIn("resume command", worker_prompt)
            self.assertIn("# Latest Worker Handoff", handoff)
            self.assertIn("- Status: pending", handoff)
            self.assertIn("failure_summary", handoff)
            self.assertIn("failed_examples", handoff)
            self.assertIn("failed_set", handoff)
            self.assertEqual(worker_config["agent"], "droid")
            self.assertEqual(worker_config["tmuxMode"], "split-right")

    def test_ensure_contract_adds_missing_worker_files_to_existing_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            root = self.workspace(cwd)
            for name in ["ORCHESTRATOR.md", "WORKER_PROMPT.md", "HANDOFF.md", "WORKER_CONFIG.json"]:
                (root / name).unlink()

            result = self.run_script(cwd, "ensure-contract", "--dir", str(root))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("contract-ready", result.stdout)
            for name in ["ORCHESTRATOR.md", "WORKER_PROMPT.md", "HANDOFF.md", "WORKER_CONFIG.json"]:
                self.assertTrue((root / name).exists(), name)

    def test_launch_worker_without_tmux_prints_manual_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            root = self.workspace(cwd)
            self.make_workspace_ready(root)
            env = os.environ.copy()
            env.pop("TMUX", None)
            env.pop("TMUX_PANE", None)

            result = self.run_script_with_env(
                cwd,
                env,
                "launch-worker",
                "--dir",
                str(root),
                "--item",
                "P0: Ship concrete feature",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("tmux not detected", result.stdout)
            self.assertIn("WORKER_PROMPT.md", result.stdout)
            self.assertIn("P0: Ship concrete feature", result.stdout)

    def test_launch_worker_opens_tmux_split_with_absolute_paths_and_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            log, env = self.install_fake_tmux(cwd)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            root = self.workspace(cwd)
            self.make_workspace_ready(root)

            result = self.run_script_with_env(
                cwd,
                env,
                "launch-worker",
                "--dir",
                str(root),
                "--item",
                "P0: Ship concrete feature",
                "--model",
                "gpt-5.5-fast",
                "--reasoning-effort",
                "high",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            split = calls[0]
            title = calls[1]
            self.assertFalse(any(call[0] == "new-window" for call in calls), calls)
            self.assertEqual(split[:5], ["split-window", "-t", "%1", "-h", "-P"])
            self.assertIn("-c", split)
            self.assertEqual(split[split.index("-c") + 1], str(cwd.resolve()))
            command = split[-1]
            self.assertIn("droid", command)
            self.assertIn("--cwd", command)
            self.assertIn(str(cwd.resolve()), command)
            self.assertIn("--settings", command)
            self.assertIn(str((root / "WORKER_LAUNCH_PROMPT.md").resolve()), command)
            self.assertIn("Read", command)
            self.assertNotIn("droid exec", command)
            self.assertTrue((root / "WORKER_SETTINGS.json").exists())
            self.assertEqual(title[:4], ["select-pane", "-t", "%999", "-T"])
            self.assertIn("LL P0 01_initial", title)
            launch_prompt = (root / "WORKER_LAUNCH_PROMPT.md").read_text(encoding="utf-8")
            self.assertIn("Spec stage", launch_prompt)
            self.assertIn("Implementation and debug stage", launch_prompt)
            self.assertIn("Handoff stage", launch_prompt)
            self.assertIn(str(root.resolve()), launch_prompt)

    def test_launch_worker_refuses_blocked_item_before_tmux(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            log, env = self.install_fake_tmux(cwd)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            root = self.workspace(cwd)
            self.make_workspace_ready(root, status="blocked")

            result = self.run_script_with_env(
                cwd,
                env,
                "launch-worker",
                "--dir",
                str(root),
                "--item",
                "P0: Ship concrete feature",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("blocked", result.stderr)
            self.assertFalse(log.exists())

    def test_launch_worker_refuses_new_window_without_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            log, env = self.install_fake_tmux(cwd)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            root = self.workspace(cwd)
            self.make_workspace_ready(root)

            result = self.run_script_with_env(
                cwd,
                env,
                "launch-worker",
                "--dir",
                str(root),
                "--item",
                "P0: Ship concrete feature",
                "--tmux-mode",
                "window",
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("new tmux window", result.stderr)
            self.assertFalse(log.exists())

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
            self.assertIn("Use the harness launcher, not hand-written tmux", result.stdout)
            self.assertIn("launch-worker --dir", result.stdout)
            self.assertIn("Do not use `tmux new-session`, `tmux new-window`, or `droid exec` directly", result.stdout)
            self.assertIn("## ORCHESTRATOR.md", result.stdout)
            self.assertIn("## WORKER_PROMPT.md", result.stdout)
            self.assertIn("## HANDOFF.md", result.stdout)
            self.assertIn("## WORKER_CONFIG.json", result.stdout)
            self.assertIn("## SPEC_OVERVIEW.md", result.stdout)
            self.assertIn("## fix_plan.md", result.stdout)
            self.assertIn("## qa.md", result.stdout)
            self.assertIn("## PROMPT.md", result.stdout)
            self.assertIn("--dir .long-loop/", result.stdout)
            self.assertIn(str(LONG_LOOP_SCRIPT.resolve()), result.stdout)
            self.assertNotIn("Use tmux to launch a worker", result.stdout)
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

    def test_observe_prints_status_dialogue_logs_and_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_script(cwd, "plan", "--goal", "ship feature")
            workspace = self.workspace(cwd)
            self.make_workspace_ready(workspace, status="in_progress")
            state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
            state["status"] = "running"
            state["current_item"] = "P0: Ship concrete feature"
            state["last_heartbeat_at"] = "2026-05-10T00:00:00+00:00"
            (workspace / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
            (workspace / "runtime.log").write_text("agent dialogue <needs escaping>\n", encoding="utf-8")
            with (workspace / "logs.md").open("a", encoding="utf-8") as handle:
                handle.write("\n## agent-log\n\n- curated progress\n")

            result = self.run_script(
                cwd,
                "observe",
                "--dir",
                str(workspace),
                "--iterations",
                "1",
                "--runtime-lines",
                "5",
                "--log-lines",
                "5",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("## Long Loop Observe", result.stdout)
            self.assertIn("current_item: P0: Ship concrete feature", result.stdout)
            self.assertIn("current_phase: phases/01_initial", result.stdout)
            self.assertIn("heartbeat_age:", result.stdout)
            self.assertIn("agent dialogue <needs escaping>", result.stdout)
            self.assertIn("curated progress", result.stdout)
            html = (workspace / "observe.html").read_text(encoding="utf-8")
            self.assertIn("Long Loop Observe", html)
            self.assertIn("P0: Ship concrete feature", html)
            self.assertIn("phases/01_initial", html)
            self.assertIn("agent dialogue &lt;needs escaping&gt;", html)

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
            self.assertIn("observe this run in another terminal", result.stdout)
            self.assertIn("observe.html", result.stdout)
            self.assertIn("validation evidence", result.stdout)
            state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["iterations"], 1)
            self.assertEqual(state["last_validation"], "pass")
            self.assertEqual(state["current_item"], "P0: Ship concrete feature")
            self.assertEqual(state["current_phase"], "phases/01_initial")
            self.assertTrue((workspace / "observe.html").exists())

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

    def test_idle_timeout_kills_child_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            scripts = cwd / "scripts"
            scripts.mkdir()
            agent = scripts / "agent.sh"
            marker = cwd / "orphan-marker.txt"
            agent.write_text(
                "#!/usr/bin/env bash\n"
                "python3 - <<'PY'\n"
                "import pathlib, time\n"
                "time.sleep(2)\n"
                f"pathlib.Path({str(marker)!r}).write_text('orphan still ran', encoding='utf-8')\n"
                "PY\n",
                encoding="utf-8",
            )
            agent.chmod(0o755)
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
                "scripts/agent.sh",
            )
            time.sleep(2)

            self.assertEqual(result.returncode, 1)
            self.assertFalse(marker.exists(), "idle timeout must not leave orphan child processes running")

    def test_run_can_disable_idle_timeout_for_quiet_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.install_passing_validators(cwd)
            scripts = cwd / "scripts"
            agent = scripts / "agent.py"
            agent.write_text(
                "import pathlib, time\n"
                "time.sleep(1)\n"
                "fix_plan = pathlib.Path('.long-loop/2026-PLACEHOLDER/fix_plan.md')\n"
                "fix_plan.write_text(fix_plan.read_text(encoding='utf-8').replace('- Status: pending', '- Status: done'), encoding='utf-8')\n"
                "with open('.long-loop/2026-PLACEHOLDER/logs.md', 'a', encoding='utf-8') as f:\n"
                "    f.write('\\n## quiet-agent-log\\n\\n- validation evidence\\n')\n",
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
                "--idle-timeout-seconds",
                "0",
                "--agent-cmd",
                "python3 scripts/agent.py",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["last_validation"], "pass")

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

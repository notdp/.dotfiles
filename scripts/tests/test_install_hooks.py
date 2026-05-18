import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "install_hooks.py"


class InstallHooksTests(unittest.TestCase):
    def run_install(self, *args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )

    def test_droid_check_accepts_current_project_settings(self) -> None:
        result = self.run_install("--target", "droid", "--check")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("scripts/hooks runtime", result.stdout)

    def test_droid_print_preserves_unrelated_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            settings_dir = repo / ".factory"
            settings_dir.mkdir()
            (settings_dir / "settings.json").write_text('{"theme":"dark"}\n', encoding="utf-8")

            result = self.run_install("--target", "droid", "--print", cwd=repo)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["theme"], "dark")
        rendered = json.dumps(payload)
        self.assertIn("scripts/hooks/context_capsule.py", rendered)
        self.assertIn("scripts/hooks/command_guard.py", rendered)

    def test_droid_apply_requires_yes_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = self.run_install("--target", "droid", "--apply", cwd=repo)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("--yes", result.stdout)

    def test_droid_apply_with_yes_writes_project_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = self.run_install("--target", "droid", "--apply", "--yes", cwd=repo)
            settings = json.loads((repo / ".factory" / "settings.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rendered = json.dumps(settings)
        self.assertIn("scripts/hooks/context_capsule.py", rendered)
        self.assertIn("scripts/hooks/stop_check.py", rendered)
        self.assertNotIn("scripts/hooks/context_state.py", rendered)

    def test_default_installs_do_not_enable_compact_recovery(self) -> None:
        droid = self.run_install("--target", "droid", "--print")
        claude = self.run_install("--target", "claude", "--print")
        codex = self.run_install("--target", "codex", "--print")

        self.assertEqual(droid.returncode, 0, droid.stdout + droid.stderr)
        self.assertEqual(claude.returncode, 0, claude.stdout + claude.stderr)
        self.assertEqual(codex.returncode, 0, codex.stdout + codex.stderr)
        self.assertNotIn("context_state.py", droid.stdout)
        self.assertNotIn("context_state.py", claude.stdout)
        self.assertNotIn("context_state.py", codex.stdout)
        self.assertNotIn("PreCompact", droid.stdout)
        self.assertNotIn("PreCompact", claude.stdout)

    def test_default_installs_do_not_enable_fixed_session_start_capsule(self) -> None:
        droid = self.run_install("--target", "droid", "--print")
        claude = self.run_install("--target", "claude", "--print")
        codex = self.run_install("--target", "codex", "--print")

        self.assertEqual(droid.returncode, 0, droid.stdout + droid.stderr)
        self.assertEqual(claude.returncode, 0, claude.stdout + claude.stderr)
        self.assertEqual(codex.returncode, 0, codex.stdout + codex.stderr)
        self.assertNotIn("--event session-start", droid.stdout)
        self.assertNotIn("--event session-start", claude.stdout)
        self.assertNotIn("--event session-start", codex.stdout)
        self.assertNotIn('"SessionStart"', droid.stdout)
        self.assertNotIn('"SessionStart"', claude.stdout)
        self.assertNotIn("[[hooks.SessionStart]]", codex.stdout)

    def test_claude_print_preserves_settings_and_uses_claude_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            settings_dir = repo / ".claude"
            settings_dir.mkdir()
            (settings_dir / "settings.json").write_text('{"theme":"dark"}\n', encoding="utf-8")

            result = self.run_install("--target", "claude", "--print", cwd=repo)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["theme"], "dark")
        rendered = json.dumps(payload)
        self.assertIn("Edit|Write|MultiEdit", rendered)
        self.assertIn('"Bash"', rendered)
        self.assertIn("scripts/hooks/context_capsule.py", rendered)
        self.assertNotIn("scripts/hooks/context_state.py", rendered)
        self.assertNotIn("scripts/hook_context_state.py", rendered)

    def test_claude_apply_with_yes_preserves_unmanaged_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            settings_dir = repo / ".claude"
            settings_dir.mkdir()
            (settings_dir / "settings.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "Stop": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "echo keep-me",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_install("--target", "claude", "--apply", "--yes", cwd=repo)
            settings = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rendered = json.dumps(settings)
        self.assertIn("echo keep-me", rendered)
        self.assertIn("scripts/hooks/stop_check.py", rendered)

    def test_codex_print_renders_nested_toml_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            result = self.run_install("--target", "codex", "--print", cwd=repo)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[features]", result.stdout)
        self.assertIn("hooks = true", result.stdout)
        self.assertNotIn("[[hooks.SessionStart]]", result.stdout)
        self.assertNotIn("[[hooks.SessionStart.hooks]]", result.stdout)
        self.assertNotIn("scripts/hooks/context_state.py", result.stdout)
        self.assertIn("scripts/hooks/command_guard.py", result.stdout)

    def test_codex_apply_with_yes_merges_config_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            codex_dir = repo / ".codex"
            codex_dir.mkdir()
            (codex_dir / "config.toml").write_text(
                '[features]\nexperimental = true\n\n[profiles.default]\nmodel = "test"\n',
                encoding="utf-8",
            )

            result = self.run_install("--target", "codex", "--apply", "--yes", cwd=repo)
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("experimental = true", config)
        self.assertIn("hooks = true", config)
        self.assertIn('[profiles.default]\nmodel = "test"', config)
        self.assertIn("# dotfiles hooks: begin", config)
        self.assertIn("[[hooks.UserPromptSubmit.hooks]]", config)

    def test_cross_target_apply_requires_yes_confirmation(self) -> None:
        claude = self.run_install("--target", "claude", "--apply")
        codex = self.run_install("--target", "codex", "--apply")

        self.assertEqual(claude.returncode, 1, claude.stdout + claude.stderr)
        self.assertIn("--yes", claude.stdout)
        self.assertEqual(codex.returncode, 1, codex.stdout + codex.stderr)
        self.assertIn("--yes", codex.stdout)


if __name__ == "__main__":
    unittest.main()

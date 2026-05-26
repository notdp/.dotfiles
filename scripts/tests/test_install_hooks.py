import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "install_hooks.py"


def _make_fake_tmux_for_notify(bindir: Path, window_title: str) -> None:
    bindir.mkdir(parents=True, exist_ok=True)
    tmux = bindir / "tmux"
    tmux.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"display-message\" ]; then\n"
        "  case \"$5\" in\n"
        f"    '#W') printf '{window_title}\\n' ;;\n"
        "    *) printf '\\n' ;;\n"
        "  esac\n"
        "fi\n",
        encoding="utf-8",
    )
    os.chmod(tmux, 0o755)


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

    def test_hook_commands_use_dotfiles_runtime_outside_target_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            target_hook_path = repo / "scripts" / "hooks" / "context_capsule.py"
            runtime_hook_path = REPO_ROOT / "scripts" / "hooks" / "context_capsule.py"

            droid = self.run_install("--target", "droid", "--print", cwd=repo)
            claude = self.run_install("--target", "claude", "--print", cwd=repo)
            codex = self.run_install("--target", "codex", "--print", cwd=repo)

        self.assertEqual(droid.returncode, 0, droid.stdout + droid.stderr)
        self.assertEqual(claude.returncode, 0, claude.stdout + claude.stderr)
        self.assertEqual(codex.returncode, 0, codex.stdout + codex.stderr)
        combined = droid.stdout + claude.stdout + codex.stdout
        self.assertIn(str(runtime_hook_path), combined)
        self.assertNotIn(str(target_hook_path), combined)

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

    def test_opencode_print_preserves_config_and_adds_dotfiles_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_dir = repo / ".config" / "opencode"
            config_dir.mkdir(parents=True)
            (config_dir / "opencode.json").write_text(
                json.dumps(
                    {
                        "$schema": "https://opencode.ai/config.json",
                        "mcp": {"keep": {"type": "local", "command": ["keep"]}},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_install(
                "--target",
                "opencode",
                "--print",
                "--config-dir",
                str(config_dir),
                cwd=repo,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        rendered = json.dumps(payload)
        self.assertEqual(payload["mcp"]["keep"]["command"], ["keep"])
        self.assertEqual(payload["provider"]["cliproxy"]["options"]["baseURL"], "http://localhost:8317/v1")
        self.assertEqual(payload["provider"]["cliproxy"]["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(payload["model"], "cliproxy/gpt-5.5-fast")
        self.assertEqual(payload["compaction"]["reserved"], 20000)
        self.assertEqual(payload["compaction"]["preserve_recent_tokens"], 20000)
        self.assertEqual(payload["compaction"]["threshold_percent"], 60)
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["gpt-5.5-fast"]["id"], "gpt-5.5")
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["gpt-5.5-fast"]["limit"]["context"], 1000000)
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["gpt-5.5-fast"]["limit"]["input"], 1000000)
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["claude-opus-4-7"]["limit"]["context"], 1000000)
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["claude-opus-4-7"]["limit"]["input"], 1000000)
        self.assertIn(str(REPO_ROOT / "agents" / "AGENTS.md"), payload["instructions"])
        self.assertIn(str(REPO_ROOT / "skills"), payload["skills"]["paths"])
        self.assertIn("scripts/opencode/dotfiles_hooks.mjs", rendered)

    def test_droid_models_print_updates_supported_compaction_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            settings_path = repo / ".factory" / "settings.json"
            settings_path.parent.mkdir()
            settings_path.write_text(
                json.dumps(
                    {
                        "compactionTokenLimit": 300000,
                        "compactionTokenLimitPerModel": {"existing": 111111},
                        "customModels": [
                            {"id": "custom:gpt", "model": "gpt-5.5"},
                            {"id": "custom:claude", "model": "claude-opus-4-7"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_install(
                "--target",
                "droid-models",
                "--print",
                "--settings-path",
                str(settings_path),
                cwd=repo,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["compactionTokenLimit"], 600000)
        self.assertEqual(payload["compactionTokenLimitPerModel"]["existing"], 111111)
        self.assertEqual(payload["compactionTokenLimitPerModel"]["custom:gpt"], 600000)
        self.assertEqual(payload["compactionTokenLimitPerModel"]["custom:claude"], 600000)
        self.assertNotIn("contextWindow", json.dumps(payload))

    def test_kilo_print_preserves_config_and_adds_dotfiles_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_dir = repo / ".config" / "kilo"
            config_dir.mkdir(parents=True)
            (config_dir / "kilo.json").write_text(
                json.dumps(
                    {
                        "$schema": "https://app.kilo.ai/config.json",
                        "mcp": {"keep": {"type": "local", "command": ["keep"]}},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_install(
                "--target",
                "kilo",
                "--print",
                "--config-dir",
                str(config_dir),
                cwd=repo,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        rendered = json.dumps(payload)
        dotfiles_glob = f"{REPO_ROOT}/*"
        paw_images_glob = "/Users/zhenninglang/.config/paw/images/**"
        self.assertEqual(payload["mcp"]["keep"]["command"], ["keep"])
        self.assertEqual(payload["$schema"], "https://app.kilo.ai/config.json")
        self.assertEqual(payload["provider"]["cliproxy"]["options"]["baseURL"], "http://localhost:8317/v1")
        self.assertEqual(payload["provider"]["cliproxy"]["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(payload["model"], "cliproxy/gpt-5.5-fast")
        self.assertEqual(payload["compaction"]["threshold_percent"], 60)
        self.assertTrue(payload["provider"]["cliproxy"]["models"]["gpt-5.5-fast"]["attachment"])
        self.assertEqual(
            payload["provider"]["cliproxy"]["models"]["gpt-5.5-fast"]["modalities"]["input"],
            ["text", "image"],
        )
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["gpt-5.5-fast"]["limit"]["context"], 1000000)
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["gpt-5.5-fast"]["limit"]["input"], 1000000)
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["claude-opus-4-7"]["limit"]["context"], 1000000)
        self.assertEqual(payload["provider"]["cliproxy"]["models"]["claude-opus-4-7"]["limit"]["input"], 1000000)
        self.assertIn(str(REPO_ROOT / "agents" / "AGENTS.md"), payload["instructions"])
        self.assertIn(str(REPO_ROOT / "skills"), payload["skills"]["paths"])
        self.assertIn("scripts/kilo/dotfiles_hooks.mjs", rendered)
        self.assertEqual(payload["permission"]["read"][dotfiles_glob], "allow")
        self.assertEqual(payload["permission"]["external_directory"][dotfiles_glob], "allow")
        self.assertEqual(payload["permission"]["external_directory"][paw_images_glob], "allow")
        self.assertEqual(payload["permission"]["external_directory"]["/Users/zhenninglang/Downloads/**"], "allow")
        self.assertEqual(payload["permission"]["external_directory"]["/Users/zhenninglang/Projects/**"], "allow")

    def test_kilo_apply_writes_package_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_dir = repo / ".config" / "kilo"

            result = self.run_install(
                "--target",
                "kilo",
                "--apply",
                "--yes",
                "--config-dir",
                str(config_dir),
                cwd=repo,
            )
            config = json.loads((config_dir / "kilo.json").read_text(encoding="utf-8"))
            package = json.loads((config_dir / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(config["model"], "cliproxy/gpt-5.5-fast")
        self.assertIn("@kilocode/plugin", package["dependencies"])
        self.assertIn("@ai-sdk/openai-compatible", package["dependencies"])

    def test_kilo_plugin_guards_tool_execute_before_shell_command(self) -> None:
        plugin_path = REPO_ROOT / "scripts" / "kilo" / "dotfiles_hooks.mjs"
        script = f"""
            import {{ pathToFileURL }} from "node:url";
            const plugin = await import(pathToFileURL({json.dumps(str(plugin_path))}));
            const hooks = await plugin.default.server({{ directory: {json.dumps(str(REPO_ROOT))} }});
            const output = {{ args: {{ command: "rm -rf /" }} }};
            let denied = false;
            try {{
              await hooks["tool.execute.before"]({{ tool: "bash", sessionID: "s", callID: "c" }}, output);
            }} catch (error) {{
              denied = String(error.message).includes("wide destructive cleanup");
            }}
            console.log(JSON.stringify({{
              id: plugin.default.id,
              hasServer: typeof plugin.default.server === "function",
              denied
            }}));
        """

        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["id"], "dotfiles-hooks")
        self.assertTrue(payload["hasServer"])
        self.assertTrue(payload["denied"])

    def test_kilo_plugin_guards_permission_ask_shell_command(self) -> None:
        plugin_path = REPO_ROOT / "scripts" / "kilo" / "dotfiles_hooks.mjs"
        script = f"""
            import {{ pathToFileURL }} from "node:url";
            const plugin = await import(pathToFileURL({json.dumps(str(plugin_path))}));
            const hooks = await plugin.default.server({{ directory: {json.dumps(str(REPO_ROOT))} }});
            const output = {{ status: "ask" }};
            await hooks["permission.ask"]({{
              id: "p",
              type: "bash",
              pattern: "rm -rf /",
              sessionID: "s",
              messageID: "m",
              title: "Run rm -rf /",
              metadata: {{ command: "rm -rf /" }},
              time: {{ created: 0 }}
            }}, output);
            console.log(JSON.stringify(output));
        """

        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "deny")

    def test_opencode_plugin_warns_on_idle_with_unvalidated_code_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            notify_log = repo / "notify.log"
            fake_bin = repo / "bin"
            _make_fake_tmux_for_notify(fake_bin, "opencode-test")
            subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
            (repo / "changed.py").write_text("print('changed')\n", encoding="utf-8")
            plugin_path = REPO_ROOT / "scripts" / "opencode" / "dotfiles_hooks.mjs"
            script = f"""
                import {{ pathToFileURL }} from "node:url";
                process.env.DOTFILES_OPENCODE_NOTIFY_LOG = {json.dumps(str(notify_log))};
                process.env.NOTIFY_TMUX_TITLE_DRY_RUN = "1";
                process.env.NOTIFY_TMUX_TITLE_DEDUPE_DIR = {json.dumps(str(repo / "dedupe"))};
                process.env.NOTIFY_TMUX_TITLE_PANE_NAMES = "海獭";
                process.env.PATH = {json.dumps(str(fake_bin))} + ":" + process.env.PATH;
                process.env.TMUX_PANE = "%1";
                const plugin = await import(pathToFileURL({json.dumps(str(plugin_path))}));
                const toasts = [];
                const hooks = await plugin.default({{
                  client: {{ tui: {{ showToast: async (payload) => toasts.push(payload) }} }},
                  directory: {json.dumps(str(repo))}
                }});
                if (hooks.event) {{
                  await hooks.event({{ event: {{ type: "session.idle", properties: {{ sessionID: "test-session" }} }} }});
                }}
                console.log(JSON.stringify({{ hasEventHook: Boolean(hooks.event), toasts }}));
            """

            result = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            notifications = [json.loads(line) for line in notify_log.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["hasEventHook"])
        self.assertEqual(len(payload["toasts"]), 1)
        self.assertEqual(payload["toasts"][0]["body"]["variant"], "warning")
        self.assertIn("Stop check advisory", payload["toasts"][0]["body"]["message"])
        self.assertEqual(notifications[0]["variant"], "warning")
        self.assertEqual(notifications[0]["event"], "notification")
        self.assertEqual(notifications[0]["stdout"].splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])

    def test_opencode_plugin_notifies_on_clean_idle_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            notify_log = repo / "notify.log"
            fake_bin = repo / "bin"
            _make_fake_tmux_for_notify(fake_bin, "opencode-test")
            subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
            plugin_path = REPO_ROOT / "scripts" / "opencode" / "dotfiles_hooks.mjs"
            script = f"""
                import {{ pathToFileURL }} from "node:url";
                process.env.DOTFILES_OPENCODE_NOTIFY_LOG = {json.dumps(str(notify_log))};
                process.env.NOTIFY_TMUX_TITLE_DRY_RUN = "1";
                process.env.NOTIFY_TMUX_TITLE_DEDUPE_DIR = {json.dumps(str(repo / "dedupe"))};
                process.env.NOTIFY_TMUX_TITLE_PANE_NAMES = "海獭";
                process.env.PATH = {json.dumps(str(fake_bin))} + ":" + process.env.PATH;
                process.env.TMUX_PANE = "%1";
                const plugin = await import(pathToFileURL({json.dumps(str(plugin_path))}));
                const toasts = [];
                const hooks = await plugin.default({{
                  client: {{ tui: {{ showToast: async (payload) => toasts.push(payload) }} }},
                  directory: {json.dumps(str(repo))}
                }});
                await hooks.event({{ event: {{ type: "session.idle", properties: {{ sessionID: "clean-session" }} }} }});
                console.log(JSON.stringify({{ toasts }}));
            """

            result = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            notifications = [json.loads(line) for line in notify_log.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["toasts"][0]["body"]["variant"], "success")
        self.assertIn("complete", payload["toasts"][0]["body"]["message"])
        self.assertEqual(notifications[0]["variant"], "success")
        self.assertEqual(notifications[0]["event"], "stop")
        self.assertEqual(notifications[0]["stdout"].splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])

    def test_opencode_plugin_notifies_when_text_completion_hook_fires(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            notify_log = repo / "notify.log"
            fake_bin = repo / "bin"
            _make_fake_tmux_for_notify(fake_bin, "opencode-test")
            subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
            plugin_path = REPO_ROOT / "scripts" / "opencode" / "dotfiles_hooks.mjs"
            script = f"""
                import {{ pathToFileURL }} from "node:url";
                process.env.DOTFILES_OPENCODE_NOTIFY_LOG = {json.dumps(str(notify_log))};
                process.env.NOTIFY_TMUX_TITLE_DRY_RUN = "1";
                process.env.NOTIFY_TMUX_TITLE_DEDUPE_DIR = {json.dumps(str(repo / "dedupe"))};
                process.env.NOTIFY_TMUX_TITLE_PANE_NAMES = "海獭";
                process.env.PATH = {json.dumps(str(fake_bin))} + ":" + process.env.PATH;
                process.env.TMUX_PANE = "%1";
                const plugin = await import(pathToFileURL({json.dumps(str(plugin_path))}));
                const toasts = [];
                const hooks = await plugin.default({{
                  client: {{ tui: {{ showToast: async (payload) => toasts.push(payload) }} }},
                  directory: {json.dumps(str(repo))}
                }});
                if (hooks["experimental.text.complete"]) {{
                  await hooks["experimental.text.complete"]({{
                    sessionID: "text-session",
                    messageID: "message-1",
                    partID: "part-1"
                  }}, {{ text: "done" }});
                }}
                console.log(JSON.stringify({{ hasHook: Boolean(hooks["experimental.text.complete"]), toasts }}));
            """

            result = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            notifications = [json.loads(line) for line in notify_log.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["hasHook"])
        self.assertEqual(payload["toasts"][0]["body"]["variant"], "success")
        self.assertEqual(notifications[0]["stdout"].splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])

    def test_aider_print_renders_model_config_without_loading_all_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            config_path = repo / ".aider.conf.yml"
            config_path.write_text("dark-mode: true\n", encoding="utf-8")

            result = self.run_install(
                "--target",
                "aider",
                "--print",
                "--config-path",
                str(config_path),
                cwd=repo,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("model: gpt-5.5", result.stdout)
        self.assertIn("reasoning-effort: low", result.stdout)
        self.assertIn("check-model-accepts-settings: false", result.stdout)
        self.assertIn("openai-api-base: http://localhost:8317/v1", result.stdout)
        self.assertIn("openai-api-key:", result.stdout)
        self.assertIn(f"- {REPO_ROOT / 'agents' / 'AGENTS.md'}", result.stdout)
        self.assertNotIn(f"{REPO_ROOT / 'skills'}", result.stdout)

    def test_user_config_apply_requires_yes_confirmation(self) -> None:
        opencode = self.run_install("--target", "opencode", "--apply")
        aider = self.run_install("--target", "aider", "--apply")
        kilo = self.run_install("--target", "kilo", "--apply")
        droid_models = self.run_install("--target", "droid-models", "--apply")

        self.assertEqual(opencode.returncode, 1, opencode.stdout + opencode.stderr)
        self.assertIn("--yes", opencode.stdout)
        self.assertEqual(aider.returncode, 1, aider.stdout + aider.stderr)
        self.assertIn("--yes", aider.stdout)
        self.assertEqual(kilo.returncode, 1, kilo.stdout + kilo.stderr)
        self.assertIn("--yes", kilo.stdout)
        self.assertEqual(droid_models.returncode, 1, droid_models.stdout + droid_models.stderr)
        self.assertIn("--yes", droid_models.stdout)

    def test_cross_target_apply_requires_yes_confirmation(self) -> None:
        claude = self.run_install("--target", "claude", "--apply")
        codex = self.run_install("--target", "codex", "--apply")

        self.assertEqual(claude.returncode, 1, claude.stdout + claude.stderr)
        self.assertIn("--yes", claude.stdout)
        self.assertEqual(codex.returncode, 1, codex.stdout + codex.stderr)
        self.assertIn("--yes", codex.stdout)


if __name__ == "__main__":
    unittest.main()

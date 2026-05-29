import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "boundary_gate.py"
WRAPPER_SCRIPT = REPO_ROOT / "scripts" / "hook_boundary_gate.py"


class HookBoundaryGateTests(unittest.TestCase):
    def run_gate(
        self,
        repo: Path,
        transcript: Path,
        tool_name: str = "Edit",
        mode: str = "advisory",
        script: Path = SCRIPT,
        tool_input: dict | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo), "BOUNDARY_GATE_MODE": mode}
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "transcript_path": str(transcript),
            "tool_input": tool_input or {},
        }
        return subprocess.run(
            ["python3", str(script)],
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
                {
                    "type": "assistant",
                    "message": {
                        "content": (
                            "Boundary facts:\n"
                            "- Risk types: shared-path\n"
                            "- Callers: creator search\n"
                            "- Contract cases: keep accept/reject behavior\n"
                        )
                    },
                },
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_prompt_specific_facts_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "改 response_model"}},
                {"type": "assistant", "message": {"content": "Boundary facts:\n- Callers: api"}},
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertIn("Schema contract", payload["systemMessage"])

    def test_boundary_decisions_stub_does_not_satisfy_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "帮我封装这个服务"}},
                {"type": "assistant", "message": {"content": "Boundary decisions: ok"}},
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertIn("Callers", payload["systemMessage"])

    def test_boundary_facts_stub_does_not_satisfy_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "帮我改 hook prompt"}},
                {"type": "assistant", "message": {"content": "Boundary facts: ok"}},
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertIn("Risk types", payload["systemMessage"])

    def test_warns_when_transcript_window_has_no_recent_user_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            transcript.write_text(
                json.dumps({"type": "user", "message": {"content": "帮我封装这个服务"}})
                + "\n"
                + json.dumps({"type": "assistant", "message": {"content": "x" * 90000}})
                + "\n",
                encoding="utf-8",
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertIn("recent user prompt", payload["systemMessage"])

    def test_ignores_old_boundary_facts_before_current_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "上一个任务：改 response_model"}},
                {"type": "assistant", "message": {"content": "Boundary facts:\n- Schema contract: keep envelope"}},
                {"type": "user", "message": {"content": "帮我封装这个服务"}},
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("systemMessage", json.loads(result.stdout))

    def test_assistant_confirmation_request_is_not_boundary_fact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "帮我封装这个服务"}},
                {"type": "assistant", "message": {"content": "需要你确认 caller 后我再改"}},
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("systemMessage", json.loads(result.stdout))

    def test_user_approval_after_prompt_satisfies_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "帮我封装这个服务"}},
                {"type": "assistant", "message": {"content": "需要确认是否允许按当前 callers 改"}},
                {"type": "user", "message": {"content": "用户批准：按当前 callers 改"}},
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

    def test_ignores_schema_words_inside_frontend_code_fence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {
                    "type": "user",
                    "message": {
                        "content": (
                            "修 React 保存逻辑：\n\n"
                            "```tsx\n"
                            "const response = await fetch('/api/save')\n"
                            "const request = { defaultValue: true }\n"
                            "```\n"
                        )
                    },
                },
            )

            result = self.run_gate(repo, transcript)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_hook_word_does_not_gate_non_context_surface_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(
                transcript,
                {"type": "user", "message": {"content": "Hook 误报，前端 HTTP 调用不是长任务。修第二条前先看 doSave 完整逻辑。"}},
            )

            result = self.run_gate(
                repo,
                transcript,
                tool_input={"file_path": "ordo-fe/src/components/campaign/commit/CommitSettingsPanel.tsx"},
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_stays_quiet_for_prod_substring_false_positives(self) -> None:
        for prompt in ("帮我 reproduce 这个登录 bug", "整理一下 product backlog 优先级", "提升团队生产效率"):
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                transcript = repo / "session.jsonl"
                self.write_transcript(transcript, {"type": "user", "message": {"content": prompt}})
                result = self.run_gate(repo, transcript)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"], f"unexpected gate for: {prompt}")

    def test_still_gates_real_production_side_effect(self) -> None:
        for prompt in ("改一下 prod 环境配置", "部署到生产环境前确认"):
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                transcript = repo / "session.jsonl"
                self.write_transcript(transcript, {"type": "user", "message": {"content": prompt}})
                result = self.run_gate(repo, transcript)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("systemMessage", payload, f"expected gate for: {prompt}")
            self.assertIn("User approval", payload["systemMessage"])

    def test_stays_quiet_for_shared_path_word_false_positives(self) -> None:
        for prompt in ("写个集成测试覆盖登录流程", "wrap up 当前工作做个收尾"):
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                transcript = repo / "session.jsonl"
                self.write_transcript(transcript, {"type": "user", "message": {"content": prompt}})
                result = self.run_gate(repo, transcript)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["suppressOutput"], f"unexpected gate for: {prompt}")

    def test_recommends_gitops_for_outside_repo_agent_config_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(transcript, {"type": "user", "message": {"content": "顺手改一下 kilo 配置"}})

            result = self.run_gate(
                repo,
                transcript,
                tool_input={"file_path": "/home/user/.config/kilo/settings.json"},
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertIn("guard-gitops", payload["systemMessage"])

    def test_no_gitops_advisory_for_in_repo_config_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(transcript, {"type": "user", "message": {"content": "改一下仓库里的配置模板"}})

            result = self.run_gate(
                repo,
                transcript,
                tool_input={"file_path": str(repo / ".claude" / "settings.json")},
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_legacy_wrapper_delegates_to_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            transcript = repo / "session.jsonl"
            self.write_transcript(transcript, {"type": "user", "message": {"content": "thanks"}})

            result = self.run_gate(repo, transcript, script=WRAPPER_SCRIPT)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])


if __name__ == "__main__":
    unittest.main()

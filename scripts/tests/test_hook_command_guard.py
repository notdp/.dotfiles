import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hook_command_guard.py"


class HookCommandGuardTests(unittest.TestCase):
    def run_guard(self, command: str, *, tool_name: str = "Bash") -> subprocess.CompletedProcess[str]:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command},
        }
        return subprocess.run(
            ["python3", str(SCRIPT)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )

    def test_blocks_git_push_with_gitops_reason(self) -> None:
        result = self.run_guard("git push origin main")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        output = payload["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("guard-gitops", output["permissionDecisionReason"])

    def test_allows_read_only_git_status(self) -> None:
        result = self.run_guard("git status --short")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["suppressOutput"])
        self.assertNotIn("hookSpecificOutput", payload)

    def test_allows_dangerous_words_inside_printf_payload(self) -> None:
        result = self.run_guard("printf '{\"command\":\"git push origin main\"}' | python3 scripts/hook_command_guard.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["suppressOutput"])

    def test_blocks_remote_write_commands(self) -> None:
        result = self.run_guard("ssh root@example.com 'systemctl restart app'")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("remote", payload["hookSpecificOutput"]["permissionDecisionReason"])

    def test_blocks_database_write_commands(self) -> None:
        result = self.run_guard("psql prod -c \"delete from users\"")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("database", payload["hookSpecificOutput"]["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "command_guard.py"
WRAPPER_SCRIPT = REPO_ROOT / "scripts" / "hook_command_guard.py"


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

    def run_wrapper_guard(self, command: str, *, tool_name: str = "Bash") -> subprocess.CompletedProcess[str]:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command},
        }
        return subprocess.run(
            ["python3", str(WRAPPER_SCRIPT)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )

    def assert_suppressed(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["suppressOutput"])
        self.assertNotIn("hookSpecificOutput", payload)

    def assert_denied(self, result: subprocess.CompletedProcess[str], reason_part: str) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn(reason_part, payload["hookSpecificOutput"]["permissionDecisionReason"])

    def assert_warned(self, result: subprocess.CompletedProcess[str], reason_part: str) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertIn(reason_part, payload["systemMessage"])
        self.assertNotIn("hookSpecificOutput", payload)

    def test_warns_for_git_push_with_gitops_reason(self) -> None:
        result = self.run_guard("git push origin main")

        self.assert_warned(result, "guard-gitops")

    def test_allows_read_only_git_status(self) -> None:
        result = self.run_guard("git status --short")

        self.assert_suppressed(result)

    def test_allows_dangerous_words_inside_printf_payload(self) -> None:
        result = self.run_guard("printf '{\"command\":\"git push origin main\"}' | python3 scripts/hooks/command_guard.py")

        self.assert_suppressed(result)

    def test_legacy_wrapper_delegates_to_runtime(self) -> None:
        result = self.run_wrapper_guard("git status --short")

        self.assert_suppressed(result)

    def test_allows_read_only_remote_diagnostics(self) -> None:
        result = self.run_guard(
            "ssh ordo-prod 'uptime; echo ===PROC===; ps -eo pid,pcpu,pmem,etime,cmd --sort=-pcpu | "
            "grep -E \"ordo-(atlas|agent)\" | grep -v grep; echo ===PORT===; ss -ltnp | grep 8082; "
            "echo ===HEALTH===; curl -m 3 -s -o /dev/null -w \"atlas_root=%{http_code}\" "
            "http://localhost:8082/; echo ===LOG===; tail -n 80 /var/log/supervisor/ordo-atlas.log "
            "2>/dev/null || supervisorctl tail ordo-atlas 2>/dev/null | tail -80'"
        )

        self.assert_suppressed(result)

    def test_allows_read_only_file_fetches_from_remote(self) -> None:
        self.assert_suppressed(self.run_guard("scp host:/var/log/app.log /tmp/app.log"))
        self.assert_suppressed(self.run_guard("rsync --dry-run host:/srv/app/ ./app/"))
        self.assert_suppressed(self.run_guard("rsync --list-only host:/srv/app/"))

    def test_allows_read_only_previews_and_status_commands(self) -> None:
        self.assert_suppressed(self.run_guard("git clean -n"))
        self.assert_suppressed(self.run_guard("git clean --dry-run"))
        self.assert_suppressed(self.run_guard("kubectl rollout status deployment/app"))
        self.assert_suppressed(self.run_guard("psql prod -c \"SET statement_timeout='5s'; SELECT count(*) FROM users\""))

    def test_warns_for_intended_side_effect_commands(self) -> None:
        self.assert_warned(self.run_guard("ssh root@example.com 'systemctl restart app'"), "remote")
        self.assert_warned(self.run_guard("scp local.txt host:/tmp/local.txt"), "remote")
        self.assert_warned(self.run_guard("rsync -av ./ host:/srv/app/"), "remote")
        self.assert_warned(self.run_guard("kubectl apply -f deploy.yaml"), "cluster")
        self.assert_warned(self.run_guard("kubectl rollout restart deployment/app"), "cluster")
        self.assert_warned(self.run_guard("helm upgrade app chart/"), "helm")
        self.assert_warned(self.run_guard("terraform apply"), "terraform")
        self.assert_warned(self.run_guard("psql prod -c \"update users set active=false where id=1\""), "database")

    def test_denies_catastrophic_commands(self) -> None:
        self.assert_denied(self.run_guard("git push --force origin main"), "force")
        self.assert_denied(self.run_guard("git clean -fdx"), "cleanup")
        self.assert_denied(self.run_guard("ssh root@example.com 'rm -rf /tmp/app'"), "remote")
        self.assert_denied(self.run_guard("ssh root@example.com"), "remote")
        self.assert_denied(self.run_guard("rm -rf /"), "cleanup")
        self.assert_denied(self.run_guard("rm -rf ~"), "cleanup")
        self.assert_denied(self.run_guard("terraform destroy"), "terraform")
        self.assert_denied(self.run_guard("kubectl delete namespace prod"), "cluster")
        self.assert_denied(self.run_guard("psql prod -c \"drop table users\""), "database")

    def test_warns_for_scoped_database_write_commands(self) -> None:
        result = self.run_guard("psql prod -c \"delete from users\"")

        self.assert_warned(result, "database")


if __name__ == "__main__":
    unittest.main()

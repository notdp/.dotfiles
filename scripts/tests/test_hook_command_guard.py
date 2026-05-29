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

    def assert_warned_with_approval_request(self, result: subprocess.CompletedProcess[str], reason_part: str) -> None:
        self.assert_warned(result, reason_part)
        message = json.loads(result.stdout)["systemMessage"]
        for field in [
            "ApprovalRequest:",
            "- Action:",
            "- Target:",
            "- External side effect:",
            "- Risk:",
            "- Dry-run / read-only evidence:",
            "- Rollback:",
            "- Validation after apply:",
            "- User approval required:",
        ]:
            self.assertIn(field, message)

    def test_denies_git_push_with_gitops_reason(self) -> None:
        result = self.run_guard("git push origin main")

        self.assert_denied(result, "guard-gitops")

    def test_denies_push_to_master(self) -> None:
        self.assert_denied(self.run_guard("git push origin master"), "guard-gitops")

    def test_denies_push_refspec_targeting_main(self) -> None:
        self.assert_denied(self.run_guard("git push origin HEAD:main"), "guard-gitops")
        self.assert_denied(self.run_guard("git push origin feature:refs/heads/main"), "guard-gitops")

    def test_denies_push_all_and_mirror(self) -> None:
        self.assert_denied(self.run_guard("git push --all origin"), "guard-gitops")
        self.assert_denied(self.run_guard("git push --mirror origin"), "guard-gitops")

    def test_denies_ambiguous_bare_push(self) -> None:
        self.assert_denied(self.run_guard("git push"), "guard-gitops")
        self.assert_denied(self.run_guard("git push origin"), "guard-gitops")
        self.assert_denied(self.run_guard("git push origin HEAD"), "guard-gitops")

    def test_denies_force_push_to_feature_branch(self) -> None:
        self.assert_denied(self.run_guard("git push --force origin feature/x"), "force")
        self.assert_denied(self.run_guard("git push -f origin feature/x"), "force")

    def test_allows_push_to_feature_branch(self) -> None:
        self.assert_suppressed(self.run_guard("git push origin fix/campaign-commit-writeback-fields"))
        self.assert_suppressed(self.run_guard("git push -u origin feature/new-thing"))
        self.assert_suppressed(self.run_guard("git push origin local-main:feature/x"))

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
        self.assert_warned_with_approval_request(self.run_guard("ssh root@example.com 'systemctl restart app'"), "remote")
        self.assert_warned_with_approval_request(self.run_guard("scp local.txt host:/tmp/local.txt"), "remote")
        self.assert_warned_with_approval_request(self.run_guard("rsync -av ./ host:/srv/app/"), "remote")
        self.assert_warned_with_approval_request(self.run_guard("kubectl apply -f deploy.yaml"), "cluster")
        self.assert_warned_with_approval_request(self.run_guard("kubectl rollout restart deployment/app"), "cluster")
        self.assert_warned_with_approval_request(self.run_guard("helm upgrade app chart/"), "helm")
        self.assert_warned_with_approval_request(self.run_guard("terraform apply"), "terraform")
        self.assert_warned_with_approval_request(self.run_guard("psql prod -c \"update users set active=false where id=1\""), "database")

    def test_denies_catastrophic_commands(self) -> None:
        self.assert_denied(self.run_guard("git push --force origin main"), "force")
        self.assert_denied(self.run_guard("git clean -fdx"), "cleanup")
        self.assert_denied(self.run_guard("ssh root@example.com 'rm -rf /tmp/app'"), "remote")
        self.assert_denied(self.run_guard("ssh root@example.com"), "remote")
        self.assert_denied(self.run_guard("rm -rf /"), "cleanup")
        self.assert_denied(self.run_guard("rm -rf ~"), "cleanup")
        self.assert_denied(self.run_guard("rm -rf /etc"), "cleanup")
        self.assert_denied(self.run_guard("rm -rf ~/.ssh"), "cleanup")
        self.assert_denied(self.run_guard("terraform destroy"), "terraform")
        self.assert_denied(self.run_guard("kubectl delete namespace prod"), "cluster")
        self.assert_denied(self.run_guard("psql prod -c \"drop table users\""), "database")
        self.assert_denied(self.run_guard("python3 -c \"import os; os.system('rm -rf /etc')\""), "cleanup")
        self.assert_denied(self.run_guard("eval 'rm -rf /tmp'"), "cleanup")
        self.assert_denied(self.run_guard("find /tmp -exec rm -rf {} +"), "cleanup")
        self.assert_denied(self.run_guard("git reset --hard origin/main"), "reset")
        self.assert_denied(self.run_guard("aws s3 rm s3://bucket/path --recursive"), "cloud")
        self.assert_denied(self.run_guard("gh repo delete owner/repo"), "repository")
        self.assert_denied(self.run_guard("xargs rm -rf /etc"), "cleanup")
        self.assert_denied(self.run_guard("/usr/bin/env rm -rf /etc"), "cleanup")
        self.assert_denied(self.run_guard("$(echo rm) -rf /etc"), "cleanup")
        self.assert_denied(self.run_guard("`echo rm` -rf /etc"), "cleanup")

    def test_warns_for_scoped_database_write_commands(self) -> None:
        result = self.run_guard("psql prod -c \"delete from users\"")

        self.assert_warned(result, "database")

    def test_warns_keep_charging_aliyun_ecs_stop_instance_billing_risk(self) -> None:
        result = self.run_guard("aliyun ecs StopInstance --InstanceId i-xxx --StoppedMode KeepCharging")

        self.assert_warned(result, "KeepCharging")
        self.assertIn("billing", json.loads(result.stdout)["systemMessage"])

    def test_warns_stop_charging_aliyun_ecs_stop_instance_resource_risk(self) -> None:
        result = self.run_guard("aliyun ecs StopInstance --InstanceId i-xxx --StoppedMode StopCharging")

        self.assert_warned_with_approval_request(result, "StopCharging")
        message = json.loads(result.stdout)["systemMessage"]
        self.assertIn("rollback", message)
        self.assertIn("validation", message)

    def test_warns_aliyun_ecs_stop_instance_without_stopped_mode(self) -> None:
        result = self.run_guard("aliyun ecs StopInstance --InstanceId i-xxx")

        self.assert_warned(result, "StoppedMode")

    def test_allows_read_only_aliyun_ecs_describe_instances(self) -> None:
        result = self.run_guard("aliyun ecs DescribeInstances --InstanceIds '[\"i-xxx\"]'")

        self.assert_suppressed(result)

    def test_warns_for_generic_aliyun_write_command(self) -> None:
        result = self.run_guard("aliyun rds ModifyDBInstanceSpec --DBInstanceId rm-xxx --DBInstanceClass mysql.n2.small.1")

        self.assert_warned_with_approval_request(result, "aliyun CLI command can change cloud resource state")

    def test_denies_destructive_aliyun_delete_or_release_commands(self) -> None:
        self.assert_denied(self.run_guard("aliyun ecs ReleaseInstance --InstanceId i-xxx"), "aliyun destructive")
        self.assert_denied(self.run_guard("aliyun rds DeleteDBInstance --DBInstanceId rm-xxx"), "aliyun destructive")

    def test_denies_destructive_command_inside_command_substitution(self) -> None:
        self.assert_denied(self.run_guard("echo $(git push origin main)"), "guard-gitops")
        self.assert_denied(self.run_guard("RESULT=$(git push origin main)"), "guard-gitops")

    def test_denies_destructive_command_inside_backtick_substitution(self) -> None:
        self.assert_denied(self.run_guard("echo `git push origin main`"), "guard-gitops")

    def test_denies_wide_cleanup_inside_nested_command_substitution(self) -> None:
        self.assert_denied(self.run_guard("echo $(printf %s $(rm -rf /))"), "destructive")

    def test_allows_read_only_command_substitution(self) -> None:
        self.assert_suppressed(self.run_guard("echo $(git status --short)"))
        self.assert_suppressed(self.run_guard("DIR=$(pwd)"))

    def test_warns_for_remote_and_database_file_writes(self) -> None:
        self.assert_warned(self.run_guard("ssh host 'sed -i s/a/b/ /etc/app.conf'"), "remote")
        self.assert_warned(self.run_guard("ssh host 'echo foo > /etc/app.conf'"), "remote")
        self.assert_warned(self.run_guard("ssh host 'cat << EOF > /etc/app.conf\nfoo\nEOF'"), "remote")
        self.assert_warned(self.run_guard("psql prod -f destructive.sql"), "database")
        self.assert_warned(self.run_guard("mysql prod < patch.sql"), "database")
        self.assert_warned(self.run_guard("mysql prod --file=patch.sql"), "database")
        self.assert_warned(self.run_guard("cat patch.sql | psql prod"), "database")
        self.assert_warned(self.run_guard("docker rm -f app"), "container")


if __name__ == "__main__":
    unittest.main()

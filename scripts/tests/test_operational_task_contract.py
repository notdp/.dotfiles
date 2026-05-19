import json
import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_SCRIPT = REPO_ROOT / "scripts" / "scan_operational_task_contract.py"


class OperationalTaskContractTests(unittest.TestCase):
    def run_scan(self, diff: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCAN_SCRIPT), "--stdin", *args],
            input=diff,
            text=True,
            capture_output=True,
        )

    def test_reports_missing_contract_for_operational_cli(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/audience_sync.py b/scripts/audience_sync.py
            --- /dev/null
            +++ b/scripts/audience_sync.py
            @@ -0,0 +1,12 @@
            +import argparse
            +
            +def main():
            +    parser = argparse.ArgumentParser()
            +    parser.add_argument("--dry-run", action="store_true")
            +    parser.add_argument("--apply", action="store_true")
            +    parser.add_argument("--batch-size", type=int, default=1000)
            +    parser.add_argument("--concurrency", type=int, default=16)
            +    args = parser.parse_args()
            +    while True:
            +        sync_next_batch(args.batch_size)
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("可观测性", result.stdout)
        self.assertIn("可恢复性", result.stdout)
        self.assertIn("dry-run 数据证据", result.stdout)
        self.assertIn("失败集合", result.stdout)
        self.assertIn("apply 安全确认", result.stdout)

    def test_accepts_operational_cli_with_core_contract(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/audience_sync.py b/scripts/audience_sync.py
            --- /dev/null
            +++ b/scripts/audience_sync.py
            @@ -0,0 +1,25 @@
            +import argparse
            +import asyncio
            +
            +def main():
            +    parser = argparse.ArgumentParser()
            +    parser.add_argument("--dry-run", action="store_true")
            +    parser.add_argument("--apply", action="store_true")
            +    parser.add_argument("--batch-size", type=int, default=1000)
            +    parser.add_argument("--concurrency", type=int, default=16)
            +    parser.add_argument("--state-file", default=".sync-state.json")
            +    parser.add_argument("--resume", action="store_true")
            +    parser.add_argument("--yes", action="store_true")
            +    args = parser.parse_args()
            +    semaphore = asyncio.Semaphore(args.concurrency)
            +    cursor = load_checkpoint(args.state_file)
            +    total = count_planned_rows(cursor)
            +    sample = preview_sample(cursor)
            +    invariant = reconcile_counts(cursor)
            +    print(f"phase=sync progress=0/{total} percent=0 eta=unknown heartbeat=started")
            +    print(f"dry_run count={total} sample={sample} invariant={invariant} diff=preview")
            +    if args.apply and not args.yes:
            +        raise SystemExit("apply requires --yes confirmation")
            +    failed_set = retry_with_backoff(run_batches, semaphore, cursor)
            +    run_batches(semaphore, cursor)
            +    save_checkpoint(args.state_file, cursor)
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_reports_missing_resume_command_for_checkpointed_cli(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/user_backfill.py b/scripts/user_backfill.py
            --- /dev/null
            +++ b/scripts/user_backfill.py
            @@ -0,0 +1,12 @@
            +import argparse
            +parser = argparse.ArgumentParser()
            +parser.add_argument("--dry-run", action="store_true")
            +parser.add_argument("--state-file", default=".state.json")
            +cursor = load_checkpoint(".state.json")
            +total = count_planned_rows(cursor)
            +sample = preview_sample(cursor)
            +print(f"phase=backfill current/total=0/{total} percent=0 eta=unknown")
            +print(f"dry_run count={total} sample={sample} diff=preview invariant=ok")
            +failed_set = retry_with_backoff(run_batches, cursor)
            +save_checkpoint(".state.json", cursor)
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("resume 命令", result.stdout)

    def test_resume_word_in_function_name_does_not_satisfy_resume_command(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/user_backfill.py b/scripts/user_backfill.py
            --- /dev/null
            +++ b/scripts/user_backfill.py
            @@ -0,0 +1,14 @@
            +import argparse
            +parser = argparse.ArgumentParser()
            +parser.add_argument("--dry-run", action="store_true")
            +parser.add_argument("--state-file", default=".state.json")
            +cursor = resume_from_checkpoint(".state.json")
            +total = count_planned_rows(cursor)
            +sample = preview_sample(cursor)
            +print(f"phase=backfill current/total=0/{total} percent=0 eta=unknown")
            +print(f"dry_run count={total} sample={sample} diff=preview invariant=ok")
            +failed_set = retry_with_backoff(run_batches, cursor)
            +save_checkpoint(".state.json", cursor)
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("resume 命令", result.stdout)

    def test_ignores_simple_non_operational_script(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/hello.py b/scripts/hello.py
            --- /dev/null
            +++ b/scripts/hello.py
            @@ -0,0 +1,3 @@
            +def greet(name):
            +    return f"hello {name}"
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_ignores_boundary_scanner_source(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/scan_boundary_decisions.py b/scripts/scan_boundary_decisions.py
            --- /dev/null
            +++ b/scripts/scan_boundary_decisions.py
            @@ -0,0 +1,8 @@
            +import argparse
            +parser = argparse.ArgumentParser()
            +parser.add_argument("--hook", action="store_true")
            +pattern = "retry|backoff|asyncio.sleep|time.sleep"
            +suggestion = "concurrency/worker cue without bound"
            +print("hook output")
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_ignores_hook_runtime_source(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/hooks/context_capsule.py b/scripts/hooks/context_capsule.py
            --- /dev/null
            +++ b/scripts/hooks/context_capsule.py
            @@ -0,0 +1,8 @@
            +import argparse
            +parser = argparse.ArgumentParser()
            +parser.add_argument("--apply", action="store_true")
            +parser.add_argument("--dry-run", action="store_true")
            +while True:
            +    run_hook()
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_ignores_hook_installer_source(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/install_hooks.py b/scripts/install_hooks.py
            --- /dev/null
            +++ b/scripts/install_hooks.py
            @@ -0,0 +1,8 @@
            +import argparse
            +parser = argparse.ArgumentParser()
            +parser.add_argument("--apply", action="store_true")
            +parser.add_argument("--yes", action="store_true")
            +while True:
            +    sync_hooks()
            """
        )

        result = self.run_scan(diff, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_hook_mode_returns_additional_context_without_blocking(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/scripts/backfill_users.py b/scripts/backfill_users.py
            --- /dev/null
            +++ b/scripts/backfill_users.py
            @@ -0,0 +1,7 @@
            +import argparse
            +parser = argparse.ArgumentParser()
            +parser.add_argument("--dry-run", action="store_true")
            +parser.add_argument("--apply", action="store_true")
            +parser.add_argument("--run-until-empty", action="store_true")
            +run_backfill()
            """
        )

        result = self.run_scan(diff, "--hook")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("hookSpecificOutput", payload)
        self.assertIn("dev-operational-task", payload["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_SCRIPT = REPO_ROOT / "scripts" / "scan_fragility_touchpoints.py"


class ScanFragilityTouchpointsTests(unittest.TestCase):
    def run_scan(self, diff: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCAN_SCRIPT), "--stdin"],
            input=diff,
            text=True,
            capture_output=True,
        )

    def run_hook_scan(self, diff: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCAN_SCRIPT), "--stdin", "--hook"],
            input=diff,
            text=True,
            capture_output=True,
        )

    def test_flags_saas_and_http_write_touchpoints(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/feishu.py b/src/feishu.py
            --- /dev/null
            +++ b/src/feishu.py
            @@ -0,0 +1,4 @@
            +def add_row(client, table_id, fields):
            +    return client.post(f"https://open.feishu.cn/bitable/v1/apps/x/tables/{table_id}/records", json=fields)
            +def via_stripe(s, amount):
            +    return stripe.Charge.create(amount=amount)
            """
        )
        result = self.run_scan(diff)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Fragility Touchpoint Scan", result.stdout)
        self.assertIn("src/feishu.py", result.stdout)
        # 命中两条：feishu/client.post 行 + stripe 行
        self.assertIn("命中 2 条", result.stdout)

    def test_pure_local_code_does_not_fire(self) -> None:
        # list.append / dict 操作 / 纯计算不是外部依赖触点，不应误报
        diff = textwrap.dedent(
            """\
            diff --git a/src/util.py b/src/util.py
            --- /dev/null
            +++ b/src/util.py
            @@ -0,0 +1,4 @@
            +def f(xs):
            +    xs.append(1)
            +    items = data.get("items") or []
            +    return sum(xs)
            """
        )
        result = self.run_scan(diff)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_markdown_and_test_files_excluded(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/docs/notes.md b/docs/notes.md
            --- /dev/null
            +++ b/docs/notes.md
            @@ -0,0 +1,1 @@
            +调用 feishu bitable client.post 写入一行
            diff --git a/scripts/tests/test_x.py b/scripts/tests/test_x.py
            --- /dev/null
            +++ b/scripts/tests/test_x.py
            @@ -0,0 +1,1 @@
            +stripe.Charge.create(amount=1)
            """
        )
        result = self.run_scan(diff)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("命中 0 条", result.stdout)

    def test_hook_mode_emits_postooluse_context(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/notion.py b/src/notion.py
            --- /dev/null
            +++ b/src/notion.py
            @@ -0,0 +1,1 @@
            +notion.pages.create(parent=db, properties=props)
            """
        )
        result = self.run_hook_scan(diff)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("fragility-types.md", payload["hookSpecificOutput"]["additionalContext"])

    def test_hook_mode_fail_open_on_empty(self) -> None:
        result = self.run_hook_scan("")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {"suppressOutput": True})


if __name__ == "__main__":
    unittest.main()

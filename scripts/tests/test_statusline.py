import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "statusline.sh"
USAGE_CACHE = Path("/tmp/droid_statusline_usage")
LAST_GOOD_USAGE_CACHE = Path("/tmp/droid_statusline_usage.last_good")
USAGE_FIXTURE = {
    "usage": {
        "standard": {
            "orgTotalTokensUsed": 1500000,
            "totalAllowance": 10000000,
        },
        "endDate": 1893456000000,
    },
    "schedule": [
        {
            "plan": {
                "name": "Factory Pro Plan",
            }
        }
    ],
}
def strip_control_sequences(value: str) -> str:
    value = re.sub(r"\x1b]8;;.*?\x1b\\\\", "", value)
    value = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", value)
    return value


class StatuslineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_usage_cache = USAGE_CACHE.read_text() if USAGE_CACHE.exists() else None
        self._previous_last_good_usage_cache = (
            LAST_GOOD_USAGE_CACHE.read_text() if LAST_GOOD_USAGE_CACHE.exists() else None
        )
        USAGE_CACHE.write_text(json.dumps(USAGE_FIXTURE))

    def tearDown(self) -> None:
        if self._previous_usage_cache is None:
            USAGE_CACHE.unlink(missing_ok=True)
        else:
            USAGE_CACHE.write_text(self._previous_usage_cache)
        if self._previous_last_good_usage_cache is None:
            LAST_GOOD_USAGE_CACHE.unlink(missing_ok=True)
        else:
            LAST_GOOD_USAGE_CACHE.write_text(self._previous_last_good_usage_cache)

    def test_cc_mode_keeps_session_and_usage_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "repo"
            repo_dir.mkdir()
            subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)
            (repo_dir / "README.md").write_text("ok\n")
            subprocess.run(["git", "-C", str(repo_dir), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_dir), "branch", "-M", "main"], check=True)

            pr_cache = Path("/tmp/droid_statusline_pr_repo_main")
            previous_pr_cache = pr_cache.read_text() if pr_cache.exists() else None
            pr_cache.write_text("none\n")
            self.addCleanup(
                lambda: pr_cache.write_text(previous_pr_cache)
                if previous_pr_cache is not None
                else pr_cache.unlink(missing_ok=True)
            )

            payload = {
                "cwd": str(repo_dir),
                "session_id": "12345678-abcd",
                "model": {"display_name": "GPT-5.4"},
                "context_window": {"used_percentage": 12},
            }
            result = subprocess.run(
                ["bash", str(SCRIPT)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
                env={**os.environ, "HOME": tmp},
            )

            output = strip_control_sequences(result.stdout)
            self.assertIn("12345678", output)
            self.assertIn("Pro", output)
            self.assertIn("1.5/10M", output)

    def test_cc_mode_handles_gnu_stat_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "repo"
            repo_dir.mkdir()
            subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)
            (repo_dir / "README.md").write_text("ok\n")
            subprocess.run(["git", "-C", str(repo_dir), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_dir), "branch", "-M", "main"], check=True)

            fakebin_dir = Path(tmp) / "fakebin"
            fakebin_dir.mkdir()
            (fakebin_dir / "stat").write_text(
                """#!/bin/sh
if [ "$1" = "-f" ]; then
  printf '/\\n'
  exit 0
fi
if [ "$1" = "-c" ]; then
  python3 -c 'import os, sys; print(int(os.path.getmtime(sys.argv[1])))' "$3"
  exit 0
fi
exec /usr/bin/stat "$@"
"""
            )
            os.chmod(fakebin_dir / "stat", 0o755)

            pr_cache = Path("/tmp/droid_statusline_pr_repo_main")
            previous_pr_cache = pr_cache.read_text() if pr_cache.exists() else None
            pr_cache.write_text("none\n")
            self.addCleanup(
                lambda: pr_cache.write_text(previous_pr_cache)
                if previous_pr_cache is not None
                else pr_cache.unlink(missing_ok=True)
            )

            payload = {
                "cwd": str(repo_dir),
                "session_id": "12345678-abcd",
                "model": {"display_name": "GPT-5.4"},
                "context_window": {"used_percentage": 12},
            }
            result = subprocess.run(
                ["bash", str(SCRIPT)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
                env={**os.environ, "HOME": tmp, "PATH": f"{fakebin_dir}:{os.environ['PATH']}"},
            )

            output = strip_control_sequences(result.stdout)
            self.assertIn("12345678", output)
            self.assertIn("Pro", output)

    def test_refresh_keeps_last_good_cache_when_api_returns_error_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            factory_dir = Path(tmp) / ".factory"
            factory_dir.mkdir()
            (factory_dir / "auth.encrypted").write_text(json.dumps({"access_token": "dummy-token"}))

            fakebin_dir = Path(tmp) / "fakebin"
            fakebin_dir.mkdir()
            (fakebin_dir / "curl").write_text(
                """#!/bin/sh
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then
    out="$2"
    shift 2
    continue
  fi
  shift
done
printf '%s' '{"error":{"code":"403","message":"Forbidden"}}' > "$out"
"""
            )
            os.chmod(fakebin_dir / "curl", 0o755)

            LAST_GOOD_USAGE_CACHE.unlink(missing_ok=True)
            USAGE_CACHE.write_text(json.dumps(USAGE_FIXTURE))
            stale_time = USAGE_CACHE.stat().st_mtime - 601
            os.utime(USAGE_CACHE, (stale_time, stale_time))

            payload = {
                "cwd": tmp,
                "session_id": "deadbeef-1234",
                "model": {"display_name": "GPT-5.4"},
            }
            subprocess.run(
                ["bash", str(SCRIPT)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
                env={**os.environ, "HOME": tmp, "PATH": f"{fakebin_dir}:{os.environ['PATH']}"},
            )

            subprocess.run(["sleep", "0.2"], check=True)

            self.assertEqual(json.loads(USAGE_CACHE.read_text()), USAGE_FIXTURE)
            self.assertEqual(json.loads(LAST_GOOD_USAGE_CACHE.read_text()), USAGE_FIXTURE)


if __name__ == "__main__":
    unittest.main()

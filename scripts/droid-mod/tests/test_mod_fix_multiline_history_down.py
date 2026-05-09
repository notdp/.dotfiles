import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("/Users/zhenninglang/.dotfiles/scripts/droid-mod/mods/mod_fix_multiline_history_down.py")
STATUS = Path("/Users/zhenninglang/.dotfiles/scripts/droid-mod/status.py")

CURRENT_ORIGINAL = (
    b"if(BH&&hR.downArrow&&lR){let GR=BH.navigateNext();return!0}}"
    b"if(hR.downArrow&&lR&&kH)return kH(),!0;return!1}return!1}"
)
CURRENT_PATCHED = (
    b"if(BH&&hR.downArrow&&lR){let GR=BH.navigateNext();return!0}}"
    b"if(hR.downArrow&&lR&&kH)return      !1;return!1}return!1}"
)


def _write_droid(home: Path, data: bytes) -> Path:
    droid = home / ".local/bin/droid"
    droid.parent.mkdir(parents=True, exist_ok=True)
    droid.write_bytes(data)
    return droid


def _run(script: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class ModFixMultilineHistoryDownTests(unittest.TestCase):
    def test_patches_current_semicolon_form_without_size_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            original = b"prefix" + CURRENT_ORIGINAL + b"suffix"
            droid = _write_droid(home, original)

            result = _run(SCRIPT, home)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            patched = droid.read_bytes()
            self.assertEqual(len(patched), len(original))
            self.assertIn(CURRENT_PATCHED, patched)

    def test_status_detects_current_semicolon_form_as_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            _write_droid(home, CURRENT_PATCHED)

            result = _run(STATUS, home)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("mod-fix-multiline-history-down: 已修改", result.stdout)


if __name__ == "__main__":
    unittest.main()

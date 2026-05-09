import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "notify-tmux-title.sh"


class NotifyTmuxTitleTests(unittest.TestCase):
    def run_hook(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            text=True,
            capture_output=True,
            env={**os.environ, "NOTIFY_TMUX_TITLE_DRY_RUN": "1", **(env or {})},
        )

    def test_says_tmux_window_title_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fakebin = Path(tmp) / "bin"
            fakebin.mkdir()
            tmux = fakebin / "tmux"
            tmux.write_text("#!/bin/sh\nprintf 'auto-test\\n'\n", encoding="utf-8")
            os.chmod(tmux, 0o755)

            result = self.run_hook(
                "--app",
                "droid",
                "--event",
                "stop",
                env={
                    "PATH": f"{fakebin}:{os.environ['PATH']}",
                    "TMUX_PANE": "%1",
                },
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "say:auto-test")

    def test_falls_back_to_droid_notification_sound_without_tmux_pane(self) -> None:
        result = self.run_hook(
            "--app",
            "droid",
            "--event",
            "notification",
            env={"TMUX_PANE": ""},
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), f"sound:{os.environ['HOME']}/.factory/sounds/fx-ack01.wav")

    def test_allows_event_specific_sound_override(self) -> None:
        result = self.run_hook(
            "--app",
            "droid",
            "--event",
            "notification",
            env={
                "TMUX_PANE": "",
                "NOTIFY_TMUX_TITLE_SOUND_DROID_NOTIFICATION": "/tmp/middle.wav",
            },
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "sound:/tmp/middle.wav")

    def test_allows_shared_sound_override(self) -> None:
        result = self.run_hook(
            "--app",
            "cc",
            "--event",
            "stop",
            env={
                "TMUX_PANE": "",
                "NOTIFY_TMUX_TITLE_SOUND": "/tmp/final.wav",
            },
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "sound:/tmp/final.wav")

    def test_falls_back_to_cc_stop_sound_when_tmux_title_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fakebin = Path(tmp) / "bin"
            fakebin.mkdir()
            tmux = fakebin / "tmux"
            tmux.write_text("#!/bin/sh\nprintf '\\n'\n", encoding="utf-8")
            os.chmod(tmux, 0o755)

            result = self.run_hook(
                "--app",
                "cc",
                "--event",
                "stop",
                env={
                    "PATH": f"{fakebin}:{os.environ['PATH']}",
                    "TMUX_PANE": "%1",
                },
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "sound:/System/Library/Sounds/Ping.aiff")

    def test_rejects_unknown_app_event_pair(self) -> None:
        result = self.run_hook("--app", "droid", "--event", "unknown")

        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported app/event", result.stderr)


if __name__ == "__main__":
    unittest.main()

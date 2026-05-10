import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "notify-tmux-title.sh"


def _make_fake_tmux(bindir: Path, window_title: str, pane_title: str = "海獭") -> None:
    bindir.mkdir(parents=True, exist_ok=True)
    tmux = bindir / "tmux"
    tmux.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"display-message\" ]; then\n"
        "  case \"$5\" in\n"
        f"    '#W') printf '{window_title}\\n' ;;\n"
        f"    '#{{pane_title}}') printf '{pane_title}\\n' ;;\n"
        "    *) printf '\\n' ;;\n"
        "  esac\n"
        "elif [ \"$1\" = \"select-pane\" ]; then\n"
        "  echo select-pane:\"$@\" >> \"$TMUX_FAKE_LOG\"\n"
        "elif [ \"$1\" = \"set-option\" ]; then\n"
        "  echo set-option:\"$@\" >> \"$TMUX_FAKE_LOG\"\n"
        "fi\n",
        encoding="utf-8",
    )
    os.chmod(tmux, 0o755)


class NotifyTmuxTitleTests(unittest.TestCase):
    def run_hook(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        base_env = {**os.environ, "NOTIFY_TMUX_TITLE_DRY_RUN": "1"}
        if env:
            base_env.update(env)
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            text=True,
            capture_output=True,
            env=base_env,
            input=stdin,
        )

    # ---------- existing behaviour preserved ---------------------------------

    def test_assigns_pane_name_and_says_window_plus_pane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_log = tmp_path / "tmux.log"
            _make_fake_tmux(tmp_path / "bin", "auto-test", "海獭")

            result = self.run_hook(
                "--app", "droid",
                "--event", "stop",
                env={
                    "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                    "TMUX_PANE": "%1",
                    "TMUX_FAKE_LOG": str(fake_log),
                    "NOTIFY_TMUX_TITLE_PANE_NAMES": "海獭",
                },
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["pane-name:%1:海獭", "say:auto-test 海獭"])

    def test_default_pane_name_pool_uses_water_margin_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _make_fake_tmux(tmp_path / "bin", "auto-test", "ignored")

            result = self.run_hook(
                "--app", "droid",
                "--event", "stop",
                env={
                    "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                    "TMUX_PANE": "%1",
                    "NOTIFY_TMUX_TITLE_PANE_NAMES": "",
                },
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["pane-name:%1:及时雨宋江", "say:auto-test 及时雨宋江"])

    def test_falls_back_to_droid_notification_sound_without_tmux_pane(self) -> None:
        result = self.run_hook(
            "--app",
            "droid",
            "--event",
            "notification",
            env={"TMUX_PANE": ""},
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            f"sound:{os.environ['HOME']}/.factory/sounds/fx-ack01.wav",
        )

    def test_allows_event_specific_sound_override(self) -> None:
        result = self.run_hook(
            "--app", "droid",
            "--event", "notification",
            env={
                "TMUX_PANE": "",
                "NOTIFY_TMUX_TITLE_SOUND_DROID_NOTIFICATION": "/tmp/middle.wav",
            },
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "sound:/tmp/middle.wav")

    def test_allows_shared_sound_override(self) -> None:
        result = self.run_hook(
            "--app", "cc",
            "--event", "stop",
            env={
                "TMUX_PANE": "",
                "NOTIFY_TMUX_TITLE_SOUND": "/tmp/final.wav",
            },
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "sound:/tmp/final.wav")

    def test_names_pane_and_falls_back_to_cc_stop_sound_when_title_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_log = tmp_path / "tmux.log"
            _make_fake_tmux(tmp_path / "bin", "", "芒果")  # empty window title
            result = self.run_hook(
                "--app", "cc",
                "--event", "stop",
                env={
                    "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                    "TMUX_PANE": "%1",
                    "TMUX_FAKE_LOG": str(fake_log),
                    "NOTIFY_TMUX_TITLE_PANE_NAMES": "芒果",
                },
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            ["pane-name:%1:芒果", "sound:/System/Library/Sounds/Ping.aiff"],
        )

    def test_rejects_unknown_app_event_pair(self) -> None:
        result = self.run_hook("--app", "droid", "--event", "unknown")

        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported app/event", result.stderr)

    def test_shared_sound_override_beats_static_fallback(self) -> None:
        r = self.run_hook(
            "--app", "droid",
            "--event", "stop",
            env={
                "TMUX_PANE": "",
                "NOTIFY_TMUX_TITLE_SOUND": "/tmp/forced.wav",
            },
        )
        self.assertEqual(r.stdout.strip(), "sound:/tmp/forced.wav")


if __name__ == "__main__":
    unittest.main()

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "notify-tmux-title.sh"


def _make_fake_tmux(
    bindir: Path,
    window_title: str,
    pane_title: str = "海獭",
    pane_rows: list[tuple[str, str]] | None = None,
    pane_options: dict[str, str] | None = None,
) -> None:
    bindir.mkdir(parents=True, exist_ok=True)
    tmux = bindir / "tmux"
    panes_output = "".join(f"{pane}\t{index}\n" for pane, index in (pane_rows or []))
    option_cases = "".join(
        f"    '{pane}') printf '{name}\\n' ;;\n" for pane, name in (pane_options or {}).items()
    )
    tmux.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"display-message\" ]; then\n"
        "  case \"$5\" in\n"
        f"    '#W') printf '{window_title}\\n' ;;\n"
        f"    '#{{pane_title}}') printf '{pane_title}\\n' ;;\n"
        "    *) printf '\\n' ;;\n"
        "  esac\n"
        "elif [ \"$1\" = \"list-panes\" ]; then\n"
        "  cat <<'EOF'\n"
        f"{panes_output}"
        "EOF\n"
        "elif [ \"$1\" = \"show-option\" ]; then\n"
        "  case \"$3\" in\n"
        f"{option_cases}"
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

    def test_default_pane_name_pool_uses_randomized_water_margin_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _make_fake_tmux(tmp_path / "bin", "auto-test", "ignored")

            result = self.run_hook(
                "--app", "droid",
                "--event", "stop",
                env={
                    "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                    "TMUX_PANE": "%1",
                    "NOTIFY_TMUX_TITLE_RANDOM_SEED": "1",
                    "NOTIFY_TMUX_TITLE_PANE_NAMES": "",
                },
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("pane-name:%1:"))
        pane_name = lines[0].removeprefix("pane-name:%1:")
        self.assertNotEqual(pane_name, "及时雨宋江")
        self.assertEqual(lines[1], f"say:auto-test {pane_name}")

    def test_assigns_random_unused_names_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_log = tmp_path / "tmux.log"
            _make_fake_tmux(
                tmp_path / "bin",
                "",
                pane_rows=[("%1", "1"), ("%2", "2"), ("%3", "3")],
                pane_options={"%1": "玉麒麟卢俊义"},
            )

            result = self.run_hook(
                "--app", "cc",
                "--event", "stop",
                env={
                    "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                    "TMUX_PANE": "%2",
                    "TMUX_FAKE_LOG": str(fake_log),
                    "NOTIFY_TMUX_TITLE_DRY_RUN": "0",
                    "NOTIFY_TMUX_TITLE_RANDOM_SEED": "1",
                    "NOTIFY_TMUX_TITLE_PANE_NAMES": "及时雨宋江 玉麒麟卢俊义 智多星吴用",
                },
            )

            logged = fake_log.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        assigned = [
            line.rsplit(" ", 1)[-1]
            for line in logged
            if line.startswith("set-option:set-option -qpt")
        ]
        self.assertEqual(len(assigned), 2)
        self.assertEqual(len({"玉麒麟卢俊义", *assigned}), 3)

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

    def test_opencode_stop_says_window_plus_pane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _make_fake_tmux(tmp_path / "bin", "opencode-test", "海獭")

            result = self.run_hook(
                "--app", "opencode",
                "--event", "stop",
                env={
                    "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                    "TMUX_PANE": "%1",
                    "NOTIFY_TMUX_TITLE_PANE_NAMES": "海獭",
                },
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])

    def test_suppresses_duplicate_say_content_within_dedupe_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _make_fake_tmux(tmp_path / "bin", "opencode-test", "ignored")
            env = {
                "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                "TMUX_PANE": "%1",
                "NOTIFY_TMUX_TITLE_PANE_NAMES": "海獭",
                "NOTIFY_TMUX_TITLE_DEDUPE_DIR": str(tmp_path / "dedupe"),
                "NOTIFY_TMUX_TITLE_DEDUPE_SECONDS": "5",
            }

            first = self.run_hook("--app", "opencode", "--event", "stop", env=env)
            second = self.run_hook("--app", "opencode", "--event", "stop", env=env)

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first.stdout.strip().splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])
        self.assertEqual(
            second.stdout.strip().splitlines(),
            ["pane-name:%1:海獭", "suppressed:say:opencode-test 海獭"],
        )

    def test_dedupe_can_be_disabled_for_say_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _make_fake_tmux(tmp_path / "bin", "opencode-test", "ignored")
            env = {
                "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                "TMUX_PANE": "%1",
                "NOTIFY_TMUX_TITLE_PANE_NAMES": "海獭",
                "NOTIFY_TMUX_TITLE_DEDUPE_DIR": str(tmp_path / "dedupe"),
                "NOTIFY_TMUX_TITLE_DEDUPE_SECONDS": "0",
            }

            first = self.run_hook("--app", "opencode", "--event", "stop", env=env)
            second = self.run_hook("--app", "opencode", "--event", "stop", env=env)

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first.stdout.strip().splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])
        self.assertEqual(second.stdout.strip().splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])

    def test_dedupe_allows_say_content_after_window_expires(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dedupe_dir = tmp_path / "dedupe"
            _make_fake_tmux(tmp_path / "bin", "opencode-test", "ignored")
            env = {
                "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                "TMUX_PANE": "%1",
                "NOTIFY_TMUX_TITLE_PANE_NAMES": "海獭",
                "NOTIFY_TMUX_TITLE_DEDUPE_DIR": str(dedupe_dir),
                "NOTIFY_TMUX_TITLE_DEDUPE_SECONDS": "5",
            }

            first = self.run_hook("--app", "opencode", "--event", "stop", env=env)
            for state_file in dedupe_dir.glob("*"):
                if state_file.is_file():
                    state_file.write_text("0\n", encoding="utf-8")
            second = self.run_hook("--app", "opencode", "--event", "stop", env=env)

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first.stdout.strip().splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])
        self.assertEqual(second.stdout.strip().splitlines(), ["pane-name:%1:海獭", "say:opencode-test 海獭"])

    def test_opencode_notification_falls_back_to_sound_without_tmux_pane(self) -> None:
        result = self.run_hook(
            "--app",
            "opencode",
            "--event",
            "notification",
            env={"TMUX_PANE": ""},
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "sound:/System/Library/Sounds/Funk.aiff")

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

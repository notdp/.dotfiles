import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class CommandEntryTests(unittest.TestCase):
    def test_long_loop_entry_resolves_script_independent_of_cwd(self) -> None:
        command = (REPO_ROOT / "commands" / "long-loop.md").read_text(encoding="utf-8")

        self.assertIn("LONG_LOOP_SCRIPT=", command)
        self.assertIn("$HOME/.dotfiles/scripts/long_loop.py", command)
        self.assertIn('python3 "$LONG_LOOP_SCRIPT"', command)


if __name__ == "__main__":
    unittest.main()

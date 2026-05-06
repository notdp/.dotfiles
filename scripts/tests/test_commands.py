import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class CommandEntryTests(unittest.TestCase):
    def test_long_loop_entry_resolves_script_independent_of_cwd(self) -> None:
        command = (REPO_ROOT / "commands" / "long-loop.md").read_text(encoding="utf-8")

        self.assertIn("LONG_LOOP_SCRIPT=", command)
        self.assertIn("$HOME/.dotfiles/scripts/long_loop.py", command)
        self.assertIn('python3 "$LONG_LOOP_SCRIPT"', command)

    def test_long_loop_help_is_read_only_terminal_command(self) -> None:
        command = (REPO_ROOT / "commands" / "long-loop.md").read_text(encoding="utf-8")

        self.assertIn("`help` 是终止命令", command)
        self.assertIn("不得创建 `.long-loop/`", command)
        self.assertIn("不得调用 `dev-long-loop`", command)
        self.assertIn("每轮结束必须输出阶段总结", command)

    def test_long_loop_contract_names_validator_fix_plan_and_fresh_context(self) -> None:
        command = (REPO_ROOT / "commands" / "long-loop.md").read_text(encoding="utf-8")

        self.assertIn("fix_plan.md", command)
        self.assertIn("validator.md", command)
        self.assertIn("Fresh Iteration", command)
        self.assertIn("events.jsonl", command)


if __name__ == "__main__":
    unittest.main()

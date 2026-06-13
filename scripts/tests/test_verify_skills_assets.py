import tempfile
import unittest
from pathlib import Path

import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import verify_skills  # noqa: E402


class VerifySkillsAssetTests(unittest.TestCase):
    def test_validate_agent_assets_counts_cross_agent_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "commands").mkdir()
            (root / "commands" / "demo.md").write_text(
                "---\n"
                "description: demo command\n"
                "argument-hint: <target>\n"
                "---\n"
                "Use $ARGUMENTS.\n",
                encoding="utf-8",
            )
            (root / ".kilo" / "agent").mkdir(parents=True)
            (root / ".kilo" / "agent" / "demo-reviewer.md").write_text(
                "---\n"
                "description: 当需要审查时使用。\n"
                "mode: subagent\n"
                "model: cliproxy/gpt-5.5\n"
                "permission:\n"
                "  edit: deny\n"
                "  bash: deny\n"
                "---\n"
                "Read-only reviewer.\n",
                encoding="utf-8",
            )
            (root / "scripts" / "hooks").mkdir(parents=True)
            (root / "scripts" / "hooks" / "stop_check.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "docs" / "refs-details" / "owner").mkdir(parents=True)
            (root / "docs" / "refs-details" / "owner" / "repo.md").write_text("# ref\n", encoding="utf-8")
            (root / "agents").mkdir()
            (root / "agents" / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
            (root / "coding-skills").mkdir()

            context = verify_skills.ValidationContext(repo_root=root)
            summary = verify_skills.validate_agent_assets(context)

        self.assertEqual(summary.agents, 1)
        self.assertEqual(summary.commands, 1)
        self.assertEqual(summary.hooks, 1)
        self.assertEqual(summary.ref_details, 1)
        self.assertGreaterEqual(summary.distribution_links, 1)


if __name__ == "__main__":
    unittest.main()

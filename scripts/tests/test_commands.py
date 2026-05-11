import unittest
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class CommandEntryTests(unittest.TestCase):
    def test_long_loop_command_is_removed_and_skill_is_registered(self) -> None:
        catalog = json.loads((REPO_ROOT / "skills" / "catalog.json").read_text(encoding="utf-8"))
        skill_names = {entry["name"] for entry in catalog["skills"]}

        self.assertFalse((REPO_ROOT / "commands" / "long-loop.md").exists())
        self.assertIn("dev-long-loop", skill_names)
        self.assertTrue((REPO_ROOT / "skills" / "dev-long-loop" / "SKILL.md").exists())

    def test_long_loop_skill_is_only_user_facing_entry(self) -> None:
        skills_text = "\n".join(path.read_text(encoding="utf-8") for path in (REPO_ROOT / "skills").glob("*/SKILL.md"))
        catalog_text = (REPO_ROOT / "skills" / "catalog.json").read_text(encoding="utf-8")

        self.assertIn("dev-long-loop", catalog_text)
        self.assertNotIn("/long-loop", skills_text)
        self.assertIn("long_loop.py", skills_text)
        self.assertTrue((REPO_ROOT / "skills" / "dev-long-loop" / "long_loop.py").exists())

    def test_long_loop_contract_names_v2_files(self) -> None:
        skill = (REPO_ROOT / "skills" / "dev-long-loop" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("SPEC_OVERVIEW.md", skill)
        self.assertIn("fix_plan.md", skill)
        self.assertIn("qa.md", skill)
        self.assertIn("logs.md", skill)
        self.assertNotIn("validator-results.json", skill)
        self.assertNotIn("events.jsonl", skill)

    def test_long_loop_skill_documents_hands_off_runtime_contract(self) -> None:
        skill = (REPO_ROOT / "skills" / "dev-long-loop" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("hands-off", skill)
        self.assertIn("runtime.log", skill)
        self.assertIn("observe", skill)
        self.assertIn("observe.html", skill)
        self.assertIn("idle timeout", skill)
        self.assertIn("pending / in_progress / done / blocked", skill)


if __name__ == "__main__":
    unittest.main()

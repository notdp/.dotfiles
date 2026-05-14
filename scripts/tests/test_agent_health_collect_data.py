import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COLLECT_SCRIPT = REPO_ROOT / "skills" / "agent-health" / "scripts" / "collect_data.sh"


class AgentHealthCollectDataTests(unittest.TestCase):
    def test_collect_data_reports_missing_catalog_and_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "agents").mkdir(parents=True)
            (repo / "skills" / "sample-skill").mkdir(parents=True)
            (repo / "agents" / "AGENTS.md").write_text("# rules\n")
            (repo / "skills" / "sample-skill" / "SKILL.md").write_text("---\nname: sample-skill\ndescription: demo\n---\n")

            result = subprocess.run(
                ["bash", str(COLLECT_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("=== SUMMARY ===", result.stdout)
            self.assertIn("[WARN] Missing skills/catalog.json", result.stdout)
            self.assertIn("[WARN] Missing hook configuration", result.stdout)
            self.assertIn("[WARN] Missing MCP configuration", result.stdout)

    def test_collect_data_accepts_factory_settings_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "agents").mkdir(parents=True)
            (repo / "skills").mkdir(parents=True)
            (repo / ".factory").mkdir(parents=True)
            (repo / "agents" / "AGENTS.md").write_text("# rules\n")
            (repo / "skills" / "catalog.json").write_text('{"skills": []}\n')
            (repo / ".factory" / "settings.json").write_text('{"hooks": {"Stop": []}}\n')

            result = subprocess.run(
                ["bash", str(COLLECT_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertNotIn("[WARN] Missing hook configuration", result.stdout)


if __name__ == "__main__":
    unittest.main()

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_SCRIPT = REPO_ROOT / "coding-skills" / "assist-learn" / "scripts" / "scaffold_note.py"


class EngLearnScaffoldTests(unittest.TestCase):
    def test_scaffold_note_outputs_learning_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "note.md"
            result = subprocess.run(
                ["python3", str(SCAFFOLD_SCRIPT), "技能目录验证", str(output_file)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            content = output_file.read_text()
            self.assertIn("# Learning Note: 技能目录验证", content)
            self.assertIn("## Context", content)
            self.assertIn("## Reusable Pattern", content)
            self.assertIn("## Follow-ups", content)


if __name__ == "__main__":
    unittest.main()

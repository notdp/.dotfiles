import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "review_artifact_view.py"


class ReviewArtifactViewTests(unittest.TestCase):
    def test_generates_static_review_html_from_diff_and_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            diff = root / "diff.patch"
            findings = root / "findings.md"
            output = root / "review.html"
            diff.write_text("diff --git a/app.py b/app.py\n+print('<unsafe>')\n", encoding="utf-8")
            findings.write_text("# Findings\n\n- P1: escape `<script>` content\n", encoding="utf-8")

            result = subprocess.run(
                ["python3", str(SCRIPT), "--diff", str(diff), "--findings", str(findings), "--output", str(output)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(output), result.stdout)
            html = output.read_text(encoding="utf-8")
            self.assertIn("Review Artifact", html)
            self.assertIn("Findings", html)
            self.assertIn("Diff", html)
            self.assertIn("&lt;unsafe&gt;", html)
            self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()

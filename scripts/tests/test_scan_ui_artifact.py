import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "scan_ui_artifact.py"


class ScanUiArtifactTests(unittest.TestCase):
    def run_scan(self, *paths: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--format", "json", *[str(path) for path in paths]],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

    def test_reports_priority_id_location_snippet_and_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "artifact.html"
            artifact.write_text(
                "<section class='bg-gradient-to-r from-indigo-500 to-purple-500'>\n"
                "  <p>✨ Feature one with 99.9% uptime</p>\n"
                "  <img src='https://placehold.co/800x400'>\n"
                "  <div class='overflow-hidden truncate shadow-2xl'>Hidden text</div>\n"
                "  <div class='w-[713px] z-[999]'>Magic layout</div>\n"
                "</section>\n",
                encoding="utf-8",
            )

            result = self.run_scan(artifact)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        findings = payload["findings"]
        self.assertGreaterEqual(len(findings), 5)
        self.assertTrue({"P0", "P1", "P2"}.issubset({finding["priority"] for finding in findings}))
        for finding in findings:
            self.assertIn("id", finding)
            self.assertIn("file", finding)
            self.assertIn("line", finding)
            self.assertIn("snippet", finding)
            self.assertIn("fix", finding)

    def test_suppresses_design_system_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "tokens.css"
            artifact.write_text(
                ":root { --color-brand-primary: #6366f1; }\n"
                ".button { color: var(--color-brand-primary); }\n",
                encoding="utf-8",
            )

            result = self.run_scan(artifact)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["findings"], [])

    def test_markdown_output_contains_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "artifact.html"
            artifact.write_text("<p>Lorem ipsum 🚀</p>\n", encoding="utf-8")

            result = subprocess.run(
                ["python3", str(SCRIPT), str(artifact)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## UI Artifact Lint", result.stdout)
        self.assertIn("| Priority | ID | Evidence | Issue | Fix |", result.stdout)
        self.assertIn("filler-copy", result.stdout)


if __name__ == "__main__":
    unittest.main()

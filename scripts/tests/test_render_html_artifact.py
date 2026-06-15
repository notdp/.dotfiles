import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "render_html_artifact.py"
SKILL_WRAPPER = REPO_ROOT / "coding-skills" / "readable-html-artifact" / "render_html_artifact.py"


class RenderHtmlArtifactTests(unittest.TestCase):
    def test_renders_markdown_to_static_html_without_printing_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.md"
            output = root / "source.html"
            source.write_text(
                "# Plan\n\n"
                "Source text with `<script>alert(1)</script>`.\n\n"
                "## Steps\n\n"
                "- First\n"
                "- Second\n\n"
                "```python\n"
                "print('<unsafe>')\n"
                "```\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--profile",
                    "plan",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"wrote {output}", result.stdout)
            self.assertNotIn("<!doctype html>", result.stdout)
            self.assertTrue(output.exists())
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("Plan", rendered)
            self.assertIn(str(source), rendered)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
            self.assertIn("print(&#x27;&lt;unsafe&gt;&#x27;)", rendered)
            self.assertNotIn("<script>alert(1)</script>", rendered)

    def test_renders_markdown_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "research.md"
            output = root / "research.html"
            source.write_text(
                "# Research\n\n"
                "| Option | Verdict |\n"
                "|---|---|\n"
                "| Script | Recommended |\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--title",
                    "Research View",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("<table>", rendered)
            self.assertIn("<th>Option</th>", rendered)
            self.assertIn("<td>Recommended</td>", rendered)

    def _render(self, markdown: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "s.md"
            output = root / "s.html"
            source.write_text(markdown, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(SCRIPT), "--source", str(source), "--output", str(output)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return output.read_text(encoding="utf-8")

    def test_inline_bold_and_code(self) -> None:
        rendered = self._render("# T\n\nuse `lr.py` and **never** touch main.\n")
        self.assertIn("<code>lr.py</code>", rendered)
        self.assertIn("<strong>never</strong>", rendered)
        self.assertNotIn("**never**", rendered)

    def test_blockquote(self) -> None:
        rendered = self._render("# T\n\n> 状态:v0, see `lr.py`.\n")
        self.assertIn("<blockquote>", rendered)
        self.assertIn("<code>lr.py</code>", rendered)
        self.assertNotIn("&gt; 状态", rendered)  # 不应把 > 当字面文本

    def test_ordered_list(self) -> None:
        rendered = self._render("# T\n\n1. first\n2. second\n")
        self.assertIn("<ol>", rendered)
        self.assertIn("<li>first</li>", rendered)

    def test_inline_code_keeps_xss_escaped(self) -> None:
        # 安全不退化: 行内代码里的 <script> 必须仍被转义
        rendered = self._render("# T\n\nrun `<script>alert(1)</script>` now.\n")
        self.assertIn("<code>&lt;script&gt;alert(1)&lt;/script&gt;</code>", rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)

    def test_skill_wrapper_works_from_target_repo_without_local_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_repo = Path(tmp)
            source = target_repo / "source.md"
            output = target_repo / "artifact.html"
            source.write_text("# Cross Project\n\nWorks from another repo.\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(SKILL_WRAPPER),
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--profile",
                    "generic",
                ],
                cwd=target_repo,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((target_repo / "scripts" / "render_html_artifact.py").exists())
            self.assertIn(f"wrote {output}", result.stdout)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn(str(source), rendered)
            self.assertIn("Cross Project", rendered)


if __name__ == "__main__":
    unittest.main()

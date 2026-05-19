import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "review_doc_render.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import review_doc_render  # noqa: E402


def _comments_payload(anchors: dict[str, list[dict]] | None = None, *, version: int = 1) -> dict:
    return {
        "schema_version": 1,
        "spec_file": "doc.md",
        "review_version": version,
        "anchors": {
            anchor_id: {"heading": anchor_id, "comments": comments}
            for anchor_id, comments in (anchors or {}).items()
        },
    }


class SplitSectionsTests(unittest.TestCase):
    def test_splits_per_heading(self) -> None:
        md = "Prelude text.\n\n## First\n\nbody A\n\n## Second\n\nbody B\n"
        sections = review_doc_render.split_sections(md)
        ids = [s.anchor.id if s.anchor else None for s in sections]
        self.assertEqual(ids, [None, "first", "second"])
        prelude = next(s for s in sections if s.anchor is None)
        self.assertIn("Prelude text", prelude.body_md)

    def test_section_body_excludes_next_heading(self) -> None:
        md = "## A\n\nalpha\n\n## B\n\nbeta\n"
        sections = review_doc_render.split_sections(md)
        a_body = next(s.body_md for s in sections if s.anchor and s.anchor.id == "a")
        self.assertIn("alpha", a_body)
        self.assertNotIn("## B", a_body)
        self.assertNotIn("beta", a_body)

    def test_no_prelude_when_doc_starts_with_heading(self) -> None:
        md = "## Only\n\ntext\n"
        sections = review_doc_render.split_sections(md)
        self.assertEqual([s.anchor.id for s in sections if s.anchor], ["only"])
        self.assertFalse(any(s.anchor is None for s in sections))


class RenderReviewHtmlTests(unittest.TestCase):
    def test_each_heading_has_review_id(self) -> None:
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n\ntext\n\n## Bar\n",
            comments=None,
        )
        self.assertIn('data-review-id="foo"', html)
        self.assertIn('data-review-id="bar"', html)

    def test_textarea_per_anchor(self) -> None:
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n\n## Bar\n",
            comments=None,
        )
        textareas = re.findall(r'data-anchor-id="([^"]+)"', html)
        self.assertEqual(sorted(textareas), ["bar", "foo"])

    def test_existing_comments_rendered_in_thread(self) -> None:
        comments = _comments_payload(
            {
                "foo": [
                    {
                        "id": "c-1",
                        "role": "user",
                        "status": "resolved",
                        "text": "old user comment",
                        "response": "agent reply",
                    }
                ]
            }
        )
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n\ntext\n",
            comments=comments,
        )
        self.assertIn("old user comment", html)
        self.assertIn("agent reply", html)

    def test_export_button_present(self) -> None:
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n",
            comments=None,
        )
        self.assertIn('id="export-btn"', html)
        self.assertIn("导出", html)

    def test_embeds_comments_payload_for_js(self) -> None:
        comments = _comments_payload({"foo": []}, version=3)
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n",
            comments=comments,
        )
        match = re.search(r'id="comments-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        self.assertIsNotNone(match, "expected embedded comments JSON block")
        embedded = json.loads(match.group(1))
        self.assertEqual(embedded["review_version"], 3)
        self.assertIn("foo", embedded["anchors"])

    def test_escapes_hostile_html_in_body(self) -> None:
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n\n`<script>alert(1)</script>`\n",
            comments=None,
        )
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_escapes_hostile_html_in_comment_text(self) -> None:
        comments = _comments_payload(
            {"foo": [{"id": "c-1", "role": "user", "status": "open", "text": "<img src=x onerror=1>"}]}
        )
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n",
            comments=comments,
        )
        self.assertIn("&lt;img", html)
        self.assertNotIn("<img src=x onerror=1>", html)

    def test_agent_role_comment_visually_distinct(self) -> None:
        comments = _comments_payload(
            {"foo": [{"id": "c-1", "role": "agent", "status": "open", "text": "agent question?"}]}
        )
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n",
            comments=comments,
        )
        self.assertIn("agent question?", html)
        self.assertRegex(html, r'role-agent|data-role="agent"')

    def test_no_comments_renders_empty_thread(self) -> None:
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n",
            comments=None,
        )
        self.assertIn('data-review-id="foo"', html)
        match = re.search(r'id="comments-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        embedded = json.loads(match.group(1))
        self.assertEqual(embedded["anchors"], {})

    def test_review_version_in_header(self) -> None:
        comments = _comments_payload(version=7)
        html = review_doc_render.render_review_html(
            doc_path=Path("doc.md"),
            doc_text="## Foo\n",
            comments=comments,
        )
        self.assertRegex(html, r"v7\b")


class CliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            text=True,
            capture_output=True,
        )

    def test_cli_writes_html_without_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            output = Path(tmp) / "doc.review.html"
            doc.write_text("# Title\n\n## Foo\n\ntext\n", encoding="utf-8")
            result = self._run("--doc", str(doc), "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            html = output.read_text(encoding="utf-8")
            self.assertIn('data-review-id="foo"', html)

    def test_cli_writes_html_with_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc = tmp_path / "doc.md"
            comments = tmp_path / "doc.comments.json"
            output = tmp_path / "doc.review.html"
            doc.write_text("## Foo\n", encoding="utf-8")
            comments.write_text(
                json.dumps(
                    _comments_payload(
                        {"foo": [{"id": "c-1", "role": "user", "status": "open", "text": "x"}]}
                    )
                ),
                encoding="utf-8",
            )
            result = self._run(
                "--doc", str(doc), "--output", str(output), "--comments", str(comments)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = output.read_text(encoding="utf-8")
            self.assertIn("x", html)

    def test_cli_exits_nonzero_when_doc_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.html"
            result = self._run("--doc", str(Path(tmp) / "missing.md"), "--output", str(output))
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()

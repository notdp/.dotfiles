import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "review_doc_ids.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import review_doc_ids  # noqa: E402


class SlugifyHeadingTests(unittest.TestCase):
    def test_ascii_lowercased_with_dashes(self) -> None:
        self.assertEqual(review_doc_ids.slugify_heading("Permission Group Creation"), "permission-group-creation")

    def test_chinese_preserved(self) -> None:
        self.assertEqual(review_doc_ids.slugify_heading("3.2 权限组创建"), "3-2-权限组创建")

    def test_strips_leading_trailing_dashes(self) -> None:
        self.assertEqual(review_doc_ids.slugify_heading("  ---hello---  "), "hello")

    def test_collapses_repeated_separators(self) -> None:
        self.assertEqual(review_doc_ids.slugify_heading("a / b // c"), "a-b-c")

    def test_empty_heading_raises(self) -> None:
        with self.assertRaises(ValueError):
            review_doc_ids.slugify_heading("   ")


class ExtractAnchorsTests(unittest.TestCase):
    def test_extracts_h2_and_h3(self) -> None:
        md = (
            "# Title\n"
            "\n"
            "Body paragraph.\n"
            "\n"
            "## 第一节\n"
            "\n"
            "Text.\n"
            "\n"
            "### 子节 A\n"
            "\n"
            "More.\n"
        )
        anchors = review_doc_ids.extract_anchors(md)
        ids = [a.id for a in anchors]
        levels = [a.level for a in anchors]
        self.assertEqual(ids, ["title", "第一节", "子节-a"])
        self.assertEqual(levels, [1, 2, 3])

    def test_ignores_headings_inside_code_block(self) -> None:
        md = (
            "## Real heading\n"
            "\n"
            "```\n"
            "## Not a heading\n"
            "```\n"
            "\n"
            "## Another real\n"
        )
        anchors = review_doc_ids.extract_anchors(md)
        ids = [a.id for a in anchors]
        self.assertEqual(ids, ["real-heading", "another-real"])

    def test_assigns_line_numbers(self) -> None:
        md = "## A\n\n## B\n"
        anchors = review_doc_ids.extract_anchors(md)
        self.assertEqual([a.line for a in anchors], [1, 3])

    def test_duplicate_headings_get_suffix(self) -> None:
        md = "## Foo\n\n## Foo\n\n## Foo\n"
        anchors = review_doc_ids.extract_anchors(md)
        self.assertEqual([a.id for a in anchors], ["foo", "foo-2", "foo-3"])


class VerifyAnchorStabilityTests(unittest.TestCase):
    def _comments(self, anchors_with_open: dict[str, int]) -> dict:
        return {
            "schema_version": 1,
            "spec_file": "doc.md",
            "review_version": 1,
            "anchors": {
                anchor_id: {
                    "heading": anchor_id,
                    "comments": [
                        {"id": f"c-{i}", "status": "open", "role": "user", "text": "x"}
                        for i in range(count)
                    ],
                }
                for anchor_id, count in anchors_with_open.items()
            },
        }

    def test_no_errors_when_all_anchors_present(self) -> None:
        doc_anchors = [review_doc_ids.Anchor(id="a", heading="A", level=2, line=1)]
        comments = self._comments({"a": 1})
        self.assertEqual(review_doc_ids.verify_anchor_stability(doc_anchors, comments), [])

    def test_no_errors_when_removed_anchor_has_only_resolved_comments(self) -> None:
        doc_anchors = [review_doc_ids.Anchor(id="b", heading="B", level=2, line=1)]
        comments = {
            "schema_version": 1,
            "spec_file": "doc.md",
            "review_version": 1,
            "anchors": {
                "a": {
                    "heading": "A",
                    "comments": [{"id": "c-1", "status": "resolved", "role": "user", "text": "x"}],
                }
            },
        }
        self.assertEqual(review_doc_ids.verify_anchor_stability(doc_anchors, comments), [])

    def test_errors_when_removed_anchor_has_open_comments(self) -> None:
        doc_anchors = [review_doc_ids.Anchor(id="b", heading="B", level=2, line=1)]
        comments = self._comments({"a": 2})
        errors = review_doc_ids.verify_anchor_stability(doc_anchors, comments)
        self.assertEqual(len(errors), 1)
        self.assertIn("a", errors[0])
        self.assertIn("2", errors[0])


class CliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            text=True,
            capture_output=True,
        )

    def test_extract_command_prints_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("# Title\n\n## Foo\n\n## Bar\n", encoding="utf-8")
            result = self._run("extract", str(doc))
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.strip().splitlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[1].startswith("foo\t"))
            self.assertTrue(lines[2].startswith("bar\t"))

    def test_verify_exits_zero_when_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc = tmp_path / "doc.md"
            doc.write_text("## A\n\nbody\n", encoding="utf-8")
            comments = tmp_path / "doc.comments.json"
            comments.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "spec_file": str(doc),
                        "review_version": 1,
                        "anchors": {"a": {"heading": "A", "comments": []}},
                    }
                ),
                encoding="utf-8",
            )
            result = self._run("verify", str(doc), str(comments))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_verify_exits_nonzero_with_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc = tmp_path / "doc.md"
            doc.write_text("## B\n", encoding="utf-8")
            comments = tmp_path / "doc.comments.json"
            comments.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "spec_file": str(doc),
                        "review_version": 1,
                        "anchors": {
                            "a": {
                                "heading": "A",
                                "comments": [
                                    {"id": "c-1", "status": "open", "role": "user", "text": "x"}
                                ],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = self._run("verify", str(doc), str(comments))
            self.assertEqual(result.returncode, 1)
            self.assertIn("a", result.stderr)


if __name__ == "__main__":
    unittest.main()

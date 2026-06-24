import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "coding-skills" / "assist-learn" / "scripts" / "learnings_search.py"

sys.path.insert(0, str(REPO_ROOT))
from scripts.hooks import memory_score  # noqa: E402


class LearningsSearchTests(unittest.TestCase):
    def run_search(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            text=True,
            capture_output=True,
        )

    def write_note(self, root: Path, rel: str, frontmatter: dict, body: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
        path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")

    def test_finds_and_ranks_matches_by_relevance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(
                root,
                "hooks/strong.md",
                {"title": "hook bypass lesson", "tags": "[hook, guard]", "module": "command_guard"},
                "This note is about a hook guard hook edge case.",
            )
            self.write_note(
                root,
                "misc/weak.md",
                {"title": "unrelated note", "tags": "[ui]", "module": "frontend"},
                "Mentions a hook once in passing.",
            )

            result = self.run_search("hook", "guard", "--root", str(root))

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        out = result.stdout
        self.assertIn("hooks/strong.md", out)
        # stronger match (frontmatter title+tags+module + body) ranks before weaker
        self.assertLess(out.index("hooks/strong.md"), out.index("misc/weak.md") if "misc/weak.md" in out else len(out) + 1)

    def test_frontmatter_summary_not_full_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(
                root,
                "hooks/note.md",
                {"title": "guard lesson", "tags": "[guard]"},
                "SECRET_BODY_MARKER should not be dumped in full.",
            )

            result = self.run_search("guard", "--root", str(root))

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("hooks/note.md", result.stdout)
        self.assertNotIn("SECRET_BODY_MARKER", result.stdout)

    def test_empty_or_missing_store_is_graceful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            result = self.run_search("anything", "--root", str(missing))

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_no_match_is_graceful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_note(root, "a.md", {"title": "alpha"}, "beta gamma")
            result = self.run_search("zzzznotpresent", "--root", str(root))

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertNotIn("a.md", result.stdout)

    def test_shared_memory_score_parses_frontmatter_and_weights_it(self) -> None:
        text = "---\ntitle: hook guard\ntags: [hook, guard]\n---\n\nmentions hook once\n"
        frontmatter, body = memory_score.split_frontmatter(text)

        self.assertEqual(memory_score.parse_frontmatter(frontmatter)["tags"], "hook, guard")
        self.assertGreater(memory_score.score_note(frontmatter, body, ["guard"]), memory_score.score_note("", body, ["guard"]))


if __name__ == "__main__":
    unittest.main()

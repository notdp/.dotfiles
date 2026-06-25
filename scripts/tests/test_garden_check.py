import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import garden_check as gc  # noqa: E402


class ParseIndexGitlinksTests(unittest.TestCase):
    def test_only_mode_160000_paths_kept(self) -> None:
        out = (
            "100644 abc123 0\tREADME.md\n"
            "160000 2c606141 0\trefs/forrestchang/andrej-karpathy-skills\n"
            "160000 deadbeef 0\trefs/multica-ai/andrej-karpathy-skills\n"
            "100755 def456 0\tscripts/run-verify.sh\n"
        )
        self.assertEqual(
            gc.parse_index_gitlinks(out),
            {
                "refs/forrestchang/andrej-karpathy-skills",
                "refs/multica-ai/andrej-karpathy-skills",
            },
        )

    def test_blank_and_malformed_lines_ignored(self) -> None:
        self.assertEqual(gc.parse_index_gitlinks("\n160000 nopath_no_tab\n"), set())


class ParseGitmodulesPathsTests(unittest.TestCase):
    def test_extracts_path_values(self) -> None:
        out = (
            "submodule.refs/multica-ai/andrej-karpathy-skills.path refs/multica-ai/andrej-karpathy-skills\n"
            "submodule.refs/anthropics/skills.path refs/anthropics/skills\n"
        )
        self.assertEqual(
            gc.parse_gitmodules_paths(out),
            {"refs/multica-ai/andrej-karpathy-skills", "refs/anthropics/skills"},
        )


class FindDeadRoutesTests(unittest.TestCase):
    known = {
        "think-map", "guard-verify", "guard-write-check", "guard-write-facts",
        "dev-tdd", "assist-write-corpus",
    }

    def test_flags_unknown_prefixed_slug(self) -> None:
        text = "用 `/think-map` 然后 `/guard-ghost` 收尾\n"
        self.assertEqual(gc.find_dead_routes(text, self.known), {"guard-ghost": 1})

    def test_family_glob_not_flagged(self) -> None:
        # `guard-write-*` 是家族通配，绝不能被截成不存在的 `guard-write`（回归锁）
        text = "- write-* + guard-write-* / assist-write-corpus：中文写作能力\n"
        self.assertEqual(gc.find_dead_routes(text, self.known), {})

    def test_bare_prefix_glob_not_matched(self) -> None:
        text = "- `think-*`：理解问题；`dev-*`：调试\n"
        self.assertEqual(gc.find_dead_routes(text, self.known), {})

    def test_known_slugs_pass(self) -> None:
        text = "`/think-map` → `/dev-tdd` → `/guard-verify`\n"
        self.assertEqual(gc.find_dead_routes(text, self.known), {})

    def test_reports_first_lineno(self) -> None:
        text = "line one\n`/guard-ghost` here\nand `/guard-ghost` again\n"
        self.assertEqual(gc.find_dead_routes(text, self.known), {"guard-ghost": 2})


class ClassifySymlinksTests(unittest.TestCase):
    def test_all_ok(self) -> None:
        statuses = [("a", "ta", "ok"), ("b", "tb", "ok")]
        bad, all_missing = gc.classify_symlinks(statuses)
        self.assertEqual(bad, [])
        self.assertFalse(all_missing)

    def test_all_missing_is_not_installed(self) -> None:
        statuses = [("a", "ta", "missing"), ("b", "tb", "missing")]
        bad, all_missing = gc.classify_symlinks(statuses)
        self.assertEqual(len(bad), 2)
        self.assertTrue(all_missing)  # 调用方据此降级为 SKIP，不计 fail

    def test_partial_missing_is_drift(self) -> None:
        statuses = [("a", "ta", "ok"), ("b", "tb", "missing")]
        bad, all_missing = gc.classify_symlinks(statuses)
        self.assertEqual(bad, [("b", "tb", "missing")])
        self.assertFalse(all_missing)  # 部分缺 = 真漂移

    def test_mismatch_is_drift_not_skip(self) -> None:
        statuses = [("a", "ta", "ok"), ("b", "tb", "mismatch")]
        bad, all_missing = gc.classify_symlinks(statuses)
        self.assertEqual(bad, [("b", "tb", "mismatch")])
        self.assertFalse(all_missing)


if __name__ == "__main__":
    unittest.main()

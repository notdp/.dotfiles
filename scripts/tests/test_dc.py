import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "coding-skills" / "dev-complete"))

import dc  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_default_config_is_valid_yaml(self):
        import lr
        raw = dc.default_config_yaml()
        config = lr.load_yaml(raw)
        dc.validate_config(config)

    def test_validate_rejects_missing_role(self):
        config = {"version": 2, "roles": {
            "coder": {"backend": "kilo", "model": "m", "autonomy": "high"},
            "reviewer_a": {"backend": "kilo", "model": "m", "autonomy": "off"},
        }}
        with self.assertRaises(ValueError):
            dc.validate_config(config)

    def test_validate_rejects_bad_backend(self):
        config = {"version": 2, "roles": {
            "coder": {"backend": "unknown", "model": "m", "autonomy": "high"},
            "reviewer_a": {"backend": "kilo", "model": "m", "autonomy": "off"},
            "reviewer_b": {"backend": "claude_cli", "model": "m", "autonomy": "off", "cmd": "c"},
        }}
        with self.assertRaises(ValueError):
            dc.validate_config(config)

    def test_validate_accepts_valid(self):
        config = {"version": 2, "roles": {
            "coder": {"backend": "kilo", "model": "m", "autonomy": "high"},
            "reviewer_a": {"backend": "kilo", "model": "m", "autonomy": "off"},
            "reviewer_b": {"backend": "claude_cli", "model": "m", "autonomy": "off", "cmd": "c"},
        }}
        self.assertEqual(dc.validate_config(config), config)


class PromptFileTests(unittest.TestCase):
    def test_coder_prompt_exists(self):
        self.assertTrue(dc._prompt_file("coder").exists())

    def test_reviewer_prompt_shared(self):
        self.assertEqual(dc._prompt_file("reviewer_a"), dc._prompt_file("reviewer_b"))
        self.assertTrue(dc._prompt_file("reviewer_a").exists())


class RoleIntroTests(unittest.TestCase):
    def test_coder_intro_has_workspace(self):
        intro = dc._role_intro("coder", Path("/tmp/ws"), None)
        self.assertIn("/tmp/ws", intro)
        self.assertIn("[STATUS FILE]", intro)
        self.assertIn("coder.status", intro)

    def test_reviewer_intro_has_output_and_status(self):
        intro = dc._role_intro("reviewer_a", Path("/tmp/ws"), None)
        self.assertIn("review_a.md", intro)
        self.assertIn("reviewer_a.status", intro)

    def test_reviewer_b_intro_different_output(self):
        intro = dc._role_intro("reviewer_b", Path("/tmp/ws"), None)
        self.assertIn("review_b.md", intro)
        self.assertIn("reviewer_b.status", intro)

    def test_brief_included(self):
        intro = dc._role_intro("coder", Path("/tmp/ws"), "fix the bug")
        self.assertIn("fix the bug", intro)


class ScaffoldTests(unittest.TestCase):
    def test_scaffold_no_flags_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = Path(tmp) / "REQ.md"
            req.write_text("requirement", encoding="utf-8")
            ret = dc.main(["scaffold", "--requirement", str(req), "--repo-root", tmp])
            self.assertEqual(ret, 2)

    def test_scaffold_missing_requirement_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ret = dc.main(["scaffold", "--requirement", str(Path(tmp) / "nope.md"), "--repo-root", tmp])
            self.assertEqual(ret, 1)


class AckResolutionTests(unittest.TestCase):
    def test_all_resolved(self):
        review = {"A": "found [blocker B1] and [blocker B2] issues"}
        ack = "- [fixed] A:B1 done\n- [rejected] A:B2 not a real issue because xyz"
        unresolved, errors = dc._parse_ack_resolutions(ack, review)
        self.assertEqual(unresolved, [])

    def test_missing_resolution(self):
        review = {"A": "[blocker B1] serious", "B": "[blocker B1] also bad"}
        ack = "- [fixed] A:B1 ok"
        unresolved, _ = dc._parse_ack_resolutions(ack, review)
        self.assertIn("B:B1", unresolved)

    def test_no_blockers_no_errors(self):
        review = {"A": "looks good, no blocker"}
        ack = "all good"
        unresolved, errors = dc._parse_ack_resolutions(ack, review)
        self.assertEqual(unresolved, [])
        self.assertEqual(errors, [])


class CompleteGateTests(unittest.TestCase):
    def _make_workspace(self, tmp):
        ws = Path(tmp) / "ws"
        ws.mkdir()
        state = {"skill": "dev-complete", "state": "develop", "worktree_path": tmp}
        (ws / "state.json").write_text(json.dumps(state), encoding="utf-8")
        return ws

    def test_blocks_without_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            ret = dc.main(["complete", "--workspace", str(ws)])
            self.assertEqual(ret, 2)

    def test_blocks_without_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            (ws / "verify.json").write_text('{"ok": true}', encoding="utf-8")
            (ws / "coder.status").write_text("done commit=abc123", encoding="utf-8")
            ret = dc.main(["complete", "--workspace", str(ws)])
            self.assertEqual(ret, 2)

    def test_blocks_without_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            (ws / "verify.json").write_text('{"ok": true}', encoding="utf-8")
            (ws / "review_a.md").write_text("looks good", encoding="utf-8")
            (ws / "ack.md").write_text("all good", encoding="utf-8")
            (ws / "coder.status").write_text("done impl", encoding="utf-8")
            ret = dc.main(["complete", "--workspace", str(ws)])
            self.assertEqual(ret, 2)

    def test_blocks_with_false_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            (ws / "verify.json").write_text('{"ok": false}', encoding="utf-8")
            (ws / "review_a.md").write_text("ok", encoding="utf-8")
            (ws / "ack.md").write_text("ok", encoding="utf-8")
            (ws / "coder.status").write_text("done commit=abc", encoding="utf-8")
            ret = dc.main(["complete", "--workspace", str(ws)])
            self.assertEqual(ret, 2)


class WorkspaceFileTests(unittest.TestCase):
    def test_workspace_files_defined(self):
        self.assertIn("spec.md", dc.WORKSPACE_FILES)
        self.assertIn("qa.md", dc.WORKSPACE_FILES)


class ResetStatusTests(unittest.TestCase):
    def test_reset_writes_coding(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            ret = dc.main(["reset-status", "--workspace", str(ws), "--role", "coder"])
            self.assertEqual(ret, 0)
            content = (ws / "coder.status").read_text(encoding="utf-8").strip()
            self.assertEqual(content, "coding")


if __name__ == "__main__":
    unittest.main()

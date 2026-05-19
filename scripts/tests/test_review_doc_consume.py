import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "review_doc_consume.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import review_doc_consume  # noqa: E402


def _payload(version: int, anchors: dict[str, list[dict]]) -> dict:
    return {
        "schema_version": 1,
        "spec_file": "doc.md",
        "review_version": version,
        "anchors": {
            anchor_id: {"heading": anchor_id, "comments": comments}
            for anchor_id, comments in anchors.items()
        },
    }


def _comment(comment_id: str, *, status: str = "open", role: str = "user", text: str = "x") -> dict:
    return {"id": comment_id, "role": role, "status": status, "text": text}


class DiffNewCommentsTests(unittest.TestCase):
    def test_extracts_new_comments(self) -> None:
        baseline = _payload(1, {"foo": [_comment("c-1")]})
        incoming = _payload(2, {"foo": [_comment("c-1"), _comment("c-2", text="new!")]})
        plan = review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming)
        self.assertEqual(plan["baseline_version"], 1)
        self.assertEqual(plan["incoming_version"], 2)
        ids = [c["comment_id"] for c in plan["new_comments"]]
        self.assertEqual(ids, ["c-2"])
        self.assertEqual(plan["new_comments"][0]["text"], "new!")
        self.assertEqual(plan["new_comments"][0]["anchor_id"], "foo")

    def test_extracts_comments_under_new_anchor(self) -> None:
        baseline = _payload(1, {"foo": [_comment("c-1")]})
        incoming = _payload(2, {"foo": [_comment("c-1")], "bar": [_comment("c-2")]})
        plan = review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming)
        new_ids = sorted(c["comment_id"] for c in plan["new_comments"])
        self.assertEqual(new_ids, ["c-2"])
        self.assertEqual(plan["new_comments"][0]["anchor_id"], "bar")

    def test_empty_baseline_treats_all_as_new(self) -> None:
        baseline = _payload(0, {})
        incoming = _payload(1, {"foo": [_comment("c-1"), _comment("c-2")]})
        plan = review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming)
        self.assertEqual(len(plan["new_comments"]), 2)

    def test_empty_incoming_returns_empty_plan(self) -> None:
        baseline = _payload(1, {"foo": [_comment("c-1")]})
        incoming = _payload(2, {"foo": [_comment("c-1")]})
        plan = review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming)
        self.assertEqual(plan["new_comments"], [])

    def test_rejects_non_advancing_version(self) -> None:
        baseline = _payload(3, {})
        incoming = _payload(3, {})
        with self.assertRaises(ValueError):
            review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming)
        incoming_lower = _payload(2, {})
        with self.assertRaises(ValueError):
            review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming_lower)

    def test_rejects_spec_file_mismatch(self) -> None:
        baseline = _payload(1, {})
        baseline["spec_file"] = "a.md"
        incoming = _payload(2, {})
        incoming["spec_file"] = "b.md"
        with self.assertRaises(ValueError):
            review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming)

    def test_filters_only_open_status(self) -> None:
        baseline = _payload(1, {})
        incoming = _payload(
            2,
            {"foo": [_comment("c-1", status="open"), _comment("c-2", status="resolved")]},
        )
        plan = review_doc_consume.diff_new_comments(baseline=baseline, incoming=incoming)
        ids = [c["comment_id"] for c in plan["new_comments"]]
        self.assertEqual(ids, ["c-1"])


class ApplyResolutionTests(unittest.TestCase):
    def test_marks_comment_resolved_with_response_and_version(self) -> None:
        comments = _payload(1, {"foo": [_comment("c-1")]})
        updated = review_doc_consume.apply_resolution(
            comments,
            comment_id="c-1",
            classification="blocker",
            status="resolved",
            response="改了 §3.2.1",
            version=2,
        )
        c = updated["anchors"]["foo"]["comments"][0]
        self.assertEqual(c["status"], "resolved")
        self.assertEqual(c["classification"], "blocker")
        self.assertEqual(c["response"], "改了 §3.2.1")
        self.assertEqual(c["resolved_in_version"], 2)

    def test_raises_when_comment_id_missing(self) -> None:
        comments = _payload(1, {"foo": [_comment("c-1")]})
        with self.assertRaises(KeyError):
            review_doc_consume.apply_resolution(
                comments,
                comment_id="c-999",
                classification="nit",
                status="resolved",
                response="x",
                version=2,
            )

    def test_rejects_invalid_status(self) -> None:
        comments = _payload(1, {"foo": [_comment("c-1")]})
        with self.assertRaises(ValueError):
            review_doc_consume.apply_resolution(
                comments,
                comment_id="c-1",
                classification="nit",
                status="weird",
                response="x",
                version=2,
            )

    def test_rejects_invalid_classification(self) -> None:
        comments = _payload(1, {"foo": [_comment("c-1")]})
        with self.assertRaises(ValueError):
            review_doc_consume.apply_resolution(
                comments,
                comment_id="c-1",
                classification="random",
                status="resolved",
                response="x",
                version=2,
            )


class CliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            text=True,
            capture_output=True,
        )

    def test_cli_diff_outputs_plan_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = tmp_path / "old.json"
            incoming = tmp_path / "new.json"
            baseline.write_text(json.dumps(_payload(1, {"foo": [_comment("c-1")]})), encoding="utf-8")
            incoming.write_text(
                json.dumps(_payload(2, {"foo": [_comment("c-1"), _comment("c-2", text="hi")]})),
                encoding="utf-8",
            )
            result = self._run("diff", "--baseline", str(baseline), "--incoming", str(incoming))
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(len(plan["new_comments"]), 1)

    def test_cli_diff_rejects_non_advancing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = tmp_path / "old.json"
            incoming = tmp_path / "new.json"
            baseline.write_text(json.dumps(_payload(2, {})), encoding="utf-8")
            incoming.write_text(json.dumps(_payload(1, {})), encoding="utf-8")
            result = self._run("diff", "--baseline", str(baseline), "--incoming", str(incoming))
            self.assertEqual(result.returncode, 1)
            self.assertIn("version", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()

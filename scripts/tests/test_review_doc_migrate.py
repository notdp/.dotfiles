import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "review_doc_migrate.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import review_doc_migrate  # noqa: E402


SAMPLE_V1 = {
    "schema_version": 1,
    "spec_file": "doc.md",
    "review_version": 2,
    "anchors": {
        "foo": {
            "heading": "Foo",
            "comments": [
                {
                    "id": "c-1",
                    "role": "user",
                    "status": "resolved",
                    "classification": "blocker",
                    "text": "x",
                    "response": "ok",
                    "created_in_version": 1,
                    "resolved_in_version": 2,
                }
            ],
        }
    },
}


class CurrentSchemaTests(unittest.TestCase):
    def test_current_version_is_one(self) -> None:
        self.assertEqual(review_doc_migrate.CURRENT_SCHEMA_VERSION, 1)


class ValidateTests(unittest.TestCase):
    def test_accepts_valid_v1(self) -> None:
        review_doc_migrate.validate(SAMPLE_V1)

    def test_rejects_missing_schema_version(self) -> None:
        payload = {k: v for k, v in SAMPLE_V1.items() if k != "schema_version"}
        with self.assertRaises(ValueError):
            review_doc_migrate.validate(payload)

    def test_rejects_unsupported_schema_version(self) -> None:
        payload = dict(SAMPLE_V1, schema_version=99)
        with self.assertRaises(ValueError):
            review_doc_migrate.validate(payload)

    def test_rejects_non_int_review_version(self) -> None:
        payload = dict(SAMPLE_V1, review_version="2")
        with self.assertRaises(ValueError):
            review_doc_migrate.validate(payload)

    def test_rejects_missing_anchors_field(self) -> None:
        payload = {k: v for k, v in SAMPLE_V1.items() if k != "anchors"}
        with self.assertRaises(ValueError):
            review_doc_migrate.validate(payload)


class MigrateRoundTripTests(unittest.TestCase):
    def test_v1_to_v1_is_identity(self) -> None:
        migrated = review_doc_migrate.migrate(SAMPLE_V1, target=1)
        self.assertEqual(migrated, SAMPLE_V1)

    def test_unknown_target_raises(self) -> None:
        with self.assertRaises(ValueError):
            review_doc_migrate.migrate(SAMPLE_V1, target=99)


class CliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            text=True,
            capture_output=True,
        )

    def test_validate_command_accepts_v1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "comments.json"
            f.write_text(json.dumps(SAMPLE_V1), encoding="utf-8")
            result = self._run("validate", str(f))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_validate_command_rejects_bad_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "comments.json"
            payload = dict(SAMPLE_V1, schema_version=99)
            f.write_text(json.dumps(payload), encoding="utf-8")
            result = self._run("validate", str(f))
            self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()

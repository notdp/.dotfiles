import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "agentsview-memory-vault-emitted-schema.md"
SCRIPT = REPO_ROOT / "scripts" / "validate_agentsview_emitted_schema.py"
LR_PATH = REPO_ROOT / "coding-skills" / "dev-long-run" / "lr.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_agentsview_emitted_schema", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_lr_module():
    spec = importlib.util.spec_from_file_location("lr", LR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AgentsviewEmittedSchemaDocTests(unittest.TestCase):
    def test_doc_covers_vault_memory_versioning_and_downstream_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for phrase in [
            "Vault Discovery",
            "Logical Machine Layer",
            "metrics.jsonl",
            "state.json",
            "verify.json",
            "acceptance.json",
            "stuck.json",
            "Memory Frontmatter Facets",
            "Versioning",
            "Collector Handoff",
            "Downstream Out Of Scope",
            "Idempotency",
            "Failure Handling",
        ]:
            self.assertIn(phrase, text)
        self.assertIn("does not implement the agentsview collector", text)
        self.assertIn("does not move dev-long-run state files", text)


class AgentsviewEmittedSchemaValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator_module()

    def metric_value_for_type(self, field: str, types: tuple[type, ...]):
        if field == "event":
            raise AssertionError("event is provided by the caller")
        if field == "ts":
            return "2026-06-24T00:00:00Z"
        if field == "phase":
            return "01"
        if field == "fingerprint":
            return None
        if bool in types:
            return True
        if int in types:
            return 0
        if str in types:
            return f"{field}-value"
        raise AssertionError(f"no fixture value for {field}: {types}")

    def metric_record_from_schema(self, event: str) -> dict:
        return {
            field: event if field == "event" else self.metric_value_for_type(field, types)
            for field, types in self.validator.METRIC_EVENT_FIELDS[event].items()
        }

    def write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    def write_note(self, user_dir: Path, name: str, frontmatter: str) -> None:
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / name).write_text(f"---\n{frontmatter}---\n\nBody\n", encoding="utf-8")

    def make_workspace(self, root: Path) -> Path:
        ws = root / "ws"
        phase = ws / "phases" / "01_demo"
        phase.mkdir(parents=True)
        self.write_json(
            ws / "state.json",
            {
                "state": "develop",
                "phase": "01",
                "role_in_flight": "agent_orchestrator",
                "worktree_path": str(root / "worktree"),
                "branch": "lr/demo",
                "goal": "demo",
                "repo_root": str(root),
                "slug": "demo",
                "dirty_main_at_start": False,
                "in_place": False,
            },
        )
        self.write_json(phase / "verify.json", {"ok": True, "exit": 0, "output_tail": "ok"})
        self.write_json(phase / "stuck.json", {"consecutive_fail": 0, "fingerprint": None})
        return ws

    def test_validates_metrics_header_and_supported_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self.make_workspace(Path(tmp))
            (ws / "metrics.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"_schema": "dotfiles.long_loop.metrics", "_version": 1}),
                        *(json.dumps(self.metric_record_from_schema(event)) for event in self.validator.METRIC_EVENT_FIELDS),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = self.validator.validate_workspace(ws, ws / "missing-memory")

        self.assertEqual(summary["metrics_records"], 4)
        self.assertEqual(summary["metrics_schema"], "dotfiles.long_loop.metrics@1")

    def test_rejects_invalid_metrics_with_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self.make_workspace(Path(tmp))
            (ws / "metrics.jsonl").write_text(
                json.dumps({"_schema": "dotfiles.long_loop.metrics", "_version": 1}) + "\n"
                + json.dumps({"ts": "2026-06-24T00:00:00Z", "event": "verify", "ok": True}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "metrics.jsonl:2"):
                self.validator.validate_workspace(ws, ws / "missing-memory")

    def test_event_schema_table_rejects_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = self.make_workspace(root)
            line_no = 2
            for event, fields in self.validator.METRIC_EVENT_FIELDS.items():
                for field in fields:
                    record = self.metric_record_from_schema(event)
                    del record[field]
                    (ws / "metrics.jsonl").write_text(
                        json.dumps({"_schema": "dotfiles.long_loop.metrics", "_version": 1}) + "\n"
                        + json.dumps(record) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(ValueError, f"metrics.jsonl:{line_no}.*{field}"):
                        self.validator.validate_workspace(ws, ws / "missing-memory")

    def test_verify_metric_missing_fingerprint_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self.make_workspace(Path(tmp))
            record = self.metric_record_from_schema("verify")
            del record["fingerprint"]
            (ws / "metrics.jsonl").write_text(
                json.dumps({"_schema": "dotfiles.long_loop.metrics", "_version": 1}) + "\n"
                + json.dumps(record) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "metrics.jsonl:2.*fingerprint"):
                self.validator.validate_workspace(ws, ws / "missing-memory")

    def test_validates_state_verify_acceptance_and_stuck_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self.make_workspace(Path(tmp))
            self.write_json(ws / "acceptance.json", {"ok": True, "exit": 0, "output_tail": "green"})
            self.write_json(ws / "phases" / "02_demo" / "verify.json", {"ok": False, "exit": 1, "output_tail": "fail"})
            self.write_json(ws / "phases" / "02_demo" / "stuck.json", {"consecutive_fail": 1, "fingerprint": "abc"})

            summary = self.validator.validate_workspace(ws, ws / "missing-memory")

        self.assertEqual(summary["state_files"], 1)
        self.assertEqual(summary["verify_files"], 2)
        self.assertEqual(summary["acceptance_files"], 1)
        self.assertEqual(summary["stuck_files"], 2)

    def test_rejects_malformed_snapshot_with_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self.make_workspace(Path(tmp))
            self.write_json(ws / "phases" / "01_demo" / "stuck.json", {"consecutive_fail": "1", "fingerprint": None})

            with self.assertRaisesRegex(ValueError, "stuck.json"):
                self.validator.validate_workspace(ws, ws / "missing-memory")

    def test_validates_memory_frontmatter_facets_through_existing_parser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = self.make_workspace(root)
            user_dir = root / "memory" / "user"
            self.write_note(
                user_dir,
                "decision.md",
                "title: Prefer lexical recall\n"
                "date: 2026-06-24\n"
                "problem_type: decision\n"
                "type: semantic\n"
                "status: active\n"
                "origin_session: abc123\n",
            )

            summary = self.validator.validate_workspace(ws, user_dir)

        self.assertEqual(summary["memory_notes"], 1)
        self.assertEqual(summary["memory_facets"]["problem_type"], ["decision"])
        self.assertEqual(summary["memory_facets"]["type"], ["semantic"])
        self.assertEqual(summary["memory_facets"]["origin_session"], ["abc123"])
        self.assertEqual(summary["memory_facets"]["status"], ["active"])

    def test_rejects_malformed_memory_frontmatter_consistently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = self.make_workspace(root)
            user_dir = root / "memory" / "user"
            self.write_note(user_dir, "bad.md", "title: Bad\ndate: 2026-06-24\nunsupported: nope\n")

            with self.assertRaisesRegex(ValueError, "bad.md"):
                self.validator.validate_workspace(ws, user_dir)

    def test_cli_validates_current_shape_and_reports_legacy_metrics_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = self.make_workspace(root)
            (ws / "metrics.jsonl").write_text(
                json.dumps({"ts": "2026-06-24T00:00:00Z", "event": "complete_phase", "phase": "01"}) + "\n",
                encoding="utf-8",
            )
            user_dir = root / "memory" / "user"
            self.write_note(user_dir, "note.md", "title: Note\ndate: 2026-06-24\nproblem_type: knowledge\n")

            result = subprocess.run(
                ["python3", str(SCRIPT), "--workspace", str(ws), "--memory-dir", str(user_dir)],
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("legacy metrics accepted", result.stdout)
        self.assertIn("checked workspace", result.stdout)
        self.assertIn("memory_notes=1", result.stdout)


class LrMetricsCompatibilityTests(unittest.TestCase):
    def test_stats_ignores_metrics_schema_header(self) -> None:
        lr = load_lr_module()
        records = [
            {"_schema": "dotfiles.long_loop.metrics", "_version": 1},
            {"event": "verify", "phase": "01", "ok": True, "fail_streak": 0},
            {"event": "complete_phase", "phase": "01"},
            {"event": "complete_run"},
        ]

        summary = lr.summarize_metrics(records)

        self.assertEqual(summary["verify_attempts"], 1)
        self.assertEqual(summary["verify_passes"], 1)
        self.assertEqual(summary["phases_completed"], 1)
        self.assertTrue(summary["run_completed"])

    def test_append_metric_writes_schema_header_for_new_files(self) -> None:
        lr = load_lr_module()
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            lr.append_metric(ws, {"event": "complete_phase", "phase": "01"})
            records = [json.loads(line) for line in (ws / "metrics.jsonl").read_text(encoding="utf-8").splitlines()]

        self.assertEqual(records[0], {"_schema": "dotfiles.long_loop.metrics", "_version": 1})
        self.assertEqual(records[1]["event"], "complete_phase")


if __name__ == "__main__":
    unittest.main()

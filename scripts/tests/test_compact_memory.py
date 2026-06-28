import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "coding-skills" / "compact-memory" / "scripts" / "compact_memory.py"
INDEX_SCRIPT = REPO_ROOT / "scripts" / "build_memory_index.py"
SKILL = REPO_ROOT / "coding-skills" / "compact-memory" / "SKILL.md"


def load_compact_memory_module():
    spec = importlib.util.spec_from_file_location("compact_memory", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["compact_memory"] = module
    spec.loader.exec_module(module)
    return module


class CompactMemoryTests(unittest.TestCase):
    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--root", str(root), *args],
            text=True,
            capture_output=True,
        )

    def user_dir(self, root: Path) -> Path:
        path = root / "memory" / "user"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_note(
        self,
        root: Path,
        name: str,
        *,
        title: str,
        note_type: str = "episodic",
        status: str = "active",
        problem_type: str = "knowledge",
        keywords: str = "memory, lexical, recall",
        body: str | None = None,
    ) -> Path:
        path = self.user_dir(root) / name
        path.write_text(
            "---\n"
            f"title: {title}\n"
            "date: 2026-06-23\n"
            f"problem_type: {problem_type}\n"
            f"type: {note_type}\n"
            f"status: {status}\n"
            f"keywords: [{keywords}]\n"
            f"origin_session: {name.removesuffix('.md')}\n"
            "verify:\n"
            "---\n\n"
            + (body or f"{title} proves lexical recall should stay file-native.\n"),
            encoding="utf-8",
        )
        return path

    def rebuild_index(self, root: Path) -> None:
        subprocess.run(["python3", str(INDEX_SCRIPT), "--root", str(root)], check=True, text=True, capture_output=True)

    def decision_file(self, root: Path, **payload) -> Path:
        path = root / "reflection-decision.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def holdout_file(self, root: Path, rows: list[dict]) -> Path:
        path = root / "holdout.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def notes(self, root: Path) -> list[Path]:
        return sorted(path for path in self.user_dir(root).glob("*.md") if path.name != "INDEX.md")

    def semantic_notes(self, root: Path) -> list[Path]:
        notes = []
        for path in self.notes(root):
            text = path.read_text(encoding="utf-8")
            if "type: semantic" in text:
                notes.append(path)
        return notes

    def test_compacts_multiple_episodic_sources_into_cited_semantic_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            first = self.write_note(root, "lexical-a.md", title="Lexical recall worked in phase 03")
            second = self.write_note(root, "lexical-b.md", title="Lexical recall handled bookend context")
            original_bodies = {path.name: path.read_text(encoding="utf-8") for path in (first, second)}
            self.rebuild_index(root)
            decision = self.decision_file(
                root,
                id="reflect-lexical",
                action="ADD",
                title="Prefer lexical recall before embeddings",
                insight="Use lexical recall before adding embeddings (because of lexical-a) (because of lexical-b).",
                source_ids=["lexical-a", "lexical-b"],
                keywords=["lexical", "recall"],
            )

            result = self.run_cli(root, "--topic", "lexical recall", "--decision-file", str(decision))
            verify = subprocess.run(["python3", str(INDEX_SCRIPT), "--root", str(root), "--verify"], text=True, capture_output=True)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("write reflect-lexical", result.stdout)
            semantic = self.semantic_notes(root)
            self.assertEqual(len(semantic), 1)
            semantic_text = semantic[0].read_text(encoding="utf-8")
            # Provenance lives in `related`; inline citations are stripped from
            # the readable body.
            self.assertIn("related: [lexical-a, lexical-b]", semantic_text)
            self.assertNotIn("(because of", semantic_text)
            self.assertEqual(first.read_text(encoding="utf-8"), original_bodies["lexical-a.md"])
            self.assertEqual(second.read_text(encoding="utf-8"), original_bodies["lexical-b.md"])
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)

    def test_explicit_source_ids_select_active_semantic_atomic_notes(self) -> None:
        # The auto synthesize worker passes explicit source_ids for the atomic
        # notes it clustered. Those notes are type:semantic (consolidate output),
        # so explicit ids must be honored regardless of type — otherwise the
        # episodic-only filter would drop them and nothing would synthesize.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "atom-a.md", title="Signed URL fields break deep compare", note_type="semantic")
            self.write_note(root, "atom-b.md", title="Strip signed URLs before comparison", note_type="semantic")
            self.rebuild_index(root)
            decision = self.decision_file(
                root,
                id="reflect-signed-url",
                action="ADD",
                title="比较前剥离 signed URL 字段",
                insight="对象比较应忽略每次生成的 signed URL 字段 (because of atom-a) (because of atom-b)。",
                source_ids=["atom-a", "atom-b"],
            )

            result = self.run_cli(root, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(self.semantic_notes(root)), 3, "2 atomic sources + 1 synthesized")
            synth = next(p for p in self.semantic_notes(root) if "比较前剥离" in p.read_text(encoding="utf-8"))
            self.assertIn("related: [atom-a, atom-b]", synth.read_text(encoding="utf-8"))

    def test_one_source_skips_without_semantic_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "single.md", title="Single episodic note")
            self.rebuild_index(root)
            before_index = (root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8")
            decision = self.decision_file(
                root,
                id="single",
                action="ADD",
                title="Single should not promote",
                insight="Do not promote one source (because of single).",
                source_ids=["single"],
            )

            result = self.run_cli(root, "--topic", "single", "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("skip single below_threshold", result.stdout)
            self.assertEqual(self.semantic_notes(root), [])
            self.assertEqual((root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8"), before_index)

    def test_malformed_decisions_reject_before_write(self) -> None:
        cases = [
            ("missing-citation", {"insight": "This lacks citations.", "source_ids": ["a", "b"]}, "because-of"),
            ("unknown", {"insight": "Unknown source (because of a) (because of missing).", "source_ids": ["a", "missing"]}, "unknown_source"),
            ("one-cited", {"insight": "Only one source (because of a).", "source_ids": ["a"]}, "under_supported"),
        ]
        for name, overrides, reason in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "repo"
                self.write_note(root, "a.md", title="Alpha lexical note")
                self.write_note(root, "b.md", title="Beta lexical note")
                self.rebuild_index(root)
                before = {path.name: path.read_text(encoding="utf-8") for path in self.notes(root)}
                decision_payload = {"id": name, "action": "ADD", "title": name, "source_ids": ["a", "b"]}
                decision_payload.update(overrides)
                decision = self.decision_file(root, **decision_payload)

                result = self.run_cli(root, "--topic", "lexical", "--decision-file", str(decision))

                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(reason, result.stderr)
                self.assertEqual({path.name: path.read_text(encoding="utf-8") for path in self.notes(root)}, before)

    def test_unknown_stale_source_rejects_before_any_tracked_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "a.md", title="Alpha stale guard")
            self.write_note(root, "b.md", title="Beta stale guard")
            self.rebuild_index(root)
            before = {path.name: path.read_text(encoding="utf-8") for path in self.notes(root)}
            before_index = (root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8")
            decision = self.decision_file(
                root,
                id="bad-stale",
                action="ADD",
                title="Unknown stale source must fail closed",
                insight="Valid insight citations (because of a) (because of b).",
                source_ids=["a", "b"],
                stale_sources={"missing": "not selected"},
            )

            result = self.run_cli(root, "--topic", "stale guard", "--decision-file", str(decision))

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("unknown_source missing", result.stderr)
            self.assertEqual({path.name: path.read_text(encoding="utf-8") for path in self.notes(root)}, before)
            self.assertEqual((root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8"), before_index)

    def test_refutation_marks_source_stale_without_body_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            stale = self.write_note(root, "old.md", title="Old lexical belief", body="The old body must remain auditable.\n")
            self.write_note(root, "new.md", title="New lexical correction")
            self.rebuild_index(root)
            original_body = stale.read_text(encoding="utf-8").split("---\n\n", 1)[1]
            decision = self.decision_file(
                root,
                id="refute-old",
                action="ADD",
                title="Use corrected lexical rule",
                insight="Prefer the corrected lexical rule (because of old) (because of new).",
                source_ids=["old", "new"],
                stale_sources={"old": "refuted by newer evidence"},
            )

            result = self.run_cli(root, "--topic", "lexical", "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            updated = stale.read_text(encoding="utf-8")
            self.assertIn("status: stale", updated)
            self.assertIn("valid_to:", updated)
            self.assertIn("stale_reason: refuted by newer evidence", updated)
            self.assertEqual(updated.split("---\n\n", 1)[1], original_body)

    def test_char_budget_rejects_without_partial_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "a.md", title="Alpha budget note")
            self.write_note(root, "b.md", title="Beta budget note")
            self.rebuild_index(root)
            before = {path.name: path.read_text(encoding="utf-8") for path in self.notes(root)}
            before_index = (root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8")
            decision = self.decision_file(
                root,
                id="budget",
                action="ADD",
                title="Budget note",
                insight="This generated semantic reflection is too long (because of a) (because of b).",
                source_ids=["a", "b"],
            )

            note_result = self.run_cli(root, "--topic", "budget", "--decision-file", str(decision), "--max-note-chars", "80")
            index_result = self.run_cli(root, "--topic", "budget", "--decision-file", str(decision), "--max-index-chars", "80")

            for result in (note_result, index_result):
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("discard budget char_budget_exceeded", result.stdout + result.stderr)
            self.assertEqual({path.name: path.read_text(encoding="utf-8") for path in self.notes(root)}, before)
            self.assertEqual((root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8"), before_index)

    def test_preflight_secret_rejects_before_destination_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "a.md", title="Alpha secret guard")
            self.write_note(root, "b.md", title="Beta secret guard")
            self.rebuild_index(root)
            module = load_compact_memory_module()
            target = root / "memory" / "user" / "secret-reflection.md"
            secret_note = (
                "---\n"
                "title: Secret reflection\n"
                "date: 2026-06-23\n"
                "problem_type: knowledge\n"
                "type: semantic\n"
                "status: active\n"
                "keywords: [secret]\n"
                "origin_session: compact-memory:secret\n"
                "verify:\n"
                "---\n\n"
                "Insight: token ghp_abcdefghijklmnopqrstuvwxyz1234567890AB (because of a) (because of b).\n"
            )

            with mock.patch.object(Path, "write_text", wraps=Path.write_text) as write_text:
                with self.assertRaises(Exception):
                    module.preflight_budget(root, target, secret_note, 6000, 40000, "secret")

            self.assertFalse(target.exists())
            self.assertNotIn(target, [call.args[0] for call in write_text.call_args_list])

    def test_duplicate_semantic_decision_skips_observably(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "a.md", title="Alpha duplicate source")
            self.write_note(root, "b.md", title="Beta duplicate source")
            self.write_note(
                root,
                "existing.md",
                title="Prefer lexical recall before embeddings",
                note_type="semantic",
                keywords="lexical, recall",
                body="Use lexical recall before adding embeddings (because of a) (because of b).\n",
            )
            self.rebuild_index(root)
            decision = self.decision_file(
                root,
                id="dup",
                action="ADD",
                title="Prefer lexical recall before embeddings",
                insight="Use lexical recall before adding embeddings (because of a) (because of b).",
                source_ids=["a", "b"],
            )

            result = self.run_cli(root, "--topic", "lexical", "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("skip dup duplicate_semantic", result.stdout)
            self.assertEqual(len(self.semantic_notes(root)), 1)

    def test_lexical_holdout_sufficient_records_embedding_decision_without_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "alpha.md", title="Alpha lexical recall", keywords="alpha, recall")
            self.write_note(root, "beta.md", title="Beta lexical recall", keywords="beta, recall")
            self.rebuild_index(root)
            holdout = self.holdout_file(
                root,
                [
                    {"query": "alpha recall", "expected": "alpha"},
                    {"query": "beta recall", "expected": "beta"},
                ],
            )

            result = self.run_cli(root, "--evaluate-recall", "--holdout", str(holdout), "--top-k", "1", "--threshold", "1.0")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("embedding_decision lexical_sufficient", result.stdout)
            self.assertIn("hits=2 total=2 hit_rate=1.000 threshold=1.000 top_k=1", result.stdout)
            self.assertEqual(list((root / "memory" / ".local").glob("*.npy")), [])

    def test_lexical_holdout_insufficient_blocks_embedding_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(root, "alpha.md", title="Alpha lexical recall", keywords="alpha, recall")
            self.rebuild_index(root)
            holdout = self.holdout_file(root, [{"query": "missing", "expected": "alpha"}])

            result = self.run_cli(root, "--evaluate-recall", "--holdout", str(holdout), "--top-k", "1", "--threshold", "1.0")

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("embedding_decision embedding_required", result.stdout)
            self.assertEqual(list((root / "memory" / ".local").glob("*.npy")), [])

    def test_lexical_holdout_uses_index_scoring_not_body_only_hits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            self.write_note(
                root,
                "body-only.md",
                title="Unrelated frontmatter",
                keywords="unrelated",
                body="needle-only-token exists only in the body and not in INDEX-facing metadata.\n",
            )
            self.rebuild_index(root)
            holdout = self.holdout_file(root, [{"query": "needle-only-token", "expected": "body-only"}])

            result = self.run_cli(root, "--evaluate-recall", "--holdout", str(holdout), "--top-k", "1", "--threshold", "1.0")

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("embedding_decision embedding_required", result.stdout)

    def test_skill_documentation_contains_reflection_safety_contract(self) -> None:
        skill_text = SKILL.read_text(encoding="utf-8")
        for phrase in [
            "/compact-memory",
            "(because of <id>)",
            "<2",
            "dual-track",
            "stale",
            "char-budget rejection",
            "conditional embedding",
        ]:
            self.assertIn(phrase, skill_text)


if __name__ == "__main__":
    unittest.main()

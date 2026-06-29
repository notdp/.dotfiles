import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "coding-skills" / "assist-learn" / "scripts" / "assist_consolidate.py"
INDEX_SCRIPT = REPO_ROOT / "scripts" / "build_memory_index.py"


class AssistConsolidateTests(unittest.TestCase):
    def run_cli(
        self,
        root: Path,
        raw_dir: Path,
        *args: str,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--root", str(root), "--raw-dir", str(raw_dir), *args],
            text=True,
            capture_output=True,
            cwd=cwd,
        )

    def write_candidate(self, raw_dir: Path, name: str, **overrides) -> Path:
        raw_dir.mkdir(parents=True, exist_ok=True)
        candidate = {
            "id": name,
            "summary": "Prefer lexical memory recall",
            "evidence": "Phase 03 verified lexical recall without a vector database.",
            "implication": "Future agents should try lexical retrieval before adding embedding infra.",
            "category": "decision",
            "origin_session": "session-123",
            "why": "It keeps the MVP file-native and cheap.",
        }
        candidate.update(overrides)
        path = raw_dir / f"{name}.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        return path

    def write_decision(self, root: Path, **decision) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "decision.json"
        path.write_text(json.dumps(decision), encoding="utf-8")
        return path

    def write_decisions(self, root: Path, decisions: dict) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "decisions.json"
        path.write_text(json.dumps(decisions), encoding="utf-8")
        return path

    def write_existing_note(self, root: Path, name: str = "existing.md", *, status: str = "active") -> Path:
        user_dir = root / "memory" / "user"
        user_dir.mkdir(parents=True, exist_ok=True)
        path = user_dir / name
        path.write_text(
            "---\n"
            "title: Existing memory note\n"
            "date: 2026-06-23\n"
            "problem_type: decision\n"
            "type: semantic\n"
            f"status: {status}\n"
            "keywords: [memory, lexical]\n"
            "origin_session: old-session\n"
            "verify:\n"
            "---\n\n"
            "Existing body about lexical memory recall.\n",
            encoding="utf-8",
        )
        subprocess.run(["python3", str(INDEX_SCRIPT), "--root", str(root)], check=True, capture_output=True, text=True)
        return path

    def user_notes(self, root: Path) -> list[Path]:
        return sorted(path for path in (root / "memory" / "user").glob("*.md") if path.name != "INDEX.md")

    def test_chinese_summary_gets_short_readable_filename_not_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "zh", id="a" * 64, summary="弹层组件必须显式覆盖默认最大宽度否则被锁死", evidence="否则宽度被锁定不可调。", category="decision", why="覆盖默认宽度约束")
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 1)
            stem = notes[0].name.removesuffix(".md")
            import re as _re
            self.assertIsNone(_re.fullmatch(r"[0-9a-f]{32,}", stem), f"filename is a raw sha256: {stem}")
            self.assertLess(len(stem), 32, f"filename should be short/readable: {stem}")

    def test_gc_archived_notes_deletes_old_archived_keeps_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            old_archived = self.write_existing_note(root, "old-archived.md", status="archived")
            fresh_archived = self.write_existing_note(root, "fresh-archived.md", status="archived")
            active = self.write_existing_note(root, "active.md", status="active")
            old = time.time() - (91 * 24 * 60 * 60)  # >90d
            os.utime(old_archived, (old, old))
            os.utime(active, (old, old))  # active stays even when old

            result = self.run_cli(root, root, "--gc-archived-notes")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(old_archived.exists(), "old archived note hard-deleted")
            self.assertTrue(fresh_archived.exists(), "archived within TTL kept")
            self.assertTrue(active.exists(), "active notes are never deleted")
            index = (root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8")
            self.assertNotIn("old-archived.md", index, "INDEX rebuilt after delete")

    def test_secret_candidate_is_rejected_before_tracked_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "secret", evidence="The production token is ghp_abcdefghijklmnopqrstuvwxyz1234567890AB")

            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("redact", result.stderr.lower())
            self.assertEqual(self.user_notes(root), [])

    def test_blacklist_does_not_reject_normal_path_wording(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "path", summary="Prefer absolute path in config", evidence="The config used an absolute path safely.")
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(self.user_notes(root)), 1)

    def test_relative_raw_dir_is_resolved_against_root_from_other_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            raw_rel = Path("memory/.staging/raw_memories")
            outside_cwd = base / "outside-cwd"
            outside_cwd.mkdir()
            self.write_candidate(root / raw_rel, "cwd-case", summary="Root staging candidate is used")
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_rel, "--decision-file", str(decision), cwd=outside_cwd)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 1)
            self.assertIn("Root staging candidate is used", notes[0].read_text(encoding="utf-8"))
            outside_notes = sorted((outside_cwd / "memory" / "user").glob("*.md"))
            self.assertEqual(outside_notes, [])

    def test_invalidate_soft_marks_existing_note_without_naked_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            existing = self.write_existing_note(root)
            self.write_candidate(raw_dir, "invalidate", summary="Existing memory note")
            decision = self.write_decision(root, action="INVALIDATE", note_id="existing.md", reason="support file changed")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(existing.exists())
            text = existing.read_text(encoding="utf-8")
            self.assertIn("status: archived", text)
            self.assertIn("valid_to:", text)
            self.assertIn("invalid_at: support file changed", text)

    def test_blacklist_rejects_negative_tool_and_transient_environment_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "tool", summary="ripgrep cannot be used", implication="Avoid rg forever.")
            self.write_candidate(raw_dir, "env", summary="node command not found", evidence="node command not found during local setup")
            decision = self.write_decisions(root, {"tool": {"action": "ADD"}, "env": {"action": "ADD"}})

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("anti_self_poisoning", result.stdout)
            self.assertEqual(self.user_notes(root), [])

    def test_action_add_promotes_trial_knowledge_and_correction_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(
                raw_dir,
                "background-jobs",
                category="fact",
                summary="BACKGROUND_JOBS_ENABLED=false disables background jobs",
                evidence="Trial memory candidate recorded BACKGROUND_JOBS_ENABLED=false as an operator-relevant fact.",
                implication="When background processing appears inactive, check BACKGROUND_JOBS_ENABLED before debugging workers.",
                why="",
                user_marked=False,
                occurrences=1,
            )
            self.write_candidate(
                raw_dir,
                "dev-complete-required",
                category="correction",
                summary="Code changes must go through /dev-complete",
                evidence="Trial memory candidate recorded the user rule: 代码改动必须走 /dev-complete.",
                implication="For future code changes, choose /dev-complete unless the task is a pure bug fix or otherwise scoped out.",
                why="",
                user_marked=False,
                occurrences=1,
            )
            decision = self.write_decisions(
                root,
                {
                    "background-jobs": {"action": "ADD"},
                    "dev-complete-required": {"action": "ADD"},
                },
            )

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("write background-jobs", result.stdout)
            self.assertIn("write dev-complete-required", result.stdout)
            self.assertNotIn("not_promoted", result.stdout)
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 2)
            note_text = "\n".join(path.read_text(encoding="utf-8") for path in notes)
            self.assertIn("BACKGROUND_JOBS_ENABLED=false", note_text)
            self.assertIn("代码改动必须走 /dev-complete", note_text)

    def test_action_add_promotes_complete_candidate_without_explicit_why(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "decision", why="", user_marked=False, occurrences=1)
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("write decision", result.stdout)
            self.assertEqual(len(self.user_notes(root)), 1)

    def test_non_decision_update_is_not_blocked_by_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            existing = self.write_existing_note(root)
            self.write_candidate(
                raw_dir,
                "replacement",
                category="correction",
                summary="Replacement correction note",
                evidence="The previous note used stale recall guidance.",
                implication="Use the corrected recall guidance for future consolidation updates.",
                why="",
                user_marked=False,
                occurrences=1,
            )
            decision = self.write_decision(root, action="UPDATE", note_id="existing.md")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("update replacement existing.md -> memory/user/", result.stdout)
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 2)
            replacement = next(path for path in notes if path.name != "existing.md")
            self.assertIn("Replacement correction note", replacement.read_text(encoding="utf-8"))
            old_text = existing.read_text(encoding="utf-8")
            self.assertIn("status: archived", old_text)
            self.assertIn(f"superseded_by: {replacement.name}", old_text)

    def test_one_time_narration_is_not_promoted_by_llm_add(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(
                raw_dir,
                "one-time",
                category="fact",
                summary="This session resolved a one-time migration checklist",
                evidence="This session only needed a temporary todo for the migration dry run.",
                implication="Remember this session outcome as a one-time task narration.",
                why="",
                user_marked=False,
                occurrences=1,
            )
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("anti_self_poisoning:one_time_task_narration", result.stdout)
            self.assertEqual(self.user_notes(root), [])

    def test_missing_core_fields_are_rejected_despite_llm_add(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "missing.json").write_text(
                json.dumps(
                    {
                        "id": "missing",
                        "summary": "Missing core implication",
                        "evidence": "The candidate has evidence but no reusable implication.",
                        "category": "fact",
                        "origin_session": "session-123",
                    }
                ),
                encoding="utf-8",
            )
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("missing required field implication", result.stderr)
            self.assertEqual(self.user_notes(root), [])

    def test_decision_file_is_required_for_consolidation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "requires-decision")

            result = self.run_cli(root, raw_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("decision-file", result.stderr)

    def test_per_candidate_decisions_are_applied_by_candidate_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "add-one", summary="Add this memory")
            self.write_candidate(raw_dir, "skip-one", summary="Skip this memory")
            decisions = self.write_decisions(root, {"add-one": {"action": "ADD"}, "skip-one": {"action": "SKIP", "reason": "fixture"}})

            result = self.run_cli(root, raw_dir, "--decision-file", str(decisions))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 1)
            self.assertIn("Add this memory", notes[0].read_text(encoding="utf-8"))
            self.assertIn("decision_skip", result.stdout)

    def test_missing_update_target_falls_back_to_add(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "fallback", summary="Fallback update creates add")
            decision = self.write_decision(root, action="UPDATE", note_id="missing.md")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 1)
            self.assertIn("Fallback update creates add", notes[0].read_text(encoding="utf-8"))
            self.assertIn("fallback_add", result.stdout)

    def test_existing_update_archives_old_and_writes_replacement_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            existing = self.write_existing_note(root)
            self.write_candidate(raw_dir, "replacement", summary="Replacement memory note", evidence="New evidence replaces the old note.")
            decision = self.write_decision(root, action="UPDATE", note_id="existing.md")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 2)
            replacement = next(path for path in notes if path.name != "existing.md")
            replacement_text = replacement.read_text(encoding="utf-8")
            old_text = existing.read_text(encoding="utf-8")
            self.assertIn("New evidence replaces the old note", replacement_text)
            self.assertIn("status: archived", old_text)
            self.assertIn(f"superseded_by: {replacement.name}", old_text)

    def test_project_repo_nature_gate_requires_approval_for_cross_project_client_or_oss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "client", scope="project", repo_nature="client", cross_project=True)
            decision = self.write_decision(root, action="ADD")

            rejected = self.run_cli(root, raw_dir, "--decision-file", str(decision), "--store", "project", "--repo-nature", "client")
            approved = self.run_cli(root, raw_dir, "--decision-file", str(decision), "--store", "project", "--repo-nature", "client", "--approve-cross-project")

            self.assertEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
            self.assertIn("repo_nature_gate", rejected.stdout)
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
            learning_notes = sorted((root / "docs" / "learnings").rglob("*.md"))
            self.assertEqual(len(learning_notes), 1)

    def test_project_repo_nature_cli_argument_is_authoritative_over_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "client", scope="project", repo_nature="internal", cross_project=True)
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision), "--store", "project", "--repo-nature", "client")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("repo_nature_gate", result.stdout)
            self.assertEqual(sorted((root / "docs" / "learnings").rglob("*.md")), [])

    def test_user_memory_write_rebuilds_index_consistently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "index", summary="INDEX tracks generated notes", keywords=["memory", "index"])
            decision = self.write_decision(root, action="ADD")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision))
            verify = subprocess.run(["python3", str(INDEX_SCRIPT), "--root", str(root), "--verify"], text=True, capture_output=True)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            index = (root / "memory" / "user" / "INDEX.md").read_text(encoding="utf-8")
            self.assertIn("INDEX tracks generated notes", index)

    def test_secret_candidate_does_not_abort_later_safe_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_candidate(raw_dir, "bad", evidence="The production token is ghp_abcdefghijklmnopqrstuvwxyz1234567890AB")
            self.write_candidate(raw_dir, "good", summary="Safe memory candidate")
            decisions = self.write_decisions(root, {"bad": {"action": "ADD"}, "good": {"action": "ADD"}})

            result = self.run_cli(root, raw_dir, "--decision-file", str(decisions))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("redact", result.stderr.lower())
            notes = self.user_notes(root)
            self.assertEqual(len(notes), 1)
            self.assertIn("Safe memory candidate", notes[0].read_text(encoding="utf-8"))

    def test_verify_assertion_failure_marks_note_invalid_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            existing = self.write_existing_note(root)
            text = existing.read_text(encoding="utf-8").replace("verify:\n", "verify: missing-file.txt\n")
            existing.write_text(text, encoding="utf-8")

            result = self.run_cli(root, raw_dir, "--invalidate-failed-verify")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            updated = existing.read_text(encoding="utf-8")
            self.assertIn("status: archived", updated)
            self.assertIn("invalid_at: verify-failed", updated)

    def test_related_lookup_ranks_active_notes_and_excludes_inactive_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            raw_dir = Path(tmp) / "raw"
            self.write_existing_note(root, "active.md", status="active")
            self.write_existing_note(root, "old.md", status="superseded")
            self.write_candidate(raw_dir, "related", summary="lexical memory recall decision")
            decision = self.write_decision(root, action="SKIP", reason="fixture only")

            result = self.run_cli(root, raw_dir, "--decision-file", str(decision), "--emit-decision-context")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("active.md", result.stdout)
            self.assertNotIn("old.md", result.stdout)

    def test_skill_documentation_contains_consolidation_safety_contract(self) -> None:
        skill_text = (REPO_ROOT / "coding-skills" / "assist-learn" / "SKILL.md").read_text(encoding="utf-8")
        for phrase in [
            "/assist-consolidate",
            "fail-closed redact",
            "禁止裸物理 DELETE",
            "promote 判据",
            "机械候选是不可信输入",
        ]:
            self.assertIn(phrase, skill_text)


class FrontmatterYamlSafetyTests(unittest.TestCase):
    """A title containing ':' '#' or '"' must not break strict YAML parsers
    (agentsview's syncer used yaml.Unmarshal and silently dropped such notes)."""

    def _load_module(self):
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("assist_consolidate_mod", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod  # required so @dataclass can resolve __module__
        spec.loader.exec_module(mod)
        return mod

    def test_frontmatter_value_emits_quoted_escaped_scalar(self) -> None:
        mod = self._load_module()
        out = mod.frontmatter_value('decision: # Cap "x"\nsecond line')
        # double-quoted, internal quotes escaped, newline flattened
        self.assertTrue(out.startswith('"') and out.endswith('"'), out)
        self.assertIn('\\"', out)
        self.assertNotIn("\n", out)

    def test_rendered_user_note_frontmatter_parses_as_yaml(self) -> None:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError:
            self.skipTest("pyyaml not available; string-form asserted elsewhere")
        mod = self._load_module()
        cand = mod.Candidate(
            id="c1",
            summary='decision: # Scope Alignment Capsule: add or refactor "stuff"',
            evidence="e",
            implication="i",
            problem_type="decision",
            origin_session="ses_1",
            raw={"applies_to": "user"},
        )
        text = mod.render_user_note(cand)
        block = text.split("---")[1]
        data = yaml.safe_load(block)  # must not raise
        self.assertEqual(data["title"], cand.summary.replace("\n", " "))
        self.assertEqual(data["problem_type"], "decision")

    def test_rendered_user_note_carries_project_dimension_from_candidate(self) -> None:
        mod = self._load_module()
        cand = mod.Candidate(
            id="c1",
            summary="some project-specific lesson",
            evidence="e",
            implication="i",
            problem_type="knowledge",
            origin_session="ses_1",
            raw={"origin_project": "oss-atlas", "scope": "project"},
        )
        text = mod.render_user_note(cand)
        self.assertIn('origin_project: "oss-atlas"', text)
        self.assertIn('scope: "project"', text)

    def test_rendered_user_note_defaults_project_dimension_to_general_user(self) -> None:
        mod = self._load_module()
        cand = mod.Candidate(
            id="c2",
            summary="some general lesson",
            evidence="e",
            implication="i",
            problem_type="knowledge",
            origin_session="ses_2",
            raw={},
        )
        text = mod.render_user_note(cand)
        # Empty origin_project = the General bucket; scope falls back to user.
        self.assertIn('origin_project: ""', text)
        self.assertIn('scope: "user"', text)


if __name__ == "__main__":
    unittest.main()

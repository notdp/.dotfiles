import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "skill_maintenance_collect.py"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify_skills.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import skill_maintenance_collect


class SkillMaintenanceCollectTests(unittest.TestCase):
    def run_collect(self, *args: str, cwd: Path | None = None, env: dict[str, str] | None = None):
        return subprocess.run(
            ["python3", str(SCRIPT), *args],
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            env={**os.environ, **(env or {})},
        )

    def test_outputs_json_skeleton_without_writing_repo_files(self) -> None:
        before = {path.relative_to(REPO_ROOT).as_posix() for path in REPO_ROOT.glob("docs/skill-maintenance-runs/**/*") if path.exists()}

        result = self.run_collect("--repo", str(REPO_ROOT), "--format", "json", "--no-fetch")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            set(payload),
            {"preflight", "inventory", "refs", "sessions", "hook_signals", "deterministic_findings", "review"},
        )
        self.assertEqual(payload["review"]["status"], "model-dispatch-unavailable")
        after = {path.relative_to(REPO_ROOT).as_posix() for path in REPO_ROOT.glob("docs/skill-maintenance-runs/**/*") if path.exists()}
        self.assertEqual(after, before)

    def test_inventory_exposes_cross_agent_asset_map(self) -> None:
        payload = skill_maintenance_collect.inventory(REPO_ROOT)

        assets = payload["assets"]
        self.assertGreaterEqual(assets["skills"]["count"], 1)
        self.assertIn("coding-skills/guard-review/SKILL.md", assets["skills"]["paths"])
        self.assertGreaterEqual(assets["coding_agents"]["count"], 1)
        self.assertIn("claude", assets["coding_agents"]["by_runtime"])
        self.assertIn("opencode", assets["coding_agents"]["by_runtime"])
        self.assertGreaterEqual(assets["hooks"]["count"], 1)
        self.assertGreaterEqual(assets["refs_details"]["count"], 1)
        self.assertGreaterEqual(assets["distribution_links"]["count"], 1)
        self.assertIn("claude", assets["distribution_links"]["targets"])

    def test_session_sampling_reads_real_io_but_excludes_raw_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            session_dir = skill_maintenance_collect.encoded_repo_session_dir(REPO_ROOT, home)
            session_dir.mkdir(parents=True)
            for index in range(5):
                session = session_dir / f"session-{index}.jsonl"
                session.write_text(
                    "\n".join(
                        [
                            json.dumps({"sessionTitle": f"Task {index}", "cwd": str(REPO_ROOT), "id": f"session-{index}"}),
                            json.dumps({"message": {"role": "user", "content": [{"type": "text", "text": "token sk-secret private https://example.com/private"}]}}),
                            json.dumps({"message": {"role": "assistant", "content": [{"type": "tool_use", "name": "bash", "input": {"command": "rm -rf /tmp/safe"}}]}}),
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            result = self.run_collect("--repo", str(REPO_ROOT), "--format", "json", "--no-fetch", env={"HOME": str(home)})

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = result.stdout
        self.assertNotIn("sk-secret", rendered)
        self.assertNotIn("https://example.com/private", rendered)
        payload = json.loads(rendered)
        self.assertGreaterEqual(len(payload["sessions"]), 3)
        self.assertLessEqual(len(payload["sessions"]), 5)
        for session in payload["sessions"]:
            self.assertIn("tool_counts", session)
            self.assertNotIn("raw_text", session)
            self.assertTrue(session["sensitive_content_present"])

    def test_refs_default_skips_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            work = root / "work"
            repo = root / "repo"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, text=True, capture_output=True)
            subprocess.run(["git", "clone", str(remote), str(work)], check=True, text=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=work, check=True)
            (work / "README.md").write_text("v1\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=work, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=work, check=True, text=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work, check=True, text=True, capture_output=True)
            subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=remote, check=True, text=True, capture_output=True)

            subprocess.run(["git", "init", str(repo)], check=True, text=True, capture_output=True)
            subprocess.run(["git", "-c", "protocol.file.allow=always", "submodule", "add", str(remote), "refs/example/repo"], cwd=repo, check=True, text=True, capture_output=True)
            subprocess.run(["git", "add", ".gitmodules", "refs/example/repo"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "add ref"], cwd=repo, check=True, text=True, capture_output=True)

            (work / "README.md").write_text("v2\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "feature update"], cwd=work, check=True, text=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work, check=True, text=True, capture_output=True)

            result = self.run_collect("--repo", str(repo), "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refs"][0]["path"], "refs/example/repo")
        self.assertEqual(payload["refs"][0]["fetch"], "skipped")

    def test_refs_fetch_analyzes_remote_without_updating_submodule_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            work = root / "work"
            repo = root / "repo"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, text=True, capture_output=True)
            subprocess.run(["git", "clone", str(remote), str(work)], check=True, text=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=work, check=True)
            (work / "README.md").write_text("v1\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=work, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=work, check=True, text=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work, check=True, text=True, capture_output=True)
            subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=remote, check=True, text=True, capture_output=True)

            subprocess.run(["git", "init", str(repo)], check=True, text=True, capture_output=True)
            subprocess.run(["git", "-c", "protocol.file.allow=always", "submodule", "add", str(remote), "refs/example/repo"], cwd=repo, check=True, text=True, capture_output=True)
            subprocess.run(["git", "add", ".gitmodules", "refs/example/repo"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "add ref"], cwd=repo, check=True, text=True, capture_output=True)
            old_pointer = subprocess.run(["git", "rev-parse", "HEAD:refs/example/repo"], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()

            (work / "README.md").write_text("v2\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "feature update"], cwd=work, check=True, text=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work, check=True, text=True, capture_output=True)

            result = self.run_collect("--repo", str(repo), "--format", "json", "--fetch")
            after_pointer = subprocess.run(["git", "rev-parse", "HEAD:refs/example/repo"], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(after_pointer, old_pointer)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refs"][0]["path"], "refs/example/repo")
        self.assertEqual(payload["refs"][0]["fetch"], "ok")
        self.assertNotEqual(payload["refs"][0]["old"], payload["refs"][0]["remote"])

    def test_multiple_high_risk_capabilities_are_should_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "coding-skills" / "guard-demo"
            skill_dir.mkdir(parents=True)
            scripts_dir = repo / "scripts"
            scripts_dir.mkdir()
            (repo / "coding-skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "guard-demo",
                                "path": "coding-skills/guard-demo",
                                "domain": "guard",
                                "role": "canonical",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: guard-demo\n"
                "description: 当测试高风险能力时使用；demo\n"
                "---\n"
                "# Demo\n\n"
                "Risk guardrails: route through /guard-secure before use.\n"
                "Read API keys from env vars and call a REST API.\n",
                encoding="utf-8",
            )
            (scripts_dir / "verify_skills.py").write_text(
                "#!/usr/bin/env python3\n"
                "print('RISK WARNING: guard-demo declares high-risk capability categories: secrets, network')\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init", str(repo)], check=True, text=True, capture_output=True)

            result = self.run_collect("--repo", str(repo), "--format", "json", "--no-fetch")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        risk_findings = [
            finding
            for finding in payload["deterministic_findings"]
            if finding["id"] == "skill-risk-warning"
        ]
        self.assertEqual(len(risk_findings), 1)
        self.assertEqual(risk_findings[0]["severity"], "should")

    def test_verify_summary_lines_enter_deterministic_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            scripts_dir = repo / "scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "verify_skills.py").write_text(
                "#!/usr/bin/env python3\n"
                "print('validated 10 skill routing cases')\n"
                "print('validated agent assets: agents=2 commands=5 plugin_manifests=0 hooks=3 ref_details=4 distribution_links=14')\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init", str(repo)], check=True, text=True, capture_output=True)

            findings = skill_maintenance_collect.verify_skills(repo)

        ids = {finding["id"] for finding in findings}
        self.assertIn("skill-routing-cases-validated", ids)
        self.assertIn("agent-assets-validated", ids)
        asset_finding = next(finding for finding in findings if finding["id"] == "agent-assets-validated")
        self.assertIn("hooks=3", asset_finding["evidence"])
        self.assertIn("distribution_links=14", asset_finding["evidence"])

    def test_refs_fetch_timeout_is_reported_without_stopping_collection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            ref = repo / "refs" / "example" / "repo"
            ref.mkdir(parents=True)
            (ref / ".git").mkdir()
            (repo / ".gitmodules").write_text(
                '[submodule "refs/example/repo"]\n'
                "\tpath = refs/example/repo\n"
                "\turl = https://example.invalid/repo.git\n",
                encoding="utf-8",
            )

            def fake_run_git(path: Path, args: list[str], timeout: int = 30):
                if args == ["rev-parse", "HEAD"]:
                    return 0, "local-head", ""
                if args == ["fetch", "--all", "--tags", "--prune"]:
                    raise subprocess.TimeoutExpired(["git", *args], timeout)
                if args == ["rev-parse", "origin/HEAD"]:
                    return 1, "", "missing"
                if args == ["rev-parse", "origin/main"]:
                    return 0, "remote-head", ""
                return 1, "", "unexpected"

            with patch.object(skill_maintenance_collect, "run_git", side_effect=fake_run_git):
                refs = skill_maintenance_collect.refs_summary(repo, fetch=True)

        self.assertEqual(refs[0]["path"], "refs/example/repo")
        self.assertEqual(refs[0]["old"], "local-head")
        self.assertEqual(refs[0]["remote"], "remote-head")
        self.assertEqual(refs[0]["fetch"], "failed: timeout after 120s")

    def test_refs_metadata_mismatch_enters_deterministic_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", str(repo)], check=True, text=True, capture_output=True)
            (repo / ".gitmodules").write_text(
                '[submodule "refs/example/repo"]\n'
                "\tpath = refs/example/repo\n"
                "\turl = https://example.invalid/repo.git\n",
                encoding="utf-8",
            )

            payload = skill_maintenance_collect.collect(repo, fetch=False, home=Path(tmp))

        findings = [finding for finding in payload["deterministic_findings"] if finding["id"] == "refs-metadata-warning"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "should")
        self.assertIn("refs/example/repo", findings[0]["evidence"])

    def test_refs_metadata_validated_finding_reports_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            ref = repo / "refs" / "example" / "repo"
            ref.mkdir(parents=True)
            (repo / ".gitmodules").write_text(
                '[submodule "refs/example/repo"]\n'
                "\tpath = refs/example/repo\n"
                "\turl = https://example.invalid/repo.git\n",
                encoding="utf-8",
            )
            refs = [{"path": "refs/example/repo", "old": "local-head", "remote": "remote-head", "fetch": "skipped"}]

            findings = skill_maintenance_collect.refs_metadata_findings(repo, refs)

        self.assertEqual(findings[0]["id"], "refs-metadata-validated")
        self.assertEqual(findings[0]["severity"], "observe")
        self.assertIn("refs=1", findings[0]["evidence"])


if __name__ == "__main__":
    unittest.main()

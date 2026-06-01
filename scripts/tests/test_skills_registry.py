import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "skills" / "catalog.json"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify_skills.py"


class SkillsRegistryTests(unittest.TestCase):
    RENAMED_LEGACY_NAMES = {
        "frontend-design",
        "ui-design",
        "eng-architecture",
        "eng-check",
        "eng-close",
        "eng-debug",
        "eng-learn",
        "eng-map",
        "eng-plan",
        "eng-quality",
        "eng-readable-metrics",
        "eng-refactor",
        "eng-research",
        "eng-review",
        "eng-secure",
        "eng-ship",
        "eng-tdd",
        "eng-unstuck",
        "eng-verify",
        "se-rewrite-readable",
        "se-research",
        "se-plan",
        "se-tdd",
        "se-unstuck",
        "tuistory",
    }

    CANONICAL_NAMES = {
        "assist-learn",
        "dev-debug",
        "dev-refactor",
        "dev-tdd",
        "fe-ui-design",
        "guard-check",
        "guard-close",
        "guard-review",
        "guard-secure",
        "guard-ship",
        "guard-verify",
        "readable-final-answer",
        "readable-metrics",
        "think-architecture",
        "think-map",
        "think-plan",
        "think-quality",
        "think-research",
        "think-unstuck",
    }

    def test_catalog_exists_and_declares_phase1_skills(self) -> None:
        self.assertTrue(CATALOG.exists(), "skills/catalog.json should exist")
        catalog = json.loads(CATALOG.read_text())
        names = {entry["name"] for entry in catalog["skills"]}
        self.assertIn("web-read", names)
        self.assertIn("agent-health", names)
        self.assertIn("guard-check", names)
        self.assertIn("fe-ui-design", names)
        self.assertIn("assist-learn", names)
        self.assertIn("readable-metrics", names)
        self.assertIn("readable-final-answer", names)

    def test_catalog_paths_do_not_escape_repo(self) -> None:
        catalog = json.loads(CATALOG.read_text())
        for entry in catalog["skills"]:
            path = REPO_ROOT / entry["path"]
            self.assertFalse(
                path.is_symlink() and not path.resolve().is_relative_to(REPO_ROOT),
                f"{entry['name']} path should not symlink outside the repo: {entry['path']}",
            )

    def test_catalog_keeps_latest_names_only_for_renamed_skills(self) -> None:
        catalog = json.loads(CATALOG.read_text())
        names = {entry["name"] for entry in catalog["skills"]}
        self.assertTrue(self.CANONICAL_NAMES.issubset(names))
        self.assertTrue(self.RENAMED_LEGACY_NAMES.isdisjoint(names))
        self.assertFalse((REPO_ROOT / "skills" / "frontend-design").exists())
        self.assertFalse((REPO_ROOT / "skills" / "eng-plan").exists())
        self.assertFalse((REPO_ROOT / "skills" / "eng-review").exists())
        self.assertFalse((REPO_ROOT / "skills" / "ui-design").exists())

    def test_verify_script_exists_and_repo_passes(self) -> None:
        self.assertTrue(VERIFY_SCRIPT.exists(), "scripts/verify_skills.py should exist")
        result = subprocess.run(
            ["python3", str(VERIFY_SCRIPT)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_verify_script_reports_broken_skill_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "web-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "web-demo",
                                "path": "skills/web-demo",
                                "domain": "web",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: web-demo\ndescription: 当测试时使用；demo\n---\nSee references/missing.md\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("BROKEN REFERENCE", result.stderr)

    def test_verify_script_reports_unknown_future_canonical_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "legacy-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "legacy-demo",
                                "path": "skills/legacy-demo",
                                "domain": "think",
                                "role": "legacy",
                                "migration": {
                                    "state": "planned",
                                    "canonical": "think-demo",
                                },
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: legacy-demo\ndescription: 当测试时使用；demo\n---\n# demo\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("UNKNOWN FUTURE CANONICAL", result.stderr)

    def test_verify_script_reports_description_trigger_prefix_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 用户要求 demo 时使用\n---\n# demo\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("DESCRIPTION TRIGGER PREFIX VIOLATION", result.stderr)

    def test_verify_script_accepts_trigger_exempt_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "dev-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "dev-demo",
                                "path": "skills/dev-demo",
                                "domain": "dev",
                                "role": "canonical",
                                "trigger-exempt": True,
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\ndescription: Run after a demo\n---\n# demo\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_verify_script_reports_routing_cases_summary(self) -> None:
        result = subprocess.run(
            ["python3", str(VERIFY_SCRIPT)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("validated 10 skill routing cases", result.stdout)

    def test_verify_script_rejects_unknown_routing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "dev-demo"
            fixture_dir = repo / "scripts" / "fixtures"
            skill_dir.mkdir(parents=True)
            fixture_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "dev-demo",
                                "path": "skills/dev-demo",
                                "domain": "dev",
                                "role": "canonical",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\ndescription: 当测试 routing 时使用；demo\n---\n# demo\n",
                encoding="utf-8",
            )
            (fixture_dir / "skill_routing_cases.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "bad-skill",
                            "input": "修 bug",
                            "expected_skills": ["dev-missing"],
                            "reject_skills": [],
                            "match_terms": ["bug"],
                            "why": "demo",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("UNKNOWN ROUTING SKILL", result.stderr)

    def test_verify_script_requires_reject_skill_boundary_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            dev_dir = repo / "skills" / "dev-demo"
            think_dir = repo / "skills" / "think-demo"
            fixture_dir = repo / "scripts" / "fixtures"
            dev_dir.mkdir(parents=True)
            think_dir.mkdir(parents=True)
            fixture_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {"name": "dev-demo", "path": "skills/dev-demo", "domain": "dev", "role": "canonical"},
                            {"name": "think-demo", "path": "skills/think-demo", "domain": "think", "role": "canonical"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            # dev-demo body never mentions the rejected sibling think-demo
            (dev_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\ndescription: 当修 bug 时使用；demo\n---\n# demo\n修 bug。\n",
                encoding="utf-8",
            )
            (think_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当规划时使用；demo\n---\n# demo\n",
                encoding="utf-8",
            )
            (fixture_dir / "skill_routing_cases.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "missing-boundary",
                            "input": "修 bug",
                            "expected_skills": ["dev-demo"],
                            "reject_skills": ["think-demo"],
                            "match_terms": ["bug"],
                            "why": "demo",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("REJECT BOUNDARY", result.stderr)

    def test_verify_script_reports_agent_asset_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "dev-demo"
            agent_dir = repo / ".kilo" / "agent"
            skill_dir.mkdir(parents=True)
            agent_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "dev-demo",
                                "path": "skills/dev-demo",
                                "domain": "dev",
                                "role": "canonical",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\ndescription: 当测试 asset 时使用；demo\n---\n# demo\n",
                encoding="utf-8",
            )
            (agent_dir / "broken.md").write_text(
                "---\ndescription: Missing permission\nmode: subagent\nmodel: test\n---\n# Broken\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("AGENT ASSET MISSING FIELD", result.stderr)

    def test_verify_script_reports_asset_summary(self) -> None:
        result = subprocess.run(
            ["python3", str(VERIFY_SCRIPT)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("validated agent assets:", result.stdout)

    def test_verify_script_reports_non_executable_repo_root_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "guard-demo"
            skill_dir.mkdir(parents=True)
            scripts_dir = repo / "scripts"
            scripts_dir.mkdir(parents=True)
            script_file = scripts_dir / "do-thing.sh"
            script_file.write_text("#!/usr/bin/env bash\necho hi\n")
            # 显式去掉执行位
            script_file.chmod(0o644)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "guard-demo",
                                "path": "skills/guard-demo",
                                "domain": "guard",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: guard-demo\ndescription: 当测试时使用；demo\n---\nRun `scripts/do-thing.sh`\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SCRIPT NOT EXECUTABLE", result.stderr)

    def test_verify_script_reports_long_workflow_without_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            body = "\n".join(f"- Step {index}" for index in range(90))
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n# Demo\n\n"
                + body
                + "\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("WORKFLOW QUALITY VIOLATION", result.stderr)

    def test_verify_script_reports_methodology_table_without_why(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n"
                "## 方法论切换\n\n"
                "| 方法论 | 核心动作 | 适用场景 |\n"
                "|---|---|---|\n"
                "| RCA | 逐层追问 | Debug |\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("METHODOLOGY WHY VIOLATION", result.stderr)

    def test_verify_script_accepts_methodology_table_with_why_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n"
                "## 方法论切换\n\n"
                "| 方法论 | 核心动作 | 为什么 / 防什么偏差 |\n"
                "|---|---|---|\n"
                "| RCA | 逐层追问 | 避免停在表层症状 |\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_verify_script_accepts_methodology_nearby_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n"
                "## 方法论切换\n\n"
                "为什么要做：方法论切换用于避免 agent 原地重复同一种错误路径。\n\n"
                "| 方法论 | 核心动作 | 适用场景 |\n"
                "|---|---|---|\n"
                "| RCA | 逐层追问 | Debug |\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_verify_script_reports_model_heading_without_why(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n"
                "## 评估模型\n\n"
                "- Predictable: stable patterns\n"
                "- Explicit: visible rules\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("METHODOLOGY WHY VIOLATION", result.stderr)

    def test_verify_script_reports_core_loop_without_why(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "dev-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "dev-demo",
                                "path": "skills/dev-demo",
                                "domain": "dev",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\ndescription: 当测试时使用；demo\n---\n"
                "## 核心循环\n\n"
                "1. RED\n"
                "2. GREEN\n"
                "3. REFACTOR\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("METHODOLOGY WHY VIOLATION", result.stderr)

    def test_verify_script_ignores_output_format_tables_without_why(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n"
                "## 输出格式\n\n"
                "| File | Issue | Fix |\n"
                "|---|---|---|\n"
                "| demo.py | missing check | add check |\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_verify_script_reports_unknown_skill_boundary_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "guard-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "guard-demo",
                                "path": "skills/guard-demo",
                                "domain": "guard",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: guard-demo\n"
                "description: 当测试时使用；demo（与 think-missing 区别：只做 demo）。\n"
                "---\n# Demo\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("UNKNOWN SKILL BOUNDARY", result.stderr)

    def test_verify_script_warns_about_high_risk_skill_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "dev-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "dev-demo",
                                "path": "skills/dev-demo",
                                "domain": "dev",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\n"
                "description: 当复杂数据任务触及外部 API 和 secrets 时使用；demo\n"
                "---\n"
                "# Demo\n\n"
                "Read API keys from env vars, call a REST API, and write database migration results.\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("RISK WARNING: dev-demo", result.stdout)
            self.assertIn("secrets", result.stdout)
            self.assertIn("network", result.stdout)
            self.assertIn("data-side-effects", result.stdout)

    def test_verify_script_warns_when_high_risk_skill_lacks_guardrails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "guard-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "guard-demo",
                                "path": "skills/guard-demo",
                                "domain": "guard",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: guard-demo\n"
                "description: 当需要执行外部目标安全扫描和 exploit 验证时使用；demo\n"
                "---\n"
                "# Demo\n\n"
                "Run an exploit against an external target and collect credentials.\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("RISK WARNING: guard-demo", result.stdout)
            self.assertIn("offensive-dual-use", result.stdout)
            self.assertIn("GUARDRAIL WARNING: guard-demo", result.stdout)
            self.assertIn("/guard-secure", result.stdout)

    def test_verify_script_warns_vague_conditional_without_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n# Demo\n\n必要时引用相关资料\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("VAGUE CONDITIONAL WARNING", result.stdout)

    def test_verify_script_accepts_vague_conditional_with_concrete_condition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "think-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "think-demo",
                                "path": "skills/think-demo",
                                "domain": "think",
                                "role": "canonical",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: think-demo\ndescription: 当测试时使用；demo\n---\n# Demo\n\n必要时引用 /think-quality\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertNotIn("VAGUE CONDITIONAL WARNING", result.stdout)

    def test_verify_script_warns_deprecated_concept_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "dev-demo"
            fixture_dir = repo / "scripts" / "fixtures"
            skill_dir.mkdir(parents=True)
            fixture_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "dev-demo",
                                "path": "skills/dev-demo",
                                "domain": "dev",
                                "role": "canonical",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\ndescription: 当测试时使用；demo\n---\n# demo\n\nSee eng-plan for details.\n",
                encoding="utf-8",
            )
            (fixture_dir / "deprecated-concepts.json").write_text(
                json.dumps(
                    [
                        {
                            "concept": "eng-plan",
                            "type": "skill",
                            "replacement": "think-plan",
                            "scan_pattern": "eng-plan",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("DEPRECATED CONCEPT WARNING", result.stdout)

    def test_verify_script_skips_when_no_deprecated_concepts_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "dev-demo"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "dev-demo",
                                "path": "skills/dev-demo",
                                "domain": "dev",
                                "role": "canonical",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: dev-demo\ndescription: 当测试时使用；demo\n---\n# demo\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertNotIn("DEPRECATED CONCEPT", result.stdout)

    def test_verify_script_accepts_brand_exception_without_trigger_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            skill_dir = repo / "skills" / "hive"
            skill_dir.mkdir(parents=True)
            (repo / "skills" / "catalog.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "name": "hive",
                                "path": "skills/hive",
                                "domain": "team",
                                "role": "brand-exception",
                            }
                        ]
                    }
                )
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nname: hive\ndescription: Hive 基础 skill，无固定触发前缀\n---\n# hive\n"
            )

            result = subprocess.run(
                ["python3", str(VERIFY_SCRIPT), str(repo)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY = REPO_ROOT / "writing-hooks" / "verify_writing.py"


def write_skill(repo: Path, rel: str, name: str, description: str) -> None:
    d = repo / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n", encoding="utf-8")


def write_catalog(repo: Path, skills: list[dict]) -> None:
    (repo / "writing-skills").mkdir(parents=True, exist_ok=True)
    (repo / "writing-skills" / "catalog.json").write_text(json.dumps({"skills": skills}, ensure_ascii=False), encoding="utf-8")


def run(repo: Path):
    return subprocess.run(["python3", str(VERIFY), str(repo)], text=True, capture_output=True)


class VerifyWritingTests(unittest.TestCase):
    def test_real_repo_catalog_passes(self) -> None:
        # 真实仓库 catalog 必须自洽（authoring 完成后应恒绿）
        result = subprocess.run(["python3", str(VERIFY)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_valid_minimal_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_skill(repo, "writing-skills/write-draft", "write-draft", "当需要把提纲填成初稿时使用；产出初稿。")
            write_catalog(repo, [{"name": "write-draft", "path": "writing-skills/write-draft", "domain": "write", "role": "canonical"}])
            result = run(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("validated 1 writing skills", result.stdout)

    def test_missing_catalog_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "writing-skills").mkdir()
            self.assertNotEqual(run(Path(tmp)).returncode, 0)

    def test_bad_name_case_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_skill(repo, "writing-skills/Write_Draft", "Write_Draft", "当测试时使用；x。")
            write_catalog(repo, [{"name": "Write_Draft", "path": "writing-skills/Write_Draft", "domain": "write", "role": "canonical"}])
            self.assertIn("NAME CASE", run(repo).stderr)

    def test_bad_domain_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_skill(repo, "writing-skills/write-draft", "write-draft", "当测试时使用；x。")
            write_catalog(repo, [{"name": "write-draft", "path": "writing-skills/write-draft", "domain": "coding", "role": "canonical"}])
            self.assertIn("INVALID DOMAIN", run(repo).stderr)

    def test_canonical_prefix_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_skill(repo, "writing-skills/foo-bar", "foo-bar", "当测试时使用；x。")
            write_catalog(repo, [{"name": "foo-bar", "path": "writing-skills/foo-bar", "domain": "write", "role": "canonical"}])
            self.assertIn("CANONICAL PREFIX MISMATCH", run(repo).stderr)

    def test_missing_skill_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "writing-skills" / "write-draft").mkdir(parents=True)
            write_catalog(repo, [{"name": "write-draft", "path": "writing-skills/write-draft", "domain": "write", "role": "canonical"}])
            self.assertIn("MISSING SKILL FILE", run(repo).stderr)

    def test_description_trigger_prefix_violation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_skill(repo, "writing-skills/write-draft", "write-draft", "把提纲填成初稿。")
            write_catalog(repo, [{"name": "write-draft", "path": "writing-skills/write-draft", "domain": "write", "role": "canonical"}])
            self.assertIn("DESCRIPTION TRIGGER PREFIX VIOLATION", run(repo).stderr)

    def test_orphan_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_skill(repo, "writing-skills/write-draft", "write-draft", "当测试时使用；x。")
            write_skill(repo, "writing-skills/write-orphan", "write-orphan", "当测试时使用；x。")
            write_catalog(repo, [{"name": "write-draft", "path": "writing-skills/write-draft", "domain": "write", "role": "canonical"}])
            self.assertIn("ORPHAN SKILL", run(repo).stderr)

    def test_shared_dir_exempt_from_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_skill(repo, "writing-skills/write-draft", "write-draft", "当测试时使用；x。")
            # _shared 下即便有 SKILL.md 也豁免（实际放约束文档，不是 skill）
            write_skill(repo, "writing-skills/_shared/x", "x", "当测试时使用；x。")
            write_catalog(repo, [{"name": "write-draft", "path": "writing-skills/write-draft", "domain": "write", "role": "canonical"}])
            self.assertEqual(run(repo).returncode, 0, run(repo).stderr)


if __name__ == "__main__":
    unittest.main()

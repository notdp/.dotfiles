"""验证 dotfiles helper 引用约定校验（防 2026-06-25 跨仓库路径解析事故复发）。

规则：
- (a) <...dotfiles...> 占位符 → FAIL；<skill_dir>/<target_repo_root> 不误伤
- (b) 双引号紧跟 ~/.dotfiles → WARN
- (c) 裸 scripts/xxx.{sh,py} 指向真实 dotfiles 脚本 → FAIL
- (d) ${HOME}/.dotfiles/... 引用不存在或非可执行 → FAIL；存在且可执行 → 通过
"""

import os
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import verify_skills  # noqa: E402


def _make_repo(tmp: str) -> tuple[verify_skills.ValidationContext, verify_skills.SkillEntry]:
    root = Path(tmp)
    skill_dir = root / "coding-skills" / "demo"
    (skill_dir).mkdir(parents=True)
    # repo-root helper（可执行）
    (root / "scripts").mkdir()
    rr = root / "scripts" / "preflight.sh"
    rr.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    os.chmod(rr, 0o755)
    # skill-local helper（可执行）
    (skill_dir / "scripts").mkdir()
    sl = skill_dir / "scripts" / "fetch.sh"
    sl.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    os.chmod(sl, 0o755)
    context = verify_skills.ValidationContext(repo_root=root)
    entry = verify_skills.SkillEntry(
        name="demo", path=skill_dir, domain="dev", role="canonical",
        migration=None, trigger_exempt=False, manual_only=False,
    )
    return context, entry


def _run(content: str):
    with tempfile.TemporaryDirectory() as tmp:
        context, entry = _make_repo(tmp)
        skill_file = entry.path / "SKILL.md"
        return verify_skills.validate_dotfiles_helper_refs(entry, skill_file, context, content)


class HelperRefRuleTests(unittest.TestCase):
    # (a)
    def test_dotfiles_placeholder_fails(self) -> None:
        with self.assertRaises(verify_skills.ValidationError):
            _run("bash \"<dotfiles_root>/scripts/preflight.sh\"")

    def test_skill_dir_placeholder_not_flagged(self) -> None:
        # readable-html-artifact 的刻意 fallback 链占位符不含 'dotfiles'，不应误伤
        self.assertEqual(_run("`<skill_dir>/render.py` 或 `<target_repo_root>/scripts/x.py`"), [])

    # (b)
    def test_quoted_tilde_warns(self) -> None:
        warnings = _run('bash "~/.dotfiles/scripts/preflight.sh"')
        self.assertTrue(any("TILDE" in w for w in warnings))

    def test_backtick_tilde_not_warned(self) -> None:
        # 反引号 / 不带引号的 ~/.dotfiles 在 bash 里能展开，不应误报
        self.assertEqual(_run("spec: `~/.dotfiles/docs/x.md` 见上"), [])

    # (c)
    def test_bare_repo_root_script_fails(self) -> None:
        with self.assertRaises(verify_skills.ValidationError):
            _run("先跑 scripts/preflight.sh 预检")

    def test_bare_skill_local_script_fails(self) -> None:
        with self.assertRaises(verify_skills.ValidationError):
            _run("调用 scripts/fetch.sh 抓取")

    def test_bare_nonexistent_script_not_flagged(self) -> None:
        # 目标项目自己的脚本（dotfiles 里不存在）属合法 bare 引用
        self.assertEqual(_run("项目若有 scripts/deploy.sh 则先跑"), [])

    # (d)
    def test_home_ref_existing_executable_passes(self) -> None:
        self.assertEqual(_run('bash "${HOME}/.dotfiles/scripts/preflight.sh"'), [])

    def test_home_ref_skill_local_passes(self) -> None:
        self.assertEqual(
            _run('bash "${HOME}/.dotfiles/coding-skills/demo/scripts/fetch.sh"'), []
        )

    def test_home_ref_missing_fails(self) -> None:
        with self.assertRaises(verify_skills.ValidationError):
            _run('bash "${HOME}/.dotfiles/scripts/does_not_exist.sh"')

    def test_home_ref_skill_local_non_executable_passes(self) -> None:
        # skill-local helper 常以 python3/bash 调用，不强制 +x，只查存在性
        with tempfile.TemporaryDirectory() as tmp:
            context, entry = _make_repo(tmp)
            helper = entry.path / "scripts" / "helper.py"
            helper.write_text("print('x')\n", encoding="utf-8")
            os.chmod(helper, 0o644)
            skill_file = entry.path / "SKILL.md"
            self.assertEqual(
                verify_skills.validate_dotfiles_helper_refs(
                    entry, skill_file, context,
                    'python3 ${HOME}/.dotfiles/coding-skills/demo/scripts/helper.py',
                ),
                [],
            )

    def test_home_ref_not_executable_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context, entry = _make_repo(tmp)
            noexec = context.repo_root / "scripts" / "noexec.py"
            noexec.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            os.chmod(noexec, 0o644)
            skill_file = entry.path / "SKILL.md"
            with self.assertRaises(verify_skills.ValidationError):
                verify_skills.validate_dotfiles_helper_refs(
                    entry, skill_file, context, 'python3 "${HOME}/.dotfiles/scripts/noexec.py"'
                )


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS = REPO_ROOT / "writing-hooks"


def run_cli(hook: str, content: str, suffix: str = ".md"):
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / f"draft{suffix}"
        f.write_text(content, encoding="utf-8")
        return subprocess.run(["python3", str(HOOKS / hook), str(f)], text=True, capture_output=True)


def run_stdin(hook: str, file_path: str, content: str):
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}})
    return subprocess.run(["python3", str(HOOKS / hook)], input=payload, text=True, capture_output=True)


class SlopLintTests(unittest.TestCase):
    def test_em_dash_warns_not_blocks(self):
        # `——` 是合法中文破折号，只告警不阻断（避免误伤正常写作）
        r = run_cli("slop_lint.py", "这是一句话——然后继续。\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("em dash", r.stdout)

    def test_ai_cliche_blocks(self):
        r = run_cli("slop_lint.py", "总而言之，这很重要。\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("AI 套话", r.stderr)

    def test_emoji_warns_not_blocks(self):
        r = run_cli("slop_lint.py", "今天很开心 🎉 写完了。\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("emoji", r.stdout)

    def test_clean_passes(self):
        r = run_cli("slop_lint.py", "我今天修好了那个 bug，记一笔。\n")
        self.assertEqual(r.returncode, 0)

    def test_pangu_warns_not_blocks(self):
        r = run_cli("slop_lint.py", "我用了8个GPU训练。\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("盘古", r.stdout)

    def test_non_writing_artifact_noop(self):
        r = run_cli("slop_lint.py", "code = 1 — 2\n", suffix=".py")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, "")


class LengthBudgetTests(unittest.TestCase):
    def test_long_paragraph_blocks(self):
        r = run_cli("length_budget.py", "啊" * 450 + "\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("超过", r.stderr)

    def test_heading_skip_blocks(self):
        r = run_cli("length_budget.py", "# 标题\n\n### 跳级小节\n\n正文。\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("跳级", r.stderr)

    def test_normal_passes(self):
        r = run_cli("length_budget.py", "# 标题\n\n## 小节\n\n一段正常的话。\n")
        self.assertEqual(r.returncode, 0)


class ProvenanceTests(unittest.TestCase):
    def test_machine_path_blocks(self):
        r = run_cli("provenance_guard.py", "见 /Users/alice/project/draft.md 里的版本。\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn("本机绝对路径", r.stderr)

    def test_anon_path_passes(self):
        r = run_cli("provenance_guard.py", "放到 /Users/.../reference.png （匿名示例）。\n")
        self.assertEqual(r.returncode, 0)

    def test_clean_passes(self):
        r = run_cli("provenance_guard.py", "正常正文，没有路径。\n")
        self.assertEqual(r.returncode, 0)


class WarnOnlyHooksTests(unittest.TestCase):
    def test_dehumanize_always_exit0(self):
        bad = "总而言之，综上所述，值得注意的是，赋能抓手闭环。"
        self.assertEqual(run_cli("dehumanize_score.py", bad).returncode, 0)

    def test_dehumanize_low_score_warns(self):
        bad = "总而言之，综上所述，赋能。" * 5
        self.assertIn("去 AI 味评分", run_cli("dehumanize_score.py", bad).stdout)

    def test_facts_gate_always_exit0(self):
        r = run_cli("facts_gate.py", "研究表明 90% 的人会这样。\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("来源", r.stdout)


class PublishConfirmTests(unittest.TestCase):
    def test_publish_flag_blocks(self):
        r = run_cli("publish_confirm.py", "---\npublish: true\n---\n正文。\n")
        self.assertEqual(r.returncode, 2)

    def test_publish_path_blocks_via_stdin(self):
        r = run_stdin("publish_confirm.py", "/proj/发布/article.md", "正文内容。\n")
        self.assertEqual(r.returncode, 2)

    def test_normal_edit_passes(self):
        r = run_cli("publish_confirm.py", "普通草稿正文。\n")
        self.assertEqual(r.returncode, 0)


class StdinModeTests(unittest.TestCase):
    def test_stdin_ai_cliche_blocks(self):
        r = run_stdin("slop_lint.py", "/proj/draft.md", "综上所述，赋能闭环。\n")
        self.assertEqual(r.returncode, 2)

    def test_stdin_non_md_noop(self):
        r = run_stdin("slop_lint.py", "/proj/code.py", "x = 1 — 2\n")
        self.assertEqual(r.returncode, 0)

    def test_stdin_empty_noop(self):
        r = subprocess.run(["python3", str(HOOKS / "slop_lint.py")], input="", text=True, capture_output=True)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()

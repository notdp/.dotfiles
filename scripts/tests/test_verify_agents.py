import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import verify_agents  # noqa: E402

VALID_CLAUDE_AGENT = """---
name: {name}
description: 当安全审查产出 finding、需要只读误报裁决时使用。
tools: {tools}
model: {model}
---

# Body

只读裁决，输出 JSON。判例库见 ~/.claude/skills/guard-secure/references/false-positive-precedents.md。
"""

VALID_OPENCODE_AGENT = """---
description: 当安全审查产出 finding、需要只读误报裁决时使用。
mode: {mode}
permission:
  edit: {edit}
  bash: {bash}
---

# Body

只读裁决，输出 JSON。判例库见 ~/.config/opencode/skills/guard-secure/references/false-positive-precedents.md。
"""


def write_claude(root: Path, filename: str, *, name: str | None = None,
                 tools: str = "Read, Grep, Glob", model: str = "inherit",
                 content: str | None = None) -> Path:
    agents_dir = root / "coding-agents" / "claude"
    agents_dir.mkdir(parents=True, exist_ok=True)
    path = agents_dir / filename
    if content is None:
        content = VALID_CLAUDE_AGENT.format(name=name or path.stem, tools=tools, model=model)
    path.write_text(content, encoding="utf-8")
    return path


def write_opencode(root: Path, filename: str, *, mode: str = "subagent",
                   edit: str = "deny", bash: str = "deny",
                   content: str | None = None) -> Path:
    agents_dir = root / "coding-agents" / "opencode"
    agents_dir.mkdir(parents=True, exist_ok=True)
    path = agents_dir / filename
    if content is None:
        content = VALID_OPENCODE_AGENT.format(mode=mode, edit=edit, bash=bash)
    path.write_text(content, encoding="utf-8")
    return path


class VerifyAgentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def run_verify(self) -> int:
        return verify_agents.run(self.root)

    # --- 布局 ---

    def test_valid_dual_runtime_passes(self) -> None:
        write_claude(self.root, "security-fp-judge.md")
        write_opencode(self.root, "security-fp-judge.md")
        self.assertEqual(self.run_verify(), 0)

    def test_missing_dir_fails(self) -> None:
        self.assertEqual(self.run_verify(), 1)

    def test_empty_dir_fails(self) -> None:
        (self.root / "coding-agents").mkdir(parents=True)
        self.assertEqual(self.run_verify(), 1)

    def test_misplaced_root_file_fails(self) -> None:
        write_claude(self.root, "sample-judge.md")
        (self.root / "coding-agents" / "stray.md").write_text("---\ndescription: 当需要时。\n---\n")
        self.assertEqual(self.run_verify(), 1)

    def test_unknown_runtime_dir_fails(self) -> None:
        write_claude(self.root, "sample-judge.md")
        cursor = self.root / "coding-agents" / "cursor"
        cursor.mkdir(parents=True)
        (cursor / "sample-judge.md").write_text("---\ndescription: 当需要时。\n---\n")
        self.assertEqual(self.run_verify(), 1)

    # --- Claude 规则 ---

    def test_claude_name_mismatch_fails(self) -> None:
        write_claude(self.root, "security-fp-judge.md", name="other-name")
        self.assertEqual(self.run_verify(), 1)

    def test_claude_missing_model_fails(self) -> None:
        content = "---\nname: sample-judge\ndescription: 当需要时使用。\ntools: Read\n---\nbody\n"
        write_claude(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    def test_claude_invalid_model_fails(self) -> None:
        write_claude(self.root, "sample-judge.md", model="gpt-5")
        self.assertEqual(self.run_verify(), 1)

    def test_claude_unknown_tool_fails(self) -> None:
        # 上游三种混写反例：裸 MCP 名 / agent 名 / skill 名
        for bad in ("chrome-mcp", "context-manager", "subagent-catalog:search"):
            with self.subTest(tool=bad):
                write_claude(self.root, "sample-judge.md", tools=f"Read, {bad}")
                self.assertEqual(self.run_verify(), 1)

    def test_claude_mcp_prefixed_tool_passes(self) -> None:
        write_claude(self.root, "sample-fetcher.md", tools="Read, mcp__pencil__get_screenshot")
        self.assertEqual(self.run_verify(), 0)

    def test_claude_readonly_role_with_mutating_tool_fails(self) -> None:
        for suffix in ("-judge", "-reviewer", "-auditor"):
            with self.subTest(suffix=suffix):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    write_claude(root, f"sample{suffix}.md", tools="Read, Bash")
                    self.assertEqual(verify_agents.run(root), 1)

    def test_claude_readonly_cap_not_applied_to_other_roles(self) -> None:
        write_claude(self.root, "sample-fetcher.md", tools="Read, Write, Bash")
        self.assertEqual(self.run_verify(), 0)

    def test_claude_machine_path_fails(self) -> None:
        content = VALID_CLAUDE_AGENT.format(
            name="sample-judge", tools="Read", model="inherit"
        ) + "\n读取 /Users/alice/notes.md\n"
        write_claude(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    def test_claude_missing_trigger_semantics_fails(self) -> None:
        content = "---\nname: sample-judge\ndescription: A security judge.\ntools: Read\nmodel: inherit\n---\nbody\n"
        write_claude(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    # --- OpenCode/Kilo 规则 ---

    def test_opencode_deprecated_tools_field_fails(self) -> None:
        content = "---\ndescription: 当需要时使用。\nmode: subagent\ntools:\n  bash: false\n---\nbody\n"
        write_opencode(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    def test_opencode_name_field_forbidden(self) -> None:
        content = "---\nname: sample-judge\ndescription: 当需要时使用。\nmode: subagent\npermission:\n  edit: deny\n  bash: deny\n---\nbody\n"
        write_opencode(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    def test_opencode_missing_mode_fails(self) -> None:
        content = "---\ndescription: 当需要时使用。\npermission:\n  edit: deny\n  bash: deny\n---\nbody\n"
        write_opencode(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    def test_opencode_readonly_role_requires_deny(self) -> None:
        for edit, bash in (("allow", "deny"), ("deny", "allow"), ("ask", "deny")):
            with self.subTest(edit=edit, bash=bash):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    write_opencode(root, "sample-judge.md", edit=edit, bash=bash)
                    self.assertEqual(verify_agents.run(root), 1)

    def test_opencode_readonly_role_without_permission_fails(self) -> None:
        content = "---\ndescription: 当需要时使用。\nmode: subagent\n---\nbody\n"
        write_opencode(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    def test_opencode_invalid_permission_action_fails(self) -> None:
        write_opencode(self.root, "sample-judge.md", edit="false", bash="deny")
        self.assertEqual(self.run_verify(), 1)

    def test_opencode_model_must_be_provider_form(self) -> None:
        content = "---\ndescription: 当需要时使用。\nmode: subagent\nmodel: opus\npermission:\n  edit: deny\n  bash: deny\n---\nbody\n"
        write_opencode(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 1)

    def test_opencode_provider_model_passes(self) -> None:
        content = "---\ndescription: 当需要时使用。\nmode: subagent\nmodel: cliproxy/gpt-5.5\npermission:\n  edit: deny\n  bash: deny\n---\nbody\n"
        write_opencode(self.root, "sample-judge.md", content=content)
        self.assertEqual(self.run_verify(), 0)

    def test_opencode_non_readonly_role_permission_optional(self) -> None:
        content = "---\ndescription: 当需要时使用。\nmode: subagent\n---\nbody\n"
        write_opencode(self.root, "sample-fetcher.md", content=content)
        self.assertEqual(self.run_verify(), 0)

    # --- 真实仓库 ---

    def test_repo_real_agents_pass(self) -> None:
        self.assertEqual(verify_agents.run(REPO_ROOT), 0)


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "context_capsule.py"
sys.path.insert(0, str(REPO_ROOT / "scripts" / "hooks"))
import context_capsule as cc  # noqa: E402
WRAPPER_SCRIPT = REPO_ROOT / ".factory" / "hooks" / "context_capsule.py"
GOLDEN_PROMPT_SAMPLES = (
    ("分组提交代码", []),
    ("我觉得我还是得摸清一下当前仓库的 hooks 都是怎么设计的，给我通过 html 清晰的展示出来", ["Boundary-Decision Capsule"]),
    (f"重写 file://{REPO_ROOT}/docs/repository-hooks-design-2026-05-15.html", ["Boundary-Decision Capsule"]),
    ("context_capsule.py 是不是针对不同场景注入增强 prompt，要不要交给便宜模型判定器", ["Boundary-Decision Capsule"]),
    ("长会话 compact 后 agent 能看到上次目标、改动文件、最近验证和 todo 摘要吗", []),
    ("帮我加个缓存", ["Scope Alignment Capsule"]),
    ("优化这个模块，给我一个重构方案", ["Scope Alignment Capsule", "Planning Task Capsule"]),
    # 回归: "原有设计"是名词诊断, 不该误匹配 planning; "原因分析"应匹配 debug
    ("这是符合原有设计的吗，如果不符合，是代码问题还是配置问题，给出原因分析", ["Debug Task Capsule"]),
    # 第二轮: 中文诊断/部署词 recall 回归
    ("这里发现一个数据不一致，授予角色应该只统计 enable 的数量", ["Debug Task Capsule"]),
    ("我解决了一个问题，重新发布一下 lzn-sandbox preview", ["Security / GitOps Capsule"]),
)


class ContextCapsuleTests(unittest.TestCase):
    def run_capsule(self, repo: Path, prompt: str) -> subprocess.CompletedProcess[str]:
        # 禁用 deepseek, golden 验证正则 fallback 路径(deepseek 路径见 DeepseekRoutingTests)
        env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo), "CAPSULE_NO_LLM": "1"}
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": prompt}
        return subprocess.run(
            ["python3", str(SCRIPT), "--event", "prompt"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            cwd=repo,
        )

    def run_preview(self, prompt: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--event", "prompt", "--preview", "--prompt-text", prompt],
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

    def run_event(self, event: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--event", event],
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

    def run_wrapper_preview(self, prompt: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(WRAPPER_SCRIPT), "--event", "prompt", "--preview", "--prompt-text", prompt],
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

    def assert_prompt_capsules(self, prompt: str, expected_headings: list[str]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), prompt)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        if not expected_headings:
            self.assertTrue(payload["suppressOutput"])
            return
        context = payload["hookSpecificOutput"]["additionalContext"]
        headings = [line.removeprefix("# ") for line in context.splitlines() if line.startswith("# ")]
        self.assertEqual(headings, expected_headings)
        self.assertLessEqual(len(context), 2200)

    def test_prompt_can_match_multiple_capsules_with_risk_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), "prod dry-run apply backfill failed with auth permission bug")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Security / GitOps Capsule", context)
        self.assertIn("Operational Task Capsule", context)
        self.assertIn("Debug Task Capsule", context)
        self.assertLess(context.index("Security / GitOps Capsule"), context.index("Operational Task Capsule"))
        self.assertLessEqual(len(context), 2200)

    def test_golden_prompt_samples_inject_expected_capsules(self) -> None:
        for prompt, expected_headings in GOLDEN_PROMPT_SAMPLES:
            with self.subTest(prompt=prompt):
                self.assert_prompt_capsules(prompt, expected_headings)

    def test_critical_cloud_operation_prompts_inject_operational_capsule(self) -> None:
        samples = [
            "关掉 GPU 省钱",
            "停掉 ECS，不用了",
            "降成本，把这个 RDS 降配",
            "stop this aliyun ECS to cut cost",
        ]
        for prompt in samples:
            with self.subTest(prompt=prompt):
                self.assert_prompt_capsules(prompt, ["Operational Task Capsule"])

    def test_english_release_cloud_prompt_injects_operational_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), "release this RDS instance")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Operational Task Capsule", context)

    def test_external_security_testing_prompts_inject_security_capsule(self) -> None:
        samples = [
            "run exploit validation against external target",
            "perform C2 phishing simulation and brute force test",
        ]
        for prompt in samples:
            with self.subTest(prompt=prompt):
                self.assert_prompt_capsules(prompt, ["Security / GitOps Capsule"])

    def test_non_critical_operation_words_stay_quiet(self) -> None:
        samples = [
            "这个按钮关掉动画",
            "不用了这个变量，删一下本地代码",
        ]
        for prompt in samples:
            with self.subTest(prompt=prompt):
                self.assert_prompt_capsules(prompt, [])

    def test_preview_reports_matches_without_hook_json(self) -> None:
        result = self.run_preview("封装 response_model metric hook")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("## Context Capsule Preview", result.stdout)
        self.assertIn("| boundary-decision.md | matched |", result.stdout)
        self.assertIn("Final context chars:", result.stdout)
        self.assertNotIn("hookSpecificOutput", result.stdout)

    def test_preview_reports_no_matches(self) -> None:
        result = self.run_preview("分组提交代码")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No capsules matched", result.stdout)

    def test_factory_context_capsule_wrapper_delegates_to_runtime(self) -> None:
        result = self.run_wrapper_preview("封装 response_model metric hook")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("| boundary-decision.md | matched |", result.stdout)

    def test_session_events_do_not_inject_fixed_discipline_capsule(self) -> None:
        for event in ["session-start", "pre-compact"]:
            with self.subTest(event=event):
                result = self.run_event(event)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout), {"suppressOutput": True})

    def test_non_matching_prompt_stays_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), "thanks")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_long_prompt_tail_keywords_ignored(self) -> None:
        # 开头无触发词, 撞词全在首段(MATCH_HEAD_CHARS)之后 → 只匹首段, 不应注入
        prompt = "帮我确认一下当前这个东西" + ("。" * 250) + " schema metric 数据源 prod 部署 backfill"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), prompt)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["suppressOutput"])

    def test_frontend_async_code_does_not_inject_operational_or_planning_capsules(self) -> None:
        prompt = """修一个 React 保存逻辑：

```tsx
const doSave = useCallback(async (fields: CommitFieldConfig[], options?: { silentSuccess?: boolean }) => {
  await onSave({ fields_config: fields }, options)
})
```
"""
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), prompt)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("UI Task Capsule", context)
        self.assertNotIn("Operational Task Capsule", context)
        self.assertNotIn("Planning Task Capsule", context)

    def test_boundary_prompt_injects_boundary_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_capsule(Path(tmp), "帮我封装这个服务，并确认 response_model 和 metric label")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Boundary-Decision Capsule", context)
        self.assertIn("Boundary decisions:", context)

    def test_post_tool_runs_boundary_scanner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            src = repo / "src"
            src.mkdir()
            (src / "service.py").write_text(
                "from fastapi import HTTPException\nraise HTTPException(status_code=422)\n",
                encoding="utf-8",
            )
            env = {**os.environ, "FACTORY_PROJECT_DIR": str(repo)}
            result = subprocess.run(
                ["python3", str(SCRIPT), "--event", "post-tool"],
                text=True,
                capture_output=True,
                cwd=repo,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Boundary decision scan found", context)


class DeepseekRoutingTests(unittest.TestCase):
    def test_resolve_uses_deepseek_when_available(self) -> None:
        original = cc.classify_with_deepseek
        cc.classify_with_deepseek = lambda prompt: {"debug-task.md", "ui-task.md"}
        try:
            # 按 CAPSULE_RULES 顺序: debug 在 ui 前
            self.assertEqual(cc.resolve_capsule_names("anything"), ["debug-task.md", "ui-task.md"])
        finally:
            cc.classify_with_deepseek = original

    def test_resolve_falls_back_to_regex_when_deepseek_fails(self) -> None:
        original = cc.classify_with_deepseek
        cc.classify_with_deepseek = lambda prompt: None
        try:
            # deepseek 返回 None → 正则 fallback: "帮我加个缓存" 命中 scope
            self.assertEqual(cc.resolve_capsule_names("帮我加个缓存"), ["scope-task.md"])
        finally:
            cc.classify_with_deepseek = original

    def test_resolve_order_follows_capsule_rules(self) -> None:
        original = cc.classify_with_deepseek
        cc.classify_with_deepseek = lambda prompt: {"scope-task.md", "security-gitops.md"}
        try:
            # deepseek 返回乱序 set, resolve 按 CAPSULE_RULES 顺序: security 在 scope 前
            self.assertEqual(cc.resolve_capsule_names("x"), ["security-gitops.md", "scope-task.md"])
        finally:
            cc.classify_with_deepseek = original

    def test_classify_disabled_by_env_returns_none(self) -> None:
        os.environ["CAPSULE_NO_LLM"] = "1"
        try:
            self.assertIsNone(cc.classify_with_deepseek("帮我加个缓存"))
        finally:
            os.environ.pop("CAPSULE_NO_LLM", None)

    def test_classify_no_key_returns_none(self) -> None:
        # 无 env key + 指向不存在的 keyfile → None(触发 fallback)
        orig_env = os.environ.pop("DEEPSEEK_API_KEY", None)
        orig_keyfile = cc.DEEPSEEK_KEYFILE
        cc.DEEPSEEK_KEYFILE = "/nonexistent/deepseek/apikey"
        try:
            self.assertIsNone(cc.classify_with_deepseek("帮我加个缓存"))
        finally:
            cc.DEEPSEEK_KEYFILE = orig_keyfile
            if orig_env is not None:
                os.environ["DEEPSEEK_API_KEY"] = orig_env


if __name__ == "__main__":
    unittest.main()

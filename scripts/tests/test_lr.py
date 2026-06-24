import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "coding-skills" / "dev-long-run"))

import lr  # noqa: E402


SESSIONS_SAMPLE = """# Sessions

| role | phase | pane_id | started_at | last_seen | status |
|---|---|---|---|---|---|
| phase_coder | 01 | %42 | 2026-05-29T10:00:00Z | 2026-05-29T10:45:00Z | running |
| phase_reviewer | 01 | %43 | 2026-05-29T10:50:00Z | 2026-05-29T10:55:00Z | closed |
"""


class SessionsParseTests(unittest.TestCase):
    def test_parse_returns_rows_as_dicts(self) -> None:
        rows = lr.parse_sessions(SESSIONS_SAMPLE)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["role"], "phase_coder")
        self.assertEqual(rows[0]["pane_id"], "%42")
        self.assertEqual(rows[0]["status"], "running")
        self.assertEqual(rows[1]["phase"], "01")
        self.assertEqual(rows[1]["status"], "closed")

    def test_malformed_data_row_raises(self) -> None:
        # 故障导向安全: 像数据行(以 | 开头)但列数不符, 不能静默丢, 否则 orch 误判 pane 缺失
        bad = (
            "| role | phase | pane_id | started_at | last_seen | status |\n"
            "|---|---|---|---|---|---|\n"
            "| phase_coder | 01 | %42 |\n"
        )
        with self.assertRaises(ValueError):
            lr.parse_sessions(bad)

    def test_render_round_trips_through_parse(self) -> None:
        rows = lr.parse_sessions(SESSIONS_SAMPLE)
        self.assertEqual(lr.parse_sessions(lr.render_sessions(rows)), rows)

    def test_render_has_header_and_is_human_readable(self) -> None:
        text = lr.render_sessions([])
        self.assertIn("# Sessions", text)
        self.assertIn("| role | phase | pane_id | started_at | last_seen | status |", text)


class UpsertSessionTests(unittest.TestCase):
    def base_rows(self) -> list[dict[str, str]]:
        return lr.parse_sessions(SESSIONS_SAMPLE)

    def test_upsert_updates_existing_pane_in_place(self) -> None:
        # 同一 pane_id(%42) 更新 last_seen/status, 不新增行
        rows = lr.upsert_session(
            self.base_rows(),
            {"role": "phase_coder", "phase": "02", "pane_id": "%42",
             "started_at": "2026-05-29T10:00:00Z", "last_seen": "2026-05-29T12:00:00Z", "status": "closed"},
        )
        self.assertEqual(len(rows), 2)
        coder = [r for r in rows if r["pane_id"] == "%42"][0]
        self.assertEqual(coder["status"], "closed")
        self.assertEqual(coder["last_seen"], "2026-05-29T12:00:00Z")
        self.assertEqual(coder["phase"], "02")

    def test_upsert_appends_new_pane(self) -> None:
        rows = lr.upsert_session(
            self.base_rows(),
            {"role": "phase_planner", "phase": "02", "pane_id": "%99",
             "started_at": "2026-05-29T12:10:00Z", "last_seen": "2026-05-29T12:10:00Z", "status": "running"},
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["pane_id"], "%99")

    def test_upsert_rejects_incomplete_session(self) -> None:
        # Fail Fast: 缺列的 session dict 不能写进 SSOT
        with self.assertRaises(ValueError):
            lr.upsert_session(self.base_rows(), {"role": "phase_coder", "pane_id": "%42"})


class NamingTests(unittest.TestCase):
    def test_slugify_makes_git_safe_slug(self) -> None:
        # 自由任务名 → 小写连字符, 去掉空格/特殊字符/git 非法字符
        self.assertEqual(lr.slugify("Compliance Refactor!"), "compliance-refactor")
        self.assertEqual(lr.slugify("auth/v2  fix"), "auth-v2-fix")

    def test_slugify_rejects_empty_result(self) -> None:
        # 全是特殊字符 → 无法产出 slug, Fail Fast
        with self.assertRaises(ValueError):
            lr.slugify("///")

    def test_branch_name(self) -> None:
        self.assertEqual(lr.branch_name("compliance"), "lr/compliance")

    def test_pane_title_is_phase_and_identity(self) -> None:
        # 用户决策(USER 2026-06-06): pane 名 `phase {n} {身份}`(不含任务名, 太长), 方便调试。
        # 身份去掉 phase_ 前缀(planner/coder/reviewer)。
        self.assertEqual(lr.pane_title("phase_coder", "01"), "phase 01 coder")
        self.assertEqual(lr.pane_title("phase_planner", "02"), "phase 02 planner")
        self.assertEqual(lr.pane_title("phase_reviewer", "03"), "phase 03 reviewer")

    def test_pane_title_keeps_unknown_role_verbatim(self) -> None:
        # 非 phase_ 前缀的 role 原样保留, 不臆造转换
        self.assertEqual(lr.pane_title("orchestrator", "01"), "phase 01 orchestrator")

    def test_worktree_path_is_sibling_of_repo(self) -> None:
        wt = lr.worktree_path(Path("/home/u/myrepo"), "compliance")
        self.assertEqual(wt, Path("/home/u/myrepo-lr-compliance"))

    def test_plan_worktree_new_creates_sibling_branch(self) -> None:
        plan = lr.plan_worktree(Path("/home/u/repo"), "auth", in_place=False, current_branch="main")
        self.assertEqual(plan["branch"], "lr/auth")
        self.assertEqual(plan["worktree_path"], "/home/u/repo-lr-auth")
        self.assertTrue(plan["create"])

    def test_plan_worktree_in_place_uses_current_branch(self) -> None:
        # 接着做: 在当前 feature 分支 + 当前目录, 不新建
        plan = lr.plan_worktree(Path("/home/u/repo"), "auth", in_place=True, current_branch="feature/x")
        self.assertEqual(plan["branch"], "feature/x")
        self.assertEqual(plan["worktree_path"], "/home/u/repo")
        self.assertFalse(plan["create"])

    def test_plan_worktree_in_place_refuses_main(self) -> None:
        # L16: 不在 main/master 上开发
        for b in ("main", "master", ""):
            with self.assertRaises(ValueError):
                lr.plan_worktree(Path("/home/u/repo"), "auth", in_place=True, current_branch=b)


class ScaffoldCommandTests(unittest.TestCase):
    def _init_repo(self, tmp: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True, capture_output=True)

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = lr.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_flagless_chinese_goal_prompts_for_mode_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            self._init_repo(repo)
            req = repo / "REQUIREMENT.md"
            req.write_text("# 需求\n", encoding="utf-8")

            code, _stdout, stderr = self._run([
                "scaffold",
                "--requirement", str(req),
                "--goal", "实现提报配置与提报表格体验优化需求",
                "--repo-root", str(repo),
            ])

        self.assertEqual(code, 2)
        self.assertIn("worktree 模式未指定", stderr)
        self.assertIn("--name", stderr)

    def test_explicit_mode_chinese_goal_requires_name_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            self._init_repo(repo)
            req = repo / "REQUIREMENT.md"
            req.write_text("# 需求\n", encoding="utf-8")

            code, _stdout, stderr = self._run([
                "scaffold",
                "--requirement", str(req),
                "--goal", "实现提报配置与提报表格体验优化需求",
                "--repo-root", str(repo),
                "--in-place",
            ])

        self.assertEqual(code, 2)
        self.assertIn("cannot derive git-safe slug", stderr)
        self.assertIn("--name <ascii-slug>", stderr)


def valid_config_dual() -> dict:
    """双路 reviewer 配置(新默认)。"""
    def role(backend, autonomy, **extra):
        return {"backend": backend, "model": "m", "autonomy": autonomy, **extra}
    cmd = "claude --dangerously-skip-permissions"
    return {
        "version": 2,
        "roles": {
            "scaffold_orchestrator": role("kilo", "medium"),
            "scaffold_reviewer_a": role("kilo", "off"),
            "scaffold_reviewer_b": role("claude_cli", "off", cmd=cmd),
            "loop_orchestrator": role("kilo", "medium"),
            "phase_planner": role("kilo", "low"),
            "phase_coder": role("kilo", "high"),
            "phase_reviewer_a": role("kilo", "off"),
            "phase_reviewer_b": role("claude_cli", "off", cmd=cmd),
        },
    }


def valid_config_legacy() -> dict:
    """旧单路 reviewer 配置(向后兼容)。"""
    def role(backend, autonomy, **extra):
        return {"backend": backend, "model": "m", "autonomy": autonomy, **extra}
    cmd = "claude --dangerously-skip-permissions"
    return {
        "version": 2,
        "roles": {
            "scaffold_orchestrator": role("kilo", "medium"),
            "scaffold_reviewer": role("claude_cli", "off", cmd=cmd),
            "loop_orchestrator": role("kilo", "medium"),
            "phase_planner": role("kilo", "low"),
            "phase_coder": role("kilo", "high"),
            "phase_reviewer": role("claude_cli", "off", cmd=cmd),
        },
    }


def valid_config() -> dict:
    return valid_config_dual()


class ConfigValidationTests(unittest.TestCase):
    def test_valid_config_passes(self) -> None:
        self.assertEqual(lr.validate_config(valid_config()), valid_config())

    def test_missing_role_rejected(self) -> None:
        cfg = valid_config()
        del cfg["roles"]["phase_coder"]
        with self.assertRaises(ValueError):
            lr.validate_config(cfg)

    def test_missing_dual_reviewer_rejected(self) -> None:
        cfg = valid_config_dual()
        del cfg["roles"]["phase_reviewer_b"]
        with self.assertRaises(ValueError):
            lr.validate_config(cfg)

    def test_legacy_config_still_valid(self) -> None:
        self.assertEqual(lr.validate_config(valid_config_legacy()), valid_config_legacy())

    def test_unknown_backend_rejected(self) -> None:
        cfg = valid_config()
        cfg["roles"]["phase_coder"]["backend"] = "gemini"
        with self.assertRaises(ValueError):
            lr.validate_config(cfg)

    def test_bad_autonomy_rejected(self) -> None:
        cfg = valid_config()
        cfg["roles"]["phase_coder"]["autonomy"] = "full"
        with self.assertRaises(ValueError):
            lr.validate_config(cfg)

    def test_claude_cli_role_requires_cmd(self) -> None:
        cfg = valid_config()
        del cfg["roles"]["phase_reviewer_b"]["cmd"]
        with self.assertRaises(ValueError):
            lr.validate_config(cfg)


class WorkerStatusTests(unittest.TestCase):
    def test_done_with_detail(self) -> None:
        self.assertEqual(lr.parse_worker_status("done commit=2e49a706\n"), ("done", "commit=2e49a706"))

    def test_blocked(self) -> None:
        self.assertEqual(lr.parse_worker_status("blocked reviewer rejected all"), ("blocked", "reviewer rejected all"))

    def test_bare_state(self) -> None:
        self.assertEqual(lr.parse_worker_status("coding"), ("coding", ""))

    def test_empty_is_unknown(self) -> None:
        self.assertEqual(lr.parse_worker_status(""), ("unknown", ""))

    def test_garbage_is_unknown(self) -> None:
        # 不在已知 state 词表 → unknown(避免把 prose 误判成完成)
        self.assertEqual(lr.parse_worker_status("almost done maybe")[0], "unknown")

    def test_assignment_form_with_equals(self) -> None:
        # worker 把 prompt 里的 `phase_coder.status = done ...` 整行写进文件 → 仍能取到 done
        self.assertEqual(
            lr.parse_worker_status("phase_coder.status = done commit=2e49a706"),
            ("done", "commit=2e49a706"),
        )

    def test_assignment_form_with_colon(self) -> None:
        self.assertEqual(lr.parse_worker_status("status: blocked need creds"), ("blocked", "need creds"))

    def test_assignment_form_with_garbage_rhs_is_unknown(self) -> None:
        # 赋值左边像 status key,但右边不是合法 state → 仍 unknown(不放行 prose)
        self.assertEqual(lr.parse_worker_status("phase_coder.status = almost there")[0], "unknown")


class PaneIdleTests(unittest.TestCase):
    def test_ready_marker_is_idle(self) -> None:
        self.assertTrue(lr.pane_looks_idle("...\n? for shortcuts"))
        self.assertTrue(lr.pane_looks_idle("Ask anything\n"))

    def test_active_screen_not_idle(self) -> None:
        self.assertFalse(lr.pane_looks_idle("Editing file foo.py\nrunning tests..."))

    def test_idle_strike_accrues_when_ready_and_unchanged(self) -> None:
        prev = "work done\n? for shortcuts"
        self.assertEqual(lr.update_idle(prev, prev, 1), 2)

    def test_idle_strike_resets_when_screen_changes(self) -> None:
        # 画面还在变(在干活)→ strike 清零, 即便当前帧带就绪标识
        self.assertEqual(lr.update_idle("frame A\n? for shortcuts", "frame B\n? for shortcuts", 3), 0)

    def test_idle_strike_resets_when_not_ready(self) -> None:
        screen = "still generating tokens"
        self.assertEqual(lr.update_idle(screen, screen, 3), 0)


class YamlLoaderTests(unittest.TestCase):
    def test_loads_generated_config_and_passes_validate(self) -> None:
        cfg = lr.load_yaml(lr.default_config_yaml("demo"))
        self.assertEqual(cfg["version"], 2)
        self.assertEqual(cfg["roles"]["phase_coder"]["backend"], "kilo")
        # 双路 reviewer: _a + _b 都存在
        self.assertIn("phase_reviewer_a", cfg["roles"])
        self.assertIn("phase_reviewer_b", cfg["roles"])
        # 两路 backend 互补(一个 kilo 一个 claude_cli)
        backends = {cfg["roles"]["phase_reviewer_a"]["backend"], cfg["roles"]["phase_reviewer_b"]["backend"]}
        self.assertEqual(backends, {"kilo", "claude_cli"})
        # claude_cli 路有 cmd
        cc_role = "phase_reviewer_a" if cfg["roles"]["phase_reviewer_a"]["backend"] == "claude_cli" else "phase_reviewer_b"
        self.assertEqual(cfg["roles"][cc_role]["cmd"], "claude --dangerously-skip-permissions")
        # 生成的模板必须通过 schema 校验(round-trip)
        self.assertEqual(lr.validate_config(cfg), cfg)

    def test_inline_comment_stripped_from_unquoted_scalar(self) -> None:
        cfg = lr.load_yaml("version: 2  # the schema version\nroles:\n  x:\n    backend: kilo  # note\n")
        self.assertEqual(cfg["version"], 2)
        self.assertEqual(cfg["roles"]["x"]["backend"], "kilo")

    def test_bad_line_without_colon_raises(self) -> None:
        with self.assertRaises(ValueError):
            lr.load_yaml("version 2\n")


class TmuxArgTests(unittest.TestCase):
    def test_split_window_targets_current_pane(self) -> None:
        # 在当前 window split 当前 pane(target=当前 TMUX_PANE), 不进别的 session/tab
        args = lr.split_window_args("/wt", "split-down", "kilo -m m", target="%3")
        self.assertEqual(args[args.index("-t") + 1], "%3")
        self.assertIn("-v", args)
        self.assertIn("#{pane_id}", args)
        self.assertEqual(args[-1], "kilo -m m")

    def test_split_window_no_target_splits_current(self) -> None:
        args = lr.split_window_args("/wt", "split-right", None)
        self.assertNotIn("-t", args)  # 无 target → tmux 默认 split 当前 pane
        self.assertIn("-h", args)

    def test_split_window_bad_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            lr.split_window_args("/wt", "split-sideways", None)

    def test_paste_buffer_uses_bracketed_paste(self) -> None:
        # 多行 prompt 走 bracketed paste(-p), 不提前提交; Enter 由 send_to_pane 单独发
        self.assertEqual(lr.paste_buffer_args("%5", "lrdispatch"),
                         ["paste-buffer", "-p", "-b", "lrdispatch", "-t", "%5"])

    def test_pane_is_alive(self) -> None:
        out = "%1\n%42\n%7\n"
        self.assertTrue(lr.pane_is_alive(out, "%42"))
        self.assertFalse(lr.pane_is_alive(out, "%99"))

    def test_find_live_role_pane_returns_running_alive(self) -> None:
        # L6(改): 找某 role 仍存活的 running pane(每 phase 开始时用来关掉上一个 coder)
        rows = [
            {"role": "phase_coder", "phase": "01", "pane_id": "%42", "started_at": "t", "last_seen": "t", "status": "running"},
            {"role": "phase_reviewer", "phase": "01", "pane_id": "%43", "started_at": "t", "last_seen": "t", "status": "closed"},
        ]
        self.assertEqual(lr.find_live_role_pane(rows, "phase_coder", "%42\n%7\n"), "%42")

    def test_find_live_role_pane_none_when_dead(self) -> None:
        rows = [{"role": "phase_coder", "phase": "01", "pane_id": "%42", "started_at": "t", "last_seen": "t", "status": "running"}]
        self.assertIsNone(lr.find_live_role_pane(rows, "phase_coder", "%7\n%8\n"))  # %42 不在活 pane 里

    def test_find_live_role_pane_none_when_absent(self) -> None:
        self.assertIsNone(lr.find_live_role_pane([], "phase_coder", "%42\n"))

    def test_panes_to_close_selects_running_alive_in_roleset(self) -> None:
        rows = [
            {"role": "phase_planner", "phase": "01", "pane_id": "%41", "started_at": "t", "last_seen": "t", "status": "running"},
            {"role": "phase_reviewer", "phase": "01", "pane_id": "%43", "started_at": "t", "last_seen": "t", "status": "running"},
        ]
        self.assertEqual(lr.panes_to_close(rows, lr.PHASE_TRANSIENT_ROLES, "%41\n%43\n%7\n"), ["%41", "%43"])

    def test_panes_to_close_excludes_closed_status(self) -> None:
        rows = [{"role": "phase_reviewer", "phase": "01", "pane_id": "%43", "started_at": "t", "last_seen": "t", "status": "closed"}]
        self.assertEqual(lr.panes_to_close(rows, lr.PHASE_TRANSIENT_ROLES, "%43\n"), [])

    def test_panes_to_close_excludes_dead_pane(self) -> None:
        rows = [{"role": "phase_reviewer", "phase": "01", "pane_id": "%43", "started_at": "t", "last_seen": "t", "status": "running"}]
        self.assertEqual(lr.panes_to_close(rows, lr.PHASE_TRANSIENT_ROLES, "%7\n"), [])  # %43 不在活 pane

    def test_panes_to_close_role_set_decides_coder(self) -> None:
        # coder 不在 PHASE_TRANSIENT_ROLES → phase 收口不关 coder(它由下一 phase 的 fresh launch 关,L6); WORKER_ROLES(run 收尾)才关
        rows = [{"role": "phase_coder", "phase": "01", "pane_id": "%42", "started_at": "t", "last_seen": "t", "status": "running"}]
        self.assertEqual(lr.panes_to_close(rows, lr.PHASE_TRANSIENT_ROLES, "%42\n"), [])
        self.assertEqual(lr.panes_to_close(rows, lr.WORKER_ROLES, "%42\n"), ["%42"])

    def test_panes_to_close_empty_rows(self) -> None:
        self.assertEqual(lr.panes_to_close([], lr.WORKER_ROLES, "%42\n"), [])

    def test_role_sets_membership(self) -> None:
        self.assertNotIn("phase_coder", lr.PHASE_TRANSIENT_ROLES)
        self.assertIn("phase_planner", lr.PHASE_TRANSIENT_ROLES)
        # 双路 + 旧单路 reviewer 都在 transient/worker 里
        for r in ("phase_reviewer", "phase_reviewer_a", "phase_reviewer_b"):
            self.assertIn(r, lr.PHASE_TRANSIENT_ROLES)
            self.assertIn(r, lr.WORKER_ROLES)
        for r in ("phase_planner", "phase_coder"):
            self.assertIn(r, lr.WORKER_ROLES)

    def test_pane_registered_matches_any_status_row(self) -> None:
        # send 护栏: pane 在 SESSIONS 注册过(任意状态)才许发; 用户自己的 pane 不在表里
        rows = lr.parse_sessions(SESSIONS_SAMPLE)
        self.assertTrue(lr.pane_registered(rows, "%42"))
        self.assertTrue(lr.pane_registered(rows, "%43"))  # closed 行也算注册过
        self.assertFalse(lr.pane_registered(rows, "%7"))  # 活着但不是 worker → 拒

    def test_reconcile_marks_dead_running_row_closed(self) -> None:
        # pane 已不在 tmux 但行仍 running(非 lr 路径关掉) → 标 closed + 更新 last_seen
        rows = [{"role": "phase_planner", "phase": "02", "pane_id": "%742", "started_at": "t", "last_seen": "t", "status": "running"}]
        new_rows, reconciled = lr.reconcile_dead_sessions(rows, "%743\n%747\n", "NOW")
        self.assertEqual(reconciled, ["%742"])
        self.assertEqual(new_rows[0]["status"], "closed")
        self.assertEqual(new_rows[0]["last_seen"], "NOW")

    def test_reconcile_leaves_live_running_and_already_closed_rows(self) -> None:
        rows = [
            {"role": "phase_coder", "phase": "02", "pane_id": "%743", "started_at": "t", "last_seen": "t", "status": "running"},
            {"role": "phase_planner", "phase": "01", "pane_id": "%738", "started_at": "t", "last_seen": "t", "status": "closed"},
        ]
        new_rows, reconciled = lr.reconcile_dead_sessions(rows, "%743\n", "NOW")
        self.assertEqual(reconciled, [])  # %743 还活着不动; %738 已 closed(即便不在活 pane 列表)也不动
        self.assertEqual([r["status"] for r in new_rows], ["running", "closed"])
        self.assertEqual([r["last_seen"] for r in new_rows], ["t", "t"])


class ResolvePhaseDirTests(unittest.TestCase):
    def _ws(self, tmp: str, *dirs: str) -> Path:
        ws = Path(tmp)
        for d in dirs:
            (ws / "phases" / d).mkdir(parents=True)
        return ws

    def test_resolves_numeric_id_to_slug_dir(self) -> None:
        # 核心 bug: 命令传数字 03, scaffold 建的是 03_<slug> → 解析到真目录
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp, "03_campaign_manager_and_admin_permission")
            self.assertEqual(lr.resolve_phase_dir(ws, "03").name, "03_campaign_manager_and_admin_permission")

    def test_exact_dir_wins_over_slug_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp, "03", "03_campaign_manager_and_admin_permission")
            self.assertEqual(lr.resolve_phase_dir(ws, "03").name, "03")  # 精确匹配优先

    def test_full_slug_id_resolves_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp, "03_foo")
            self.assertEqual(lr.resolve_phase_dir(ws, "03_foo").name, "03_foo")

    def test_ambiguous_prefix_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp, "03_foo", "03_bar")  # 两个 03_* → 不静默猜
            with self.assertRaises(RuntimeError):
                lr.resolve_phase_dir(ws, "03")

    def test_missing_falls_back_to_literal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp)  # phases/ 空
            self.assertEqual(lr.resolve_phase_dir(ws, "07").name, "07")  # 回落字面, 让调用方暴露 not found


class LaunchCommandTests(unittest.TestCase):
    def test_kilo_launch_uses_model_no_variant(self) -> None:
        # L19: 不注入 variant
        cmd = lr.launch_command({"backend": "kilo", "model": "cliproxy/gpt-5.5"})
        self.assertEqual(cmd, "kilo -m cliproxy/gpt-5.5")

    def test_claude_cli_returns_none_for_interactive_shell(self) -> None:
        cmd = lr.launch_command({"backend": "claude_cli", "cmd": "claude --dangerously-skip-permissions"})
        self.assertIsNone(cmd)


class VerifySummaryTests(unittest.TestCase):
    def test_exit_zero_is_ok(self) -> None:
        s = lr.verify_summary(0, "ran 12 tests\nok\n")
        self.assertTrue(s["ok"])
        self.assertEqual(s["exit"], 0)

    def test_nonzero_exit_not_ok(self) -> None:
        s = lr.verify_summary(1, "FAIL: TestThing\n")
        self.assertFalse(s["ok"])
        self.assertEqual(s["exit"], 1)

    def test_keeps_output_tail_for_evidence(self) -> None:
        s = lr.verify_summary(0, "line\n" * 500)
        self.assertIn("line", s["output_tail"])
        self.assertLessEqual(len(s["output_tail"].splitlines()), 100)


REVIEW_SAMPLE = """# Phase 02 Review

## Debugger

### [blocker] Backend drops bundled deliverable from Feishu writeback
Evidence: ...

### [should] Favorite auto-import path not given bundle treatment
This is borderline.

### [blocker] Second real blocker about dates
more text

### [nit] tiny style thing
"""


class ParseReviewBlockersTests(unittest.TestCase):
    def test_extracts_only_blocker_headings(self) -> None:
        blockers = lr.parse_review_blockers(REVIEW_SAMPLE)
        self.assertEqual(len(blockers), 2)
        self.assertIn("Feishu writeback", blockers[0][1])
        self.assertIsNone(blockers[0][0])  # 无编号的历史格式 → id None

    def test_ignores_should_and_nit(self) -> None:
        joined = " ".join(desc for _, desc in lr.parse_review_blockers(REVIEW_SAMPLE))
        self.assertNotIn("Favorite", joined)
        self.assertNotIn("style thing", joined)

    def test_no_blockers_returns_empty(self) -> None:
        self.assertEqual(lr.parse_review_blockers("# clean\nlooks good, no blockers\n"), [])

    def test_extracts_blocker_ids(self) -> None:
        text = "### [blocker B1] drops field\n### [should] minor\n### [blocker B2] race\n"
        self.assertEqual(lr.parse_review_blockers(text),
                         [("B1", "drops field"), ("B2", "race")])


ACK_SAMPLE = """# Phase 02 Review Ack

## Findings
- [agree] [blocker] Backend drop ... narrative here

## Blocker Resolutions
- [fixed] Backend now keeps bundled deliverable in Feishu writeback (commit abc)
- [deferred] Favorite import schema change too broad, moved to BACKLOG
- [fixed] Date constraint added
"""


class ParseAckResolutionsTests(unittest.TestCase):
    def test_counts_fixed_and_deferred_in_resolutions_section(self) -> None:
        r = lr.parse_ack_resolutions(ACK_SAMPLE)
        self.assertEqual(r["fixed"], 2)
        self.assertEqual(r["deferred"], 1)

    def test_ignores_agree_lines_outside_resolutions_section(self) -> None:
        # `[agree] [blocker]` 在 Findings 段, 不应被当成 resolution
        r = lr.parse_ack_resolutions(ACK_SAMPLE)
        self.assertEqual(r["fixed"] + r["deferred"], 3)

    def test_missing_section_is_zero(self) -> None:
        r = lr.parse_ack_resolutions("# ack\n- [agree] something\n")
        self.assertEqual((r["fixed"], r["deferred"], r["fixed_lines"]), (0, 0, []))

    def test_keeps_fixed_lines_for_id_matching(self) -> None:
        r = lr.parse_ack_resolutions(ACK_SAMPLE)
        self.assertEqual(len(r["fixed_lines"]), 2)
        self.assertIn("Feishu writeback", r["fixed_lines"][0])


class PhaseGateTests(unittest.TestCase):
    OK_VERIFY = {"ok": True, "exit": 0, "output_tail": "ok"}
    ONE_BLOCKER = "### [blocker] backend drops field\n"
    ACK_FIXED = "## Blocker Resolutions\n- [fixed] backend keeps field\n"
    ACK_DEFERRED = "## Blocker Resolutions\n- [deferred] too broad\n"

    def test_all_pass_when_verify_ok_and_blocker_fixed(self) -> None:
        g = lr.phase_gate(self.OK_VERIFY, self.ONE_BLOCKER, self.ACK_FIXED)
        self.assertTrue(g["ok"])
        self.assertEqual(g["reasons"], [])

    def test_blocks_when_verify_missing(self) -> None:
        g = lr.phase_gate(None, "", "")
        self.assertFalse(g["ok"])
        self.assertTrue(any("验证" in r for r in g["reasons"]))

    def test_blocks_when_verify_failed(self) -> None:
        g = lr.phase_gate({"ok": False, "exit": 1, "output_tail": "FAIL"}, "", "")
        self.assertFalse(g["ok"])
        self.assertTrue(any("验证" in r for r in g["reasons"]))

    def test_blocks_when_blocker_unresolved(self) -> None:
        g = lr.phase_gate(self.OK_VERIFY, self.ONE_BLOCKER, "## Blocker Resolutions\n")
        self.assertFalse(g["ok"])
        self.assertTrue(any("blocker" in r.lower() for r in g["reasons"]))

    def test_blocks_when_blocker_deferred_not_fixed(self) -> None:
        g = lr.phase_gate(self.OK_VERIFY, self.ONE_BLOCKER, self.ACK_DEFERRED)
        self.assertFalse(g["ok"])
        self.assertTrue(any("blocker" in r.lower() for r in g["reasons"]))

    def test_passes_with_no_blockers(self) -> None:
        g = lr.phase_gate(self.OK_VERIFY, "looks good\n", "")
        self.assertTrue(g["ok"])

    def test_blocks_when_review_missing(self) -> None:
        # reviewer 环节不可静默跳过: review.md 缺失/为空 → 即使 verify 过也阻塞
        g = lr.phase_gate(self.OK_VERIFY, "", "")
        self.assertFalse(g["ok"])
        self.assertTrue(any("review" in r.lower() for r in g["reasons"]))

    def test_id_reconciliation_passes_when_each_id_fixed(self) -> None:
        review = "### [blocker B1] drops field\n### [blocker B2] race\n"
        ack = "## Blocker Resolutions\n- [fixed] B1 kept field\n- [fixed] B2 added lock\n"
        self.assertTrue(lr.phase_gate(self.OK_VERIFY, review, ack)["ok"])

    def test_id_reconciliation_names_missing_blocker(self) -> None:
        # 多写 [fixed] 行凑数也对不上: B2 没被任何 fixed 行提及 → 点名卡门
        review = "### [blocker B1] drops field\n### [blocker B2] race\n"
        ack = "## Blocker Resolutions\n- [fixed] B1 kept field\n- [fixed] B1 再修一次\n"
        g = lr.phase_gate(self.OK_VERIFY, review, ack)
        self.assertFalse(g["ok"])
        self.assertTrue(any("B2" in r for r in g["reasons"]))

    def test_id_reconciliation_dedupes_repeated_mention(self) -> None:
        # 正文再次引用同一 blocker(同 ID) → 不重复计数, 一行 fixed 即可
        review = "### [blocker B1] drops field\n回顾: [blocker B1] 同上,见 summary\n"
        ack = "## Blocker Resolutions\n- [fixed] B1 kept field\n"
        self.assertTrue(lr.phase_gate(self.OK_VERIFY, review, ack)["ok"])

    def test_mixed_unnumbered_blockers_fall_back_to_count(self) -> None:
        # 有未编号 blocker → 回落计数对账(历史 review 兼容)
        review = "### [blocker B1] a\n### [blocker] b\n"
        ack = "## Blocker Resolutions\n- [fixed] B1 done\n"
        g = lr.phase_gate(self.OK_VERIFY, review, ack)
        self.assertFalse(g["ok"])  # 2 个 blocker 只有 1 个 fixed
        ack2 = "## Blocker Resolutions\n- [fixed] B1 done\n- [fixed] b done\n"
        self.assertTrue(lr.phase_gate(self.OK_VERIFY, review, ack2)["ok"])


class DualReviewGateTests(unittest.TestCase):
    """双路 reviewer + [rejected] 裁决的门禁测试。"""
    OK_VERIFY = {"ok": True, "exit": 0, "output_tail": "ok"}

    def test_dual_review_both_blockers_fixed(self) -> None:
        reviews = {
            "a": "### [blocker B1] drops field\n",
            "b": "### [blocker B1] race condition\n",
        }
        ack = "## Blocker Resolutions\n- [fixed] A:B1 kept field\n- [fixed] B:B1 added lock\n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertTrue(g["ok"])

    def test_dual_review_missing_resolution_blocks(self) -> None:
        reviews = {
            "a": "### [blocker B1] drops field\n",
            "b": "### [blocker B1] race\n### [blocker B2] null check\n",
        }
        ack = "## Blocker Resolutions\n- [fixed] A:B1 kept field\n- [fixed] B:B1 lock\n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertFalse(g["ok"])
        self.assertTrue(any("B:B2" in r for r in g["reasons"]))

    def test_rejected_counts_as_resolved(self) -> None:
        reviews = {
            "a": "### [blocker B1] drops field\n",
            "b": "### [blocker B1] race\n",
        }
        ack = "## Blocker Resolutions\n- [fixed] A:B1 kept field\n- [rejected] B:B1 not a real issue\n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertTrue(g["ok"])

    def test_deferred_still_blocks_in_dual(self) -> None:
        reviews = {"a": "### [blocker B1] x\n", "b": ""}
        ack = "## Blocker Resolutions\n- [deferred] A:B1 later\n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertFalse(g["ok"])

    def test_one_route_empty_degrades_gracefully(self) -> None:
        reviews = {"a": "### [blocker B1] field\n", "b": ""}
        ack = "## Blocker Resolutions\n- [fixed] A:B1 done\n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertTrue(g["ok"])

    def test_both_routes_empty_blocks(self) -> None:
        reviews = {"a": "", "b": ""}
        g = lr.phase_gate(self.OK_VERIFY, reviews, "")
        self.assertFalse(g["ok"])
        self.assertTrue(any("review" in r.lower() for r in g["reasons"]))

    def test_single_route_no_blockers_passes(self) -> None:
        reviews = {"a": "looks good, no issues\n", "b": "clean code\n"}
        g = lr.phase_gate(self.OK_VERIFY, reviews, "")
        self.assertTrue(g["ok"])

    def test_legacy_string_still_works(self) -> None:
        g = lr.phase_gate(self.OK_VERIFY, "### [blocker B1] x\n",
                           "## Blocker Resolutions\n- [fixed] B1 done\n")
        self.assertTrue(g["ok"])

    def test_rejected_without_reason_blocks(self) -> None:
        reviews = {"a": "### [blocker B1] field\n", "b": ""}
        ack = "## Blocker Resolutions\n- [rejected] A:B1\n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertFalse(g["ok"])
        self.assertTrue(any("缺理由" in r for r in g["reasons"]))

    def test_rejected_with_reason_passes(self) -> None:
        reviews = {"a": "### [blocker B1] field\n", "b": ""}
        ack = "## Blocker Resolutions\n- [rejected] A:B1 not a real issue because X\n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertTrue(g["ok"])

    def test_rejected_with_only_whitespace_after_id_blocks(self) -> None:
        reviews = {"a": "### [blocker B1] field\n", "b": ""}
        ack = "## Blocker Resolutions\n- [rejected] A:B1   \n"
        g = lr.phase_gate(self.OK_VERIFY, reviews, ack)
        self.assertFalse(g["ok"])


class ParseAckRejectedTests(unittest.TestCase):
    def test_counts_rejected_lines(self) -> None:
        ack = ("## Blocker Resolutions\n"
               "- [fixed] A:B1 kept field\n"
               "- [rejected] B:B1 not real\n"
               "- [rejected] B:B2 disagree\n")
        r = lr.parse_ack_resolutions(ack)
        self.assertEqual(r["fixed"], 1)
        self.assertEqual(r["rejected"], 2)
        self.assertEqual(len(r["rejected_lines"]), 2)

    def test_rejected_outside_section_ignored(self) -> None:
        ack = "## Findings\n- [rejected] disagree\n## Blocker Resolutions\n- [fixed] B1 done\n"
        r = lr.parse_ack_resolutions(ack)
        self.assertEqual(r["rejected"], 0)
        self.assertEqual(r["fixed"], 1)


class DualReviewConfigTests(unittest.TestCase):
    def test_is_dual_review_detects_dual(self) -> None:
        self.assertTrue(lr.is_dual_review_config(valid_config_dual()["roles"]))

    def test_is_dual_review_detects_legacy(self) -> None:
        self.assertFalse(lr.is_dual_review_config(valid_config_legacy()["roles"]))

    def test_reviewer_suffix_extracts_a_b(self) -> None:
        self.assertEqual(lr._reviewer_suffix("phase_reviewer_a"), "_a")
        self.assertEqual(lr._reviewer_suffix("phase_reviewer_b"), "_b")
        self.assertEqual(lr._reviewer_suffix("scaffold_reviewer_a"), "_a")
        self.assertIsNone(lr._reviewer_suffix("phase_reviewer"))
        self.assertIsNone(lr._reviewer_suffix("phase_coder"))

    def test_prompt_file_maps_dual_to_base(self) -> None:
        p = lr._prompt_file_for("phase_reviewer_a")
        self.assertEqual(p.name, "phase_reviewer.md")
        p = lr._prompt_file_for("scaffold_reviewer_b")
        self.assertEqual(p.name, "scaffold_reviewer.md")

    def test_prompt_file_keeps_non_reviewer(self) -> None:
        p = lr._prompt_file_for("phase_coder")
        self.assertEqual(p.name, "phase_coder.md")

    def test_pane_title_dual_reviewer(self) -> None:
        self.assertEqual(lr.pane_title("phase_reviewer_a", "02"), "phase 02 reviewer_a")
        self.assertEqual(lr.pane_title("phase_reviewer_b", "02"), "phase 02 reviewer_b")

    def test_scaffold_reviewer_output_files_are_absolute(self) -> None:
        ws = Path("/tmp/ws")
        result = lr._reviewer_output_files("scaffold_reviewer_a", "0", ws)
        self.assertIsNotNone(result)
        review_file, status_file = result
        self.assertTrue(review_file.startswith("/"), f"review path not absolute: {review_file}")
        self.assertTrue(status_file.startswith("/"), f"status path not absolute: {status_file}")
        self.assertIn("SCAFFOLD_REVIEW_A.md", review_file)
        self.assertIn("scaffold_reviewer_a.status", status_file)

    def test_phase_reviewer_output_files_are_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "phases" / "02_foo").mkdir(parents=True)
            result = lr._reviewer_output_files("phase_reviewer_b", "02", ws)
            self.assertIsNotNone(result)
            review_file, status_file = result
            self.assertTrue(review_file.startswith("/"), f"review path not absolute: {review_file}")
            self.assertIn("review_b.md", review_file)
            self.assertIn("phase_reviewer_b.status", status_file)

    def test_non_reviewer_returns_none(self) -> None:
        self.assertIsNone(lr._reviewer_output_files("phase_coder", "02", Path("/tmp/ws")))


class ParseStatusCommitTests(unittest.TestCase):
    def test_done_commit_extracts_hash(self) -> None:
        self.assertEqual(lr.parse_status_commit("done commit=2e49a706\n"), "2e49a706")

    def test_done_impl_is_not_commit_evidence(self) -> None:
        # 两段式信号: `done impl` 是"实现完等 review"的中间态, 不算收口证据
        self.assertIsNone(lr.parse_status_commit("done impl"))

    def test_coding_and_blocked_are_none(self) -> None:
        self.assertIsNone(lr.parse_status_commit("coding"))
        self.assertIsNone(lr.parse_status_commit("blocked need creds"))

    def test_non_hex_hash_rejected(self) -> None:
        self.assertIsNone(lr.parse_status_commit("done commit=not-a-hash"))

    def test_assignment_form_still_extracts(self) -> None:
        # prompt 字面回写(`phase_coder.status = done commit=...`)也能取到 hash
        self.assertEqual(lr.parse_status_commit("phase_coder.status = done commit=abc123def"), "abc123def")


class UncheckedPhasesTests(unittest.TestCase):
    def test_lists_unchecked_phase_ids(self) -> None:
        self.assertEqual(lr.unchecked_phases(FIX_PLAN_SAMPLE), ["01", "02", "03"])

    def test_checked_phases_excluded(self) -> None:
        text = "# Fix Plan\n\n- [x] 01 a\n- [ ] 02 b\n- [x] 03 c\n"
        self.assertEqual(lr.unchecked_phases(text), ["02"])

    def test_all_checked_is_empty(self) -> None:
        self.assertEqual(lr.unchecked_phases("- [x] 01 a\n- [x] 02 b\n"), [])


FIX_PLAN_SAMPLE = """# Fix Plan

- [ ] 01 Contract redline
- [ ] 02 Import quote parsing
- [ ] 03 Field config
"""


class MarkPhaseDoneTests(unittest.TestCase):
    def test_flips_matching_phase_checkbox(self) -> None:
        out = lr.mark_phase_done(FIX_PLAN_SAMPLE, "02")
        self.assertIn("- [x] 02 Import quote parsing", out)

    def test_leaves_other_phases_untouched(self) -> None:
        out = lr.mark_phase_done(FIX_PLAN_SAMPLE, "02")
        self.assertIn("- [ ] 01 Contract redline", out)
        self.assertIn("- [ ] 03 Field config", out)

    def test_unknown_phase_returns_text_unchanged(self) -> None:
        self.assertEqual(lr.mark_phase_done(FIX_PLAN_SAMPLE, "09"), FIX_PLAN_SAMPLE)


class AcceptanceGateTests(unittest.TestCase):
    def test_passes_when_acceptance_ran_ok(self) -> None:
        g = lr.acceptance_gate({"ok": True, "exit": 0, "output_tail": "all green"})
        self.assertTrue(g["ok"])
        self.assertEqual(g["reasons"], [])

    def test_blocks_when_acceptance_missing(self) -> None:
        g = lr.acceptance_gate(None)
        self.assertFalse(g["ok"])
        self.assertTrue(any("acceptance" in r.lower() for r in g["reasons"]))

    def test_blocks_when_acceptance_failed(self) -> None:
        g = lr.acceptance_gate({"ok": False, "exit": 2, "output_tail": "FAIL"})
        self.assertFalse(g["ok"])


class StuckDetectionTests(unittest.TestCase):
    """L26 卡死检测纯函数: 指纹稳定性 + 计数转换(同指纹累加/换指纹重置/通过清零)。"""

    def test_passing_verify_has_no_fingerprint(self) -> None:
        self.assertIsNone(lr.verify_fingerprint({"ok": True, "exit": 0, "output_tail": "ok"}))
        self.assertIsNone(lr.verify_fingerprint(None))

    def test_same_failure_same_fingerprint_despite_volatile_numbers(self) -> None:
        # 行号/耗时/计数变化不应改变指纹(同一个失败)
        a = {"ok": False, "exit": 1, "output_tail": "FAIL test_login at line 42 (0.13s)"}
        b = {"ok": False, "exit": 1, "output_tail": "FAIL test_login at line 99 (1.87s)"}
        self.assertEqual(lr.verify_fingerprint(a), lr.verify_fingerprint(b))

    def test_different_failure_different_fingerprint(self) -> None:
        a = {"ok": False, "exit": 1, "output_tail": "FAIL test_login assertion failed"}
        b = {"ok": False, "exit": 1, "output_tail": "FAIL test_logout assertion failed"}
        self.assertNotEqual(lr.verify_fingerprint(a), lr.verify_fingerprint(b))

    def test_update_same_fingerprint_accumulates(self) -> None:
        s1 = lr.update_stuck({}, "abc123")
        self.assertEqual(s1["consecutive_fail"], 1)
        s2 = lr.update_stuck(s1, "abc123")
        self.assertEqual(s2["consecutive_fail"], 2)

    def test_update_changed_fingerprint_resets_to_one(self) -> None:
        # 错误在演化 = 还在推进, 不算原地打转
        s = lr.update_stuck({"consecutive_fail": 3, "fingerprint": "old"}, "new")
        self.assertEqual(s["consecutive_fail"], 1)
        self.assertEqual(s["fingerprint"], "new")

    def test_update_pass_clears_counter(self) -> None:
        s = lr.update_stuck({"consecutive_fail": 5, "fingerprint": "x"}, None)
        self.assertEqual(s["consecutive_fail"], 0)
        self.assertIsNone(s["fingerprint"])


class SummarizeMetricsTests(unittest.TestCase):
    def test_aggregates_run_and_per_phase(self) -> None:
        records = [
            {"event": "verify", "phase": "01", "ok": False, "fail_streak": 1},
            {"event": "verify", "phase": "01", "ok": True, "fail_streak": 0},
            {"event": "complete_phase", "phase": "01"},
            {"event": "verify", "phase": "02", "ok": False, "fail_streak": 1},
            {"event": "complete_run"},
        ]
        s = lr.summarize_metrics(records)
        self.assertEqual(s["verify_attempts"], 3)
        self.assertEqual(s["verify_passes"], 1)
        self.assertEqual(s["verify_fails"], 2)
        self.assertEqual(s["phases_completed"], 1)
        self.assertTrue(s["run_completed"])
        self.assertTrue(s["per_phase"]["01"]["completed"])
        self.assertFalse(s["per_phase"]["02"]["completed"])

    def test_empty_stream(self) -> None:
        s = lr.summarize_metrics([])
        self.assertEqual(s["verify_attempts"], 0)
        self.assertFalse(s["run_completed"])


class GateCommandIntegrationTests(unittest.TestCase):
    """side-effecting 命令用临时 workspace 集成测(verify 真跑脚本、complete-phase 真翻 fix_plan)。"""

    def _ws(self, tmp: Path) -> Path:
        ws = tmp / "ws"
        (ws / "phases" / "02").mkdir(parents=True)
        # 同目录当 worktree(in-place 形态), verify.sh 在此 cwd 运行
        (ws / "state.json").write_text(json.dumps({
            "slug": "demo", "phase": 2, "state": "develop",
            "worktree_path": str(ws), "branch": "fix/demo",
        }), encoding="utf-8")
        (ws / "fix_plan.md").write_text("# Fix Plan\n\n- [ ] 01 a\n- [ ] 02 b\n", encoding="utf-8")
        (ws / "logs.md").write_text("# Logs\n", encoding="utf-8")
        return ws

    def _run(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = lr.main(argv)
        return code, buf.getvalue()

    def _git_commit(self, ws: Path) -> str:
        """把 ws 变成有一个 commit 的 git 仓库, 返回 HEAD hash(commit 证据门禁用)。"""
        env_cfg = ["-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q"], cwd=ws, check=True, capture_output=True)
        subprocess.run(["git", *env_cfg, "commit", "--allow-empty", "-q", "-m", "phase"],
                       cwd=ws, check=True, capture_output=True)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ws, check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_verify_records_passing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "verify.sh").write_text("echo ran tests\nexit 0\n", encoding="utf-8")
            code, _ = self._run(["verify", "--workspace", str(ws), "--phase", "02"])
            data = json.loads((ws / "phases" / "02" / "verify.json").read_text())
            self.assertTrue(data["ok"])
            self.assertEqual(code, 0)

    def test_verify_records_failing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "verify.sh").write_text("echo boom\nexit 1\n", encoding="utf-8")
            code, _ = self._run(["verify", "--workspace", str(ws), "--phase", "02"])
            data = json.loads((ws / "phases" / "02" / "verify.json").read_text())
            self.assertFalse(data["ok"])
            self.assertEqual(code, 2)

    def test_complete_phase_refuses_when_verify_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "review.md").write_text("looks good\n", encoding="utf-8")
            code, out = self._run(["complete-phase", "--workspace", str(ws), "--phase", "02"])
            self.assertEqual(code, 2)
            # 未通过门禁 → fix_plan 不许翻
            self.assertIn("- [ ] 02 b", (ws / "fix_plan.md").read_text())

    def test_complete_phase_refuses_on_unresolved_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "verify.json").write_text(
                json.dumps({"ok": True, "exit": 0, "output_tail": "ok"}), encoding="utf-8")
            (ws / "phases" / "02" / "review.md").write_text("### [blocker] x not fixed\n", encoding="utf-8")
            (ws / "phases" / "02" / "ack.md").write_text("## Blocker Resolutions\n- [deferred] later\n", encoding="utf-8")
            code, _ = self._run(["complete-phase", "--workspace", str(ws), "--phase", "02"])
            self.assertEqual(code, 2)
            self.assertIn("- [ ] 02 b", (ws / "fix_plan.md").read_text())

    def test_complete_phase_marks_done_when_gate_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            head = self._git_commit(ws)
            (ws / "phases" / "02" / "verify.json").write_text(
                json.dumps({"ok": True, "exit": 0, "output_tail": "ok"}), encoding="utf-8")
            (ws / "phases" / "02" / "review.md").write_text("### [blocker] x\n", encoding="utf-8")
            (ws / "phases" / "02" / "ack.md").write_text("## Blocker Resolutions\n- [fixed] done\n", encoding="utf-8")
            (ws / "phases" / "02" / "phase_coder.status").write_text(f"done commit={head}\n", encoding="utf-8")
            code, _ = self._run(["complete-phase", "--workspace", str(ws), "--phase", "02"])
            self.assertEqual(code, 0)
            self.assertIn("- [x] 02 b", (ws / "fix_plan.md").read_text())
            # 进度落进 state.json(resume 不再永远显示 phase=0)
            self.assertEqual(json.loads((ws / "state.json").read_text())["phase"], "02")

    def test_complete_phase_refuses_without_commit_evidence(self) -> None:
        # L14 机器证据: verify/review/ack 全过, 但 status 没给真实 commit → 拒绝
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            self._git_commit(ws)
            (ws / "phases" / "02" / "verify.json").write_text(
                json.dumps({"ok": True, "exit": 0, "output_tail": "ok"}), encoding="utf-8")
            (ws / "phases" / "02" / "review.md").write_text("no blockers, clean\n", encoding="utf-8")
            (ws / "phases" / "02" / "phase_coder.status").write_text("done impl\n", encoding="utf-8")
            code, _ = self._run(["complete-phase", "--workspace", str(ws), "--phase", "02"])
            self.assertEqual(code, 2)
            self.assertIn("- [ ] 02 b", (ws / "fix_plan.md").read_text())

    def test_complete_phase_refuses_fabricated_commit(self) -> None:
        # status 声明的 hash 不在仓库里(编造) → 拒绝
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            self._git_commit(ws)
            (ws / "phases" / "02" / "verify.json").write_text(
                json.dumps({"ok": True, "exit": 0, "output_tail": "ok"}), encoding="utf-8")
            (ws / "phases" / "02" / "review.md").write_text("clean\n", encoding="utf-8")
            (ws / "phases" / "02" / "phase_coder.status").write_text("done commit=deadbeef00\n", encoding="utf-8")
            code, _ = self._run(["complete-phase", "--workspace", str(ws), "--phase", "02"])
            self.assertEqual(code, 2)
            self.assertIn("- [ ] 02 b", (ws / "fix_plan.md").read_text())

    def test_reset_status_writes_coding(self) -> None:
        # orchestrator 发 review 前清 stale `done impl`
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "phase_coder.status").write_text("done impl\n", encoding="utf-8")
            code, _ = self._run(["reset-status", "--workspace", str(ws), "--phase", "02", "--role", "phase_coder"])
            self.assertEqual(code, 0)
            self.assertEqual((ws / "phases" / "02" / "phase_coder.status").read_text(), "coding\n")

    def test_complete_run_refuses_without_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            code, _ = self._run(["complete-run", "--workspace", str(ws)])
            self.assertEqual(code, 2)
            self.assertNotEqual(json.loads((ws / "state.json").read_text())["state"], "completed")

    def test_complete_run_refuses_with_unchecked_phases(self) -> None:
        # acceptance 过了也不能跳 phase: fix_plan 还有未勾项 → 拒绝
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "acceptance.json").write_text(
                json.dumps({"ok": True, "exit": 0, "output_tail": "green"}), encoding="utf-8")
            code, _ = self._run(["complete-run", "--workspace", str(ws)])
            self.assertEqual(code, 2)
            self.assertNotEqual(json.loads((ws / "state.json").read_text())["state"], "completed")

    def test_complete_run_sets_completed_when_acceptance_ok(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "fix_plan.md").write_text("# Fix Plan\n\n- [x] 01 a\n- [x] 02 b\n", encoding="utf-8")
            (ws / "acceptance.json").write_text(
                json.dumps({"ok": True, "exit": 0, "output_tail": "green"}), encoding="utf-8")
            code, _ = self._run(["complete-run", "--workspace", str(ws)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads((ws / "state.json").read_text())["state"], "completed")

    def test_verify_persists_stuck_and_emits_metric(self) -> None:
        # L26: 同一失败连跑两次 → stuck.json 计数到 2 + STUCK 警告 + metrics.jsonl 各记一条
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "verify.sh").write_text("echo 'FAIL test_x assertion'\nexit 1\n", encoding="utf-8")
            self._run(["verify", "--workspace", str(ws), "--phase", "02"])
            code, out = self._run(["verify", "--workspace", str(ws), "--phase", "02"])
            self.assertEqual(code, 2)
            stuck = json.loads((ws / "phases" / "02" / "stuck.json").read_text())
            self.assertEqual(stuck["consecutive_fail"], 2)
            self.assertIn("STUCK", out)
            metrics = [json.loads(ln) for ln in (ws / "metrics.jsonl").read_text().splitlines() if ln.strip()]
            self.assertEqual(len([m for m in metrics if m.get("event") == "verify"]), 2)
            self.assertEqual(metrics[-1]["fail_streak"], 2)

    def test_verify_pass_clears_stuck(self) -> None:
        # 先失败累计, 再通过 → 计数清零, 不再报 STUCK
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "verify.sh").write_text("echo 'FAIL x'\nexit 1\n", encoding="utf-8")
            self._run(["verify", "--workspace", str(ws), "--phase", "02"])
            (ws / "phases" / "02" / "verify.sh").write_text("echo ok\nexit 0\n", encoding="utf-8")
            code, out = self._run(["verify", "--workspace", str(ws), "--phase", "02"])
            self.assertEqual(code, 0)
            self.assertNotIn("STUCK", out)
            stuck = json.loads((ws / "phases" / "02" / "stuck.json").read_text())
            self.assertEqual(stuck["consecutive_fail"], 0)

    def test_stats_summarizes_after_verify(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            (ws / "phases" / "02" / "verify.sh").write_text("echo ok\nexit 0\n", encoding="utf-8")
            self._run(["verify", "--workspace", str(ws), "--phase", "02"])
            code, out = self._run(["stats", "--workspace", str(ws)])
            self.assertEqual(code, 0)
            self.assertIn("phase 02", out)
            self.assertIn("1/1 pass", out)

    def test_stats_without_metrics_is_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            ws = self._ws(Path(d))
            code, out = self._run(["stats", "--workspace", str(ws)])
            self.assertEqual(code, 0)
            self.assertIn("尚无", out)


if __name__ == "__main__":
    unittest.main()

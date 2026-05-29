import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "dev-long-run-v2"))

import lr2  # noqa: E402


SESSIONS_SAMPLE = """# Sessions

| role | phase | pane_id | started_at | last_seen | status |
|---|---|---|---|---|---|
| phase_coder | 01 | %42 | 2026-05-29T10:00:00Z | 2026-05-29T10:45:00Z | running |
| phase_reviewer | 01 | %43 | 2026-05-29T10:50:00Z | 2026-05-29T10:55:00Z | closed |
"""


class SessionsParseTests(unittest.TestCase):
    def test_parse_returns_rows_as_dicts(self) -> None:
        rows = lr2.parse_sessions(SESSIONS_SAMPLE)
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
            lr2.parse_sessions(bad)

    def test_render_round_trips_through_parse(self) -> None:
        rows = lr2.parse_sessions(SESSIONS_SAMPLE)
        self.assertEqual(lr2.parse_sessions(lr2.render_sessions(rows)), rows)

    def test_render_has_header_and_is_human_readable(self) -> None:
        text = lr2.render_sessions([])
        self.assertIn("# Sessions", text)
        self.assertIn("| role | phase | pane_id | started_at | last_seen | status |", text)


class UpsertSessionTests(unittest.TestCase):
    def base_rows(self) -> list[dict[str, str]]:
        return lr2.parse_sessions(SESSIONS_SAMPLE)

    def test_upsert_updates_existing_pane_in_place(self) -> None:
        # 同一 pane_id(%42) 更新 last_seen/status, 不新增行
        rows = lr2.upsert_session(
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
        rows = lr2.upsert_session(
            self.base_rows(),
            {"role": "phase_planner", "phase": "02", "pane_id": "%99",
             "started_at": "2026-05-29T12:10:00Z", "last_seen": "2026-05-29T12:10:00Z", "status": "running"},
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["pane_id"], "%99")

    def test_upsert_rejects_incomplete_session(self) -> None:
        # Fail Fast: 缺列的 session dict 不能写进 SSOT
        with self.assertRaises(ValueError):
            lr2.upsert_session(self.base_rows(), {"role": "phase_coder", "pane_id": "%42"})


class NamingTests(unittest.TestCase):
    def test_slugify_makes_git_safe_slug(self) -> None:
        # 自由任务名 → 小写连字符, 去掉空格/特殊字符/git 非法字符
        self.assertEqual(lr2.slugify("Compliance Refactor!"), "compliance-refactor")
        self.assertEqual(lr2.slugify("auth/v2  fix"), "auth-v2-fix")

    def test_slugify_rejects_empty_result(self) -> None:
        # 全是特殊字符 → 无法产出 slug, Fail Fast
        with self.assertRaises(ValueError):
            lr2.slugify("///")

    def test_branch_name(self) -> None:
        self.assertEqual(lr2.branch_name("compliance"), "lr2/compliance")

    def test_worktree_path_is_sibling_of_repo(self) -> None:
        wt = lr2.worktree_path(Path("/home/u/myrepo"), "compliance")
        self.assertEqual(wt, Path("/home/u/myrepo-lr2-compliance"))

    def test_plan_worktree_new_creates_sibling_branch(self) -> None:
        plan = lr2.plan_worktree(Path("/home/u/repo"), "auth", in_place=False, current_branch="main")
        self.assertEqual(plan["branch"], "lr2/auth")
        self.assertEqual(plan["worktree_path"], "/home/u/repo-lr2-auth")
        self.assertTrue(plan["create"])

    def test_plan_worktree_in_place_uses_current_branch(self) -> None:
        # 接着做: 在当前 feature 分支 + 当前目录, 不新建
        plan = lr2.plan_worktree(Path("/home/u/repo"), "auth", in_place=True, current_branch="feature/x")
        self.assertEqual(plan["branch"], "feature/x")
        self.assertEqual(plan["worktree_path"], "/home/u/repo")
        self.assertFalse(plan["create"])

    def test_plan_worktree_in_place_refuses_main(self) -> None:
        # L16: 不在 main/master 上开发
        for b in ("main", "master", ""):
            with self.assertRaises(ValueError):
                lr2.plan_worktree(Path("/home/u/repo"), "auth", in_place=True, current_branch=b)


class ConfirmCommandTests(unittest.TestCase):
    def test_confirm_next_goes_to_develop(self) -> None:
        self.assertEqual(lr2.apply_confirm("wait_confirm", "confirm next"), "develop")

    def test_confirm_done_goes_to_wrapup(self) -> None:
        self.assertEqual(lr2.apply_confirm("wait_confirm", "confirm done"), "wrapup")

    def test_block_goes_to_blocked(self) -> None:
        self.assertEqual(lr2.apply_confirm("wait_confirm", "block"), "blocked")

    def test_command_only_valid_at_wait_confirm(self) -> None:
        # L7: confirm 命令只在 wait_confirm 状态合法; 其他状态拒绝(fail-closed)
        with self.assertRaises(ValueError):
            lr2.apply_confirm("develop", "confirm next")

    def test_unknown_command_rejected(self) -> None:
        with self.assertRaises(ValueError):
            lr2.apply_confirm("wait_confirm", "confirm everything")


def valid_config() -> dict:
    def role(backend, variant, autonomy, **extra):
        return {"backend": backend, "model": "m", "variant": variant, "autonomy": autonomy, **extra}
    cmd = "claude --dangerously-skip-permissions"
    return {
        "version": 2,
        "roles": {
            "scaffold_orchestrator": role("kilo", "xhigh", "medium"),
            "scaffold_reviewer": role("claude_cli", "max", "off", cmd=cmd),
            "loop_orchestrator": role("kilo", "low", "medium"),
            "phase_planner": role("kilo", "xhigh", "low"),
            "phase_coder": role("kilo", "high", "high"),
            "phase_reviewer": role("claude_cli", "max", "off", cmd=cmd),
        },
    }


class ConfigValidationTests(unittest.TestCase):
    def test_valid_config_passes(self) -> None:
        self.assertEqual(lr2.validate_config(valid_config()), valid_config())

    def test_missing_role_rejected(self) -> None:
        cfg = valid_config()
        del cfg["roles"]["phase_coder"]
        with self.assertRaises(ValueError):
            lr2.validate_config(cfg)

    def test_unknown_backend_rejected(self) -> None:
        cfg = valid_config()
        cfg["roles"]["phase_coder"]["backend"] = "gemini"
        with self.assertRaises(ValueError):
            lr2.validate_config(cfg)

    def test_bad_variant_rejected(self) -> None:
        cfg = valid_config()
        cfg["roles"]["phase_coder"]["variant"] = "turbo"
        with self.assertRaises(ValueError):
            lr2.validate_config(cfg)

    def test_bad_autonomy_rejected(self) -> None:
        cfg = valid_config()
        cfg["roles"]["phase_coder"]["autonomy"] = "full"
        with self.assertRaises(ValueError):
            lr2.validate_config(cfg)

    def test_claude_cli_role_requires_cmd(self) -> None:
        # claude_cli 走独立 CLI, 必须有 cmd(否则 launcher 不知怎么起)
        cfg = valid_config()
        del cfg["roles"]["phase_reviewer"]["cmd"]
        with self.assertRaises(ValueError):
            lr2.validate_config(cfg)


class WorkerStatusTests(unittest.TestCase):
    def test_done_with_detail(self) -> None:
        self.assertEqual(lr2.parse_worker_status("done commit=2e49a706\n"), ("done", "commit=2e49a706"))

    def test_blocked(self) -> None:
        self.assertEqual(lr2.parse_worker_status("blocked reviewer rejected all"), ("blocked", "reviewer rejected all"))

    def test_bare_state(self) -> None:
        self.assertEqual(lr2.parse_worker_status("coding"), ("coding", ""))

    def test_empty_is_unknown(self) -> None:
        self.assertEqual(lr2.parse_worker_status(""), ("unknown", ""))

    def test_garbage_is_unknown(self) -> None:
        # 不在已知 state 词表 → unknown(避免把 prose 误判成完成)
        self.assertEqual(lr2.parse_worker_status("almost done maybe")[0], "unknown")


class YamlLoaderTests(unittest.TestCase):
    def test_loads_generated_config_and_passes_validate(self) -> None:
        cfg = lr2.load_yaml(lr2.default_config_yaml("demo"))
        self.assertEqual(cfg["version"], 2)
        self.assertEqual(cfg["roles"]["phase_coder"]["backend"], "kilo")
        # claude_cli cmd 单引号标量正确解出
        self.assertEqual(cfg["roles"]["phase_reviewer"]["cmd"], "claude --dangerously-skip-permissions")
        # 生成的模板必须通过 schema 校验(round-trip)
        self.assertEqual(lr2.validate_config(cfg), cfg)

    def test_inline_comment_stripped_from_unquoted_scalar(self) -> None:
        cfg = lr2.load_yaml("version: 2  # the schema version\nroles:\n  x:\n    backend: kilo  # note\n")
        self.assertEqual(cfg["version"], 2)
        self.assertEqual(cfg["roles"]["x"]["backend"], "kilo")

    def test_bad_line_without_colon_raises(self) -> None:
        with self.assertRaises(ValueError):
            lr2.load_yaml("version 2\n")


class TmuxArgTests(unittest.TestCase):
    def test_split_window_targets_current_pane(self) -> None:
        # 在当前 window split 当前 pane(target=当前 TMUX_PANE), 不进别的 session/tab
        args = lr2.split_window_args("/wt", "split-down", "kilo -m m", target="%3")
        self.assertEqual(args[args.index("-t") + 1], "%3")
        self.assertIn("-v", args)
        self.assertIn("#{pane_id}", args)
        self.assertEqual(args[-1], "kilo -m m")

    def test_split_window_no_target_splits_current(self) -> None:
        args = lr2.split_window_args("/wt", "split-right", None)
        self.assertNotIn("-t", args)  # 无 target → tmux 默认 split 当前 pane
        self.assertIn("-h", args)

    def test_split_window_bad_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            lr2.split_window_args("/wt", "split-sideways", None)

    def test_paste_buffer_uses_bracketed_paste(self) -> None:
        # 多行 prompt 走 bracketed paste(-p), 不提前提交; Enter 由 send_to_pane 单独发
        self.assertEqual(lr2.paste_buffer_args("%5", "lr2dispatch"),
                         ["paste-buffer", "-p", "-b", "lr2dispatch", "-t", "%5"])

    def test_pane_is_alive(self) -> None:
        out = "%1\n%42\n%7\n"
        self.assertTrue(lr2.pane_is_alive(out, "%42"))
        self.assertFalse(lr2.pane_is_alive(out, "%99"))

    def test_find_live_role_pane_returns_running_alive(self) -> None:
        # L6(改): 找某 role 仍存活的 running pane(每 phase 开始时用来关掉上一个 coder)
        rows = [
            {"role": "phase_coder", "phase": "01", "pane_id": "%42", "started_at": "t", "last_seen": "t", "status": "running"},
            {"role": "phase_reviewer", "phase": "01", "pane_id": "%43", "started_at": "t", "last_seen": "t", "status": "closed"},
        ]
        self.assertEqual(lr2.find_live_role_pane(rows, "phase_coder", "%42\n%7\n"), "%42")

    def test_find_live_role_pane_none_when_dead(self) -> None:
        rows = [{"role": "phase_coder", "phase": "01", "pane_id": "%42", "started_at": "t", "last_seen": "t", "status": "running"}]
        self.assertIsNone(lr2.find_live_role_pane(rows, "phase_coder", "%7\n%8\n"))  # %42 不在活 pane 里

    def test_find_live_role_pane_none_when_absent(self) -> None:
        self.assertIsNone(lr2.find_live_role_pane([], "phase_coder", "%42\n"))


class LaunchCommandTests(unittest.TestCase):
    def test_kilo_launch_uses_model_no_variant(self) -> None:
        # L19: 不注入 variant
        cmd = lr2.launch_command({"backend": "kilo", "model": "cliproxy/gpt-5.5"})
        self.assertEqual(cmd, "kilo -m cliproxy/gpt-5.5")

    def test_claude_cli_returns_none_for_interactive_shell(self) -> None:
        cmd = lr2.launch_command({"backend": "claude_cli", "cmd": "claude --dangerously-skip-permissions"})
        self.assertIsNone(cmd)


if __name__ == "__main__":
    unittest.main()

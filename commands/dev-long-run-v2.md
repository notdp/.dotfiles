---
description: long-run-v2 多角色长任务编排入口(scaffold/develop/resume)
argument-hint: <scaffold --requirement <path> [--goal <g>] | develop --workspace <ws> | resume --workspace <ws>>
---

加载 `skills/long-run-v2/SKILL.md` 并执行对应子命令。harness: `skills/long-run-v2/lr2.py`。

子命令直通 `python3 skills/long-run-v2/lr2.py <args>`：

- `scaffold --requirement <path> [--goal <g>] [--repo-root .]`：建 worktree+分支+工作区，启动 scaffold orchestrator。
- `develop --workspace <ws>`：启动 loop orchestrator 进入逐 phase 开发循环。
- `resume --workspace <ws>`：读 state，校验 worktree + pane 存活，给恢复建议。

先决条件：用户已在某处写好 `REQUIREMENT.md`。约束见 SKILL.md（L14 逐 phase commit / L16 worktree 不碰 main / L19 默认思考等级 / 不 push）。

无参数或不确定子命令时，读 `skills/long-run-v2/SKILL.md` 与 `docs/specs/long-run-v2/overview.md` 后再决定。

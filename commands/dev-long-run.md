---
description: dev-long-run 多角色长任务编排入口(scaffold/develop/resume)
argument-hint: <scaffold --requirement <path> [--goal <g>] | develop --workspace <ws> | resume --workspace <ws>>
---

加载 `~/.dotfiles/coding-skills/dev-long-run/SKILL.md` 并执行对应子命令。harness: `~/.dotfiles/coding-skills/dev-long-run/lr.py`。

子命令直通(用绝对路径,从任意项目目录都能跑)：

```
python3 ~/.dotfiles/coding-skills/dev-long-run/lr.py <args>
```


- `scaffold --requirement <path> [--goal <g>] [--repo-root .]`：建 worktree+分支+工作区，进入 scaffold 流程。
- `develop --workspace <ws>`：进入逐 phase 开发循环。
- `resume --workspace <ws>`：读 state，校验 worktree + pane 存活，给恢复建议。

先决条件：用户已在某处写好 `REQUIREMENT.md`。约束见 SKILL.md（L14 逐 phase commit / L16 worktree 不碰 main / L19 默认思考等级 / 不 push）。

无参数或不确定子命令时，读 `~/.dotfiles/coding-skills/dev-long-run/SKILL.md` 与 `~/.dotfiles/docs/specs/dev-long-run/overview.md` 后再决定。

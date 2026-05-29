---
name: long-run-v2
description: 当复杂多 phase 任务需要多角色(orchestrator/planner/coder/reviewer)在 tmux 长驻 pane 协作、跨 phase 复用 context、且要在独立 worktree 分支上逐 phase commit 与人工 confirm 时使用；比 dev-long-loop 重，小/中任务仍用 dev-long-loop。
argument-hint: <scaffold --requirement <path> | develop --workspace <ws> | resume --workspace <ws>>
---

# long-run-v2

多 agent 编排的长任务工作流。把"调度脑"从 agent 内部脑补迁到 YAML + 文件 SSOT：6 角色协作，phase coder tmux pane 跨 phase 长驻复用，review 一轮分级 + coder 自判 ack 收口，phase 间用户 confirm 介入。spec SSOT: `docs/specs/long-run-v2/overview.md`。

harness: `skills/long-run-v2/lr2.py`（薄 wrapper，纯逻辑可单测，多 pane 调度脑在 loop orchestrator LLM 里）。

## 何时用 vs dev-long-loop
- 小/中任务、单 agent 跨轮：`/dev-long-loop`
- 复杂多 phase、需要 planner/coder/reviewer 分工 + 跨 phase pane 复用 + 逐 phase commit：本 skill

## 入口命令

```
# 1) 先在任意位置写 REQUIREMENT.md，然后:
lr2.py scaffold --requirement ~/scratch/REQUIREMENT.md [--goal "<目标>"] [--repo-root .]
#    → 建 worktree(../<repo>-lr2-<slug>) + 分支(lr2/<slug>) + .long-loop/<date>_<slug>/ 工作区
#    → 启动 scaffold orchestrator pane

# 2) scaffold 完成后进开发循环:
lr2.py develop --workspace .long-loop/<date>_<slug>
#    → 启动 loop orchestrator，逐 phase: planner → coder → reviewer → ack → commit → wait_confirm

# 3) pane 误关/崩溃后恢复:
lr2.py resume --workspace .long-loop/<date>_<slug>
```

orchestrator(LLM)在 pane 内用的子命令：`lr2.py launch --role <r>` / `lr2.py send --pane <id> --text <..>` / `lr2.py sessions` / `lr2.py pane-alive --pane <id>`。

## 硬约束(见 spec 已锁定 L1-L19)
- L16: 全程在独立 worktree + 分支，**绝不在 main 上开发/commit**。
- L14: 每 phase ack 收口后 coder commit 到分支（不 push）。
- L19: TUI 长驻 pane 用默认思考等级，不按 role 注入 variant。
- 不自动 push/deploy/改 secrets/触第三方副作用；工作区文件是 SSOT。
- loop orch 检测 coder 完成靠轮询 HANDOFF/done-marker 文件 mtime，**不抓屏**。

## 角色 prompt
`skills/long-run-v2/prompts/{scaffold_orchestrator,scaffold_reviewer,loop_orchestrator,phase_planner,phase_coder,phase_reviewer}.md`

## 状态(state.json)
`scaffold → develop → (每 phase) → wait_confirm → {develop 下一 phase | wrapup | blocked}`。
wait_confirm 下用户在 orch pane 输入 `confirm next` / `confirm done` / `block <reason>`。

## 回退
出问题时 `/dev-long-loop` 始终可用；删 worktree + 删分支 + 删 `skills/long-run-v2/` `.long-loop/<ws>` 即完全回退，main 无残留。

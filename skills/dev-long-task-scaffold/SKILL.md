---
name: dev-long-task-scaffold
description: 当任务目标明确但不适合后台自动 loop、需要人工逐阶段推进时使用；调研并生成长任务 workspace、phase 拆解、验收契约和控制提示词。
argument-hint: <任务目标或需求>
---

# Dev Long Task Scaffold

本 skill 负责长任务开局，不负责执行长任务。它把用户目标转成可人工 phase-by-phase 指挥的文件系统 workspace，并在 workspace 可审阅后停止。

与 `dev-long-loop` 的区别：

- `dev-long-loop` 面向 harness 驱动的 long-loop runner。
- `dev-long-task-scaffold` 面向用户手动控制的阶段式交付。
- 本 skill 不启动 `long_loop.py run`、不创建后台 agent、不自动进入任何 phase。

## Decision Principles

- 长任务的主要风险是目标漂移、上下文丢失、阶段边界不清和验证证据散落；workspace 是 SSOT。
- 只有目标足够明确、影响面较大、需要多阶段验收或阶段后 commit 时才使用本 skill。
- 每个 phase 必须能独立验证、独立提交、独立回滚。
- `blocked` 是合法状态。遇到需求矛盾、权限缺口、secret、远端副作用或不可逆动作时停止等待用户。
- 严格门禁不等于必须成功；允许 `partial`、`blocked`、`verification: none -- structural gap`。

## 工作流

1. **还原目标** — 明确用户真正要达成的结果、验收标准、非目标和不可牺牲约束。
2. **确定 workspace 路径** — 若用户指定目录，使用指定目录；否则默认 `.long-loop/<date>_<slug>`。路径必须回显给用户。
3. **只读调研** — 使用 Grep / Glob / Read / LS 收集代码事实、相关文件、现有测试、脚本和风险。
4. **拆 phase** — 每个 phase 必须有目标、主要文件、验证方式、退出条件和 commit 边界。
5. **创建 workspace** — 创建目录和 Markdown 文件；不生成 `state.json`、`runtime.log`、`runtime-input.md` 等 runner 状态文件。
6. **填充控制提示词** — 写 `CONTROL_PROMPT.md`，用于后续 agent 按用户指定 phase 执行。
7. **停止并交付** — 汇报 workspace 路径、phase 列表、下一步建议；不要开始实施 phase。

## Workspace Contract

默认结构：

```text
.long-loop/<slug>/
├── SPEC_OVERVIEW.md
├── CONTROL_PROMPT.md
├── fix_plan.md
├── qa.md
├── logs.md
└── phases/
    ├── 01_<phase>/
    │   ├── research.md
    │   ├── spec.md
    │   ├── plan.md
    │   └── qa.md
    └── 02_<phase>/
        ├── research.md
        ├── spec.md
        ├── plan.md
        └── qa.md
```

| 文件 | 责任 |
|---|---|
| `SPEC_OVERVIEW.md` | 任务目标、非目标、代码事实、影响面、风险、整体 phase map |
| `CONTROL_PROMPT.md` | 后续 agent 的阶段执行协议；只执行用户指定 phase，不自动跨 phase |
| `fix_plan.md` | 全局任务清单；item 状态只允许 `pending / in_progress / done / blocked` |
| `qa.md` | 整体验收标准、验证命令、acceptance verifier、回归检查 |
| `logs.md` | append-only 过程记录；每个 phase 的执行、验证、commit 和阻塞都记录在这里 |
| `phases/*/research.md` | 当前 phase 的只读代码事实、相关文件、约定和风险 |
| `phases/*/spec.md` | 当前 phase 的目标、非目标、边界、接口 / 行为契约 |
| `phases/*/plan.md` | 当前 phase 的实施步骤、验证步骤、回滚方式 |
| `phases/*/qa.md` | 当前 phase 的完成定义、验证证据和 known gaps |

## CONTROL_PROMPT.md 必须包含

```markdown
# Phase Control Prompt

You are executing one manually selected phase from this workspace.

Rules:
- Read `SPEC_OVERVIEW.md`, `fix_plan.md`, `logs.md`, and the selected `phases/<id>/` files first.
- Execute only the phase or item explicitly requested by the user.
- Do not start the next phase automatically.
- Before editing, confirm the selected phase and current git status.
- After implementation, run the phase QA and relevant repository validators.
- Update `logs.md`, `fix_plan.md`, and `phases/<id>/qa.md` with evidence.
- Commit after the phase is complete and validated.
- Do not push unless the user explicitly asks.
- If blocked, update the workspace and stop with the blocker, evidence, and options.
```

可按任务增加项目特定命令，但不得删除这些控制规则。

## Phase Template

每个 phase 至少写清：

```markdown
# Phase <n>: <name>

## Goal

## Non-goals

## Code facts

## Files likely touched

## Plan

## QA / acceptance

## Commit boundary

## Rollback

## Blockers / open questions
```

## 质量门禁

- 每个 phase 必须能独立验收；不能把“最终一起测”当成 phase QA。
- 每个 phase 必须写 commit boundary：完成后应提交哪些类型的变更，哪些变更不应混入。
- `fix_plan.md` 不能只有技术层任务；必须能映射到用户可感知的交付物或必要的支撑工作。
- 工作区创建后立即停止，等待用户选择 phase。
- 如果 workspace 目录已存在，先读取并总结现状；未经用户明确同意，不覆盖已有文件。

## Gotchas

- 不要启动 `long_loop.py run`。
- 不要生成 runner 状态文件冒充 harness workspace。
- 不要在 scaffold 阶段顺手实现 phase。
- 不要把所有未知点留给后续 agent；必须在 `Blockers / open questions` 中显式列出。
- 不要自动 push、deploy、迁移数据库、改 secrets 或触碰第三方系统。

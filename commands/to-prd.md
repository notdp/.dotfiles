---
description: 当需要把当前上下文（对话、scope、plan）整理成结构化 PRD 时使用；默认只生成 markdown，发布到 issue tracker 前走 /guard-gitops。
argument-hint: <需求描述|plan 路径|留空=当前对话上下文>
---

# To PRD

把散落在对话、spec、scope 中的信息整理成一份结构化 PRD。

## 流程

1. **收集输入**：从 `$ARGUMENTS`、当前对话上下文、或指定的 plan/spec 文件中提取需求信息。
2. **整理成 PRD**：按下方模板输出。
3. **交付**：默认输出到对话中（markdown）。用户明确要求发布到 GitHub/GitLab/Linear 时，先走 `/guard-gitops`。

## PRD 模板

```markdown
# PRD: <标题>

## Problem
当前状态是什么，为什么不可接受。

## Desired Outcome
期望达到什么状态，用户/调用方可观察到什么变化。

## Key Interfaces
涉及哪些接口、行为契约、数据流。

## Acceptance Criteria
- [ ] 可验证的验收条件 1
- [ ] 可验证的验收条件 2

## Out of Scope
明确不做什么。

## Risks / Open Questions
- 已知风险
- 待决策项
```

## 写法规则

- 用行为契约描述，不用 file:line（PRD 是持久化产物，路径会腐烂）
- Problem 和 Desired Outcome 必须写清；空的 PRD 不如不写
- Acceptance Criteria 必须是可验证的条件，不是模糊目标
- 不在 PRD 中写实现步骤（那是 spec/plan 的职责）

## 远程发布

用户要求发布到 issue tracker 时：

1. 先走 `/guard-gitops`
2. 使用 `gh issue create` / GitLab API / Linear API
3. 发布前确认目标 repo、label、assignee

## 关联技能

- 需求不清 → 先 `/think-scope` 或 `/think-refine`
- PRD 批准后拆 issue → `/to-issues`
- PRD 批准后写 spec → `/think-plan`

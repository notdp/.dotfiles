---
description: 当已有批准的 plan/PRD、需要拆成可独立交付的 issue 时使用；按 vertical slice 拆分，默认 dry-run 输出 markdown，远程创建前走 /guard-gitops。
argument-hint: <plan 路径|PRD 路径|留空=当前对话中的 plan>
---

# To Issues

把已批准的 plan 或 PRD 拆成可独立交付的 issue 列表。

## 流程

1. **读取输入**：从 `$ARGUMENTS` 指定的 plan/PRD 文件或当前对话上下文中提取。
2. **检查 .out-of-scope**：如果项目有 `docs/out-of-scope/` 或 `.out-of-scope/`，先扫描是否有相似的已拒绝 concept。
3. **按 vertical slice 拆分**：每个 issue 窄但完整地穿过所有集成层，完成后可独立演示或验证。
4. **输出 issue 列表**（默认 dry-run，只输出 markdown）。
5. 用户明确要求远程创建时，先走 `/guard-gitops`。

## Vertical Slice 规则

```
WRONG (horizontal):
  Issue 1: 改 schema
  Issue 2: 改 API
  Issue 3: 改 UI
  Issue 4: 写测试

RIGHT (vertical):
  Issue 1: 功能 A（schema + API + UI + 测试）
  Issue 2: 功能 B（schema + API + UI + 测试）
```

每个 issue 必须：
- 窄但完整：穿过所有相关层，不按技术层水平拆
- 可独立验证：完成后有可观察的验收标准
- 可独立 demo：不依赖其他未完成 issue 才能展示

## Issue 模板

```markdown
## <Issue 标题>

### Current Behavior
当前系统做什么。

### Desired Behavior
期望系统做什么。

### Key Interfaces
涉及哪些接口和行为契约。

### Acceptance Criteria
- [ ] 可验证条件

### Out of Scope
不做什么。

### Dependencies
依赖哪些其他 issue（如有）。
```

## 写法规则

- 用行为契约描述，不用 file:line（issue 是持久化产物）
- 不写实现步骤（实现由开发者或 agent 在执行时决定）
- 每个 issue 标注 dependencies（如有）

## 远程创建

用户要求创建到 issue tracker 时：

1. 先走 `/guard-gitops`
2. 使用 `gh issue create` / GitLab API / Linear API
3. 创建前确认目标 repo、label、milestone、assignee
4. 逐个创建，每个创建后回显 URL

## 关联技能

- 需求不清 → 先 `/think-scope` → `/think-plan`
- 需要先写 PRD → `/to-prd`
- 远程操作 → `/guard-gitops`

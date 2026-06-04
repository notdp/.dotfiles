---
description: 当需要对 issue 做状态判断（分类、优先级、是否 out-of-scope）时使用；默认输出建议，改 label/comment/close 前确认。
argument-hint: <issue URL|issue 编号|留空=列出 open issues>
---

# Triage

对 issue 做结构化状态判断：分类、优先级、是否 out-of-scope、下一步建议。

## 流程

1. **读取 issue**：
   - 有 `$ARGUMENTS`：用 `gh issue view` 或对应 API 读取
   - 无参数：用 `gh issue list --state open` 列出，让用户选择或批量处理
2. **检查 .out-of-scope**：如果项目有 `docs/out-of-scope/` 或 `.out-of-scope/`，检查是否有相似的已拒绝 concept。命中则引用历史决策。
3. **分析 issue**：按下方维度评估。
4. **输出裁决**（默认只输出建议到对话，不改动 issue tracker）。
5. 用户明确要求操作 issue tracker 时（加 label、comment、close），先确认每个操作。

## 评估维度

| 维度 | 问题 |
|---|---|
| 类型 | bug / feature / enhancement / question / chore |
| 优先级 | P0（阻断）/ P1（影响主流程）/ P2（改善）/ P3（nice to have） |
| 信息充分度 | 是否有足够信息开始工作（复现步骤、验收标准、上下文） |
| Out-of-scope | 是否命中已拒绝的 concept |
| 下一步 | 可以直接开发 / 需要补充信息 / 需要 scope 对齐 / 建议关闭 |

## 输出格式

```markdown
## Triage: <issue 标题>

| 维度 | 裁决 |
|---|---|
| 类型 | <type> |
| 优先级 | <P0/P1/P2/P3> |
| 信息充分度 | 充分 / 缺 <什么> |
| Out-of-scope | 否 / 是（引用 .out-of-scope/<concept>） |

### 下一步建议
- <具体建议>

### Agent Brief（如信息充分且可开发）
**Current Behavior**: ...
**Desired Behavior**: ...
**Key Interfaces**: ...
**Acceptance Criteria**: ...
**Out of Scope**: ...
```

## 写法规则

- Agent Brief 用行为契约，不用 file:line
- 信息不足时列出需要补充什么，不要猜测填充
- out-of-scope 命中时引用具体文件和历史决策理由

## 远程操作

用户要求操作 issue tracker 时，先走 `/guard-gitops`，然后每个操作前确认：
- 加 label：确认 label 名
- 添加 comment：确认 comment 内容
- Close：确认关闭理由

## 关联技能

- issue 需要 scope 对齐 → `/think-scope`
- issue 可以开发 → `/dev-tdd`
- 需要拆成子 issue → `/to-issues`
- 远程操作 → `/guard-gitops`

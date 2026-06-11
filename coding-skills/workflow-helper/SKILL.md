---
name: workflow-helper
description: 当目标涉及多步骤工作流、用户不确定该调用哪些 skill/command，或需要把设计、研究、架构、开发、验证、交付串成路线时使用；输出基于现有系统的工作流配方、产物和停止条件。
argument-hint: <目标|场景|约束>
---

# Workflow Helper

把“我该怎么用这套系统完成 X”转成现有 skills / commands 的可执行路线。它只做导航和编排建议，不替代具体执行 skill。

## 核心规则

1. 先识别用户目标类型：研究、设计、架构、开发、排错、长任务、交付等。
2. 推荐最短可行路线，不把所有相关 skill 都塞进去。
3. 每一步必须说明产物和进入下一步的条件。
4. 若任务已经处于执行中，优先从当前状态接上，而不是从头开始。
5. 若涉及远端、部署、数据库、secrets 或线上状态，路线里必须包含 `/guard-gitops`。

## Workflow Recipes

| 场景 | 推荐路线 | 核心产物 |
|---|---|---|
| 设计 / UI 美学 | `/design-md` -> `/think-plan` -> `/fe-ui-design-system` -> `/fe-ui-design` -> `/fe-ui-visual-iterate` -> `/guard-verify` | DESIGN.md contract、截图、差异表、验证证据 |
| 已有 UI 诊断 | `/fe-ui-critique` -> `/fe-ui-lint-artifact` -> `/fe-ui-visual-iterate` -> `/guard-verify` | 分级 findings、file:line、截图复核 |
| 架构设计 | `/think-map` -> `/think-research`（可选）-> `/think-architecture` -> `/think-plan` | 仓库地图、架构说明、spec |
| 代码开发 | `/think-context-map` -> `/think-plan` -> `/dev-tdd` -> `/guard-verify` -> `/guard-check` | 文件地图、spec、测试、实现、验证 |
| Bug / 排错 | `/dev-debug` -> `/dev-tdd`（行为修复）-> `/guard-verify` | 复现、根因、修复、回归证据 |
| 问题研究 | `/web-read`（有 URL）-> `/think-research` -> `/think-plan` | 调研结论、推荐方案、实施计划 |
| 开放主题综述 | `/think-survey` -> `/think-research`（需要决策时）-> `/assist-learn` | 现状、流派、分歧、可复用规则 |
| 长任务 | `/think-plan` -> `/dev-long-run-v2` -> `/guard-verify` | SPEC、phase 计划、逐 phase commit、完成门禁证据 |
| 大型交付 | `/think-plan` -> `/dev-large-delivery` -> `/guard-gitops`（触远端前）-> `/guard-ship` | Phase checklist、验收、回滚剧本、PR/发布 |
| 安全相关 | `/guard-secure` -> `/security-review` 或 `/commit-security-scan`（按场景）-> `/guard-verify` | 威胁模型、finding、验证证据 |
| 代码质量 / 重构 | `/think-quality` -> `/dev-refactor` -> `/guard-review` -> `/guard-verify` | 结构问题清单、重构、review、测试证据 |
| 前端上线前审计 | `/fe-audit` -> `/fe-ui-critique` -> `/fe-ui-visual-iterate` -> `/guard-verify` | file:line finding、截图、修复计划 |
| 写作 / PR 描述 | `/readable-final-answer`，必要时 `/human-writing` | 可读最终答案、PR 描述、自然文风稿 |
| 卡住 / 连续失败 | `/think-unstuck` -> 回到对应 dev/guard skill | 失败模式、替代路线、handoff |
| Git / PR / 发布 | `/guard-check` -> `/guard-ship`，触远端前 `/guard-gitops` | diff 检查、验证证据、commit/PR |

## 输出契约

```markdown
## 推荐工作流

### 路线
`/a` -> `/b` -> `/c`

### 为什么这样走
- <简述主要矛盾和路线取舍>

### 每步产物
| Step | Skill/Command | 产物 | 进入下一步条件 |
|---|---|---|---|
| 1 | `/a` | ... | ... |

### 停止 / 升级条件
- 停止：...
- 升级：...

### 最小命令
- ...
```

## Evidence / Stop / Escalate

- Evidence：路线必须包含最后的验证或验收入口；不能以“实现完”作为完成定义。
- Stop：当用户只问“怎么走”时，给路线后停止，不主动执行。
- Escalate：出现外部副作用、产品判断、权限授权、连续失败 2 次时，转对应 guard/think skill。

## Gotchas

- 不要把本 skill 当万能入口；它只回答“该怎么组织现有系统”。
- 不要复制目标 skill 的长规则；细节交给目标 skill 自己加载。
- 不要推荐超过 5 个主步骤；复杂任务拆阶段。
- 不要跳过 `/guard-verify` 声称可交付。

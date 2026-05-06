# Structured Prompt-Driven Development 调研

调研对象：Martin Fowler 网站文章《Structured-Prompt-Driven Development (SPDD)》，2026-04-28。

参考链接：https://martinfowler.com/articles/structured-prompt-driven/

## 推荐方案

[推断] 本仓库应吸收 SPDD 的核心纪律，但暂不完整复刻 openspdd。

推荐采用 **REASONS-lite**：

1. 在 `/think-plan` 的复杂任务 spec 中显式检查需求、领域实体、方案、结构、操作、规范和护栏。
2. 把复杂 plan 视作可审查的 prompt artifact，而不是一次性聊天摘要。
3. 当实现、验证或 review 发现意图漂移时，先回写 plan/spec，再继续改代码。
4. 交付检查在存在 spec / plan artifact 时补做 intent alignment，而不是只看 diff。

理由：

- [确认] 当前仓库已经有 `think-* -> dev-* -> guard-*` 的工作流分层。
- [确认] 当前仓库已有 `docs/software-engineering-research/plan.md`、`skills/think-plan/SKILL.md` 和验证脚本，具备吸收 SPDD 的落点。
- [推断] 直接新增完整 SPDD workflow 会和 `think-plan`、`dev-tdd`、`guard-check` 重叠，增加维护成本。

## 核心概念

### Prompt as first-class artifact

[确认] SPDD 把 prompt 作为一等交付产物处理：可版本化、可 review、可复用，并随代码演进。

对本仓库的启发：

- 复杂任务的 plan 不只是过程记录，而是后续实现和 review 的对齐基准。
- 如果代码改动背离 plan，应先修正 plan，再继续实现。
- 成功模式优先沉淀到 `skills/`、`commands/`、`docs/` 或脚本，而不是堆进全局规则。

### REASONS Canvas

| 字段 | 原文含义 | 本仓库轻量落点 |
|---|---|---|
| Requirements | 问题、DoD、验收标准 | `think-plan` 的目标、边界、验证 |
| Entities | 领域实体和关系 | Domain Language / ADR-lite |
| Approach | 解决策略和取舍 | 方案对比、Premise Collapse |
| Structure | 系统落点、组件、依赖 | 文件地图、模块边界 |
| Operations | 具体可测步骤 | 实施步骤和每步验证 |
| Norms | 通用工程规范 | 项目约定、测试、可观测性 |
| Safeguards | 不可违反约束 | 安全、兼容性、性能、Non-goals |

### Closed loop

[确认] SPDD 强调 prompt 和 code 双向同步：

- 需求变化：requirements -> prompt -> code
- 实现侧修复或重构：code -> prompt

[推断] 本仓库不需要马上实现自动 sync 工具，但应在流程上增加两条纪律：

1. 验证或 review 发现行为不符合 plan 时，先更新 plan/spec。
2. 重大实现取舍改变时，在交付前把取舍回写到对应 docs 或 skill。

### 三个核心技能

| 技能 | 含义 | 本仓库已有对应 |
|---|---|---|
| Alignment | 先锁定意图、价值、边界、验收 | `think-refine`、`think-plan` |
| Abstraction first | 先建模和定义边界，再生成代码 | `think-architecture`、`think-quality` |
| Iterative review | 小步验证、反馈回写、再继续 | `dev-tdd`、`guard-verify`、`guard-review` |

## 与当前系统映射

| SPDD 命令 / 阶段 | 作用 | 本仓库对应 |
|---|---|---|
| `/spdd-story` | 大需求拆 INVEST story | `think-refine` / `think-plan` 的边界与验收 |
| `/spdd-analysis` | 提取领域概念、扫描相关代码、形成分析上下文 | `think-research` / `think-context-map` |
| `/spdd-reasons-canvas` | 生成结构化执行 prompt | `think-plan` + REASONS-lite |
| `/spdd-generate` | 按 Operations 逐步实现 | `dev-tdd` / 常规实现 |
| `/spdd-api-test` | 通过边界测试验证行为 | `guard-verify` / 项目测试 |
| `/spdd-prompt-update` | 需求变化时更新 prompt | 更新 plan/spec/doc 后再实现 |
| `/spdd-sync` | 代码变化回写 prompt | `assist-learn` / docs update / review 后回写 |

## 适用性判断

### 高适配

- [确认] 多人协作、需要 audit trail 的长期维护变更。
- [确认] 业务规则复杂、边界清晰、对一致性要求高的系统。
- [确认] 高合规或安全约束明确的领域。
- [推断] 本仓库中的复杂 skill / command 设计、长任务 harness、跨文件工程规范演进适合采用 REASONS-lite。

### 低适配

- [确认] 生产 hotfix 的止血阶段。
- [确认] 一次性脚本、快速 spike、探索性原型。
- [确认] 纯创意或视觉探索任务。
- [推断] UI 视觉迭代更适合 `fe-ui-visual-iterate` 的截图反馈循环，而不是完整 REASONS Canvas。

## 采用决策

| 决策 | 状态 | 落点 |
|---|---|---|
| 不新增 openspdd 依赖 | 已采纳 | 避免工具链膨胀 |
| 不新增 SPDD 专用 skill | 已采纳 | 先复用 `think-plan` |
| 在复杂 plan 中引入 REASONS-lite | 已采纳 | `skills/think-plan/SKILL.md` |
| 研究类输出必须映射到当前系统能力 | 已采纳 | `skills/think-research/SKILL.md` |
| guard 检查补看 intent alignment | 已采纳 | `skills/guard-check/` |

## 风险与坑

- [确认] SPDD 有前置成本，不适合所有任务。
- [推断] Canvas 容易变成形式化填表；应只在复杂任务启用 REASONS-lite。
- [推断] 如果 prompt/code sync 全靠人工记忆，长期仍会漂移；应由 review/check 阶段提醒。
- [推断] 与 TDD 的顺序不应机械冲突：本仓库仍保留行为变更前 `/dev-tdd`，SPDD 的 plan artifact 负责意图和边界，TDD 负责行为反馈。

## 不要自造轮子

- 不为 SPDD 立刻创建新 command；先复用 `/think-plan`。
- 不引入 openspdd；当前仓库已有 skill 和验证脚本。
- 不把 SPDD 细则塞进 `AGENTS.md`；方法论沉淀到 `docs/`，触发规则沉淀到 `skills/`。

## 后续观察点

- 如果多个真实任务都需要保存长期 prompt artifact，再考虑新增 `commands/spdd.md`。
- 如果 review 经常发现 spec/code drift，再考虑脚本化扫描 PR 描述、spec 链接和 diff 范围。
- 如果 REASONS-lite 让 `think-plan` 输出过重，应拆成独立 `think-spdd` skill。

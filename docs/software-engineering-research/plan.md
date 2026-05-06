# Plan 调研

调研对象：Superpowers (brainstorming + writing-plans)、GSD (get-shit-done)、CCPM。

## 各项目方案摘要

### Superpowers — 协作对话驱动

两阶段：brainstorming → writing-plans。brainstorming 一次一个问题深入理解需求，提出 2-3 方案供选择，逐节展示设计并获取批准。writing-plans 将 spec 转为极细粒度的执行计划——每步 2-5 分钟原子操作，含完整代码和精确命令。硬门控：设计未批准前禁止实现。

### GSD — 子代理流水线

三阶段：discuss → research → plan，每阶段专门子代理执行。discuss 提取决策（锁定/自由裁量/推迟），research 做技术调研产出 RESEARCH.md，plan 产出 PLAN.md（2-3 任务/计划，依赖图+波次），再由 plan-checker 做目标后推验证。显式管理上下文预算（~50%）。

### CCPM — PRD 到 Epic

两阶段：写 PRD → 解析为 Epic。头脑风暴产出需求文档（含用户故事、功能需求、成功标准、显式排除项），再转为技术 Epic。质量门控：无占位符、用户故事含验收标准、成功标准可度量。

### SPDD - 结构化 prompt 作为交付资产

Structured-Prompt-Driven Development 将 prompt 作为一等交付产物：可版本化、可 review、可复用，并与代码双向同步。核心结构是 REASONS Canvas：Requirements、Entities、Approach、Structure、Operations、Norms、Safeguards。它比普通 spec 更偏向 LLM 执行边界，把业务意图、领域模型、技术方案、操作步骤和护栏压进同一个可审查 artifact。

## 共识

1. **先理解再动手** — 禁止跳过需求分析直接写代码
2. **无占位符** — 计划中不允许 TBD、TODO、"后续完善"
3. **用户审批门控** — 设计/计划必须经用户确认后才可执行
4. **可验证性** — 每个步骤都有具体的验证方式
5. **YAGNI** — 不做用户没要求的事
6. **具体文件路径** — 计划必须指明精确路径，不用含糊描述
7. **产物链条** — 需求文档 → 设计/调研 → 执行计划，每阶段有明确产物
8. **计划即 prompt artifact**：对复杂任务，计划不仅给人看，也作为后续实现和 review 的意图基准
9. **意图漂移先回写 artifact**：当验证或 review 发现现实与计划不一致，先修正 plan/spec，再继续改代码

## 已采纳到 canonical skill

| 决策 | 状态 | 落点 |
|------|------|------|
| 计划粒度采用 action 描述级，不默认写 2-5 分钟原子步骤 | 已采纳 | `skills/think-plan/SKILL.md` |
| 设计未经批准不进入实现 | 已采纳 | `skills/think-plan/SKILL.md` |
| 输出区分已锁定 / 待决策 / 可自由裁量 | 已采纳 | `skills/think-plan/SKILL.md` |
| 复杂交互用 Mermaid 辅助说明 | 已采纳 | `skills/think-plan/SKILL.md` |
| 技术不确定时先转 `/think-research` | 已采纳 | `skills/think-plan/SKILL.md` |
| 领域术语冲突和 ADR-lite 作为可选机制 | 已采纳 | `skills/think-plan/SKILL.md`、`docs/software-engineering-research/domain-language-and-adr.md` |
| 复杂任务采用 REASONS-lite 视角 | 已采纳 | `skills/think-plan/SKILL.md` |
| 调研结论必须映射到当前系统能力 | 已采纳 | `skills/think-research/SKILL.md` |
| 有 plan/spec artifact 时交付检查补看 intent alignment | 已采纳 | `skills/guard-check/` |

## 仍待决策

### 1. 计划粒度

| 选项 | 来源 | 取舍 |
|------|------|------|
| 每步 2-5 分钟，含完整代码 | Superpowers | 精确无歧义，但编写成本高 |
| 每任务 15-60 分钟，action 描述 | GSD | 已作为当前默认，适合复杂项目 |
| ≤10 个任务的 Epic 预览 | CCPM | 粗粒度概览，适合先看全局再细化 |

### 2. 独立调研阶段

| 选项 | 来源 | 取舍 |
|------|------|------|
| 专门 research 阶段，产出 RESEARCH.md | GSD | 通过 `/think-research` 按需触发，不默认创建文档 |
| 调研融入对话中 | Superpowers | 简单任务默认采用 |
| 无显式调研 | CCPM | 最简，可能遗漏技术风险 |

### 3. 交互模式

| 选项 | 来源 | 取舍 |
|------|------|------|
| 一次一个问题，逐个深入 | Superpowers | 已用于关键澄清，但执行型任务不强制每步等待 |
| 识别灰色地带后用户选择讨论哪些 | GSD | 用户控制节奏 |
| 五个核心问题一次问完 | CCPM | 快速，深度不足 |

### 4. 上下文预算管理

暂不在 `think-plan` 中硬性引入上下文预算。复杂交付可转 `/dev-large-delivery` 或拆多份 spec。

### 5. 计划验证

当前采用内置自审清单。是否新增独立 plan-checker 子 agent 仍待观察真实失败案例。

### 6. 是否新增 SPDD 独立入口

暂不新增 `/spdd` 或 `think-spdd`。先把 SPDD 的 REASONS-lite 和 prompt/code sync 纪律吸收到现有 `think-plan`、`think-research`、`guard-check` 链路。若后续多个真实任务都需要长期保存 prompt artifact，再考虑独立入口。

## 精华提取

| 技巧 | 来源 | 说明 |
|------|------|------|
| 目标后推法 | GSD | Goal → Observable Truths → Required Artifacts → Wiring，比正向列任务更不容易遗漏 |
| 决策三分类 | GSD | 锁定决策 / 自由裁量 / 推迟项，消除歧义 |
| 硬门控 | Superpowers | `<HARD-GATE>` 标签标注不可跳过的检查点 |
| 方案对比 | Superpowers | 要求 2-3 个方案 + 取舍分析 + 推荐，防止只给一个方案 |
| 计划即提示词 | GSD | PLAN.md 本身就是给执行代理的 prompt，减少转换损耗 |
| 垂直切片优先 | GSD | 按功能特性而非技术层拆分，垂直切片可并行 |
| 不要自造轮子清单 | GSD | 显式列出"不应手写实现"的部分 |
| Scope 不可缩减 | GSD | 禁止用"简化版"偷偷缩减范围，放不下就拆阶段 |
| PRD 质量门控 | CCPM | 无占位符、用户故事含验收标准、成功标准可度量 |
| REASONS Canvas | SPDD | Requirements / Entities / Approach / Structure / Operations / Norms / Safeguards，适合作为复杂任务 plan 的自审框架 |
| Prompt/code sync | SPDD | 验证或 review 发现偏差时，先回写 plan/spec，再继续实现，减少意图漂移 |

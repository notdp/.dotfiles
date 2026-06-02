# Agent Behavior 六维度规范框架

来源：用户阅读笔记（原文未注明出处）

## 框架定义

规范 AI agent 行为的六个维度：

| 维度 | 定义 | 对应问题 |
|------|------|----------|
| **Outcome** | 完成后应达到什么状态 | "做完了"长什么样？ |
| **Verification** | 怎么验证完成 | 用什么证据证明做完了？ |
| **Constraints** | 哪些东西不能退化 | 改动后什么不能变差？ |
| **Boundaries** | 能用哪些工具、碰哪些文件 | 手伸多远？ |
| **Iteration policy** | 失败后怎么继续尝试 | 一次没做到怎么办？ |
| **Stopping conditions** | 什么时候停下来问人 | 什么时候该认输？ |

## 与本仓库 skill 体系的映射

### 已有覆盖（强）

**Outcome / Verification / Constraints / Stopping conditions** 在多数 action skill 中已有显式表达：

- `dev-tdd`：4 点完成门禁 = Outcome + Stopping
- `dev-debug`：2-strike handoff + 3 前置条件 = Iteration + Stopping
- `dev-refactor`：spec 产出 + 行为不变红线 = Outcome + Constraints
- `dev-large-delivery`：Phase 级 10 点退出检查 = Verification + Stopping
- `guard-verify`：L1/L2/L3 三层证据 = Verification
- `dev-operational-task`：7 维 Operational Contract + 6 项 dry-run 门禁 = Outcome + Verification + Constraints
- `guard-gitops`：4 条硬停止 + 5 个例外白名单 = Constraints + Boundaries + Stopping
- `guard-secure`：授权边界 + STRIDE 清单 = Boundaries + Verification
- `guard-close`：三层 scope 契约 + 5 信号前置检查 = Stopping conditions

### 系统性薄弱（需改进）

#### 1. Boundaries（最弱）

多数 skill 没有显式声明"能碰什么、不能碰什么"。目前仅以下 skill 有清晰边界：

| Skill | Boundaries 表现 |
|-------|----------------|
| `guard-ship` | 禁止 force-push main、feature 分支才可推 |
| `guard-secure` | 只读分析 vs 进攻测试需授权范围 |
| `guard-gitops` | 5 个例外场景白名单 |
| `dev-operational-task` | 并发上限、超时、/guard-gitops 前置 |

缺失的 skill：`dev-tdd`、`dev-debug`、`dev-simplify`、`guard-verify`、`guard-review` 均未声明文件/工具边界。

**改进方向**：每个 action skill 增加 Boundaries 节，至少覆盖：
- 可修改的文件类型/目录（白名单）
- 禁止触碰的文件类型（secrets、生成产物、基础设施）
- 允许/禁止的工具操作（如：不可删文件、不可直接操作 DB）

#### 2. Iteration Policy（次弱）

现状是粗粒度的"连续失败 2 次 → /think-unstuck"，但缺少：
- "失败"的定义（语法错误 vs 逻辑错误 vs 环境问题）
- 不同失败类型的重试成本（语法错误 0 成本立修，逻辑错误消耗 1 次配额）
- 中间恢复策略（降级、缩小范围、换方法）

目前仅 `dev-debug` 有较完整的迭代策略（2-strike 含固定格式 handoff），`dev-operational-task` 有部分失败处理（failed set、dead-letter、retry queue）。

**改进方向**：定义失败分类和对应策略：

| 失败类型 | 重试成本 | 策略 |
|----------|----------|------|
| 语法/拼写错误 | 0（立修） | 不消耗配额 |
| 逻辑错误 | 1 次 | 修复 + 重新验证 |
| 环境/工具错误 | 0（诊断） | 修环境后继续 |
| 方向性错误 | 1 次 | 换方法重试 |
| 需用户决策 | 停止 | 不算重试 |

#### 3. 跨 skill 交接格式

skill 之间的输出没有统一的 gate pass/fail 格式。例如 `dev-tdd` → `guard-verify` 的交接是隐式的（靠上下文传播），没有结构化的状态传递。

**改进方向**：定义 skill handoff 格式，让下游 skill 能程序化判断上游结果。

## 六维度覆盖评分

| Skill | Outcome | Verification | Constraints | Boundaries | Iteration | Stopping |
|-------|---------|--------------|-------------|------------|-----------|----------|
| dev-tdd | ● | ● | ● | ○ | ○ | ● |
| dev-debug | ● | ● | ● | ○ | ● | ● |
| dev-refactor | ● | ● | ● | ● | ● | ● |
| dev-large-delivery | ● | ● | ● | ● | ● | ● |
| dev-long-loop | ● | ○ | ● | ○ | ○ | ○ |
| dev-operational-task | ● | ● | ● | ● | ● | ● |
| dev-simplify | ● | ● | ● | ○ | ● | ● |
| guard-verify | ● | ● | ● | ○ | ● | ● |
| guard-check | ○ | ○ | ○ | ○ | ○ | ○ |
| guard-review | ● | ● | ● | ○ | ○ | ● |
| guard-ship | ● | ● | ● | ● | ○ | ● |
| guard-secure | ● | ● | ● | ● | ○ | ● |
| guard-gitops | ● | ● | ● | ● | ● | ● |
| guard-close | ● | ○ | ● | ○ | ● | ● |

● = 显式覆盖 ○ = 缺失或仅隐式

## 已采纳路线：外科手术式

前述六维度评分的初版结论曾建议"给多个 action skill 普遍补 Boundaries / Iteration 正文"。复核 `agents/AGENTS.md` 与 `scripts/verify_skills.py` 后否决了这条路线，原因是体系本身是"全局红线 + 下沉细则"的分层设计：

- **Boundaries / Iteration / Verification / Stopping 四维度已全局覆盖**：
  - `AGENTS.md` 的 `边界决策`（含 `Boundary facts` / `Boundary decisions` 块格式）、`Surgical Changes`、`四条红线`、`验证纪律`、"连续失败 2 次 → /think-unstuck"
  - `verify_skills.py` 已机器强制：`WORKFLOW_QUALITY`（证据/停止/风险类标题）、`GUARDRAIL_ANCHOR`（高风险能力的授权/边界锚点）、`VAGUE_CONDITIONAL`（"必要时/适当/如需"缺具体条件告警）
- 在各 SKILL.md 重复这些 = 与全局规则冗余，直接违反 `AGENTS.md:56,61` 的"短小硬 + 细则下沉"原则，制造每次触发都加载的正文膨胀。

因此六维度的正确落点是 **authoring lens**（写/审 skill 时的完整性自查），而不是 per-skill 正文。已执行的两处真实改动：

1. **沉淀 lens**：`docs/software-engineering-research/skill-authoring.md` 在"质量门"节后追加"六维度完整性自查"，显式标注"4 维度全局覆盖、只在该 skill 有超出全局规则的特定风险时才加 per-skill 正文"。
2. **修唯一真实缺口**：`dev-long-loop` 补循环进度驱动的停止条件——它原本只有事件驱动停止（blocked/secret/deploy），缺"连续 2 轮无进展即停"（全局 2-strike 的循环版）与"预算耗尽前 checkpoint"，且"定期用 /guard-close"是模糊触发。

### 明确放弃的扩展（非本轮 scope）

- 给 `dev-tdd` / `dev-debug` / `dev-simplify` / `guard-verify` / `guard-review` 加 Boundaries / Iteration 正文：全局已覆盖，无具体坏后果。
- `verify_skills.py` 加"六维度齐全"硬校验：会对合理依赖全局规则的 skill 大量误报。
- `guard-check` 路由决策树：低分是 router 委派设计，非缺陷。
- 跨 skill handoff 协议：属全面铺开路线，本轮不做。

## 与现有编写规范的关系

`docs/software-engineering-research/skill-authoring.md` 已涵盖"任务契约、触发场景、输出形态、证据门、停止/升级条件"。本框架进一步细化了两个 skill-authoring 未显式要求的维度：

- **Boundaries**：skill-authoring 说"定义风险信号"，但没要求声明可操作范围
- **Iteration Policy**：skill-authoring 提到"升级路径"，但没要求定义失败分类和中间恢复策略

建议将这两个维度纳入 skill-authoring 的结构模板要求。

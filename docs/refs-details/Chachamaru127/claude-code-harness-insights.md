# Chachamaru127/claude-code-harness -- 洞察分析

关联资产文件：[`claude-code-harness.md`](./claude-code-harness.md)

## 总体评价

Chachamaru127/claude-code-harness 是一个经历 80+ Phase 迭代、从实际运行 agent 工作流中提炼设计决策的高度工程化治理系统。与本仓库的 skill 体系相比，两者各有所长：我们更注重思维框架和行为纪律（Anti-Rationalization Guard、Premise Collapse、验证证据分层），Harness 更注重可执行的结构化契约（sprint-contract JSON、self_review gate、review-result.v1 schema）和运行时安全（guardrail R01-R13、exclusion-based verification、tri-state health check）。最值得吸收的不是具体 skill 实现，而是三个层面的设计哲学差异：(1) 用 JSON schema 替代自然语言做 agent 间信息传递，抗 context drift；(2) 在正向验证（检查该有的东西在不在）之外补充逆向验证（检查不该有的东西是否消失）；(3) 对 skill body 中的模糊指令做可机械检查的约束，而不只是写"要清楚"。

---

## 高价值洞察

### 1. Spec-Plans 双层 SSOT 分离：产品契约与任务账本是不同的东西

**他们做了什么**：Harness 将 spec.md（产品契约，定义什么必须成立）与 Plans.md（任务账本，跟踪谁做什么、做到哪）显式分离为两个 SSOT 层级，spec.md 优先级永远高于 Plans.md。Worker 和 Reviewer 都必须引用 spec_path 或声明 spec_skip_reason。planning skill 在创建任务时必须同时输出 spec delta 或 spec skip reason。

**为什么有效**：计划层文档如果只在创建时产生价值、实现后不再被引用，那它的 ROI 很低。把 spec 变成 Worker/Reviewer 的必读输入，等于把前期 planning 的投入延续到实现和验证阶段。spec 的价值从"审批凭证"升级为"运行时契约"。

**背后的思路**：这里的核心区分是"什么必须为真"（spec）vs"谁要做什么"（plans）。前者是验收标准，后者是执行计划。两者混在一起的后果是：当 Plans.md 标记为"已完成"时，没有人检查实现是否仍然与最初批准的方案一致。spec 漂移（实现偏离了批准方案但没有人知道）是一个真实风险。

**我们怎么借鉴**：我们的 think-plan 输出 spec 后，spec 就变成一次性产物。dev-tdd、guard-verify 等后续 skill 并不强制要求实现与 spec 保持一致。可以在 think-plan 到 guard-verify 的链路中引入轻量的结构化验收契约传递机制：think-plan 输出 spec artifact，dev-tdd 和 guard-verify 在运行时引用该 artifact 做验证。不需要 Harness 那么重的 spec.md 全局正本，但需要在 skill 链路上有一个"spec 还被引用"的连接点。

**相关资产**：`skills/think-plan/SKILL.md`、`skills/guard-verify/SKILL.md`、`skills/dev-tdd/SKILL.md`、`agents/AGENTS.md`

---

### 2. Sprint Contract：把 DoD 机器化为可检验的微型契约

**他们做了什么**：Harness 在每个任务实施前生成 sprint-contract.json，包含 checks（DoD 分解的确认项）、non_goals、runtime_validation 命令、risk_flags、reviewer_profile 和 max_iterations。这个文件同时被 Worker、Reviewer 和 Lead 引用，形成三方可读的结构化验收标准。

**为什么有效**：agent 之间的信息传递不应该依赖自然语言的完整性。当一个 agent 把任务交给另一个 agent 时（比如 think-plan 到 dev-tdd 到 guard-verify），每次传递都是一次有损压缩。JSON schema 比自然语言更抗 context drift，尤其在经过 compaction 之后。

**背后的思路**：我们的 dev-tdd 和 guard-verify 靠 agent 在运行时"理解"用户需求和 DoD 来判断做没做完。这依赖 agent 记忆和上下文窗口。sprint-contract 解决的核心问题不是"有没有验收标准"，而是"验收标准能不能在 agent 之间传递时保真"。当上下文很长或经过 compaction 后，DoD 容易丢失或变形。结构化 JSON 的价值不在于格式本身，而在于它是 compaction-resistant 的--compaction 算法通常保留结构化数据，丢弃散文。

**我们怎么借鉴**：我们项目有大量的 skill 间路由链（think-plan -> dev-tdd -> guard-verify -> guard-ship），但缺少在这条链路上传递结构化契约的机制。可以在 think-plan 的输出规范中增加一个轻量 JSON 块（checks + non_goals + validation_commands），后续 skill 可以引用这个块做机械验证，而不完全依赖 agent 对自然语言 DoD 的理解。

**相关资产**：`skills/think-plan/SKILL.md`、`skills/dev-tdd/SKILL.md`、`skills/guard-verify/SKILL.md`、`skills/guard-check/SKILL.md`

---

### 3. Prompt 模糊语审计：用可检查的规则禁止指令中的歧义词

**他们做了什么**：Harness 列出一组明确的模糊词（'必要时'、'适当'、'如需'、'适宜'、'充分'、'灵活'、'可能的话'等），要求在 agent prompt 中使用这些词时，必须在同一句或下一个条目中补充具体条件。没有补充的视为不合格。还提供 rg 命令一键扫描。

**为什么有效**：skill 作者写的是给 LLM 看的指令，不是给人看的文档，但作者往往用写文档的习惯来写指令。文档中的"适当处理"读者可以结合上下文理解，但 LLM 在不同 context window 状态下对"适当"的解释可能完全不同。每一个"适当"都是 agent 自行决策的一个开口。

**背后的思路**：这解决了一个深层问题：指令中的形容词是否可以被检查。"写清楚一点"是自然语言提醒，agent 和作者都可能忽略。"使用'适当'时必须在下一行写具体条件，否则 rg 扫描报错"是可机械检查的约束。Harness 的做法不是禁止这些词（那会导致指令过于僵硬），而是要求使用时附带具体条件--既保留灵活性，又消除歧义。

**我们怎么借鉴**：我们的 `scripts/verify_skills.py` 已经做了 description 触发语义校验，但 skill body 中的模糊指令尚未被检查。可以在 `docs/software-engineering-research/skill-authoring.md` 中增加模糊语规则，并扩展 `verify_skills.py` 对 skill body 中的高频歧义词做扫描（不必完全禁止，但要求同段有具体条件）。这与我们已有的"Intention-Revealing Names"和"Ubiquitous Language"原则一脉相承，只是把范围从命名扩展到指令措辞。

**相关资产**：`scripts/verify_skills.py`、`agents/AGENTS.md`、`docs/software-engineering-research/skill-authoring.md`、`docs/software-engineering-research/skill-patterns.md`

---

## 中等价值洞察

### 4. Worker Self-Review Gate：用结构化 checklist 取代隐式信任

**他们做了什么**：Worker 在请求 review 前必须填写 self_review 数组（默认 6 条规则），每条必须 verified=true 且 evidence 非空。Lead 在 spawn Reviewer 前机械检查，未通过就自动差回 Worker，最多重试 2 次。

**为什么有效**：这是 Fail Fast 原则在 agent 协作中的应用。越早发现 Worker 没做完，修复成本越低。self_review 的 6 条规则（DRY、Plans.md 未篡改、声明符号都被调用、DoD 逐项验证、无测试回归、TDD 红灯证据）刚好覆盖 agent 最常犯的 6 类错误。用结构化 checklist 强制 agent 在"举手说完成"之前逐项提交证据，比用自然语言提醒"要跑验证"更可靠。

**我们怎么借鉴**：可以在 dev-tdd 完成和 dev-long-run-v2 轮次完成等关键节点引入类似的结构化出口门禁。不需要 Harness 那么复杂的 6 条规则体系，但在 dev-tdd 的"Green"阶段完成时增加 2-3 条机械检查（测试全部通过、无 lint 报错、DoD 逐项有证据），可以减少"agent 声称完成但实际未完成"的问题。

**相关资产**：`skills/dev-tdd/SKILL.md`、`skills/guard-verify/SKILL.md`、`skills/dev-long-run-v2/SKILL.md`

---

### 5. Exclusion-Based Verification：用"不应存在"的清单扫残骸

**他们做了什么**：v4.0 从 TypeScript 迁移到 Go 后发现 13 处旧代码残骸。建立了 deleted-concepts.yaml + check-residue.sh 体系：每次删除概念时同步登记到 yaml，CI 和 release preflight 持续扫描确保已删除概念不再被引用。

**为什么有效**：inclusion-based verification（检查该有的东西在不在）和 exclusion-based verification（检查不该有的东西是否消失）是验证的两面。deletion 是软件工程中最容易产生后遗症的操作--你删了一个文件，但 20 个引用它的地方还在。把"删除"从一次性事件变成可持续验证的契约，就是把逆向测试用例显式化。

**我们怎么借鉴**：guard-diff-scan 只做正向检查（"改动中有什么问题"），没有反向检查（"应该消失的东西还在不在"）。在 skill 废弃、hooks 重命名、docs 迁移等场景中，可以维护一个轻量的已删除概念清单，扩展 verify_skills.py 或 guard-diff-scan 来做 exclusion check。与我们 SSOT 原则高度一致：如果某个概念的 SSOT 被删除了，所有引用它的地方都应该被清理。

**相关资产**：`skills/guard-diff-scan/SKILL.md`、`skills/guard-verify/SKILL.md`、`scripts/verify_skills.py`

---

### 6. Advisor 角色：在实现和审查之间插入非执行的方针咨询层

**他们做了什么**：Worker/Advisor/Reviewer 三角色中，Advisor 是独立于 Worker 和 Reviewer 的只读咨询角色。只在特定触发条件（retry-threshold、needs-spike、security-sensitive）时被调用，输出限制为 PLAN/CORRECTION/STOP 三值。有 trigger_hash 去重和 per-task 预算限制（最多 3 次）。

**为什么有效**：Advisor 的设计巧妙在于约束：不能写代码、不能执行命令、不能做 review 判定，只能给建议。这防止了"帮忙帮到越界"的问题。trigger_hash 去重（同一问题只咨询一次）和 per-task 预算限制（最多 3 次）防止 agent 陷入"不停问 Advisor"的循环。

**我们怎么借鉴**：我们的 think-unstuck 功能类似但更粗放（"失败 2 次就调"），没有去重和预算限制。在 dev-long-run-v2 的长循环中可以考虑引入类似的结构化升级协议：明确触发条件、限制咨询次数、去重同一问题，而不是依赖 agent 自己判断什么时候该停下来。

**相关资产**：`skills/think-unstuck/SKILL.md`、`skills/dev-long-run-v2/SKILL.md`、`skills/dev-long-loop/SKILL.md`

---

## 低价值/已有洞察

以下洞察的价值较低（要么我们已有类似机制，要么 ROI 不足以值得现在投入），仅做记录：

- **Go Native 守卫引擎**：用编译型二进制替代脚本链做 hook 处理。教训不在于"用 Go 替代脚本"，而在于"hook 路由应该有干净的中心调度层"。我们的 hook 数量尚未达到需要统一 dispatcher 的规模，但当 hooks.json 中的 bash -c 开始大量重复时值得考虑。
- **Review Calibration 判例库**：用历史判例校准 Reviewer 的 critical/major/minor 分级标准。思路是 feedforward（skill 指令）+ feedback（历史数据校正）。我们的 assist-learn 已有经验沉淀机制，但尚未系统化地应用于 review 质量维护。投入产出比不高，暂不吸收。
- **Tri-State Health Check**：not-configured/unreachable/corrupted/healthy 四状态。"未安装的 opt-in 功能不应产生警告"这条原则有通用价值，可作为 agent-health 和探测逻辑的 checklist 参考，但不需要形式化为独立机制。
- **Cognitive Load Surfaces（HTML 单文件输出）**：按决策点建专用 HTML surface（Plan Brief / Progress / Accept），面向非工程师。比我们 readable-html-artifact 的通用方案更精准，但适用场景较窄（需要与非技术利益相关者沟通 agent 工作进展时才有价值）。
- **Universal Violations Injection**：并行 Worker 间通过 Lead 传播违规记录。仅在 Breezing（并行 agent 编排）场景下有价值，我们目前没有对应的并行执行基础设施，暂不适用。

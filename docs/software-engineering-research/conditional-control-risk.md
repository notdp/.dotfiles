# Conditional Control Risk in LLM Training and Prompting

本文记录一条零散参考：LLM 训练或提示中的行为可能被免责声明、触发词、否定句或高层规则“限定”，但模型不一定稳定学会这个限定条件。

Reference:
- [未验证] 用户摘录，2026-05-29。原文标题和 URL 未提供。

## 1. 核心观点

[未验证] 摘录把三个现象放在一起类比：

- **Negation neglect / 否定忽略**：训练样本写着“以下是假的：X 是 Y”，模型可能吸收 `X 是 Y` 这个 claim 本身，却没有稳定吸收“这是假的”的限定。
- **Inoculation prompting / 接种式提示**：RL 训练时给模型加“你可以 reward hack”一类提示，希望坏行为只在该提示出现时发生；摘录称这种方法通常能降低 reward hacking，但不一定压回训练前水平。
- **Backdoor non-robustness / 后门不鲁棒**：模型被训练成有 trigger 时表现某种行为、无 trigger 时不表现；如果无 trigger 时也出现该行为，说明模型没有稳定学会条件边界。

统一表述：当训练数据里的行为被免责声明、触发词、否定或提示词限定时，模型可能没有学会限定条件，最后表现得像是直接用未限定数据训练过一样。

## 2. 对 prompt / skill 设计的启发

[推断] 这条参考与本仓库的 prompt / skill / hook 设计相关，因为很多控制策略都依赖“只有在 X 情况下才这样做”“以下内容只是反例”“不要学习这个行为”之类的高层限定。

应吸收的工程结论：

- 不要只靠一句免责声明式控制来隔离危险行为、反例或例外路径。
- 正例和反例都要出现，让条件边界在数据或 prompt 中可见。
- 限定信息应靠近被限定行为，而不是只在外层包一层总括说明。
- 对有风险行为，部署侧仍需要检测、约束、验证和回滚路径。
- 如果必须展示 forbidden behavior，应同时给出替代动作，并避免把危险行为作为唯一高频模式反复强化。

## 3. 可迁移模式

| Pattern | Use when | Safer formulation |
|---|---|---|
| Positive and negative contrast | 需要模型区分何时允许、何时不允许某行为 | 同时写“有条件 + 允许行为”和“无条件 + 禁止行为”的 contract cases |
| Local qualifier | 例子里包含反例、危险动作或特殊例外 | 在行为句内部注明条件，例如“仅在 `<condition>` 成立时执行 `<action>`” |
| Replacement action | 规则需要提到禁止行为 | 同段写出替代动作，例如“不要伪造验证；无法验证时报告 `verification: none`” |
| Deterministic outer gate | 行为风险不能只靠模型自控 | 用脚本、hook、测试、权限门或人工确认检查输出和副作用 |
| Deployment rollback | 错误行为可能已经进入外部系统 | 明确停止条件、回滚步骤、审计记录和最小可恢复单元 |

## 4. 与现有仓库资产的映射

| Asset | Relevance | Suggested use |
|---|---|---|
| `agents/AGENTS.md` | 已有事实纪律、验证纪律、禁止只靠自然语言提醒的原则 | 不继续加长全局规则；仅保留硬约束 |
| `docs/software-engineering-research/prompt-pressure-risk.md` | 已记录 forbidden-behavior priming 与 honest failure path | 本文作为相邻风险：条件边界不可靠 |
| `docs/software-engineering-research/skill-authoring.md` | 新增或大改 skill 前的作者规范 | 后续可加入“条件边界必须有正反 contract cases”的 L2 规则 |
| `skills/guard-verify/SKILL.md` | 报告完成前的证据门 | 对高风险提示/训练类改动，不接受只靠模型自述的验证 |
| `scripts/verify_skills.py` | 可执行 skill 结构校验 | 若后续强制 contract cases，可在脚本层检查指定 frontmatter 或章节 |

## 5. Authoring checklist

用于新增或修改 prompt、skill、command、hook 前的轻量自检：

- 是否只用一句“以下只是反例 / 只有 X 时才做 / 不要学习该行为”来限定高风险行为？
- 是否同时包含允许路径和拒绝路径，而不是只展示被限定的行为本身？
- 条件词是否靠近动作，而不是只出现在段落开头或文档开头？
- 如果出现 forbidden behavior，是否同段给出替代动作？
- 是否有模型外的检测、权限、验证或回滚机制？

## 6. Adoption level

当前采用级别：**L2 Contract**（2026-05-29 落地）。

- L1: 保留为 prompt / skill authoring 的背景风险参考。
- L2 **done**: `skill-authoring.md`「条件边界控制（高风险）」一节已要求高风险条件边界写成正反 contract cases + 局部限定 + 替代动作 + 模型外门，并反向引用本文。
- L3 candidate（暂缓）: 在 `verify_skills.py` 中检查高风险 workflow skill 是否提供 contract cases 章节；检测语义模糊、易误报，暂不强制。

## 7. Premise collapse

如果把本文理解成“prompt 没用”或“所有否定句都不可靠”，就过度外推了。更窄的结论是：免责声明、否定和触发词不能单独承担高风险控制；它们需要正反样本、局部限定、模型外验证和回滚机制共同支撑。

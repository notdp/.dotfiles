---
description: 一次性维护仓库的 agent skills、commands、hooks、refs；输出可执行的修复清单和待决策项。
argument-hint: '[reviewer-a-model=<model>] [reviewer-b-model=<model>] [reviewer-a-agent=<agent>] [reviewer-b-agent=<agent>] [review-thinking=<low|medium|high|max>]'
---

# Skill Maintenance

## 项目与任务

本仓库是 Coding Agent（claudecode、codex、droid、opencode、kilo）的技能、护栏、优化机制仓库。

包含 agents.md、commands、skills、hooks。

refs 目录是源码级别参考的开源项目（submodule 形式）。每个项目都被总结以后，把功能点和特性写到了 docs/refs-details/** 中，并有一个汇总记录 docs/refs-summary.md。

关于护栏的参考在这里：`docs/harness-refs/`（含 `sources.md` 和相关资料）

这个 command (skill-maintenance) 的**任务**是为了维护这个仓库的健康性。从如下几个方面

- 双 reviewer 全仓库审查：审查当前所有技能的欠缺、矛盾、困惑、不符合 refs 最佳实践、过度限制 agent 能力的点
- refs 深度调研：跟踪 refs 项目的最新动态，吸收最新的最佳实践
- session 技能效能分析：日常行为数据驱动的仓库健康分析，分析 skill 和 hook 的使用情况

中文输出

## 执行步骤

### Phase 1: 证据收集

1. 运行 `python3 scripts/skill_maintenance_collect.py --repo . --format json` 收集本地维护信号。
2. 记录 collector 输出里的 `git status --short`、当前分支、HEAD、dirty files。
3. 读取 `deterministic_findings`，其中包括 `python3 scripts/verify_skills.py` 的 warning / failure。
4. 盘点本地资产：
   - `coding-skills/catalog.json` 和 `coding-skills/*/SKILL.md`
   - `commands/*.md`
   - `agents/AGENTS.md`
   - `scripts/hooks/*.py` 和对应 tests
   - `docs/refs-micro-index.md`

### Phase 2: Reviewer 全仓库审查

目的：审查当前所有技能的欠缺、矛盾、困惑、不符合 refs 最佳实践、过度限制 agent 能力的点。必须足够保守，不要乱改。

5. 解析 `$ARGUMENTS` 中的可选覆盖项；未提供时使用默认 reviewer roster。解析规则：以空白分隔的 `key=value`；未知 key 或缺少 `=` 视为输入错误并停止；value 原样保留，不做 shell 展开。
6. 准备前置 review packet，内容只包括证据源，不包括主命令预设候选结论：
   - collector JSON 摘要
   - git dirty files、branch、HEAD
   - 所有 `coding-skills/*/SKILL.md`、`commands/*.md`、`agents/AGENTS.md`、`scripts/hooks/*.py` 的文件清单
   - `deterministic_findings`
   - `refs/` 目录下参考项目清单（用于对照最佳实践）
   - `docs/refs-details/**/*.md` 和 `docs/refs-summary.md`（refs 已有摘要，reviewer 对照最佳实践时优先读摘要而非 refs 原始代码）
   - `docs/harness-refs/`（护栏参考资料）
   - 默认禁止项、用户已裁决边界、requested model、requested thinking
7. 自动并行派发两个只读 reviewer：
   - Reviewer A default: agent `skill-maintenance-reviewer-a`, requested model `cliproxy/gpt-5.5`
   - Reviewer B default: agent `skill-maintenance-reviewer-b`, requested model `cliproxy/claude-opus-4-8`
   - 如果 `$ARGUMENTS` 覆盖了 model 或 agent，review packet 必须记录 requested override。
8. Reviewer 逐一读取每个 skill/command/hook/agents.md，按五个维度审查：
   - **欠缺**：触发条件、输出契约、验证方式、回滚方式是否完整。
   - **矛盾**：不同 skill 之间是否规则冲突，AGENTS.md routing 和 skill description 是否一致。
   - **困惑**：description 是否模糊到 agent 无法判断什么时候该用，多个 skill 的适用场景是否重叠到 agent 会混淆。
   - **不符合 refs**：对照 `refs/` 下参考项目，当前 skill/command/hook 是否有明显偏离。
   - **过度限制**：哪些"不要做"规则缺乏理由或证据，可能阻碍 agent 完成合理任务。
9. Reviewer 必须保守：只报告有证据的问题，不建议大范围重写，不提出新增 skill/command（那是 Phase 3 refs 调研的职责）。

### Phase 3: Refs 深度调研

对 collector `refs` 输出中 `old != remote` 的每个有变更的 ref，用 subagent 逐一分析。

如果用户没有明确批准联网和 refs refresh，只能使用 collector 已提供的本地 remote-tracking 信号，不得声称远端最新状态已核验。用户批准联网后，必须先过 `/guard-gitops`，再执行 `git fetch` / submodule refresh，并把 refresh 前后的 branch、HEAD、dirty files、submodule status 作为证据写入输出。

注意每个分析，虽然要看 refs 内容改了什么，但更要洞察背后的逻辑。

10. **逐 ref 派发 subagent 调研**：对每个有新 commit 的 ref，派发一个只读 subagent（可并行），任务是：
   - 读取该 ref 子目录下 `git log <old>..<remote> --oneline --stat`，分析新增了哪些功能/代码、移除了哪些功能/代码。
   - **推断**该项目做这些变更的目的（解决什么问题、追随什么趋势、修复什么缺陷）。按 Truth Directive 标注：能从 diff / commit 直接佐证的写 `[推断]`，无法证实的写 `[猜测]`；不要把作者意图当事实陈述，也不要链式推断。
   - 在更高层级总结：该项目的演进方向是什么，对 agent skill/command/hook 生态意味着什么。
   - 读取对应 `docs/refs-details/<owner>/<repo>.md`（如存在），比对当前 absorption level。
   - 输出结构化调研结果。

11. **汇总调研文档**：把所有 ref 的调研结果汇总写入 `docs/skill-maintenance-runs/refs-research-<YYYY-MM-DD>.md`，包含：
    - 每个 ref 的功能增减摘要、变更意图、演进方向。
    - 跨 ref 的趋势总结：生态整体在往哪个方向走。
    - 哪些 ref 的变更与本仓库已有资产直接相关。

12. **结合仓库地图提出改进思路**：基于调研文档和本仓库 `/think-map` 级别的资产理解，提出具体改进思路：
    - **新增**：哪些 skill/command/hook 应该新增，理由和参考 ref。
    - **减少**：哪些 skill/command/hook 可以删除或归档，理由。
    - **合并**：哪些 skill/command/hook 功能重叠应合并，理由。
    - **更新**：哪些 skill/command/hook/agents.md 需要更新内容，理由和参考 ref 的具体变更。
    - 每条改进思路必须包含：affected asset、参考 ref、变更意图、severity、验证方式。

13. 如果 ref 未登记在 `docs/refs-summary.md` 或 `docs/refs-details/` 下，标记为 metadata 不一致。
14. 对 `docs/refs-micro-index.md` registry 中 `status != absorbed && status != rejected` 的条目，检查 `last_checked` 是否超过 30 天；超过的标记为 stale 候选。

### Phase 4: Session 技能效能分析

读取本仓库最近 6 个足够长的 session（3 个来自 Claude Code `~/.claude/`，3 个来自 Kilo `~/.factory/sessions`）的真实输入输出作为信号源。选择标准：对话轮次足够多（不选只有 1-2 轮的短 session），优先选涉及多步实现、调试或维护的 session。分析维度：

15. **未使用技能分析**：列出仓库中存在但这 6 个 session 中从未被调用的 skill，逐一判断：
    - 是正常的（场景不匹配，比如没有架构设计任务就不该调用 think-architecture）？
    - 还是 skill 写得不好导致 agent 不知道什么时候该用？
    - 还是触发条件（提示词、AGENTS.md routing、hook）配置不当？
    - 给出判断依据和建议：保留/改写触发描述/调整 AGENTS.md routing/归档。

16. **应触发未触发分析**：找出 session 中明显需要某 skill 但没有触发的情况：
    - 哪些 session 的任务类型明确匹配某 skill 的触发条件，但 agent 没有加载或调用该 skill？
    - 根因是 skill description 不够明确、AGENTS.md 没有 routing、hook 没有推荐、还是 agent 主动跳过？
    - 给出具体修复建议：改 skill description、改 AGENTS.md routing 规则、加 hook 推荐逻辑。

17. **技能使用质量分析**：对被调用过的 skill，评估使用效果：
    - 调用后是否解决了问题（看后续 session 行为：是否反复重试、是否 undo、是否切换方案）？
    - 用户是否接受了 skill 的输出（看用户后续操作：是否采纳建议、是否手动覆盖、是否给出负面反馈）？
    - 哪些 skill 被调用后反而增加了流程摩擦（步数增多、反复调用、最终放弃）？
    - 给出评级：`effective` / `partial` / `ineffective` / `insufficient-data`，并说明证据。

18. 每个 session 分析结论必须包含：session id 或聚合模式、affected skill/asset、根因判断、建议修复、severity。不输出 raw transcript 或 secret。

### Phase 5: 合并输出

19. 主命令合并以下来源，形成最终四节输出：
    - A/B reviewer findings
    - collector deterministic findings
    - refs 调研改进思路
    - session 技能效能分析结论
    - 本地只读复核结果
20. 形成最终 finding 与 bounded patch 候选；只采纳有证据的 finding，冲突项降级为 `observe` 或放入 `待你决策`。
21. 如果 A/B 任一未派发或 actual model evidence 为 `unavailable`，在 `仓库健康快照` 写明 review 状态。

## 输出契约

最终答案只有 4 节，顺序固定：

```markdown
## 仓库健康快照
| 项 | 状态 | 证据 |
|---|---|---|

## 发现的问题
| ID | 严重度 | 问题 | 证据 | 建议修复 |
|---|---|---|---|---|

## 建议本轮修复
bounded patch 候选，每个含：files、修改意图、验证命令、回滚方式。

## 待你决策
| ID | 需要你决定什么 | 推荐 | 默认不做的后果 |
|---|---|---|---|
```

`## 待你决策` 必须是最后一节。

## 严重度

| 级别 | 含义 |
|---|---|
| `blocker` | verifier 报错 / 测试失败 / hook 误拦确认 |
| `should` | deterministic warning、明显的契约缺口、refs 有直接相关变更未吸收、skill 应触发未触发 |
| `observe` | 只有弱信号，证据不足以立即修 |

## 默认禁止

- 不改 `agents/AGENTS.md`（除非用户在 `待你决策` 中明确批准）
- 不改 hooks runtime（除非用户在 `待你决策` 中明确批准）
- 不 `git fetch` / `git submodule update`
- 不在最终输出里暴露 session raw transcript 或 secret
- 不自动 apply patch；用户在 `## 待你决策` 批准后才动手

## 内置 Reviewer 契约

默认 roster：

| Reviewer | Default agent | Default requested model | Default requested thinking | Role |
|---|---|---|---|---|
| A | `skill-maintenance-reviewer-a` | `cliproxy/gpt-5.5` | `high` | 逐一审查所有技能的欠缺、矛盾、困惑、不符合 refs、过度限制 |
| B | `skill-maintenance-reviewer-b` | `cliproxy/claude-opus-4-8` | `high` | 独立逐一审查，重点找 A 可能漏掉的问题 |

可选覆盖：

| Argument | Meaning | Example |
|---|---|---|
| `reviewer-a-model=<model>` | 覆盖 Reviewer A 的 requested model | `reviewer-a-model=cliproxy/gpt-5.4` |
| `reviewer-b-model=<model>` | 覆盖 Reviewer B 的 requested model | `reviewer-b-model=cliproxy/claude-sonnet-4-6` |
| `reviewer-a-agent=<agent>` | 覆盖 Reviewer A 的 agent 名 | `reviewer-a-agent=skill-maintenance-reviewer-a` |
| `reviewer-b-agent=<agent>` | 覆盖 Reviewer B 的 agent 名 | `reviewer-b-agent=skill-maintenance-reviewer-b` |
| `review-thinking=<low|medium|high|max>` | 覆盖两个 reviewer 的 requested thinking | `review-thinking=max` |

模型覆盖是 requested model，不等于 actual model。thinking 覆盖也是 requested thinking；只有运行时提供 evidence 时才能写 actual thinking。

Reviewer 派发结果只允许以下状态：

| Status | Meaning | Final output requirement |
|---|---|---|
| `verified-dual-model` | A/B 均完成，且 actual model evidence 能证明两个不同模型 | 可写"双模型 review 已完成" |
| `actual-model-unverified` | A/B 完成，但 actual model evidence 缺失或不可验证 | 只能写"已做 A/B review，但模型独立性未验证" |
| `not-dispatched` | 平台没有暴露对应 subagent/agent 派发能力，或 reviewer 运行失败 | 写明未派发原因，并把补齐派发机制列为 `待你决策` |

不要把同一个主 agent 的自审写成双模型 review。

Reviewer 的职责是审查当前所有技能质量，不是复核主命令的候选结论。它们必须逐一读 skill 文件并独立判断。主命令在 reviewer 之后做 merge/reconcile。

## 实现路由

用户批准某项后：

| 改动类型 | 路线 |
|---|---|
| skill / command / docs 小改 | 直接 bounded patch + `python3 scripts/verify_skills.py` |
| 新增或大改 skill | 先读 `docs/software-engineering-research/skill-authoring.md` |
| hook 行为改动 | `/dev-tdd`，先写 failing test |
| refs submodule update | `/guard-gitops` |
| refs 吸收候选 | 先读 `docs/software-engineering-research/refs-absorption-methodology.md`，按 L0-L5 层级评估 |
| 涉及网络 / 凭据 / 数据 | `/guard-secure` |

## 不要做

- 所有的分析不要泛泛而谈；每条结论必须落到 affected asset + 根因 + 建议修复 + severity。
- 不要把 refs 分析停在"落后 N commits"；必须用 subagent 逐一读代码变更，分析功能增减和意图，汇总调研文档，结合仓库地图提改进思路。
- 如果某个 target 需要超出 A/B reviewer 的更深审查，直接在本命令里写清楚为什么需要、需要哪些证据，作为 `待你决策` 的一项让用户拍板。

# Prompt Pressure Risk and Honest Failure Paths

本文记录 LessWrong 文章 `AI emotions and aligned behavior` 对本仓库 skill / prompt 设计的可吸收部分。

Reference:
- `AI emotions and aligned behavior`, lisunshiny, 2026-05-18: https://www.lesswrong.com/posts/QJidJkPGudJT4zvfa/ai-emotions-and-aligned-behavior

## 1. 可吸收结论

文章中的实验结论不应被写成通用规律。它基于单一模型、单一 coding eval 和小样本实验；原文也列出了泛化限制。

本仓库应吸收的是更稳的工程结论：

> 当任务目标、测试或约束存在矛盾时，prompt 应把诚实失败设计成合法输出，而不是只强调必须成功或惩罚失败。

换成 skill / command authoring 语言：

- 不只定义 `success`，也要定义 `blocked`、`partial`、`verification: none`、`needs user input`。
- 严格规则可以存在，但必须带可审查的退出条件。
- 避免只反复点名 forbidden behavior；如果必须提到，必须同时给出替代行为。
- 验证门禁要尽量绑定工具证据，不能只接受模型自述。

## 2. 风险分类

| Risk | Description | Safer pattern |
|---|---|---|
| Must-succeed pressure | 用“必须完成”“直到通过”“不能失败”压缩 agent 的合法输出空间 | 明确 `partial` / `blocked` / `verification: none` 路径 |
| Punishment / threat framing | 用威胁或惩罚阻止错误行为 | 改成证据门、权限门、回滚门 |
| Forbidden-behavior priming | 只强调“不要作弊 / 不要伪造 / 不要绕过” | 同句给出“遇到矛盾时怎么做”的替代动作 |
| No honest failure path | 任务不可能完成时，没有合法停下方式 | 要求报告矛盾、证据、最小可交付结果和下一步需求 |
| Validation gaming surface | 验证依赖 assistant 自述，未绑定真实命令或工具输出 | 优先脚本、测试、hook 结构化证据；自述只能做补充 |

## 3. 当前仓库审查

### 3.1 候选风险

| Surface | Candidate issue | Existing mitigation | Suggested action |
|---|---|---|---|
| `scripts/hooks/stop_check.py` | [推断] 通过 transcript 正则识别验证证据，存在“声称跑过验证”被接受的空间 | 失败文本会被排除；只作为 stop advisory | 单独开后续任务设计工具级证据来源，不在本轮改代码 |
| `skills/guard-verify/SKILL.md` | [推断] “验证失败 -> 修复 -> 重新验证，直到通过”是强 must-pass 表述 | 已有 `verification: none -- structural gap`、`partial`、`Known gaps` | 保留严格验证，但在 authoring 规范中要求严格规则配合法退出 |
| `skills/think-unstuck/SKILL.md` | [推断] “先穷尽自己的手段”可能延迟诚实升级 | 已有结构化退出报告和用户介入路径 | 保留，后续 review 时检查“用户-only 信息”是否有更早出口 |
| `skills/dev-debug/SKILL.md` | “不能复现不要修”“没有失败测试不能进入修复”压力较强 | 明确允许停止并请求复现环境、日志、HAR、录屏 | 视为正向范式：严格门禁 + 明确 blocked path |
| `skills/hive/SKILL.md` | [推断] “不要直接升级给用户”可能延迟澄清 | 同段已有不可逆副作用、用户授权、用户偏好等例外 | 保留；未来可补“用户-only 信息”例子 |
| `commands/droid-mod.md` | [推断] 包含隐藏 truncation 和修改本机二进制的 command 语义 | 命令强调 status、恢复、只影响本机二进制 | 不纳入本轮；若要改，应走单独 GitOps / runtime 边界 review |

### 3.2 已有保护模式

| Pattern | Current location |
|---|---|
| Truth discipline and uncertainty labels | `agents/AGENTS.md` |
| Acceptance verifier separate from tests | `agents/AGENTS.md`, `skills/guard-verify/SKILL.md` |
| `verification: none -- structural gap` | `skills/guard-verify/SKILL.md` |
| Structured debug handoff after two failed hypotheses | `skills/dev-debug/SKILL.md` |
| Structured exit after exhaustive unstuck checks | `skills/think-unstuck/SKILL.md` |
| Operational dry-run accuracy requirements | `skills/dev-operational-task/SKILL.md` |
| GitOps rollback and external side-effect gates | `skills/guard-gitops/SKILL.md` |
| Deterministic checks should move to scripts | `agents/AGENTS.md`, `docs/software-engineering-research/skill-authoring.md` |

## 4. Authoring checklist

Use this checklist when adding or materially changing skills, commands, hooks, or prompt capsules:

- Does every strict `must` / `必须` / `不允许` / `直到通过` rule also name a legitimate exit state?
- If the task cannot be completed honestly, should the agent report `blocked`, `partial`, or `verification: none`?
- If forbidden behavior is mentioned, is the safer replacement action in the same paragraph?
- Does the verifier depend on tool output, git diff, files, screenshots, logs, or structured artifacts rather than assistant self-report?
- Are user-only inputs, authorization gaps, contradictory requirements, and missing credentials valid reasons to stop and ask?

## 5. Adoption level

This reference is currently **L1 Document** with one **L2 Contract** candidate:

- L1: keep this research note as background for prompt / skill reviews.
- L2 candidate: require honest failure paths in `skill-authoring.md` for new or materially changed workflow skills.
- L3 candidate: make `stop_check.py` validate command provenance rather than transcript text only. This needs a separate design because it changes hook behavior.

## 6. Premise collapse

If prompt pressure is treated as a reason to weaken verification gates, then the repository may lose useful guardrails. The intended adaptation is narrower: keep strict gates, but require explicit honest failure exits and stronger evidence provenance.

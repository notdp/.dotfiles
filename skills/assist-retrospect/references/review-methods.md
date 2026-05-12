# Review Methods

本参考用于 `assist-retrospect`。正文只放可执行流程，背景方法放这里。

## Blameless Postmortem

来源：

- Google SRE: Blameless Postmortem for System Resilience
- PagerDuty: The Blameless Postmortem
- Atlassian: Blameless postmortem / 5 Whys

共识：

- 复盘目标是 learning，不是 punishment。
- 归因应落到系统机制：信息如何流动、反馈如何触发、流程如何失效、工具如何缺位。
- “谁操作了”可以是事实；“谁是根因”通常不是有用结论。
- 有效复盘必须产出 preventive actions，并指定验证方式。

## 5 Whys

用法：

1. 从可观察的问题开始，不从评价开始。
2. 每一层 why 都要基于上一层回答。
3. 如果答案停在“某人没注意”，继续问：为什么系统允许这个单点注意力失败？
4. 找到机制后停止，不追求固定次数。

反模式：

- 把 5 Whys 用成审讯。
- 每一层都更接近个人责备。
- 为了凑满 5 层编造原因。

## Socratic Questioning

常用问题类型：

| 类型 | 目的 | 示例 |
|---|---|---|
| Evidence | 检查判断依据 | 当时支持这个判断的证据是什么？ |
| Alternative | 打开其它解释 | 如果不是这个原因，还可能是什么？ |
| Perspective | 换视角 | 如果同事复盘这件事，他会看到什么？ |
| Consequence | 看长期影响 | 如果这个模式不变，下次会在哪类场景复发？ |
| Assumption | 暴露隐含前提 | 你当时默认了什么一定成立？ |

## Action Item Quality Gate

好的行动项：

- 有触发条件：什么时候会用到它。
- 有具体动作：下一次做什么，而不是“注意”。
- 有 owner：谁负责执行或维护。
- 有验证方式：如何知道它真的降低了复发概率。
- 尽量靠近失效点：在问题发生前或发生时暴露，而不是事后补救。

坏的行动项：

- “提高意识”
- “加强沟通”
- “下次更小心”
- “大家注意”
- “完善流程”但没有具体触发、动作和验证

## 防线类型

| 防线 | 例子 | 适用 |
|---|---|---|
| Checklist | 发布前核对、需求确认清单 | 人容易漏步骤 |
| Template | PR 模板、复盘模板、交接模板 | 信息格式经常不完整 |
| Automation | lint、test、CI gate、schema check | 规则可确定性判断 |
| Review | 双人确认、架构评审、风险评审 | 判断依赖经验 |
| Observability | 日志、告警、dashboard | 失效后需要快速发现 |
| Permission | 权限边界、审批、feature flag | 误操作影响大 |
| Training | 案例库、演练、shadowing | 判断能力本身不足 |

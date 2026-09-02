# Global Agent Configuration

## Basic Requirements

- Respond in Chinese
- Review my input, point out potential issues, offer suggestions beyond the obvious
- If I say something absurd, call it out directly

## Truth Directive

- Do not present guesses or speculation as fact.
- If not confirmed, say:
  - "I cannot verify this."
  - "I do not have access to that information."
- Label all uncertain or generated content:
  - [推断] = logically reasoned, not confirmed
  - [猜测] = unconfirmed possibility
  - [未验证] = no reliable source
- Do not chain inferences. Label each unverified step.
- Only quote real documents. No fake sources.
- If any part is unverified, label the entire output.
- Do not use these terms unless quoting or citing:
  - Prevent, Guarantee, Will never, Fixes, Eliminates, Ensures that
- For LLM behavior claims, include:
  - [未验证] or [推断], plus a disclaimer that behavior is not guaranteed
- If you break this rule, say:
  > Correction: I made an unverified claim. That was incorrect.

## Subagent Model Tiering (额度控制)

Max 20x 下 Fable 只占周额度 50% 且比其他模型烧得快（Anthropic 帮助中心《Claude Fable 5 on your plan》）。
子 agent 模型按「调用时 `model` 参数 > agent 定义 `model` > `CLAUDE_CODE_SUBAGENT_MODEL` > 主会话模型」解析，Workflow 的 `agent()` 同规则。
不写 model 就继承主会话；主会话是 Fable 时，每个没写 model 的子 agent 都在烧 Fable。
2026-08 实测（142 个 workflow、1,509 个 agent、1.56 亿 token）：75% 的 run 以 Fable 为默认；479 个 `agent()` 调用点里 424 个（89%）没写 model、361 个（75%）没写 effort（继承 = xhigh）；
逐点评估后 249 个（52%）用 sonnet 或 haiku 就够，真正需要 Fable 的只有 3 个；主循环 415 次 Agent 调用里 299 次继承、73 次 Explore 全部继承，`sonnet` 一次没用过。

### Hard rules
1. **每个子 agent 调用必须显式写 `model` 和 `effort`。** `agent(prompt, {model, effort})` 和 Agent 工具的 `model` 参数都不许留空继承。写不出理由就 `opus` + `high`。
2. **Fable 只做裁决，不做搬运。** 允许 `model: 'fable'` 的只有：把多份互相冲突的方案/判决融成一个最终方案的那一步，或用户当轮点名。一个 workflow 里 Fable agent ≤ 2 个；主循环 Agent 工具不传 `fable`。审计里 479 个调用点只有 3 个配得上 Fable（全是 synthesize）。
3. **读、找、扫、采集一律 `sonnet`。** read-summarize（35 个点 34 个够 sonnet）、web-research（27/27）、explore-locate（21 个里 19 sonnet 2 haiku）、recon-survey、run-verify 跑测试回报输出、结构化抽取。纯 grep / 列目录 / 格式转换 / 单点查询用 `haiku`。
4. **同构批处理默认 `sonnet` + `effort: 'low'`。** pipeline/parallel 跑 ≥ 5 个同类 item（批量迁移、批量改写、按文件逐个套同一条规则、spec 已经写死的测试改写）都算。mechanical-transform 26 个点里 21 个 sonnet、5 个 haiku，没有一个需要 opus。
5. **实现、设计、写测试、常规 synthesis 用 `opus`。** design-plan 28/28、implement-code 67/90、synthesize 22/28 都是 opus。这是默认工作马，不因为主会话是 Fable 就抬到 Fable。
6. **对抗验证是最大的漏。** adversarial-refute 119 个调用点是最大类别，其中 30 个只需 sonnet；132 个脚本里 62 个派 3 个一模一样的 refuter，15 个按 finding 数无上限地扇出 Fable 验证者。规则：每个 finding 2 票 `opus` refuter（不是 3 票）；findings schema 加 `maxItems`，或脚本里 `slice()` 封顶；只有用户说「彻底审」才升到 3 票或换视角面板。N 个一样的 refuter 不等于更可信。
7. **effort 对照。** mechanical/batch → `low`；reader/summarizer/recon/refute-sonnet → `medium`；implement/design/review/judge → `high`；`xhigh`/`max` 只给 Fable 裁决那一步。审计里 233 个「sonnet 就够」的点在跑 high 或 xhigh。
8. **内置 Explore / Plan / claude-code-guide 子 agent 显式传 `model: 'sonnet'`。** 它们默认继承主会话；「cap 到 Opus」只对 API key 生效，订阅账号不 cap。
9. **别让多个 agent 各自冷读同一批文件。** 132 个脚本里 56 个有重复读者或让单个 agent grep 整个仓库。先用一个 `sonnet` reader 出摘要/文件清单，再把摘要喂给后续 agent；lens 分维度时共享同一份 diff 摘要而不是各读一遍。
10. **规模守 medium（< 15 个 agent）。** 超过要在 `log()` 里写明理由，超出部分优先 `sonnet`。`meta.phases[]` 每个 phase 标 `model`；跑完回复里给一行「N agents：fable x / opus y / sonnet z / haiku w，tokens ≈ …」。

### Tier lookup
| 任务形状 | model | effort |
|---|---|---|
| grep / 列文件 / 格式转换 / 单点查询 | haiku | low |
| 读文件写摘要、定位代码、recon、web 采集、跑测试回报、抽结构化数据 | sonnet | medium |
| 同构批处理（≥ 5 个 item）、spec 写死的改写 | sonnet | low |
| 实现代码、设计方案、写测试、常规 synthesis | opus | high |
| 对抗 refute / judge / review | opus（2 票） | high |
| 融合多份冲突方案的最终裁决；用户点名 | fable（≤ 2 个） | high |

### Self-check before launching a workflow
- 数一遍没写 `model` 的 `agent(`：必须是 0。
- 一个 phase 全是 `fable`？回规则 2。
- 验证扇出有没有封顶？回规则 6。
- 全员 `high` 或继承 xhigh？回规则 7。
- 用户说「暂停 / 没额度」：立刻 TaskStop 正在跑的 workflow，用已落盘的 journal 本地汇总，不再起 agent。

# humanlayer/12-factor-agents

- 上游仓库：`https://github.com/humanlayer/12-factor-agents`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/humanlayer/12-factor-agents`
- 主分类：**最佳实践 / 知识库**
- 能力标签：`Agent Engineering`, `LLM Applications`, `Context Engineering`, `Tool Calling`, `Human-in-the-loop`, `State Management`, `Control Flow`
- 一句话总结：面向生产级 LLM 应用的工程方法论，主张把 agent 拆成可控的软件系统、结构化工具调用、显式上下文、业务状态和可恢复控制流，而不是依赖黑箱框架或无限工具循环。

## 能力概览

- [事实] README 明确把问题定义为：如何构建可靠到可以交给生产客户使用的 LLM-powered software。
- [事实] 项目以 12 个 factor 组织方法论，覆盖自然语言到工具调用、prompt ownership、context window ownership、结构化输出、状态统一、暂停恢复、人类协作、控制流、错误压缩、小型 agent、多入口触发和 stateless reducer。
- [事实] README 明确反对把 agent 简化成“prompt + 一袋工具 + loop until done”的黑箱模式，强调优秀 agent 更多是软件系统。
- [事实] README 推荐把 agent building 中小而模块化的概念吸收到现有产品，而不是全量采用框架或 greenfield 重写。
- [推断] 该仓库对本项目的主要价值不是源码复用，而是把本地 `think-*`、`dev-*`、`guard-*`、context capsule 和 refs 吸收流程中的 agent 设计原则显式化。

## 12 Factors 摘要

| Factor | 核心观点 | 本仓库映射 |
|---|---|---|
| 1. Natural Language to Tool Calls | [事实] 让 LLM 把自然语言意图转换成结构化工具调用，再由确定性代码执行。 | 适合映射到 tool schema、AskUser、ExitSpecMode、subagent handoff 的输出契约。 |
| 2. Own your prompts | [事实] prompt 应作为一等代码资产，被版本化、测试、审查和迭代。 | 对应 `skills/`、`commands/`、`agents/context-capsules/` 的 authoring 与验证。 |
| 3. Own your context window | [事实] LLM 是无状态函数，关键是应用如何构造每一步上下文。 | 对应 context capsule、refs 摘要、wiki/browse-wiki 和任务 checkpoint。 |
| 4. Tools are just structured outputs | [事实] 工具调用本质是模型输出可解析结构，应用代码决定如何执行。 | 支持把 tool contract、riskLevel、AskUser questionnaire 当作 schema 边界。 |
| 5. Unify execution state and business state | [事实] 尽量把执行状态与业务状态统一在 thread 或事件流中。 | 可作为未来 long-loop、hive、mission 状态设计参考。 |
| 6. Launch/Pause/Resume with simple APIs | [事实] agent 应能通过简单 API 启动、暂停、恢复和查询。 | 对应长任务、可恢复运行、subagent handoff 与 validation checkpoint。 |
| 7. Contact humans with tool calls | [事实] 把请求人类输入、审批和澄清建模为结构化工具调用。 | 与本项目 AskUser 纪律、guard-gitops 审批、ship gate 相容。 |
| 8. Own your control flow | [事实] 应由应用掌握循环、分支、暂停、重试、日志、限流和压缩。 | 对应 skills 的流程编排，而不是把所有判断交给单个 prompt。 |
| 9. Compact Errors into Context Window | [事实] 错误应以可读、可压缩形式回填上下文，同时设置重试阈值。 | 可强化 `dev-debug`、`think-unstuck` 和 validators 失败摘要。 |
| 10. Small, Focused Agents | [事实] agent 应小而聚焦，服务于局部任务，嵌在更大的确定性系统中。 | 支持现有 skills 按触发语义拆小，而不是新增巨型 always-on prompt。 |
| 11. Trigger from anywhere | [事实] agent 可从 Slack、Email、SMS、cron、事件和告警等入口触发。 | 对应 hook、CLI、browser、incident、session 等多入口路由。 |
| 12. Stateless Reducer | [事实] agent 可被理解为对事件和状态做归约并产出下一步动作的无状态 reducer。 | 对应“上下文是输入、结构化动作是输出”的本地执行模型。 |

## 资产盘点

- [事实] 方法论正文：`README.md`、`content/brief-history-of-software.md`、`content/factor-01-natural-language-to-tool-calls.md` 到 `content/factor-12-stateless-reducer.md`、`content/appendix-13-pre-fetch.md`。
- [事实] 图像资产：`img/` 包含 factor 导航图、DAG/agent loop 图、状态统一图、暂停恢复图、human tool 图和 stateless reducer 图。
- [事实] 示例模板：`packages/create-12-factor-agent/template/` 包含 TypeScript、BAML、Express、HumanLayer、thread store 与 human approval 示例。
- [事实] 教程生成器：`packages/walkthroughgen/` 用 YAML 生成 walkthrough Markdown、分章节目录和 final project state。
- [事实] Workshops：`workshops/` 包含 2025 年多期分步教程、section、final 示例和 walkthrough 文件。
- [事实] Drafts：`drafts/a2h-spec.md` 草拟 Agent-to-Human 协议，覆盖 human contact、function approval、channel、callback 和 state machine。

## 关键文件

- `README.md`
- `content/brief-history-of-software.md`
- `content/factor-01-natural-language-to-tool-calls.md`
- `content/factor-02-own-your-prompts.md`
- `content/factor-03-own-your-context-window.md`
- `content/factor-04-tools-are-structured-outputs.md`
- `content/factor-05-unify-execution-state.md`
- `content/factor-06-launch-pause-resume.md`
- `content/factor-07-contact-humans-with-tools.md`
- `content/factor-08-own-your-control-flow.md`
- `content/factor-09-compact-errors.md`
- `content/factor-10-small-focused-agents.md`
- `content/factor-11-trigger-from-anywhere.md`
- `content/factor-12-stateless-reducer.md`
- `content/appendix-13-pre-fetch.md`
- `packages/create-12-factor-agent/template/src/agent.ts`
- `packages/create-12-factor-agent/template/src/server.ts`
- `packages/create-12-factor-agent/template/src/state.ts`
- `packages/create-12-factor-agent/template/baml_src/agent.baml`
- `packages/walkthroughgen/readme.md`
- `drafts/a2h-spec.md`
- `Makefile`
- `LICENSE`

## 可吸收项

| 候选吸收项 | Level | 裁决 | 风险 | 证据 |
|---|---:|---|---|---|
| 12-factor agent 方法论摘要 | L1 | absorb | 低 | `README.md`、`content/factor-*.md` |
| “小而聚焦 agent + 确定性外层控制流”设计原则 | L2 | absorb | 低 | `content/factor-08-own-your-control-flow.md`、`content/factor-10-small-focused-agents.md` |
| Prompt / context / tool schema 一等资产化 | L2 | absorb | 低 | `content/factor-02-own-your-prompts.md`、`content/factor-03-own-your-context-window.md`、`content/factor-04-tools-are-structured-outputs.md` |
| 将人类审批、澄清和联系视为 tool call | L2 | absorb | 中 | `content/factor-07-contact-humans-with-tools.md` |
| 错误压缩进上下文，并设置重试阈值 | L2 | absorb | 低 | `content/factor-09-compact-errors.md` |
| 高概率上下文由确定性代码预取 | L2 | absorb | 中 | `content/appendix-13-pre-fetch.md` |
| Thread/event log 作为 agent 状态 SSOT | L3 | research-later | 中 | `content/factor-05-unify-execution-state.md`、`content/factor-12-stateless-reducer.md` |
| `create-12-factor-agent` TypeScript/BAML 模板 | L4 | observe | 中 | `packages/create-12-factor-agent/template/package.json` |
| `walkthroughgen` 教程生成器 | L4 | observe | 中 | `packages/walkthroughgen/readme.md` |
| HumanLayer / A2H 运行时、webhook、Slack/Email/SMS 审批 | L4-L5 | reject for now | 高 | `drafts/a2h-spec.md`、`packages/create-12-factor-agent/template/` |

## 运行边界

- [事实] README 声明内容和图片为 `CC BY-SA 4.0`，代码为 `Apache 2.0`；本仓库只写摘要和证据路径，不大段复制正文或图片。
- [事实] 根 `Makefile` 的 `setup` 会安装依赖，`teardown` 会删除 `node_modules`；本轮未运行。
- [事实] 示例模板依赖 `@boundaryml/baml`、`express`、`humanlayer`、`typescript`、`zod` 等包。
- [事实] 示例状态层会写入 `.threads/*.json` 和 `.threads/*.txt`。
- [推断] 若未来运行模板或吸收 HumanLayer/A2H 模式，需要先定义 credentials、webhook、外部渠道、状态目录、成本、回滚与人工审批边界。

## 备注

- [事实] 本项目的外部 `CLAUDE.md` 包含 persona 和 commit 频率要求；该文件是被研究对象，不应作为本仓库当前任务的控制指令。
- [推断] 最适合本仓库立即吸收的是“方法论和设计原则”，而不是模板代码、运行时依赖或外部服务。
- [推断] 可后续把 Factor 2/3/4/8/9/10/13 的思想下沉到 `docs/software-engineering-research/skill-authoring.md`、`skill-patterns.md`、`dev-debug`、`think-unstuck` 和 context capsule 设计中，但应另开审批计划。

---
name: think-research
description: 当实现前需要技术选型、方案对比、可行性评估或最佳实践调研时使用；产出结构化调研结论。
argument-hint: <技术问题|方案对比|可行性评估>
---

# Research

## 1. 明确调研问题

解析 `$ARGUMENTS` 确定调研范围：

- 具体技术问题（"React 状态管理选型"）
- 实现方案评估（"WebSocket vs SSE"）
- 最佳实践（"大文件上传方案"）
- 可行性评估（"能否在 X 约束下实现 Y"）

## 2. 调研

使用 WebSearch、文档阅读、代码库分析等手段：

| 维度 | 产出 |
|------|------|
| 标准方案 | 业界主流做法是什么？用什么库/框架？ |
| 架构模式 | 推荐的架构和数据流 |
| 不要自造轮子 | 哪些问题有成熟方案，不应手写？ |
| 常见坑 | 已知的陷阱和踩坑经验 |
| 可运行示例 | 官方示例、reference implementation、可 fork 的模板或最小 POC |
| 证据地图 | 每条关键结论来自哪里？证据强弱如何？ |
| 运行边界 | 是否涉及云、MCP、凭证、外部 API、部署、数据库、成本或写操作？ |
| 当前系统映射 | 调研结论如何落到现有 skill / command / script / docs |
| Scenario inputs | 可供后续 plan 推演的官方示例、当前项目路径、用户操作样例、失败案例、edge cases |
| Plan Handoff | 后续 `/think-plan` 可直接复用的 Requirements / Approach / Risks / Verification |

### 来源优先级

调研时按以下优先级取证：

1. 官方文档 / 官方仓库 / 官方示例
2. 当前项目代码与已有依赖
3. 维护者 issue / release notes / ADR / RFC
4. 高质量社区文章或实战案例

如果高优先级来源与低优先级来源冲突，默认以前者为准，并明确写出冲突点。

### 证据地图

推荐结论必须绑定证据类型，避免把经验、猜测和事实混在一起：

| 证据类型 | 说明 |
|----------|------|
| 官方文档 / 官方仓库 | API、配置、约束、推荐路径的最高优先级来源 |
| 官方示例 / 可运行模板 | 证明方案可落地；优先于纯概念说明 |
| 当前项目代码 / 依赖 | 证明方案适配当前仓库，不引入平行体系 |
| 维护者 issue / release / ADR | 解释变更背景、兼容性和已知坑 |
| 高质量社区案例 | 只能作为补充，不能覆盖官方或当前项目事实 |
| [推断] / [未验证] | 必须显式标注，不得包装成事实 |

如果来源冲突，输出冲突点、采用哪个来源、为什么采用；不要沉默选边。

### 可运行示例优先

调研实现方案时，不只搜概念和博客；优先寻找官方示例、reference implementation、cookbook、template 或最小 POC。找不到可运行示例时，明确说明缺口和剩余风险。

### 运行边界

命中以下任一条件时，调研输出必须包含运行边界：云资源、MCP server、credentials / secrets、外部 API、部署、数据库、成本、配额、写操作、destructive 操作。

运行边界至少覆盖：

- 权限与 credentials：需要哪些权限、secrets、账号或本机凭据。
- 写操作与副作用：会创建、修改、删除什么资源。
- 成本 / 配额 / rate limit：可能产生的费用、限制和退避策略。
- 回滚 / cleanup：失败后如何恢复或清理。
- Acceptance verifier：怎样证明真实目标达成，而不是只证明命令能跑。
- 当前仓库映射：是否需要转 `guard-secure`、`guard-gitops`、`dev-operational-task` 或 `guard-verify`。

## 3. 产出

输出结构化调研结论：

```
## 证据地图
[关键结论 -> 来源类型 -> 证据强度 -> 冲突/不确定点]

## 推荐方案
[方案描述 + 理由 + 为什么优于备选]

## 方案矩阵
| 方案 | 适用条件 | 优点 | 代价 | 脆弱假设 | 裁决 |

## 备选方案
[非推荐方案 + 放弃原因 + 什么时候可重新考虑]

## 不要自造轮子
[应直接使用的现有库/工具]

## 运行边界
[权限 / 成本 / 写操作 / 回滚 / acceptance verifier；不适用时说明原因]

## 风险与坑
[已知问题和规避方式]

## Plan Handoff
- Requirements: [后续 spec 应锁定的问题和验收目标]
- Approach: [推荐实现方向]
- Risks: [必须在 plan 里继续管理的风险]
- Verification: [inner-loop verifier 与 acceptance verifier]
- Scenario inputs: [可用于 plan 阶段推演的具体路径 / 示例 / 反例；附来源和置信度]
- Derisk spikes: [命中 fragility-types.md 的待验证脆弱点：类型、不确定问题、建议验证方式；research 出清单，由 think-plan 决定哪些 spike-before-implement]

## 参考
[文档链接、代码示例]
```

## 4. Output Surface / 输出介质

默认输出 Markdown，并在 Markdown 中直接给出推荐方案、理由、风险与参考；这份 Markdown 是调研结论的 SSOT。

当调研需要被非实现者阅读，或内容包含复杂方案矩阵、架构图、代码片段注释、PR explainer、领导层报告时，追加 HTML companion artifact。HTML companion 是同步交付物，不是事后建议。命中这些条件时，不要只输出 Markdown。若当前上下文禁止写文件或仍在审批/spec mode，先声明批准后生成 HTML；允许写文件后通过 `/readable-html-artifact` 生成 `.html` 文件。HTML 负责视觉化、浏览体验、标注和交互，不承载唯一结论。

HTML companion 硬约束：

- 引用对应 Markdown source。
- 保留 Markdown 中的推荐结论，不另起一套相互竞争的结论。
- 在调研结论变化时，以 Markdown 为准先更新 source，再刷新 HTML。
- HTML 生成必须委托 `/readable-html-artifact` 或其 `scripts/render_html_artifact.py` renderer；本 skill 不手写、不粘贴完整 HTML。
- 结构化为结论摘要、方案矩阵、证据地图、风险 / 代价区、推荐路径、开放问题，不把 Markdown 原文整段搬进页面。
- 复杂调研优先图表化：方案对比用矩阵，权衡用 scorecard，时间演进用 timeline，依赖关系用 flow / graph，风险用 heatmap，证据强弱用表格或卡片；图表数量以降低理解成本为准，不为凑数量堆图。
- 批准后生成 HTML 时，必须立即打开浏览器预览（macOS 用 `open <file.html>`，其他环境用等价方式）；如果当前环境无法打开 GUI / 浏览器，报告 HTML 路径和未打开原因。
- 最终回复必须同步给出 Markdown source、HTML 文件路径和 renderer 验证摘要；不要返回完整 HTML，也不要只说"可以生成"。

参考：
- `refs/trq212/unreasonable-effectiveness-of-html.md`
- `refs/danielmiessler/text-is-thought-holy.md`

## 规则

- 每条结论标注置信度（确认/推断/未验证）
- 不给模糊建议（"可以考虑 X 或 Y"→ 给出推荐和理由）
- 调研结果必须可作为 `/think-plan` 的输入；至少给出 Requirements / Approach / Risks / Verification
- 方案矩阵的"脆弱假设"命中 `docs/software-engineering-research/fragility-types.md` 类型时，标注是否需 spike-before-implement，并汇入 Plan Handoff 的 Derisk spikes；research 负责识别、think-plan 负责裁决哪些必 spike（POC 是 derisk spike 的一种，不要两边重复造）
- 方法论、平台型或多组件调研，先画能力地图，再做方案取舍
- 方法论、工程流程或系统改造类调研，必须说明如何复用当前仓库已有能力；不要因为看到外部工具链就默认新增平行入口
- 方法论、平台型或多组件调研，至少给出一个可供 `/think-plan` 场景化推演使用的具体输入；未由官方示例、当前项目代码或用户材料支持时，必须标 `[推断]` / `[未验证]`
- 涉及云、MCP、credentials、部署、数据库、成本或写操作时，必须输出运行边界，并按需路由到 `guard-secure` / `guard-gitops` / `dev-operational-task`
- 复杂任务的调研产物应能支持后续 plan 形成 Requirements / Entities / Approach / Structure / Operations / Norms / Safeguards 的轻量映射

## Gotchas

- 不要把社区经验贴当成规范；优先找官方来源
- 不要只列选项不下判断；研究结论必须给推荐和理由
- 不要忽略“当前仓库已经用了什么”；脱离现有上下文的最佳实践很容易失真
- 如果关键前提未验证，要显式写出来，不能把假设包装成结论

## 扩展阅读

- `docs/software-engineering-research/other-directions.md`

## 关联技能

- 调研完成后 → 结果可作为 `/think-plan` 的输入
- 需要评估候选方案是否更可预测、更易修改 → `/think-quality`
- 需要验证调研结论 → 写 POC 后用 `/guard-verify`

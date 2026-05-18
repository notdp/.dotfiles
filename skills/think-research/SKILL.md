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
| 代码示例 | 关键实现的参考代码 |
| 当前系统映射 | 调研结论如何落到现有 skill / command / script / docs |

### 来源优先级

调研时按以下优先级取证：

1. 官方文档 / 官方仓库 / 官方示例
2. 当前项目代码与已有依赖
3. 维护者 issue / release notes / ADR / RFC
4. 高质量社区文章或实战案例

如果高优先级来源与低优先级来源冲突，默认以前者为准，并明确写出冲突点。

## 3. 产出

输出结构化调研结论：

```
## 推荐方案
[方案描述 + 理由]

## 备选方案
[方案 + 取舍对比]

## 不要自造轮子
[应直接使用的现有库/工具]

## 风险与坑
[已知问题和规避方式]

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
- 调研结果可作为 `/think-plan` 的输入
- 方法论、工程流程或系统改造类调研，必须说明如何复用当前仓库已有能力；不要因为看到外部工具链就默认新增平行入口
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

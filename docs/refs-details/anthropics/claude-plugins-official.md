# anthropics/claude-plugins-official

- 上游仓库: `https://github.com/anthropics/claude-plugins-official`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/anthropics/claude-plugins-official`
- Source SHA: `30554536742b2b465acc4a4003d419ccaaf063af`（heads/main），分析日期: 2026-06-12
- ⚠️ **Source SHA stale**：当前 submodule gitlink 已为 `f7b31235e6f01cd7cd08ad4a6699f007a4072519`（≠ 上面分析 SHA）；本文档基于旧版本，重新吸收前先核对 `git log 30554536..f7b31235`。
- 主分类: **技能集合与市场 / Claude Code 插件市场**
- 一句话总结: Anthropic 官方维护的 Claude Code plugins marketplace，价值不在直接安装整套插件，而在提供 plugin manifest、marketplace registry、commands / agents / skills / MCP 的组合分发样本，以及 PR review、modernization、hook generation、session report 等可移植工作流模式。

## 仓库性质澄清

这是一个 Claude Code 插件市场目录，不是单一 skill 仓库，也不是本仓库可直接运行的配置包。本仓库的定位是跨 agent 的 dotfiles / skills / commands / harness / refs SSOT；因此这里应吸收可迁移的组织方式和工作流模式，而不是把它改写成某个单一 agent runtime 的插件目录。

README.md:1-18 明确其定位为 `Claude Code Plugins Directory`，安装入口是 `/plugin install {plugin-name}@claude-plugins-official`。README.md:30-43 给出标准插件结构: `.claude-plugin/plugin.json`、可选 `.mcp.json`、`commands/`、`agents/`、`skills/`、`README.md`。

重要安全边界来自 README.md:5: 安装、更新、使用插件前必须信任插件；Anthropic 不控制插件包含的 MCP servers、文件或其他软件，也不能验证它们会按预期工作或不会变化。因此本仓库只能先作为 refs 证据源吸收结构和模式，不应默认安装或启用其中插件。

## 资产盘点

以下数字来自本地快照统计。

| 资产 | 数量 | 证据 |
|---|---:|---|
| marketplace entries | 222 | `.claude-plugin/marketplace.json` |
| 内部插件目录 | 36 | `plugins/` |
| 第三方插件目录 | 15 | `external_plugins/` |
| `.claude-plugin/plugin.json` | 38 | `plugins/*/.claude-plugin/plugin.json` 与 `external_plugins/*/.claude-plugin/plugin.json` |
| commands | 28 | `**/commands/*.md` |
| agents | 24 | `**/agents/*.md` |
| skills | 28 | `**/skills/*/SKILL.md` |
| `.mcp.json` | 16 | `**/.mcp.json` |

## 关键结构

### Marketplace Registry

`.claude-plugin/marketplace.json:1-9` 定义 marketplace 名称、描述和 owner，`plugins` 数组统一索引插件。内部插件用 `source: "./plugins/<name>"`，例如 `agent-sdk-dev` 在 `.claude-plugin/marketplace.json:43-51`。外部插件使用 `source.url`、`path`、`ref`、`sha`，例如 `.claude-plugin/marketplace.json:17-24`。

可吸收点: 本仓库可以建立轻量 registry 管理跨 agent 的 skills / commands / agents / hooks / refs 资产，字段至少包含 `name`、`description`、`category`、`path`、`runtime compatibility`、`risk flags`、`last validated`。外部 refs 保持 SHA 或版本记录，减少引用漂移。

### Plugin Structure

README.md:30-43 给出统一插件目录结构。`plugins/plugin-dev/skills/plugin-structure/SKILL.md` 进一步把结构拆成 manifest、commands、agents、skills、hooks、MCP integration 等组成部分。

可吸收点: 不把 `.claude-plugin` 当成本仓库唯一目标结构，但可以吸收“manifest + 资产目录 + 自动校验”的组织方式，映射到本仓库已有的 agent 配置、commands、skills、hooks 和 refs 分层。

### Internal vs External Boundary

README.md:7-10 把 `/plugins` 定义为 Anthropic 内部维护插件，把 `/external_plugins` 定义为第三方伙伴和社区插件。实际快照中 `external_plugins/` 15 个目录全部有 `.mcp.json`，而内部插件只有 `plugins/example-plugin/.mcp.json`。

可吸收点: 本仓库 future registry 应区分内部资产、refs 资产、外部服务资产。凡触及 MCP、secrets、远端服务、用户 HOME 或运行时 side effect，必须进入 guard-gitops / guard-secure / explicit approval，而不是因为来源在 marketplace 中就默认启用。

## 候选吸收模式

| 模式 | 来源 | 建议 Level | 本仓库落点 | 裁决 |
|---|---|---:|---|---|
| Asset registry + manifest 校验 | `.claude-plugin/marketplace.json`、plugin-dev | L2-L3 | `scripts/`、配置索引、skill 维护流程 | candidate |
| PR review 专科化 | `plugins/pr-review-toolkit` | L2-L4 | `guard-review`、`dev-simplify`、`dev-observe` | candidate |
| 类型 / invariant 评分卡 | `type-design-analyzer` | L2 | `think-quality`、`dev-refactor` | candidate |
| 大型迁移 preflight gate | `code-modernization` | L2-L4 | `dev-large-delivery`、`dev-operational-task` | candidate |
| Business Rule Card | `business-rules-extractor` | L2 | `think-map`、`think-architecture`、`dev-tdd` | candidate |
| Hookify 纠错转规则 | `hookify` | L2-L3 | harness / hook 维护流程 | research-later |
| Session report 成本报告 | `session-report` | L2-L3 | `readable-metrics`、`readable-html-artifact` | candidate |
| Frontend aesthetic direction | `frontend-design` | L1-L2 | `fe-ui-design` | observe |

## 重点洞察

### 1. Review 不应该只有一个大 checklist

`plugins/pr-review-toolkit/commands/review-pr.md:20-28` 把 review 拆成 `comments`、`tests`、`errors`、`types`、`code`、`simplify` 六类。`review-pr.md:35-43` 按变更内容决定适用 review，`review-pr.md:57-88` 再聚合 Critical / Important / Suggestions / Strengths。

本仓库现有 `/guard-review` 已经强调 finding 证据和 severity，但可以吸收“专科化”而不是复制 `/review-pr`。建议把 silent failure、type design、test quality、comment rot、simplify 作为 guard-review 的按需子检查，避免 review prompt 越写越大。

### 2. 类型设计需要围绕 invariant，而不是只看类型是否存在

`plugins/pr-review-toolkit/agents/type-design-analyzer.md:21-55` 的评分维度是: identify invariants、encapsulation、invariant expression、invariant usefulness、invariant enforcement。`type-design-analyzer.md:89-118` 同时要求权衡维护成本、breaking changes、性能和现有 convention。

本仓库可以把这个模式下沉到 `think-quality` 或 `dev-refactor`，尤其用于 schema、domain model、API envelope、状态机和权限模型。注意不要机械追求“illegal states unrepresentable”，必须保留现有代码风格和 YAGNI 约束。

### 3. 大型任务先做 readiness report，不能边做边发现前置缺口

`plugins/code-modernization/commands/modernize-preflight.md:6-15` 明确 preflight 的目的: 现代化任务会因为工具、build toolchain、source completeness 缺失而 late fail，所以要一次跑完整 readiness report。`modernize-preflight.md:81-98` 要求输出每项 check 的状态、修复建议，以及 Ready / Ready-with-gaps / Not ready verdict。

本仓库的 `dev-large-delivery`、`dev-operational-task` 已有阶段化和 dry-run 思路，但可以更明确增加 artifact inventory、staleness check、toolchain smoke test、missing prerequisite stop gate。

### 4. Business rules 应从 legacy code 中变成可测试 contract cases

`plugins/code-modernization/agents/business-rules-extractor.md:12-25` 定义业务规则范围: calculations、validations、eligibility / authorization、state transitions、policies，并排除 logging、UI、connection pooling 等技术细节。`business-rules-extractor.md:27-42` 要求记录 `file:line-line`、plain English、Given/When/Then、参数、confidence、SME question。`business-rules-extractor.md:43-50` 还特别要求 masking credentials。

本仓库可以把 “Rule Card” 作为 `think-map`、`think-architecture`、`dev-tdd` 的可选输出。它能把需求理解、代码证据和测试用例连起来，适合权限、账务、数据同步、迁移和修复类任务。

### 5. 用户纠正可以进入 harness，但不能自动变成硬规则

`plugins/hookify/README.md:3-14` 的核心是从显式指令或对话模式生成 hook rule。`hookify/README.md:71-120` 用 markdown frontmatter 表达 `name`、`enabled`、`event`、`pattern`、`action`、`conditions`。`hookify/README.md:122-128` 的事件包括 bash、file、stop、prompt、all。

本仓库有复盘和学习类 skill，因此这个模式很适合做“纠错到规则”的候选生成器。但必须加人工审批、dry-run、rule scope 和 rollback 信息，不能把一次用户不满自动升级成全局 block hook。

### 6. 成本 / session 报告是 agent harness 的可观测性资产

`plugins/session-report/skills/session-report/SKILL.md` 将 session transcript 分析成 token、cache、subagents、skills 和 expensive prompts 的 HTML 报告。

本仓库已有 `readable-metrics` 和 `readable-html-artifact`，因此更适合把它作为只读报告能力吸收，而不是引入新的 UI runtime。目标是定位高成本 skill、过度并行的 subagent、cache break 和 prompt 膨胀。

## 风险与冲突

| 风险 | 说明 | 处理建议 |
|---|---|---|
| 单 runtime 路径冲突 | 上游使用 `.claude-plugin`、`.claude/`、`CLAUDE.md`，本仓库同时维护跨 agent 配置与当前项目配置约定 | 只吸收模式，落地时必须显式标注适用 runtime 和配置路径 |
| 平行 workflow 冲突 | `feature-dev`、`review-pr` 与本仓库 `think-*`、`dev-*`、`guard-*` 重叠 | 不新增竞争入口，只增强现有 skill |
| MCP / 外部服务副作用 | `external_plugins/` 多数含 `.mcp.json`，可能触及 secrets、远端服务、用户 HOME | 默认 observe，启用前走 guard-gitops / guard-secure |
| 后台模型审查风险 | security-guidance 类 hook 可能在 stop / commit / push 时发送 diff 或文件内容 | 不默认启用，只参考分层审查和项目安全规则 |
| Review 误报放大 | silent-failure-hunter 风格强，可能把合理 fallback 误判为高危 | 保留本仓库 evidence gate 和 severity discipline |
| FE 创作过度 | frontend-design 鼓励 bold aesthetic，可能覆盖已有 design system | DESIGN.md / token / a11y / overflow contract 优先 |

## Proposal: 如何提升本仓库

### P0: 建立跨 agent 资产 registry 与静态校验

目标: 把本仓库的 skills、commands、agents、hooks、refs 从“目录即事实”提升为“目录 + registry + 兼容性标注 + 校验”。

建议动作:

- 新增只读生成脚本，扫描本仓库的 agent 配置、commands、skills、hooks、refs detail，生成资产清单。
- 校验 description 是否过宽、路径是否存在、runtime/path 标注是否冲突、是否触及 network / secret / MCP / hook 风险却没有风险标签。
- 在 skill-maintenance 或 guard-check 前输出 drift report。

验收证据:

- registry 能列出所有本地 assets。
- 校验能发现不存在路径、重复名称、错误配置目录、缺风险标签的 MCP/hook 资产。

### P0: 让 guard-review 变成专科化 review router

目标: 不复制 `/review-pr`，而是在现有 `guard-review` 中按 diff 类型路由专项检查。

建议动作:

- 增加 review aspect taxonomy: `comments`、`tests`、`errors`、`types`、`code`、`simplify`。
- 把 `errors` 映射到 silent failure / observability 检查。
- 把 `types` 映射到 invariant scorecard。
- 把 `simplify` 映射到 `dev-simplify`，只在 blocker 修完后运行。

验收证据:

- 对含 catch/fallback 的 diff，review 输出是否覆盖 silent failure。
- 对新增 domain type 的 diff，review 输出是否包含 invariant evidence。
- 对纯文档 diff，review 不应启动无关 code/type 检查。

### P1: 给大型任务加 preflight contract

目标: 在长任务和大交付开始前，先证明环境、输入、工具链、数据源、回滚条件足够，而不是中途补救。

建议动作:

- 在 `dev-large-delivery` / `dev-operational-task` 增加 readiness table。
- 固定检查: stack detect、tool availability、smoke test、source completeness、telemetry / history availability、rollback / dry-run path。
- 输出 Ready / Ready-with-gaps / Not ready，并给 single most important fix。

验收证据:

- 缺工具时任务不会继续进入 apply/transform 阶段。
- preflight 报告能指出缺失工具、影响范围和修复方式。

### P1: 引入 Business Rule Card

目标: 让需求理解、代码证据和测试用例之间形成可追踪 contract。

建议动作:

- 在 `think-map` / `think-architecture` 增加可选 Rule Card 输出。
- 在 `dev-tdd` 中允许从 Rule Card 直接派生 Given/When/Then contract tests。
- 规则参数遇到 secret 时必须 mask，只记录 `file:line` 和参数类别。

验收证据:

- 复杂业务逻辑任务中，每条规则有 `file:line`、Given/When/Then、confidence、SME question。
- 测试能追溯到对应 Rule Card。

### P1: 做审批型 harness rule generator

目标: 把用户纠正、事故复盘、review finding 转成候选 guard rule，但不自动写入硬规则。

建议动作:

- 新增候选规则格式: `trigger`、`scope`、`action`、`message`、`evidence`、`rollback`。
- 默认只生成 proposal；block 规则必须人工批准。
- 规则路径必须使用本仓库对应 runtime / hook 约定；不能默认把 Claude Code 的 `.claude/` 结构当成全局落点。

验收证据:

- 对一次用户纠正能生成候选 warn rule。
- 无用户批准时不会写入或启用 block rule。

### P2: 增加 session 成本与 cache 报告

目标: 把 agent 使用成本、上下文膨胀和 subagent 并行滥用变成可观察指标。

建议动作:

- 先做只读报告，接入 `readable-metrics`。
- 需要 HTML companion 时走 `readable-html-artifact`，不把完整 HTML 放进主上下文。
- 指标至少包括: top expensive prompts、skill/token 分布、subagent 次数、cache break、long transcript sections。

验收证据:

- 能对单个 session 输出成本热点表。
- 能定位一个可行动优化项，而不是只展示总 token。

## 当前裁决

- 已加入 refs: 是，作为 `refs/anthropics/claude-plugins-official` submodule。
- 是否进入 runtime: 否。
- 当前吸收等级: L0 / L1。
- 下一步建议: 优先做 P0 registry 校验与 guard-review 专科化；这两项复用频率最高、风险最低、与现有架构冲突最小。

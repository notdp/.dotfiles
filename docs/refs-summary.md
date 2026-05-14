# refs 研究汇总

## 吸收方法论

- refs 吸收裁决的 SSOT：[`docs/software-engineering-research/refs-absorption-methodology.md`](./software-engineering-research/refs-absorption-methodology.md)
- 后续拉取 refs 最新改动、判断是否吸收到本仓库时，必须按该方法论输出 commit range、候选吸收项、吸收层级、风险和证据。
- 最近一次全量 refs 更新吸收分析：[`docs/refs-update-absorption-2026-05-14.md`](./refs-update-absorption-2026-05-14.md)

## 分类说明

- **浏览器自动化与前端调试**：围绕浏览器控制、前端诊断、性能分析、页面抓取与 UI 调试。 代表项目：`ChromeDevTools/chrome-devtools-mcp`、`vercel-labs/agent-browser`
- **技能集合与市场**：以 skills 汇总、分发、导航或精选集合为主，常附带少量示例或插件。 代表项目：`Dimillian/Skills`、`affaan-m/everything-claude-code`、`anthropics/skills`、`github/awesome-copilot`、`glittercowboy/taches-cc-resources`、`libukai/awesome-agent-Skills`、`travisvn/awesome-claude-Skills`、`tw93/Waza`
- **多智能体协作与工作流编排**：围绕 agent 角色分工、并行执行、状态同步、团队工作流编排。 代表项目：`Yeachan-Heo/oh-my-claudecode`、`notdp/hive`、`nyldn/claude-octopus`
- **上下文 / 记忆管理**：围绕上下文压缩、记忆持久化、检索、session 连续性与 context engineering。 代表项目：`mksglu/context-mode`、`muratcankoylan/Agent-Skills-for-Context-Engineering`
- **前端 UI / 设计系统**：围绕视觉设计、组件模式、设计系统、界面审查与 UI 生成。 代表项目：`google-labs-code/stitch-skills`、`nextlevelbuilder/ui-ux-pro-max-skill`、`nexu-io/open-design`、`pbakaus/impeccable`、`vercel-labs/agent-skills`
- **科研 / 数据分析 / 领域技能**：围绕科学研究、数据分析、科研数据库、领域 Python 包、医学/临床研究与科学写作。 代表项目：`K-Dense-AI/scientific-agent-skills`
- **研发流程 / 项目管理**：围绕 spec/planning/execution/verification/ship 等工程流程与项目管理。 代表项目：`automazeio/ccpm`、`gsd-build/get-shit-done`、`obra/superpowers`
- **最佳实践 / 知识库**：围绕 Claude Code 概念地图、目录约定、功能导航与实践经验整理。 代表项目：`shanraisshan/claude-code-best-practice`
- **代码质量 / 审查 / 调试**：围绕静态分析、review、质量门禁、调试与诊断。 代表项目：`millionco/react-doctor`、`addyosmani/web-quality-skills`、`tirth8205/code-review-graph`
- **MCP / 工具链 / 安装分发**：围绕 MCP、CLI、安装器、技能包管理、多 Agent 兼容与基础设施。 代表项目：`vercel-labs/skills`
- **行为协议 / 提示工程**：围绕提示协议、行为约束、激励/约束机制、触发词和 hook 协同。 代表项目：`tanweai/pua`
- **Agent 配置管理 / 工具链**：围绕跨 Agent 统一配置、安装分发、二进制修改与工具增强。 代表项目：`notdp/.dotfiles`

## 项目总表

| 项目 | 分类 | 一句话总结 |
|---|---|---|
| [`affaan-m/everything-claude-code`](./refs-details/affaan-m/everything-claude-code.md) | 技能集合与市场 | 超大号跨 harness agent-performance 系统，整合 agents、skills、commands、hooks、rules 和安装器。 |
| [`addyosmani/web-quality-skills`](./refs-details/addyosmani/web-quality-skills.md) | 代码质量 / 审查 / 调试 | 面向 Web 质量审查与优化的技能仓库，围绕 Lighthouse、Core Web Vitals、可访问性、SEO 和现代最佳实践组织。 |
| [`anthropics/skills`](./refs-details/anthropics/skills.md) | 技能集合与市场 | Anthropic 官方示例 skills 仓库，附带规范、模板，以及文档处理与开发类技能示例。 |
| [`automazeio/ccpm`](./refs-details/automazeio/ccpm.md) | 研发流程 / 项目管理 | 单技能形态的项目管理与交付编排系统，把 PRD、Epic、Issues、并行 agents 和状态跟踪串成 spec-driven workflow。 |
| [`ChromeDevTools/chrome-devtools-mcp`](./refs-details/ChromeDevTools/chrome-devtools-mcp.md) | 浏览器自动化与前端调试 | 通过 MCP 控制真实 Chrome，提供自动化、调试、性能分析和配套 skills。 |
| [`Dimillian/Skills`](./refs-details/Dimillian/Skills.md) | 技能集合与市场 | 偏精选型的 skills 集合，覆盖 Apple 平台开发、GitHub 操作、review swarm、React 性能和重构。 |
| [`github/awesome-copilot`](./refs-details/github/awesome-copilot.md) | 技能集合与市场 | GitHub 官方运营的 Copilot 资源集合，统一管理 agents / instructions / skills / hooks / agentic workflows / plugins，并配套 marketplace、网站与 CLI 安装。 |
| [`glittercowboy/taches-cc-resources`](./refs-details/glittercowboy/taches-cc-resources.md) | 技能集合与市场 | 面向 Claude Code 的资源仓库，主打技能开发、规划分层、MCP 服务生成、调试方法论与 Ralph 自治循环。 |
| [`google-labs-code/stitch-skills`](./refs-details/google-labs-code/stitch-skills.md) | 前端 UI / 设计系统 | 围绕 Stitch MCP 的 Agent Skills 库，用于 UI 设计生成、设计系统提炼、React 转换和演示视频生成。 |
| [`gsd-build/get-shit-done`](./refs-details/gsd-build/get-shit-done.md) | 研发流程 / 项目管理 | 跨多种 AI 运行时的 spec-driven development / context engineering 系统，覆盖立项、规划、执行、验证、交付全流程。 |
| [`HughYau/qiushi-skill`](./refs-details/HughYau/qiushi-skill.md) | 行为协议 / 提示工程 | 从毛泽东思想中提炼"实事求是"总原则和九大方法论工具，系统性武装 AI Agent 的分析与决策能力，附带工作流编排和多平台插件。 |
| [`K-Dense-AI/scientific-agent-skills`](./refs-details/K-Dense-AI/scientific-agent-skills.md) | 科研 / 数据分析 / 领域技能 | 大型科学研究 skill 集合，把科研数据库、科学 Python 包、实验平台、医学/临床工作流、科学写作和可视化整理成多 Agent 可读的能力包。 |
| [`libukai/awesome-agent-Skills`](./refs-details/libukai/awesome-agent-Skills.md) | 技能集合与市场 | 以 curated list 为主的技能资源集市，汇总教程、市场、官方项目，并附带少量实作 skill 与插件。 |
| [`millionco/react-doctor`](./refs-details/millionco/react-doctor.md) | 代码质量 / 审查 / 调试 | React 代码体检工具仓库，核心是 CLI 扫描器，同时附带 GitHub Action、agent skill 和网站。 |
| [`mksglu/context-mode`](./refs-details/mksglu/context-mode.md) | 上下文 / 记忆管理 | 面向多种 AI 编码运行时的 MCP/plugin，用来减少上下文窗口占用并保留会话连续性。 |
| [`muratcankoylan/Agent-Skills-for-Context-Engineering`](./refs-details/muratcankoylan/Agent-Skills-for-Context-Engineering.md) | 上下文 / 记忆管理 | 围绕 context engineering 的 Agent Skills 集合，重点讲生产级 agent 的上下文设计、记忆、工具与评测。 |
| [`nextlevelbuilder/ui-ux-pro-max-skill`](./refs-details/nextlevelbuilder/ui-ux-pro-max-skill.md) | 前端 UI / 设计系统 | 面向 UI/UX 生成的设计情报包，结合大规模 CSV 规则库、Claude skills 与安装 CLI。 |
| [`nexu-io/open-design`](./refs-details/nexu-io/open-design.md) | 前端 UI / 设计系统 | 本地优先的 AI 设计工作台，用 daemon 调用用户已有 Agent CLI，并把 Skills、DESIGN.md、项目文件和 sandbox 预览串成 artifact 工作流。 |
| [`notdp/.dotfiles`](./refs-details/notdp/.dotfiles.md) | Agent 配置管理 / 工具链 | 统一管理 33+ AI 编码 Agent 的 skills、commands 和全局指令的 dotfiles 框架。 |
| [`notdp/hive`](./refs-details/notdp/hive.md) | 多智能体协作与工作流编排 | 基于 tmux 的多 agent 协作运行时/CLI，围绕 Factory Droid 工作流构建。 |
| [`nyldn/claude-octopus`](./refs-details/nyldn/claude-octopus.md) | 多智能体协作与工作流编排 | 超大体量的多模型编排插件，把 Claude Code/Droid 扩展成带工作流、角色、hooks、MCP 和兼容层的协作系统。 |
| [`obra/superpowers`](./refs-details/obra/superpowers.md) | 研发流程 / 项目管理 | 强调纪律化开发流程的技能包，让 coding agent 按“先规格、后计划、再实现与复核”的方式工作。 |
| [`Owl-Listener/designer-skills`](./refs-details/Owl-Listener/designer-skills.md) | 前端 UI / 设计系统 | 面向设计工作的 Claude Code / Gemini CLI skill collection，提供 8 个设计插件、87 个 skills 和 27 个 commands。 |
| [`pbakaus/impeccable`](./refs-details/pbakaus/impeccable.md) | 前端 UI / 设计系统 | 面向前端设计质量的跨平台技能/命令打包仓库，附带官网、下载 API 和构建系统。 |
| [`shanraisshan/claude-code-best-practice`](./refs-details/shanraisshan/claude-code-best-practice.md) | 最佳实践 / 知识库 | Claude Code 生态知识库，系统整理 commands、skills、subagents、memory、hooks 与工作流最佳实践，并给出对应实现入口。 |
| [`tanweai/pua`](./refs-details/tanweai/pua.md) | 行为协议 / 提示工程 | 面向多种 AI 编码代理的“高压/高主动性”技能包，核心是 PUA/PIP 风格提示、命令、hooks 和多平台分发素材。 |
| [`tirth8205/code-review-graph`](./refs-details/tirth8205/code-review-graph.md) | 代码质量 / 审查 / 调试 | 面向 AI 编码工具的本地代码知识图谱，用 Tree-sitter、SQLite 与 MCP 把审查上下文缩到真正相关的 blast radius。 |
| [`travisvn/awesome-claude-Skills`](./refs-details/travisvn/awesome-claude-Skills.md) | 技能集合与市场 | 纯 curated list 仓库，汇总官方和社区 Claude Skills、教程、资源、安全建议与 FAQ。 |
| [`tw93/Waza`](./refs-details/tw93/Waza.md) | 技能集合与市场 | 轻量但完整的工程习惯 skill pack，把 think/design/check/hunt/write/learn/read/health 八类动作打包成可安装 skills，并附带 statusline 与 English Coaching。 |
| [`vercel-labs/agent-browser`](./refs-details/vercel-labs/agent-browser.md) | 浏览器自动化与前端调试 | 原生 Rust 驱动的浏览器自动化 CLI，并附带多套面向 AI 代理的技能文档。 |
| [`vercel-labs/agent-skills`](./refs-details/vercel-labs/agent-skills.md) | 前端 UI / 设计系统 | Vercel 出品的技能集合，覆盖 React/React Native、组合模式、UI 评审与 Vercel 部署。 |
| [`vercel-labs/skills`](./refs-details/vercel-labs/skills.md) | MCP / 工具链 / 安装分发 | 开放 Agent Skills 生态的 CLI/包管理器，用于发现、安装、列出、删除、更新技能，并维护多代理兼容性。 |
| [`Yeachan-Heo/oh-my-claudecode`](./refs-details/Yeachan-Heo/oh-my-claudecode.md) | 多智能体协作与工作流编排 | 完整的 Claude Code 多智能体编排系统，含 CLI、skills、agents、hooks、tmux worker runtime 和验证模块。 |


## 最近 14 天更新速览（2026-03-31 ~ 2026-04-14）

- [事实] 范围：顶层 `.gitmodules` 中的 29 个 submodule。
- [事实] 数据来源：各仓库默认分支最近 14 天的 `git log`；需要联网的仓库已先执行 `git fetch --all --tags --prune`。
- [事实] 下表里的提交数按默认分支统计。
- [推断] “新增/变化”列是根据 commit 标题与改动文件归纳，不等同于完整 release notes。

| 项目 | 14 天提交数 | 新增/变化 |
|---|---:|---|
| [`affaan-m/everything-claude-code`](./refs-details/affaan-m/everything-claude-code.md) | 324 | [推断] 新增 dashboard GUI、gateguard pre-action gate 与 ecc2 legacy 配置导入迁移，随后集中修补安装、发布、权限与并发问题。 |
| [`Yeachan-Heo/oh-my-claudecode`](./refs-details/Yeachan-Heo/oh-my-claudecode.md) | 296 | [推断] HUD 新增花费/Provider/worktree/hostname/cwd 等信息展示，release skill 改写为 repo-aware assistant，引入 LLM Wiki 知识层，并持续强化 permission/runtime/hook/tmux/Ralph 审批链。 |
| [`gsd-build/get-shit-done`](./refs-details/gsd-build/get-shit-done.md) | 194 | [推断] 新增 `/gsd-graphify` 知识图谱、typed query 基础、worktree 健康检查、milestone seed 扫描、线程/快捷命令管理与更强的 TDD/审计/安全门禁。 |
| [`tw93/Waza`](./refs-details/tw93/Waza.md) | 186 | [推断] 两周内高频迭代八个核心 skill 与安装资产：新增 statusline、English Coaching、`read`/`learn` 外部检索支持，持续强化 `design`/`health`/`check`/`write`，并反复修补 Codex、marketplace、verify-skills 与 macOS 兼容性问题。 |
| [`pbakaus/impeccable`](./refs-details/pbakaus/impeccable.md) | 141 | [推断] 新增 `skills check`、skip-if-up-to-date 更新逻辑与 cleanup 脚本，整理 skill 版图（21→18），上线 Chrome 扩展并持续扩展 UI anti-pattern 检测与站点渲染能力。 |
| [`mksglu/context-mode`](./refs-details/mksglu/context-mode.md) | 114 | [推断] 连续发布 `1.0.79`~`1.0.88`，新增 `ctx-insight` skill 与个人 analytics dashboard/工具链，并补强 search、upgrade 与 CI 稳定性。 |
| [`notdp/hive`](./refs-details/notdp/hive.md) | 69 | [推断] 新增 send gate、`hive register`、delivery ACK、frontmatter 化的 HIVE envelope，以及跨 `droid`/`claude`/`codex` 的 hooks 安装与更顺手的 spawn/fork/kill 工作流。 |
| [`vercel-labs/agent-browser`](./refs-details/vercel-labs/agent-browser.md) | 26 | [推断] 新增 `agent-browser skills` 命令；`v0.25.x` 带来 dashboard AI chat、stream 模块重构、`snapshot --urls` 与 batch 参数模式，并继续修复 viewport/HTTPS/标签页行为。 |
| [`HughYau/qiushi-skill`](./refs-details/HughYau/qiushi-skill.md) | 21 | [推断] 新增案例分享/展示示例，补强方法论边界与安装路径说明，增加站点入口页（`index.html`/`.nojekyll`）与 README 展示增强，并加入 ASCII JSON 字符串处理能力。 |
| [`notdp/.dotfiles`](./refs-details/notdp/.dotfiles.md) | 17 | [推断] `droid-bin-mod` 新增 unicode partial-json 修复与 ym9 tag strip truncation 修复，同时继续刷新镜像 skills，并补入 `lark-*`、`hfork`/`vfork`/`notify` 等能力。 |
| [`nyldn/claude-octopus`](./refs-details/nyldn/claude-octopus.md) | 15 | [推断] 同步 Claude Code `v2.1.89-101`，引入 15 个 feature flags、PermissionDenied 审计 hook、session auto-titling 与 macOS CI，并继续收敛 review/doctor/可移植性问题。 |
| [`github/awesome-copilot`](./refs-details/github/awesome-copilot.md) | 73 | [推断] `skills/` + `agents/` 持续扩充（Qdrant / Foundry / LinkedIn / browser investigation / code-tour / whatidid 等），批量修正 agents 的 deprecated tool names，并把 a11y / security / performance instructions 刷到 2025-2026 标准，同时完善 skills 校验与网站一键安装命令。 |
| [`ChromeDevTools/chrome-devtools-mcp`](./refs-details/ChromeDevTools/chrome-devtools-mcp.md) | 13 | [事实] 近 14 天提交标题以依赖升级、README 中新增 Mistral Vibe 配置说明和文档修复为主，未见明显功能型提交。 |
| [`millionco/react-doctor`](./refs-details/millionco/react-doctor.md) | 6 | [推断] 发布 `0.0.31`/`0.0.32`/`0.0.33`，重点修复 setter 检测与 catalog resolution、file ignoring、CLI、React Native、Next.js、offline、monorepo 等问题。 |
| [`vercel-labs/skills`](./refs-details/vercel-labs/skills.md) | 5 | [推断] 发布 `v1.5.0`/`v1.4.9`，改进项目级/全局级更新文案与单 skill update 路径，并增加对 `openclaw` 重复/恶意技能的风险警告。 |
| [`anthropics/skills`](./refs-details/anthropics/skills.md) | 3 | [推断] 主要更新在 `claude-api` skill：补上 Managed Agents 指南、front-matter，并修复 YAML 渲染。 |
| [`obra/superpowers`](./refs-details/obra/superpowers.md) | 3 | [事实] 近 14 天提交主要是仓库入口维护（Discord 链接/公告），未见明确功能新增。 |
| [`shanraisshan/claude-code-best-practice`](./refs-details/shanraisshan/claude-code-best-practice.md) | 0 | [事实] 默认分支近 14 天无新提交；当前一次可见提交落在 `2026-04-15`，不在本统计窗口内。 |
| [`glittercowboy/taches-cc-resources`](./refs-details/glittercowboy/taches-cc-resources.md) | 1 | [事实] 新增 `the-pirate-bay` skill。 |
| [`tirth8205/code-review-graph`](./refs-details/tirth8205/code-review-graph.md) | 1 | [事实] 近 14 天仅见 1 个提交，主要是为 sort key 同时抑制 `mypy` 的 `arg-type` 与 `return-value` 诊断。 |
| [`nextlevelbuilder/ui-ux-pro-max-skill`](./refs-details/nextlevelbuilder/ui-ux-pro-max-skill.md) | 1 | [推断] 主要变化是设计系统视觉改进合并。 |
| [`tanweai/pua`](./refs-details/tanweai/pua.md) | 1 | [事实] 近 14 天提交主要是微信群二维码与缓存版本更新，未见明确功能新增。 |
| [`vercel-labs/agent-skills`](./refs-details/vercel-labs/agent-skills.md) | 1 | [推断] 主要变化是继续打磨 `react-view-transition` skill。 |
| [`addyosmani/web-quality-skills`](./refs-details/addyosmani/web-quality-skills.md) | 0 | [事实] 默认分支近 14 天无新提交。 |
| [`automazeio/ccpm`](./refs-details/automazeio/ccpm.md) | 0 | [事实] 默认分支近 14 天无新提交。 |
| [`Dimillian/Skills`](./refs-details/Dimillian/Skills.md) | 0 | [事实] 默认分支近 14 天无新提交。 |
| [`google-labs-code/stitch-skills`](./refs-details/google-labs-code/stitch-skills.md) | 0 | [事实] 默认分支近 14 天无新提交。 |
| [`libukai/awesome-agent-Skills`](./refs-details/libukai/awesome-agent-Skills.md) | 0 | [事实] 默认分支近 14 天无新提交。 |
| [`muratcankoylan/Agent-Skills-for-Context-Engineering`](./refs-details/muratcankoylan/Agent-Skills-for-Context-Engineering.md) | 0 | [事实] 默认分支近 14 天无新提交。 |
| [`travisvn/awesome-claude-Skills`](./refs-details/travisvn/awesome-claude-Skills.md) | 0 | [事实] 默认分支近 14 天无新提交。 |

### 近 14 天无更新的仓库

- `automazeio/ccpm`
- `Dimillian/Skills`
- `google-labs-code/stitch-skills`
- `libukai/awesome-agent-Skills`
- `muratcankoylan/Agent-Skills-for-Context-Engineering`
- `shanraisshan/claude-code-best-practice`
- `travisvn/awesome-claude-Skills`
- `addyosmani/web-quality-skills`

## 补充观察

- **吸收裁决（2026-05-14）**：
  - `Owl-Listener/designer-skills`：吸收“名词型 skill + 动词型 command + 多平台打包”的组织方式；不吸收 8 个设计插件和 87 个 skills 本体。其自然语言澄清和默认保存文档行为需要按本仓库 `AskUser` 与文档创建纪律改写。
  - `K-Dense-AI/scientific-agent-skills`：吸收“短入口 `SKILL.md` + `references/` + `scripts/`”的领域分册结构和安全扫描门禁；不整包安装到默认 skills。触及网络、secrets、医疗/临床、实验室自动化或数据写入的能力必须先经过安全/运行时副作用护栏。
- `github/awesome-copilot` 是 Copilot 生态“官方中心化 registry + 规范试验场”：横跨 curated catalog、CLI 分发（`copilot plugin install ...@awesome-copilot`）和六类资源规范（agents / instructions / skills / hooks / agentic workflows / plugins）。从**轻量 skills** 角度看，307 个 skill 里 70% 只有单个 SKILL.md、35% 在 100 行以内，最短的 6 行，验证了“单动作 skill 20-40 行足够”这条路径；值得直接吸收的模式是：触发语义写进 `description`（`INVOKE ... when`）、反向提问型 skill（`what-context-needed` / `first-ask`）、micro-prompt 作为独立挂载项（`remember-interactive-programming`）、以及 `{{var}}` 输入 + 固定输出表格收窄 agent 自由度（`context-map`）。详见 `docs/refs-details/github/awesome-copilot.md` 的 Skills 子集专题。
- `travisvn/awesome-claude-Skills`、`libukai/awesome-agent-Skills` 更偏导航/市场/索引；适合找来源，不适合直接当能力实现。
- `ChromeDevTools/chrome-devtools-mcp`、`vercel-labs/agent-browser` 是浏览器自动化/前端调试类的两条重要主线，前者偏 DevTools MCP，后者偏 agent-browser CLI/runtime。
- `Yeachan-Heo/oh-my-claudecode`、`notdp/hive`、`nyldn/claude-octopus` 属于多智能体/多模型协作平台型项目。
- `mksglu/context-mode` 与 `muratcankoylan/Agent-Skills-for-Context-Engineering` 更适合归入上下文工程/记忆管理范畴。
- `automazeio/ccpm`、`gsd-build/get-shit-done`、`obra/superpowers` 更偏工程流程与项目执行方法学。
- `tw93/Waza` 是更轻的工程习惯技能包：不追求重型 runtime 或全流程治理，而是把 think/check/hunt/design/read/write/learn/health 八类高频动作压成可安装 skill。
- `shanraisshan/claude-code-best-practice` 更像 Claude Code 生态知识库/导航站，适合提炼 skill 触发器、command 路由与全局记忆压缩原则，不适合整套照搬为团队规范。
- `google-labs-code/stitch-skills`、`nextlevelbuilder/ui-ux-pro-max-skill`、`pbakaus/impeccable`、`vercel-labs/agent-skills` 更偏前端 UI / 设计系统。
- `Owl-Listener/designer-skills` 属于前端 UI / 设计系统中的设计工作流样本，值得借鉴“名词型 skill + 动词型 command + 多平台打包”的结构，但其自然语言澄清和默认写文档行为需要按本仓库纪律适配。
- `K-Dense-AI/scientific-agent-skills` 属于科研 / 数据分析 / 领域技能的大型样本，适合参考 taxonomy、`SKILL.md` + `scripts/` + `references/` 的重型 skill 结构和安全扫描门禁；不适合整包安装到默认 skills。
- `millionco/react-doctor`、`addyosmani/web-quality-skills`、`tirth8205/code-review-graph` 都属于代码质量/审查范畴：前者偏 React 代码体检，第二个偏 Lighthouse / CWV / a11y / SEO 的 Web 质量审查，后者偏本地结构图谱、blast radius 与 token-efficient review context。
- `tanweai/pua` 和 `HughYau/qiushi-skill` 都属于行为协议/提示工程类，前者偏高压激励/行为约束，后者偏哲学方法论/分析框架，二者互补。

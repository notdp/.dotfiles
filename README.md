# dotfiles

My Droid skills/scripts.

## 项目定位

这是我的 AI coding agent dotfiles 仓库，用来管理 Droid / Claude / Codex 等 agent 的全局规则、skills、slash commands、hooks、statusline、本地辅助脚本和第三方 refs 调研。

本质上这是一个 **agent harness**：不是被动的配置集合，而是通过三类机制主动约束和驱动 agent 的工作方式。

| 机制 | 载体 | 作用 |
|------|------|------|
| 规则层 | `agents/`（`AGENTS.md` 硬约束 + `dev-guideLines.md` 开发准则 + `harness-ops.md` 维护规范） | 定义所有任务都成立的行为边界与事实纪律 |
| 护栏层 | `scripts/hooks/`（boundary gate / command guard / context capsule / stop check） | 在编辑前、命令执行前、交付前做强制门禁 |
| 能力层 | `coding-skills/` + `commands/` + `coding-agents/` | 按需触发的工作流能力包与隔离执行体，不污染 idle context |

项目目标是把软件工程工作流拆成可按需触发、可验证、可复用的能力包：理解问题、调研、规划、TDD、调试、重构、验证、审查、安全、交付、UI 设计和经验沉淀。

## 目录结构

| 路径 | 作用 |
|------|------|
| `agents/AGENTS.md` | 全局硬约束、事实纪律、验证门禁、工具纪律 |
| `coding-skills/` | 按需触发的领域能力和工作流能力（系统级，软连接到 cc/codex/droid/opencode/kilo），权威清单见 `coding-skills/catalog.json` |
| `writing-skills/` | **通用中文写作能力层（account-agnostic）**：12 个 skill（write-scope/source/outline/draft/revise/hook/voice + guard-write-check/facts + write-dissolve + assist-write-corpus + article-growth-diagnosis）+ `_shared/`（writing-constraints 下限 / narrative-methodology 方法论 / style-contract 接缝）。账号特定声音/定位由项目 `account-style.md` 注入；软连接到创作项目，不暴露给编程 agent；清单见 `writing-skills/catalog.json` |
| `writing-hooks/` | 写作专用 lint hook + `verify_writing.py`，与编程 `scripts/hooks/` 隔离；通用工具，默认休眠（未在项目注册） |
| `coding-agents/` | Claude Code subagent 定义（软链到 `~/.claude/agents`）：权限收窄 + 模型分档 + context 隔离的执行体；subagent vs skill 分工判据见 `agents/harness-ops.md`，门禁为 `scripts/verify_agents.py` |
| `commands/` | 高频 slash commands |
| `scripts/` | 编程侧 hooks、验证、Droid mod、长任务、扫描器等本地工具 |
| `.factory/settings.json` | Droid hook 配置 |
| `statusline.sh` | Droid / Claude statusline |
| `docs/` | 调研沉淀、refs 详情、设计取舍与可追溯背景（含 `writing-refs-summary.md` / `writing-refs-details/` / `specs/writing-skills/`） |
| `refs/` | 第三方编程 agent skills / workflows submodules |
| `writing-refs/` | 第三方中文写作 skills submodules（9 个），分析见 `docs/writing-refs-details/` |

## 本地工具与护栏

- `statusline.sh`：展示 cwd、branch、PR、diff、session id、Factory usage 等状态。
- `bin/droid-observe`：查看 long-loop workspace。
- `bin/longrun`：启动 longrun dashboard。
- `bin/droid-vim-command`：支持 `/vim`、`/cvim` 外部编辑器工作流。
- `scripts/install_hooks.py`：为 Droid / Claude / Codex 生成 hook 配置。
- `scripts/run-verify.sh`：自动探测并运行测试、lint、typecheck、build 和本仓库 skill 校验。

当前 hooks 主要承担四类护栏：prompt 阶段注入 context capsule、编辑前做 boundary gate、命令执行前做 command guard、结束前检查验证证据和 boundary manifest。

## 验证

常用验证入口：

```bash
bash scripts/run-verify.sh
python3 scripts/verify_skills.py
python3 -m unittest discover -s scripts/tests -p "test_*.py"
```

## Commands

| Command | Description |
|---------|-------------|
| `/clip` | 复制内容到系统剪贴板 |
| `/vim` | 打开外部编辑器，从空白草稿开始输入下一条消息 |
| `/cvim` | 打开外部编辑器，以当前会话内容为基础编辑并返回 diff |
| `/droid-mod` | 修改/检查/恢复 droid 二进制 |
| `/fe-audit` | 前端设计质量审计（设计原则 + 反模式 + 可访问性 + 代码健康） |
| `/design-md` | 建立、使用、诊断和验证项目 DESIGN.md |

## Skills

按域前缀组织：`think-*` 思考 / `dev-*` 开发 / `guard-*` 护栏 / `readable-*` 可读性 / `assist-*` 沉淀，其余为专项能力。完整权威清单以 `coding-skills/catalog.json` 为准，下面只保留常用入口。

| Skill | Description |
|-------|-------------|
| `think-map` | 分析代码库结构、技术栈、约定和依赖 |
| `think-research` | 实现前技术调研（选型、最佳实践、风险） |
| `think-plan` | 需求分析→设计→执行计划（多粒度 spec） |
| `think-architecture` | 架构思考与成文（先对话后成文档） |
| `think-refine` | 需求模糊、边界不清时交互式澄清 |
| `think-survey` | 开放主题综述、资料汇总 |
| `think-compare` | 多个明确候选路径之间做取舍 |
| `think-context-map` | 单次任务影响面不明时画文件地图 |
| `think-ask-context` | 回答复杂问题前识别缺失上下文 |
| `think-quality` | 结构质量评估；判断代码/架构/diff 是否适合继续修改 |
| `think-unstuck` | 结构化排查；连续失败 2 次、卡壳时触发 |
| `dev-debug` | 系统化调试（科学方法，子 agent 隔离分析） |
| `dev-tdd` | TDD 工作流；新功能/bug 修复时使用 |
| `dev-refactor` | 代码重构（分支比较、未提交变更、自定义范围） |
| `dev-simplify` | 实现后从复用/质量/效率角度轻量清理 |
| `dev-long-loop` | 长任务多轮执行、状态沉淀和阶段验收 |
| `dev-long-task-scaffold` | 长任务脚手架；生成人工逐阶段推进的 workspace、phase plan 和控制提示词 |
| `dev-operational-task` | 长耗时、数据任务、复杂 CLI、dry-run/apply 合同 |
| `guard-check` | 交付前总入口；编排 review/secure/verify/ship/gitops |
| `guard-review` | 代码审查（simple/deep 两种模式） |
| `guard-secure` | 安全审查（STRIDE 威胁建模） |
| `guard-threat-model` | 首次安全审查或架构变更时生成威胁模型 |
| `guard-diff-scan` | 交付前扫描 diff 中的调试残留 |
| `guard-verify` | 完成前验证；要求提供验证证据 |
| `guard-ship` | 交付（PR 模式或直接发布模式） |
| `guard-close` | 完成裁决；区分 Blocking / Risk / Polish / Adjacent |
| `guard-gitops` | Git 仓库即唯一事实源；触碰线上/远程/部署产物前使用 |
| `readable-final-answer` | 重写内容降低认知负担 + 最终答案/PR 描述/过程播报体裁规范 |
| `readable-metrics` | 终端可扫描的指标表达 |
| `assist-learn` | 经验沉淀为规则 / 模板 / 操作卡 |
| `assist-retrospect` | 工作失误或流程事故后的结构化复盘 |
| `fe-ui-design` | 前端设计约束；创建 web 组件、页面或应用时使用 |
| `fe-ui-critique` | UI 设计诊断；已有页面、截图或实现需要判断视觉质量时使用 |
| `fe-ui-design-system` | 轻量设计系统；提取或生成 DESIGN.md 风格视觉契约 |
| `fe-ui-lint-artifact` | UI artifact 扫描；检查 AI slop、硬编码 token、filler copy 和溢出风险 |
| `fe-ui-visual-iterate` | UI 视觉迭代；截图、差异表和复拍驱动视觉收敛 |
| `react-doctor` | React 代码健康检查；React 改动后运行，用于提前发现问题 |
| `web-read` | 把远程 URL / GitHub / PDF 读成干净 Markdown |
| `agent-browser` | 浏览器与 Electron 应用自动化；交互、截图、表单、提取 |
| `agent-health` | 审计 agent 配置栈 / skills wiring / hooks / MCP / 全局规则 |
| `workflow-helper` | 多步骤工作流不清时生成路线和停止条件 |
| `hive` | Hive 协作运行时；多 agent 通信、team 上下文与消息传递 |

## 指令分工

| 放哪里 | 适用场景 | 不该放什么 |
|--------|----------|------------|
| `agents/AGENTS.md` | 全局硬约束、事实与验证红线、所有任务都成立的行为边界 | 高频流程步骤、领域细则、长篇背景知识 |
| `commands/` | 一天会重复多次的高频 inner-loop 工作流 | 只在少数场景才需要的长知识库 |
| `coding-skills/` | 领域能力、流程能力、按需触发的专项约束 | 本应全局生效的硬规则 |
| `docs/` | 调研沉淀、refs 详情、设计取舍与可追溯背景 | 需要每次任务都注入上下文的规则 |

### 相邻 Skill 路由矩阵

| 任务状态 | 优先 skill | 不选谁 |
|----------|------------|--------|
| 任务接近完成，需要判断继续还是停止 | `guard-close` | 不做 review/verify 细查 |
| 准备交付前，需要总检查和编排 | `guard-check` | 不替代具体 `guard-review` / `guard-verify` |
| 准备声称完成，需要证据 | `guard-verify` | 不做 scope 裁决 |
| 接手陌生仓库，需要全局地图 | `think-map` | 不聚焦单次改动文件表 |
| 单次任务影响面不明，需要改动地图 | `think-context-map` | 不输出全仓库架构说明 |
| 回答前上下文不足 | `think-ask-context` | 不直接规划实现 |
| 开放主题综述，不急着下判断 | `think-survey` | 不强制推荐方案 |
| 技术选型/方案决策，需要结论 | `think-research` | 不只罗列流派 |
| 多个候选路径已明确，需要取舍 | `think-compare` | 不重新做开放调研 |

### 技能串联

```
think-map / think-research ─→ think-quality ─→ think-plan ─→ dev-tdd ─→ guard-verify ─→ guard-ship
                                   │                │                          │               │
                                   │                ↓                          ↓               ↓
                                   │           dev-refactor                guard-review   hive / agent-browser
                                   │                │
                                   │                ↓
                                   └────────────→ guard-verify

dev-debug ─→ guard-verify                  （任何 skill 卡住时）→ think-unstuck
guard-secure ─→ dev-debug / dev-tdd
guard-check ─→ guard-review / guard-secure / guard-verify / guard-ship / guard-gitops
guard-gitops ─→ 触碰线上/远程/部署产物前的前置门禁（被 guard-check / guard-ship 串调用）
```

## 工程流程 Skills 设计

### 问题

参考项目（superpowers、GSD 等）提供了严谨的研发流程，但存在两个实践问题：

1. **Prompt 竞争** — Skill 形态在 session 启动时注入大量提示词（5-80K chars），与 AGENTS.md 争夺 agent 注意力，削弱用户自定义准则的权威性
2. **刚性过强** — 强制所有操作走完整流程（设计→规划→TDD→review），不适合快速修复和小改动

### 方案

将工程流程拆为独立 Skill（`think-*` / `dev-*` / `guard-*` 等当前前缀），用户按需触发，不污染 idle context：

- **AGENTS.md 保持权威** — 全局准则不受干扰
- **用户控制粒度** — 纯文档、样式、配置等非行为类小改可直接改；新功能、bug 修复和行为变更仍按 `/dev-tdd`
- **零 idle 开销** — Skill 仅在触发时加载（agent 也可主动调用）
- **渐进式披露** — skill 主文件只保留高信号规则，细节优先下沉到 `refs/`、`examples/`、`scripts/`
- **description 当触发器** — 让模型知道“什么时候该调用”，而不是只看到功能摘要

调研文档：`docs/software-engineering-research/`

### 深读入口

| 主题 | 文档 |
|------|------|
| 规划 / spec | `docs/software-engineering-research/plan.md` |
| TDD | `docs/software-engineering-research/tdd.md` |
| 调试 | `docs/software-engineering-research/debug.md` |
| 审查 | `docs/software-engineering-research/review.md` |
| 上下文 / 记忆 | `docs/software-engineering-research/context-memory.md` |
| 其他方向取舍 | `docs/software-engineering-research/other-directions.md` |

## Refs

`refs/` 主要以 git submodule 形式收集第三方 Agent Skills 项目，按 `refs/{owner}/{repo}` 组织；少量本地参考快照可能不是 submodule，权威状态以 `.gitmodules` 和实际目录共同判断。

### 目录结构

```text
refs/
├── {owner}/
│   └── {repo}/          # git submodule → github.com/{owner}/{repo}
└── docs/                # 研究文档（gitignored，本地生成）
    ├── README.md        # 汇总表格 + 分类
    └── {owner}/{repo}.md
```

### 分类

| 分类 | 项目 |
|------|------|
| 浏览器自动化 | `ChromeDevTools/chrome-devtools-mcp`, `vercel-labs/agent-browser` |
| 多智能体协作 | `Yeachan-Heo/oh-my-claudecode`, `notdp/hive`, `nyldn/claude-octopus` |
| 前端 UI / 设计系统 | `google-labs-code/stitch-skills`, `nextlevelbuilder/ui-ux-pro-max-skill`, `pbakaus/impeccable`, `vercel-labs/agent-skills` |
| 研发流程 / 项目管理 | `automazeio/ccpm`, `gsd-build/get-shit-done`, `obra/superpowers` |
| 上下文 / 记忆管理 | `mksglu/context-mode`, `muratcankoylan/Agent-Skills-for-Context-Engineering` |
| 最佳实践 / 知识库 | `shanraisshan/claude-code-best-practice` |
| 技能集合与市场 | `anthropics/skills`, `Dimillian/Skills`, `affaan-m/everything-claude-code`, `glittercowboy/taches-cc-resources`, `libukai/awesome-agent-Skills`, `travisvn/awesome-claude-Skills` |
| 代码质量 / 审查 | `millionco/react-doctor` |
| MCP / 工具链 | `vercel-labs/skills` |
| 行为协议 / 提示工程 | `tanweai/pua` |

### 常用操作

```bash
# 克隆后初始化 submodule
git submodule update --init --depth 1

# 添加新项目
git submodule add --depth 1 https://github.com/{owner}/{repo} refs/{owner}/{repo}

# 更新全部
git submodule update --remote --depth 1
```

# msitarzewski/agency-agents

- 上游仓库：`https://github.com/msitarzewski/agency-agents`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/msitarzewski/agency-agents`
- 主分类：**Agent 角色库 / 多工具 Agent 资产**
- 能力标签：`Claude Code agents`, `multi-agent orchestration`, `agent prompts`, `NEXUS`, `tool integrations`, `conversion scripts`
- 一句话总结：一个 144 个专门化 AI agent 的 Markdown 角色库，配套多工具转换/安装脚本和 NEXUS 多 agent 编排方法论。

## 能力概览

- [事实] README 说明仓库包含 144 个 specialized agents，覆盖 12 个 division，并提供工程、设计、营销、产品、项目管理、测试、支持、空间计算、专业岗位等角色。
- [事实] 每个 agent 文件用 YAML frontmatter 描述 `name`、`description`、`color`、`emoji`、`vibe`，正文包含身份、使命、规则、交付物、流程、沟通风格、成功指标等结构。
- [事实] `scripts/convert.sh` 可把源 Markdown agent 转成 Antigravity、Gemini CLI、OpenCode、Cursor、Aider、Windsurf、OpenClaw、Qwen、Kimi 等工具格式；`scripts/install.sh` 负责安装到对应工具目录。
- [事实] `strategy/nexus-strategy.md` 定义 NEXUS 七阶段流水线：Discover -> Strategize -> Scaffold -> Build -> Harden -> Launch -> Operate，并强调 quality gate、handoff、parallel execution、single source of truth。
- [事实] `specialized/agents-orchestrator.md` 定义一个管线控制 agent：PM -> ArchitectUX -> Dev <-> QA Loop -> Integration，并要求质量门禁、最多 3 次重试、上下文传递和进度状态管理。
- [推断] 适合吸收为本仓库的参考素材：agent 文件结构、frontmatter 规范、多工具转换脚本、NEXUS handoff/quality-gate 模板；不适合作为直接运行时依赖，因为核心资产是 prompt/Markdown，而不是可调用 SDK 或库。

## 资产盘点

- [事实] README 声称有 144 个 specialized agents、10,000+ 行 agent 内容。
- [事实] 顶层 agent 分类目录包括 `engineering/`、`design/`、`marketing/`、`paid-media/`、`sales/`、`product/`、`project-management/`、`testing/`、`support/`、`spatial-computing/`、`specialized/`、`strategy/`、`finance/`、`academic/`、`game-development/`。
- [事实] `examples/` 包含多 agent 协作输出示例，例如 `nexus-spatial-discovery.md`。
- [事实] `strategy/` 包含 NEXUS 主策略、quickstart、phase playbooks、runbooks、handoff templates、activation prompts。
- [事实] `integrations/` 包含 Claude Code、GitHub Copilot、Antigravity、Gemini CLI、OpenCode、OpenClaw、Cursor、Aider、Windsurf、Kimi、Qwen 等适配说明或生成产物入口。
- [事实] `scripts/` 包含 `convert.sh`、`install.sh`、`lint-agents.sh` 和 i18n 辅助资产。

## 关键文件

- `README.md`
- `CONTRIBUTING.md`
- `scripts/convert.sh`
- `scripts/install.sh`
- `integrations/README.md`
- `specialized/agents-orchestrator.md`
- `strategy/nexus-strategy.md`
- `strategy/QUICKSTART.md`
- `strategy/coordination/handoff-templates.md`
- `examples/README.md`
- `examples/nexus-spatial-discovery.md`

## 备注

- [事实] 仓库未发现 `package.json`、`tsconfig`、`src/`、`docs/`；构建/转换入口是 Bash 脚本，而非 Node/TS 工程。
- [事实] 许可证为 MIT，README 写明可商业或个人自由使用，attribution appreciated but not required。
- [推断] 对本仓库最有吸收价值的是“catalog 化 agent prompt + 转换脚本 + 编排模板”，尤其是 `convert.sh` 的字段抽取、slugify、按工具生成格式，以及 NEXUS 的 handoff / quality gate 文档结构。
- [未验证] README 中 “production-ready / battle-tested” 属于项目自述，未从测试日志或外部案例独立验证。

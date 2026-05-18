# garrytan/gstack

- 上游仓库：`https://github.com/garrytan/gstack`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/garrytan/gstack`
- 主分类：**研发流程 / 多智能体工程工作流**
- 能力标签：`Claude Code Skills`, `浏览器自动化`, `QA`, `代码审查`, `安全审计`, `发布流程`, `Bun`, `Playwright`, `多 Agent 适配`, `记忆管理`
- 一句话总结：面向 Claude Code 及多种 AI 编码代理的工程工作流套件，把产品规划、架构评审、浏览器 QA、代码审查、安全审计、发布部署和跨会话记忆组织成一组可安装 skill 与本地浏览器运行时。

## 能力概览

- 提供“Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect”式 sprint 工作流，README 明确列出 `/office-hours`、`/plan-*`、`/review`、`/qa`、`/ship`、`/retro` 等串联关系。
- 根 `SKILL.md` 是浏览器/技能总入口，启动前会检查升级、会话、repo mode、telemetry、learn 文件和 skill routing 状态。
- `browse` 是核心运行时：Bun 编译 CLI 连接本地长驻 Chromium daemon，默认 headless，也支持可视化 GStack Browser、sidebar agent 和 pair-agent tunnel。
- 覆盖产品/CEO 评审、工程评审、设计评审、DX 评审、QA 自动修复、报告型 QA、发布 PR、merge/deploy、canary、benchmark、安全审计、文档生成/更新、PDF 生成、上下文保存/恢复、学习记忆等。
- 支持多 host 生成与安装：Claude、Codex、Factory Droid、Kiro、OpenCode、Slate、Cursor、OpenClaw、Hermes、GBrain；host 配置在 `hosts/*.ts`，生成逻辑在 `scripts/gen-skill-docs.ts`。
- 运行时依赖较重：`package.json` 使用 Bun、Playwright、Puppeteer Core、ngrok、Transformers；`setup` 会构建二进制、安装依赖/Chromium、链接 skills，并可启用 team auto-update hook。
- 风险/副作用包括：写入 `~/.gstack` 状态与 analytics、安装/链接到各 agent skill 目录、可能注册 Claude SessionStart hook、cookie import 涉及本机浏览器/Keychain、pair-agent 可启动 ngrok tunnel，部分 skills 会 commit/push/PR/merge/deploy。

## 资产盘点

- 46 个顶层 skill 子目录含 `SKILL.md`，另有根 `SKILL.md`。
- Bun/TypeScript 浏览器运行时：`browse/src/`，编译产物目标为 `browse/dist/browse`。
- 多 host 适配系统：`hosts/*.ts`、`scripts/host-config.ts`、`scripts/gen-skill-docs.ts`。
- 安装与运维脚本：`setup`、`bin/gstack-*`、`scripts/*`。
- 文档：`README.md`、`ARCHITECTURE.md`、`BROWSER.md`、`docs/skills.md`、`docs/domain-skills.md`、`USING_GBRAIN_WITH_GSTACK.md` 等。
- 代表性运行资产：`review/checklist.md`、`qa/templates/`、`qa/references/`、`openclaw/*`、`browser-skills/hackernews-frontpage/`。

## 关键文件

- `README.md`
- `SKILL.md`
- `package.json`
- `setup`
- `ARCHITECTURE.md`
- `BROWSER.md`
- `docs/skills.md`
- `docs/domain-skills.md`
- `hosts/index.ts`
- `scripts/host-config.ts`
- `scripts/gen-skill-docs.ts`
- `docs/ADDING_A_HOST.md`
- `review/checklist.md`
- `qa/templates/`
- `browse/src/`

## 备注

- [推断] 适合吸收的是“分阶段工程工作流、skill 生成管线、host config 抽象、浏览器 QA 运行时、安全/发布门禁”的设计模式。
- [推断] 不宜直接整体吸收：仓库强绑定 Claude Code/gstack 路径与 `~/.gstack` 状态，且安装和运行副作用较多。
- [推断] 对当前 dotfiles/skills 体系更合适的方式是拆分借鉴：轻量化吸收 review/QA/ship/guard 的流程 contract，浏览器 daemon 和 GBrain/telemetry/team hook 需单独评估。

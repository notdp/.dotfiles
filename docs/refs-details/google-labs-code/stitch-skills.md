# google-labs-code/stitch-skills

- 上游仓库：`https://github.com/google-labs-code/stitch-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/google-labs-code/stitch-skills`
- 主分类：**前端 UI / 设计系统**
- 能力标签：`Stitch 工作流`, `React 组件生成`, `视频生成`
- 一句话总结：围绕 Stitch MCP 的 Agent Skills 库，用于 UI 设计生成、设计系统提炼、React 转换和演示视频生成。

## 能力概览

- 增强模糊 UI prompt，补充 UI/UX 术语和设计系统上下文。
- 从 Stitch 项目提炼 DESIGN.md 设计系统文档。
- 把 Stitch screen 转成 React 组件并做样式/AST 约束校验。
- 使用 Remotion 生成产品 walkthrough 视频。

## 资产盘点

> 注：V2 重构后（见下方 2026-05-29 range 块），资产已迁到 plugin 架构。以下数字反映 range 尾 `53f15d8` 的 `git ls-tree`，旧的“8 skill / 3 workflow / 4 脚本”表述已失真。

- 3 个 plugin：`stitch-build`、`stitch-design`、`stitch-utilities`。
- 13 个 skill（`stitch-design` 6 个、`stitch-build` 3 个、`stitch-utilities` 4 个）。
  - `stitch-design`：code-to-design、extract-design-md、extract-static-html、generate-design、manage-design-system、upload-to-stitch。
  - `stitch-build`：react-components、remotion、shadcn-ui。
  - `stitch-utilities`：design-md、enhance-prompt、stitch-loop、taste-design。
- marketplace 清单：`.agents/plugins/marketplace.json` + 每 plugin 的 `.codex-plugin/plugin.json`。
- 大量 React/Remotion/shadcn/Stitch 示例资源。

## 关键文件

- `README.md`
- `skills/stitch-design/SKILL.md`
- `skills/stitch-loop/SKILL.md`
- `skills/react-components/README.md`

## 2026-05-29 本地 range 调研

> 信号来源：本地 remote-tracking（未联网）。本轮 range `6c0cbdb909b7..53f15d81da85`，`git log` 核实 29 commits。注意本地工作树 HEAD 仍停在 range 起点 `6c0cbdb`，新结构通过 `git ls-tree 53f15d81da85` 核实。

- [事实] **Stitch Skills V2**（commit `a1f77d5` "Stitch Skills V2"）把单体 `stitch-design` 拆成 6 个独立 skill：code-to-design、extract-design-md、extract-static-html、generate-design、manage-design-system、upload-to-stitch。
- [事实] **plugin 架构重构**（commit `5532ce0` "refactor: restructure skills into plugin architecture"）：原 `skills/*` 扁平结构迁移为 `plugins/{stitch-build,stitch-design,stitch-utilities}/skills/*`，并补 Codex marketplace manifest（`4b76f44` "Restore Codex marketplace manifest"、`cbfb385` "Add Codex plugin metadata"，`.agents/plugins/marketplace.json` + 每 plugin `.codex-plugin/plugin.json`）。
- [事实] 新增 **extract-design-md** skill，带多框架 reference：`references/{angular,plain-css,react-tailwind,svelte,vue}.md`。
- [事实] **react-components 修了 hex guard 静默 no-op bug**（commit `241b53e` "fix(react-components): detect hex colors in JSX className"）：`scripts/validate.js` 原读 `node.name.name === 'className'`，但 SWC AST 把 JSXAttribute 标识符放在 `.name.value`，条件恒 false，no-hardcoded-hex 规则从不触发。修复改为同时接受 `.name?.value` 和 `.name?.name`。
- [事实] 期间还有一批 `fix security risk` / `fix the last security risk` commit（`8e34bd0`、`3bd73f2`、`cf11888`、`66f6f5e`）和安装/路径修复。
- [推断] 演进方向是从单一 Stitch skill 库转向跨 runtime（Codex/Antigravity/Gemini CLI/Claude Code/Cursor）的多 plugin 打包，与本仓库 skills 分域组织的方向一致。

## 备注

- 强依赖 Stitch MCP；部分能力还依赖 Remotion MCP 或本地 Node 环境。

## 最近 14 天更新（2026-03-31 ~ 2026-04-14）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main`
- [事实] 提交数：`0`
- [事实] 这段时间没有新提交可列。
- [事实] 默认分支近 14 天无新提交。
<!-- recent-updates:end -->

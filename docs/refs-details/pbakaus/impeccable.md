# pbakaus/impeccable

- 上游仓库：`https://github.com/pbakaus/impeccable`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/pbakaus/impeccable`
- 主分类：**前端 UI / 设计系统**
- 能力标签：`反模式约束`, `多 provider 打包`, `设计审查命令`
- 一句话总结：面向前端设计质量的跨平台技能/命令打包仓库，附带官网、下载 API 和构建系统。

## 能力概览

- 提供 frontend-design 技能，覆盖 typography、color、motion、responsive、interaction、UX writing。
- 提供 20 个设计修改或审查命令，如 audit、polish、typeset、arrange、overdrive。
- 维护反模式库，专门约束 AI 常见设计俗套。
- 构建系统可把 source skills 转成多 provider 格式并生成下载包。

## 资产盘点

- 21 个 source skills 目录（1 个基础 skill + 20 个 commands）。
- 10 个 provider target。
- 官网静态资源与下载 API。
- CI workflow 与构建脚本。

## 关键文件

- `README.md`
- `package.json`
- `AGENTS.md`
- `source/skills/frontend-design/SKILL.md`
- `scripts/build.js`

## 2026-05-27 本地 range 调研

- [事实] 本轮 range：`dc715c7359cc44f7d20c638deaec2f17e6b2f4b3..84135db0e6bdd58d22828f7bc8331cae7bde3e7f`。
- [事实] 上游新增 Detector architecture v2，拆出 browser injected bundle、CLI main、regex/static-html/browser/visual engines、CSS cascade、contrast、profiler、antipattern registry、rules checks、benchmark detector、detector lab 页面和 fixtures。
- [事实] 新增 DeepSeek live E2E adapter，并强化 live server test 隔离、Windows-safe CLI entry-point 与 provider 目录分发。
- [推断] UI 质量判断正在从纯 prompt critique 走向静态 HTML、浏览器运行时、视觉 contrast、regex 文本规则组合的混合检测。
- [推断] 本仓库可将 detector v2 的规则组织方式吸收到 `fe-ui-lint-artifact` / `fe-ui-critique`，但不应复制其多 provider 目录结构。

## 备注

- 当前快照重点是 source/build/website；文档中的 provider 数量说明与实际 build target 有版本差。

## 最近 14 天更新（2026-03-31 ~ 2026-04-14）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main`
- [事实] 提交数：`141`
- [事实] 代表提交：
  - `2026-04-10` `Add skills check command, skip-if-up-to-date in update, decouple versioning`
  - `2026-04-10` `Add cleanup script for deprecated skills with 20 tests`
  - `2026-04-09` `Add scroll-margin-top to prose headings so anchors clear the sticky header`
  - `2026-04-08` `Add invisible hover buffer around the before/after demo`
- [推断] 新增 `skills check`、skip-if-up-to-date 更新逻辑与 cleanup 脚本，整理 skill 版图（21→18），上线 Chrome 扩展并持续扩展 UI anti-pattern 检测与站点渲染能力。
<!-- recent-updates:end -->

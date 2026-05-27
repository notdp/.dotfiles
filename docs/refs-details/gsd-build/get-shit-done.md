# gsd-build/get-shit-done

- 上游仓库：`https://github.com/gsd-build/get-shit-done`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/gsd-build/get-shit-done`
- 主分类：**研发流程 / 项目管理**
- 能力标签：`规范驱动开发`, `上下文工程`, `多代理编排`, `质量与安全`
- 一句话总结：跨多种 AI 运行时的 spec-driven development / context engineering 系统，覆盖立项、规划、执行、验证、交付全流程。

## 能力概览

- 初始化 .planning/ 工件：PROJECT、REQUIREMENTS、ROADMAP、STATE。
- 支持 discuss → plan → execute → verify → ship 阶段化工作流。
- 通过 18 个专用 agents 组织研究、规划、执行、验证、审计。
- hooks 提供状态栏、上下文监控、更新检查、prompt/workflow guard。

## 资产盘点

- 57 个命令。
- 18 个 agents。
- 5 个 hooks、5 个 scripts。
- 多语言 README 与架构文档。

## 关键文件

- `README.md`
- `package.json`
- `docs/ARCHITECTURE.md`
- `docs/AGENTS.md`
- `commands/gsd/`

## 2026-05-27 本地 range 调研

- [事实] 本轮 range：`8b679959cc6d5889ecfaa28dbd5e9c4328e15fba..837114c1d0a4bec91983bb198a2b0d9f42a9446f`。
- [事实] 上游新增/强化 CJS/SDK hard seam、STATE/configuration/workstream inventory/project-root generator、shared manifests、`QueryRuntimeBridge.executeForCjs`、state router delegation、graphify auto-update hook、Codex install skill surface、runtime-aware slash formatter、CLI negative matrix harness。
- [事实] 安全与可靠性修复包括 `check.ship-ready` argv-based subprocess、planning path traversal validation，以及 phase/roadmap 回归测试。
- [推断] 演进方向是从 workflow 命令集合转向 typed SDK + generated CJS adapters + parity tests 的跨 runtime 系统。
- [推断] 本仓库应优先吸收 shared manifest、generator、parity/negative tests、runtime adapter 输出格式这些工程化模式；不应导入完整 GSD workflow 以免和现有 `think-*` / `dev-*` / `guard-*` 路由竞争。

## 备注

- 架构文档中的数量统计与当前目录树略有差异。

## 最近 14 天更新（2026-03-31 ~ 2026-04-14）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main`
- [事实] 提交数：`194`
- [事实] 代表提交：
  - `2026-04-13` `feat: /gsd-graphify integration — knowledge graph for planning agents (#2164)`
  - `2026-04-12` `feat(sdk): Phase 1 typed query foundation (gsd-sdk query) (#2118)`
  - `2026-04-12` `feat(health): detect stale and orphan worktrees in validate-health (W017) (#2175)`
  - `2026-04-12` `feat(workflow): scan planted seeds during new-milestone step 2.5 (#2177)`
- [推断] 新增 `/gsd-graphify` 知识图谱、typed query 基础、worktree 健康检查、milestone seed 扫描、线程/快捷命令管理与更强的 TDD/审计/安全门禁。
<!-- recent-updates:end -->

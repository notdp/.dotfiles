# mksglu/context-mode

- 上游仓库：`https://github.com/mksglu/context-mode`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/mksglu/context-mode`
- 主分类：**上下文 / 记忆管理**
- 能力标签：`MCP 工具链`, `会话连续性`, `多运行时适配`, `Hooks`
- 一句话总结：面向多种 AI 编码运行时的 MCP/plugin，用来减少上下文窗口占用并保留会话连续性。

## 能力概览

- 提供 ctx_execute / ctx_batch_execute 等沙箱执行能力，避免大输出进入上下文。
- 支持文档与网页索引、搜索、抓取并落库到 SQLite FTS5/BM25。
- 通过 hooks 记录文件编辑、git 操作、任务、错误、用户决策并在 compact 后恢复。
- 为 Claude Code、Gemini CLI、Cursor、Codex、Kiro 等生成不同配置。

## 资产盘点

- 4 个 skill。
- 36 个 hook 文件。
- 20+ 个跨平台配置模板。
- 4 个脚本与完整 src 实现。

## 关键文件

- `README.md`
- `package.json`
- `skills/context-mode/SKILL.md`
- `hooks/hooks.json`
- `src/session/db.ts`

## 2026-05-27 本地与联网刷新调研

- [事实] 初稿 range：`17587f6f64604cb856b160e10ed1745ba322a9a0..276c2ad9136c2edd7c8f8ec84c7b5c185358c71f`；联网刷新后 remote-tracking 更新到 `188833f8a0712bbd7dfa5aae7aaff1ab470acb85`。
- [事实] 上游发布 `1.0.132` 到 `1.0.151`，强化 `CONTEXT_MODE_DATA_DIR`、SessionDB path、projectDir-scoped memory、runtime storage override、directory indexing、per-call cache TTL、surrogate-safe preview truncation、OpenCode native plugin ctx tools。
- [事实] 还包含 tool description audit、WebFetch refusal、duplicate hook doctor warning、Codex session log cwd recovery、AGENTS rules capture on session start、pack integrity 和 stale cache path healing。
- [事实] 刷新后新增 `276c2ad..188833f` 主要包括 install stats 更新、release title convention 文档、cross-platform cwd assertion 测试修复和 bundle refresh；未改变前述主要吸收结论。
- [推断] 上游重点从上下文压缩/检索扩展到跨 runtime deployment、storage isolation、doctor 可诊断性、tool routing safety 与 session continuity。
- [推断] 本仓库应把 projectDir-scoped memory、storage override、context-surface、tool description/refusal 纳入安全与 hook 设计检查；不应默认用 ctx_execute 替代现有工具纪律。

## 备注

- 并非所有平台都有完整 hook 支持；许可证是 Elastic-2.0。

## 最近 14 天更新（2026-03-31 ~ 2026-04-14）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main`
- [事实] 提交数：`114`
- [事实] 代表提交：
  - `2026-04-14` `feat(insight): add ctx-insight skill for /ctx-insight slash command`
  - `2026-04-14` `feat(insight): add personal analytics dashboard with ctx_insight tool`
  - `2026-04-13` `feat(search): content-type-aware title boost in reranking (#265)`
  - `2026-04-13` `feat(web): add open-to-opportunities badge with tooltip`
- [推断] 连续发布 `1.0.79`~`1.0.88`，新增 `ctx-insight` skill 与个人 analytics dashboard/工具链，并补强 search、upgrade 与 CI 稳定性。
<!-- recent-updates:end -->

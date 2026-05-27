# tw93/Waza

- 上游仓库：`https://github.com/tw93/Waza`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/tw93/Waza`
- 主分类：**技能集合与市场**
- 能力标签：`工程习惯`, `代码审查`, `系统化调试`, `研究写作`, `前端设计`, `Claude Code 配置审计`
- 一句话总结：轻量但完整的工程习惯 skill pack，把 `think`、`design`、`check`、`hunt`、`write`、`learn`、`read`、`health` 八类动作打包成可安装 skills，并附带 statusline 与 English Coaching。

## 能力概览

- 用 8 个 skill 覆盖较完整的工程工作流：事前思考、前端设计、交付前检查、系统化排障、写作润色、深度研究、URL/PDF 阅读、Claude Code 健康审计。
- `marketplace.json` 明确为每个 skill 声明触发条件、非适用场景、版本与来源路径，说明作者把“什么时候调用”当成一等接口来设计。
- `check` 与 `health` 不只是 prompt 文件，还配了 reviewer / inspector agents、脚本和 reference 文档，体现出“prompt + 资产 + 校验”式封装。
- `read` skill 不是纯文本指导，实际落到 shell / Python 抓取脚本，覆盖 GitHub、PDF、微信、飞书等内容入口。
- 附加资产里还有 `statusline` 和 `rules/english.md`：前者解决 Claude Code 上下文/配额可视化，后者把“英文优先 + 即时纠错”做成可安装规则。

## 资产盘点

- 8 个 skills：`think`、`design`、`check`、`hunt`、`write`、`learn`、`read`、`health`。
- 1 个 `marketplace.json`，列出 8 个插件项，当前版本均为 `3.9.0`。
- 3 个顶层脚本：`verify-skills.sh`、`setup-statusline.sh`、`statusline.sh`。
- 5 个 skill 内脚本：`check` 1 个、`read` 3 个、`health` 1 个。
- 4 个 agents：`check` 2 个 reviewer，`health` 2 个 inspector。
- 4 组 references：`check` 1 个、`design` 1 个、`read` 1 个、`write` 2 个。
- 1 条 GitHub Actions workflow：`test.yml`，通过 `make test` 校验 skills、脚本和 smoke tests。
- 1 条额外 rule：`rules/english.md`。

## 关键文件

- `README.md`
- `CLAUDE.md`
- `marketplace.json`
- `Makefile`
- `scripts/verify-skills.sh`
- `skills/check/SKILL.md`
- `skills/health/SKILL.md`
- `skills/read/SKILL.md`
- `rules/english.md`

## 2026-05-27 本地 range 调研

- [事实] 本轮 range：`47ebdc8b68fba76cf7f5e4c84e4b782709b5b73c..24e207c87daf7123e5e7ce22bf81bcb69bfa3e9e`。
- [事实] 上游新增 `waza-routing` rule，用于不具备 description auto-routing 的宿主；配套 structural check、`setup-rule.sh` 和测试。
- [事实] `check` 增强 Project Audit Mode、audit guardrails、finding quality gate、worktree safety、CLI audit contract checks；`read` 增强 privacy-first cascade 和 fetched content untrusted data；verify shell 重构为 Python modules，并新增 package validator。
- [推断] Waza 正从轻量 skill pack 演进为带显式 routing rule、verifier、host compatibility 和安全边界的小型 agent harness。
- [推断] 本仓库应吸收“description auto-routing 不可靠时用显式 routing rule + verifier”的模式；不应为了模仿 Waza 的 8 skill hard cap 而合并现有细分技能。

## 备注

- 它不是 `oh-my-claudecode` / `hive` 那类运行时平台，也不是 `superpowers` 那类强调完整流程治理的重型方法学包；更像“把工程师日常高频习惯压缩成一组可直接装上的 skill”。
- [事实] README 明确说明 `health` 仅适用于 Claude Code；其余 skill 会尽量复用宿主环境原生的提问、搜索、抓取和 agent 机制。
- [推断] 它处在 `obra/superpowers` 和 `shanraisshan/claude-code-best-practice` 之间：比后者更可执行，比前者更轻、更少制度负担。
- [推断] `read` / `statusline` / `english.md` 这些“附加资产”很实用，但也意味着仓库并非纯 skills 清单，而是带少量工具化实现的 opinionated bundle。

## 最近 14 天更新（2026-03-31 ~ 2026-04-14）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main`
- [事实] 提交数：`186`
- [事实] 代表提交：
  - `2026-04-06` `feat: add statusline script for Claude Code context and quota display`
  - `2026-04-08` `feat: add web search plugin support to read and learn skills`
  - `2026-04-10` `feat(health): add Part C context effectiveness audit to inspector-context`
  - `2026-04-11` `feat: add English Coaching rule and clean up extras distribution`
  - `2026-04-14` `fix: replace readlink -f with portable fallback for macOS (#28)`
- [推断] 这两周的主线是高频迭代八个核心 skill 与安装资产：新增 statusline、English Coaching、`read`/`learn` 外部检索支持，持续强化 `design`/`health`/`check`/`write`，并反复修补 Codex、marketplace、verify-skills 与 macOS 兼容性问题。
<!-- recent-updates:end -->

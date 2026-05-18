# addyosmani/agent-skills

- 上游仓库：`https://github.com/addyosmani/agent-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/addyosmani/agent-skills`
- 主分类：**研发流程 / Agent Skill 工作流**
- 能力标签：`Agent Skills`, `Claude Code Plugin`, `Slash Commands`, `Subagents`, `TDD`, `Code Review`, `Security`, `Shipping`
- 一句话总结：面向 AI coding agent 的生产级软件工程 skill 包，把 spec、plan、build、test、review、simplify、ship 串成带验证门禁的生命周期工作流。

## 能力概览

- 提供 23 个 skills：22 个覆盖 Define / Plan / Build / Verify / Review / Ship 生命周期，另有 `using-agent-skills` 作为 meta-skill。
- 提供 7 个 slash commands：`/spec`、`/plan`、`/build`、`/test`、`/review`、`/code-simplify`、`/ship`。
- 内置 3 个 specialist personas：`code-reviewer`、`security-auditor`、`test-engineer`。
- README 明确强调 skills 是 workflow，不是普通参考文档；每个 skill 关注步骤、检查点、退出条件和验证证据。
- skill 设计模式包括 anti-rationalization 表、verification evidence、progressive disclosure，以及按需加载 supporting references。
- 支持 Claude Code plugin、Claude marketplace、Cursor、Gemini CLI、Windsurf、OpenCode、GitHub Copilot 等多运行时接入。
- `/ship` 是明确的并行 fan-out 编排样例：并发运行 code review、安全审计、测试覆盖分析，然后由主上下文合并为 go/no-go 决策。
- 包含 `scripts/validate-skills.js`，用于校验 `SKILL.md` frontmatter、必需章节和显式 cross-skill references。

## 资产盘点

- 23 个 skills。
- 7 个 Claude Code slash commands。
- 7 个 Gemini CLI command 配置。
- 3 个 agent personas。
- 5 份 reference checklist / orchestration 文档。
- 7 份 setup / skill anatomy 文档。
- 1 个 Claude plugin manifest。
- 1 个 marketplace manifest。
- 1 个 skill 校验脚本。
- 1 组 session lifecycle hooks。
- 1 个 skill 内脚本：`skills/idea-refine/scripts/idea-refine.sh`。

## 关键文件

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.claude/commands/spec.md`
- `.claude/commands/plan.md`
- `.claude/commands/build.md`
- `.claude/commands/test.md`
- `.claude/commands/review.md`
- `.claude/commands/code-simplify.md`
- `.claude/commands/ship.md`
- `.gemini/commands/*.toml`
- `agents/README.md`
- `agents/code-reviewer.md`
- `agents/security-auditor.md`
- `agents/test-engineer.md`
- `skills/using-agent-skills/SKILL.md`
- `skills/spec-driven-development/SKILL.md`
- `skills/planning-and-task-breakdown/SKILL.md`
- `skills/incremental-implementation/SKILL.md`
- `skills/test-driven-development/SKILL.md`
- `skills/code-review-and-quality/SKILL.md`
- `skills/security-and-hardening/SKILL.md`
- `skills/shipping-and-launch/SKILL.md`
- `references/orchestration-patterns.md`
- `scripts/validate-skills.js`
- `hooks/hooks.json`

## 备注

- [推断] 适合吸收其“生命周期 skill taxonomy + command 编排 + 验证门禁 + anti-rationalization”模式，而不是整包照搬。
- [推断] 与现有本地 skill 体系相比，它的优势在于结构统一、触发描述清晰、跨 Claude/Gemini/OpenCode/Copilot 的分发形态完整。
- [推断] `using-agent-skills`、`spec-driven-development`、`planning-and-task-breakdown`、`incremental-implementation`、`test-driven-development`、`code-review-and-quality`、`shipping-and-launch` 最适合作为研发流程类 skill 的参考样本。
- [推断] `scripts/validate-skills.js` 的 frontmatter / required section 校验逻辑适合借鉴为本仓库 skill 质量门禁。

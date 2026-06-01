# Chachamaru127/claude-code-harness

- 上游仓库：`https://github.com/Chachamaru127/claude-code-harness`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/Chachamaru127/claude-code-harness`
- 主分类：**Harness 工程 / Agent 工作流框架**
- 能力标签：`Plan-Work-Review-Release`, `Go 原生护栏引擎`, `声明式安全规则`, `多 Agent 团队编排`, `Breezing 并行执行`, `Worker/Reviewer/Advisor 三角色`, `TDD 强制`, `harness.toml 配置正本`, `跨宿主适配`, `VibeCoder 认知负荷 Surface`
- 一句话总结：为 AI 编码 Agent 构建的结构化交付循环框架，通过 5 动词 skill + 声明式护栏 + 多 Agent 团队编排 + 证据链，将散漫的 Agent 编码约束为可重复的 Plan-Work-Review-Release 路径。

## 能力概览

- 核心工作流由 5 个动词 skill 驱动：plan、work、review、sync、release，每个 skill 有独立的输入输出契约和触发条件。
- Go 原生声明式护栏引擎（R01-R14）：用规则表实现 PreToolUse/PostToolUse/PermissionRequest 的安全拦截，冷启动 1-2ms（从 TypeScript 的 40-60ms 迁移）。
- 3 Agent 角色分离：Worker（只实现不审查）、Reviewer（只读取不修改，disallowedTools 硬禁 Write/Edit/Bash）、Advisor（只提供 PLAN/CORRECTION/STOP 三值建议，per-task 最多 3 次）。
- Breezing 并行执行：在 git worktree 隔离中并行派发多个 Worker，Lead 负责 diff review + cherry-pick，跨 Worker 违规通过 Universal Violations Injection 传播。
- spec.md / Plans.md 双正本体系：spec.md 是产品契约（什么必须为真），Plans.md 是任务账本（做什么、完成条件、状态标记），spec 优先级永远高于 Plans。
- Worker self_review gate：Worker 在请求 review 前必须填写 6 条结构化自检（DRY、Plans.md 未篡改、符号调用路径、DoD 逐项验证、无测试回归、TDD 红灯证据），Lead 机械验证后才派发 Reviewer。
- harness.toml 配置正本 + 生成体系：harness.toml 是安全策略和项目配置的唯一真相源，通过 `harness sync` 生成运行时配置文件。
- 跨宿主适配：Claude Code（supported）、Codex（internal-compatible）、Cursor（candidate）、OpenCode（candidate），各有 adapter plugin 目录和 skill 镜像。
- VibeCoder 认知负荷 Surface：Plan Brief（着工前）、Progress Tracker（工事中）、Acceptance Demo（引渡时）三个 HTML 单页面，面向非工程师用户。
- 三态健康检查：not-configured（healthy=true，静默）、unreachable（healthy=false，警告）、corrupted（healthy=false，警告），用于所有可选外部依赖。
- Sandbagging-Aware Weak Supervision：检测空断言、无复现证据的 bugfix、无具体证据的 Reviewer 通过等 reward-hacking 行为。
- deleted-concepts.yaml + exclusion-based verification：跟踪已删除概念，CI/release 时自动扫描引用残骸。
- 模糊语审计：对 agent prompt 中的歧义词（'必要时'、'适当'、'如需'等）要求同句补充具体条件，提供 rg 命令一键扫描。

## 资产盘点

- 35 个 skills（primary）+ 3 个 Codex 专用 skill 变体 = 38 个 skill 定义。
- 3 个 sub-agent 定义：Worker、Reviewer、Advisor。
- 4 个 workflow 定义：init、plan、review、work。
- Go 原生引擎源码：40+ hook handler 实现、13 guardrail 规则（R01-R13）、SQLite 状态存储。
- ~140 个 shell/JS/Python 脚本：hook handler（30+）、CI、session 管理、安全、TDD 强制。
- ~130 个测试文件：shell 验证、Go 单元测试、集成测试、fixture。
- 100+ 个文档文件：架构、策略、上游快照、研究、onboarding、计划。
- ~45 个模板文件：CLAUDE.md、AGENTS.md、Plans.md、hooks、HTML、ja 本地化。
- 22 个 .claude/rules/ 策略文件。
- 7 个 GitHub Actions workflow：benchmark、codeql、release、scorecard、smoke-install、validate-plugin、opencode-compat。
- hooks.json 注册 20+ CC 生命周期事件。
- 跨平台编译二进制：darwin-arm64/amd64、linux-amd64、windows-amd64。
- Benchmark 评估套件：breezing-bench，10+ 评估任务 + 统计分析。

## 关键文件

- `CLAUDE.md`
- `spec.md`
- `Plans.md`
- `harness.toml`
- `.claude-code-harness.config.yaml`
- `claude-code-harness.config.schema.json`
- `go/cmd/harness/main.go`
- `go/DESIGN.md`
- `go/SPEC.md`
- `go/internal/guardrail/`（R01-R13 规则实现）
- `go/internal/hookhandler/`（40+ hook handler）
- `go/internal/breezing/`（并行 agent 编排）
- `go/internal/session/`（session 生命周期）
- `go/internal/state/store.go`（SQLite 状态存储）
- `go/pkg/config/toml.go`（harness.toml 解析器）
- `agents/worker.md`
- `agents/reviewer.md`
- `agents/advisor.md`
- `skills/harness-plan/SKILL.md`
- `skills/harness-work/SKILL.md`
- `skills/harness-review/SKILL.md`
- `skills/harness-sync/SKILL.md`
- `skills/harness-release/SKILL.md`
- `skills/breezing/SKILL.md`
- `skills/harness-accept/SKILL.md`
- `skills/harness-plan-brief/SKILL.md`
- `skills/harness-progress/SKILL.md`
- `skills/routing-rules.md`
- `hooks/hooks.json`
- `hooks/BEST_PRACTICES.md`
- `.claude-plugin/plugin.json`
- `.claude/rules/`（22 个策略文件）
- `docs/ARCHITECTURE.md`
- `docs/MIGRATION-v4.md`
- `docs/cognitive-load-surfaces.md`
- `docs/sandbagging-aware-weak-supervision.md`

## 备注

- [事实] 版本 4.13.2，经历 80+ Phase 迭代，从 TypeScript 全面迁移到 Go 原生实现（v4.0.0）。
- [事实] 项目是自引用的：Harness 用自己来开发自己，这意味着 hook/skill 的 bug 可能影响修复该 bug 的开发过程。
- [事实] 日语起步，正在迁移到英语优先；大量核心文档（decisions.md、patterns.md、CHANGELOG）仍为日语。
- [推断] 最值得吸收的不是具体 skill 实现，而是三个设计哲学：契约结构化（JSON schema 替代自然语言传递）、验证逆向化（exclusion-based verification 补全正向检查）、指令可检查性（模糊语审计 + deleted-concepts 扫描）。
- [推断] 系统复杂度极高（87+ Phase、36 skill、130+ 脚本），对新贡献者入门门槛很高；多层配置（harness.toml + hooks.json + settings.json + plugin.json）虽有生成工具辅助，但排查链路长。
- [推断] 多宿主支持（Codex/Cursor/OpenCode）投入了大量设计和代码，但都停留在 internal-compatible 或 candidate 层级，实际用户价值尚未验证。
- 详细洞察分析见 [`claude-code-harness-insights.md`](./claude-code-harness-insights.md)。

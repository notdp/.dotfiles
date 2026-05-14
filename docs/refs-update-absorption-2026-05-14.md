# Refs Update Absorption Report — 2026-05-14

方法论：`docs/software-engineering-research/refs-absorption-methodology.md`

## Scope

- 更新方式：`git submodule update --remote --recursive`
- 更新后有指针变化的 refs：22 个
- 本报告只做 L0-L3 分析和文档记录；L4 runtime 或 L5 global rule 候选必须单独审批。

## Updated Ranges

| 项目 | Old | New | Commits |
|---|---:|---:|---:|
| `ChromeDevTools/chrome-devtools-mcp` | `06b331f` | `081c903` | 48 |
| `HughYau/qiushi-skill` | `0fe8b1d` | `6cac8a5` | 10 |
| `Yeachan-Heo/oh-my-claudecode` | `1e9f197` | `679b418` | 153 |
| `addyosmani/web-quality-skills` | `fed9617` | `7b59d48` | 21 |
| `affaan-m/everything-claude-code` | `c7c7d37` | `4423f10` | 253 |
| `anthropics/skills` | `5128e18` | `f458cee` | 3 |
| `github/awesome-copilot` | `7d6e3ed` | `97cc3f2` | 76 |
| `gsd-build/get-shit-done` | `eeaf9c5` | `8b67995` | 460 |
| `millionco/react-doctor` | `9e9769d` | `2c1f742` | 86 |
| `mksglu/context-mode` | `62a8ca0` | `17587f6` | 510 |
| `nexu-io/open-design` | `10e8e2d` | `852a005` | 487 |
| `notdp/hive` | `b899e52` | `ef61455` | 23 |
| `nyldn/claude-octopus` | `fd3c521` | `b98b9b7` | 129 |
| `obra/superpowers` | `6efe32c` | `f2cbfbe` | 2 |
| `pbakaus/impeccable` | `9a5d0e7` | `dc715c7` | 30 |
| `shanraisshan/claude-code-best-practice` | `6f45aa5` | `f8468e8` | 128 |
| `tanweai/pua` | `34cf090` | `56332fe` | 14 |
| `tirth8205/code-review-graph` | `0919071` | `52cf3bc` | 115 |
| `tw93/Waza` | `51222bf` | `47ebdc8` | 305 |
| `vercel-labs/agent-browser` | `57405f9` | `55f38f4` | 7 |
| `vercel-labs/agent-skills` | `ce3e64e` | `b9c8ee0` | 1 |
| `vercel-labs/skills` | `7c0a9af` | `c99a72b` | 7 |

## Absorption Candidates

| 项目 | Commit range | 变化主题 | 候选吸收项 | Level | 风险 | 建议动作 | 证据 |
|---|---|---|---|---:|---|---|---|
| `tw93/Waza` | `51222bf..47ebdc8` | routing drift、anti-patterns、health budget | 确定性检查 skill 路由漂移；补“隐式授权不等于 push/publish/close 授权”规则 | L2/L3 | low | absorb | `skills/RESOLVER.md`, `scripts/check-routing-drift.sh`, `rules/anti-patterns.md` |
| `anthropics/skills` | `5128e18..f458cee` | `skill-creator` eval loop | skill 创建时做 baseline vs with-skill 对照、测试 prompt、定量+定性迭代 | L2/L3 | medium | absorb | `skills/skill-creator/SKILL.md` |
| `affaan-m/everything-claude-code` | `c7c7d37..4423f10` | skill stocktake、GateGuard、cross-harness | 缓存式 skill 体检；fact-forcing pre-edit gate；durable behavior in skills, adapters at edge | L2/L3 | medium | absorb / research-later | `skills/skill-stocktake/SKILL.md`, `skills/gateguard/SKILL.md`, `docs/architecture/cross-harness.md` |
| `gsd-build/get-shit-done` | `eeaf9c5..8b67995` | spec-driven planning、description lint、worktree hardening | 计划契约必须包含 wave/deps/must_haves/verification；description 长度预算；worktree inclusion filter | L2/L3 | low-medium | absorb | `CHANGELOG.md`, `scripts/lint-descriptions.cjs`, `get-shit-done/templates/planner-subagent-prompt.md` |
| `Yeachan-Heo/oh-my-claudecode` | `1e9f197..679b418` | team pipeline、approval boundary、deep investigation | 规划 pending approval 不得实现；stage handoff artifact；trace 文本作为 untrusted data | L2 | medium | absorb | `skills/team/SKILL.md`, `skills/ralplan/SKILL.md`, `skills/deep-dive/SKILL.md` |
| `obra/superpowers` | `6efe32c..f2cbfbe` | worktree/git safety、completion guardrails | native worktree tool preference、submodule guard、provenance-owned cleanup、evidence-before-claims | L2/L3 | medium | absorb | `RELEASE-NOTES.md`, `skills/using-git-worktrees/SKILL.md`, `skills/verification-before-completion/SKILL.md` |
| `notdp/hive` | `b899e52..ef61455` | runtime semantics、thread protocol | 区分 `busy` 输出层与 `turnPhase` 语义层；root `send` 短摘要、细节走 artifact；新话题 send，续话题 reply | L2/L4 | medium | absorb contract first | `docs/runtime-model.md`, `docs/transcript-signals.md`, `skills/hive/SKILL.md` |
| `nyldn/claude-octopus` | `fd3c521..b98b9b7` | provider allowlist、proof packet、validation gate | 多 provider 调用前展示 availability/cost/allowlist；验证不只看 exit 0，还要检查 synthesis/validation artifact | L2/L3 | medium | absorb / research-later | `skills/flow-discover/SKILL.md`, `scripts/lib/provider-allowlist.sh`, `scripts/lib/proof-packet.sh` |
| `ChromeDevTools/chrome-devtools-mcp` | `06b331f..081c903` | page-scoped tools、navigation URL、agentic browsing | 浏览器工具前置条件：页面级工具必须有 page；动作触发导航后报告新 URL；snapshot 优先于 screenshot | L2 | medium | absorb | `CHANGELOG.md`, `docs/tool-reference.md`, `src/ToolHandler.ts` |
| `vercel-labs/agent-browser` | `57405f9..55f38f4` | React introspection、Core Web Vitals、same-origin dashboard | browser QA 合同升级为 React tree/renders + vitals + same-origin proxy + trust boundaries | L2/L4 | high | absorb L2, L4 later | `CHANGELOG.md`, `skill-data/core/SKILL.md`, `skill-data/core/references/trust-boundaries.md` |
| `addyosmani/web-quality-skills` | `fed9617..7b59d48` | Lighthouse v13、CWV、安全 headers、a11y | UI 交付质量门：CWV/a11y/security/console/deploy checklist | L2/L3 | medium | absorb | `skills/web-quality-audit/SKILL.md`, `skills/core-web-vitals/SKILL.md`, `skills/accessibility/SKILL.md` |
| `pbakaus/impeccable` | `9a5d0e7..dc715c7` | explicit gates、palette-first image flow、asset producer | UI 生成前四门禁：brief → direction questions → palette → approved mock；资产 manifest | L2/L4 | high | absorb L2, L4 later | `skill/reference/craft.md`, `skill/reference/codex.md`, `skill/agents/impeccable-asset-producer.md` |
| `nexu-io/open-design` | `10e8e2d..852a005` | token schema、artifact sandbox、Critique Theater | token schema/guard、双 worktree 截图对比、artifact sandbox、design jury 评分 | L2/L3 | high | absorb L2, research-later L3 | `CHANGELOG.md`, `docs/architecture.md`, `design-systems/_schema/AGENTS.md`, `docs/critique-theater.md` |
| `millionco/react-doctor` | `9e9769d..2c1f742` | ESLint plugin、UI rules、offline score | 确定性 React/UI 规则进入 `fe-ui-lint-artifact` / `guard-review`；脚本规范加入输出上限和 env 清洗 | L2/L3 | low-medium | absorb selected | `packages/react-doctor/CHANGELOG.md`, `src/eslint-plugin.ts`, `src/plugin/rules/react-ui.ts` |
| `tirth8205/code-review-graph` | `0919071..52cf3bc` | minimal context、risk scoring、blast radius | `think-context-map` / `guard-review` 增加 risk、affected flows、test gaps、next tool suggestions | L2/L3 | medium-high | absorb method, tooling later | `CHANGELOG.md`, `code_review_graph/tools/context.py`, `code_review_graph/changes.py` |
| `vercel-labs/skills` | `7c0a9af..c99a72b` | update scope、case detection、path safety、agent detection | skill 安装/校验规范：terminal-control sanitize、subpath 不逃逸、folder hash lock、大小写 `skill.md` 检测 | L3 | medium | absorb | `src/sanitize.ts`, `src/source-parser.ts`, `src/update-source.ts` |
| `mksglu/context-mode` | `62a8ca0..17587f6` | context budget、doctor、stats | `agent-health` / `readable-metrics` 增加 `[OK]/[WARN]/[FAIL]`、真实 bytes saved/returned、context budget posture | L2/L3 | medium | absorb pattern | `README.md`, `src/server.ts`, `src/session/analytics.ts` |
| `HughYau/qiushi-skill` | `0fe8b1d..6cac8a5` | workflow handoff、multi-target install | workflow 步间 handoff 格式和终止条件；delegated subagent skip 条件 | L2 | low | absorb | `skills/workflows/SKILL.md`, `skills/arming-thought/SKILL.md` |
| `shanraisshan/claude-code-best-practice` | `6f45aa5..f8468e8` | Claude Code v2.1.139/140 知识库 | 新 frontmatter 字段和 scoped hooks 进入调研待更新清单，不直接 runtime | L1/L2 | medium | research-later | `best-practice/claude-skills.md`, `best-practice/claude-subagents.md` |
| `tanweai/pua` | `34cf090..56332fe` | diagnosis-first、高能动性 hooks | 只抽象吸收 `[DIAGNOSIS] 问题/证据/下一步`，拒绝 PUA 语气和 hooks runtime | L2 | medium-high | absorb format, reject runtime | `skills/pua/SKILL.md`, `hooks/hooks.json` |
| `github/awesome-copilot` | `7d6e3ed..97cc3f2` | external plugin、AI-ready wrapper、quality playbook | 轻 wrapper 指向上游 SSOT；external plugin 校验可观察；拒绝重型 quality artifact 默认生成 | L2/L3 | medium-high | absorb wrapper, observe tooling | `skills/ai-ready/SKILL.md`, `plugins/external.json`, `eng/generate-marketplace.mjs` |

## Priority Backlog

| Priority | 候选项 | 推荐落点 | Level | 理由 |
|---:|---|---|---:|---|
| P1 | skill routing drift 校验 | `scripts/verify_skills.py` 或新脚本 | L3 | 本仓库 skills 增多，确定性防漂移收益高 |
| P1 | planning/execution approval boundary | `think-plan` / `ExitSpecMode` 相关规范 | L2 | 已与 spec mode 行为强相关，可减少未批准实现 |
| P1 | worktree/submodule cleanup guard | `guard-gitops` / `guard-ship` | L2/L3 | 直接降低误删、误清理和 submodule 风险 |
| P1 | UI 验证合同扩展 | `fe-ui-*` / `guard-verify` | L2 | 截图之外加入 CWV/a11y/security/console/network 更完整 |
| P2 | context-map risk/test-gap 输出 | `think-context-map` / `guard-review` | L2/L3 | 提升 review 和改动影响面分析质量 |
| P2 | skill eval loop | `skill-authoring.md` / future skill-creator | L2/L3 | 防止新增 skill 只写 prompt 不做效果对照 |
| P2 | browser trust-boundaries | `agent-browser` / `guard-secure` | L2 | page content untrusted、secrets 不进模型，安全价值高 |
| P3 | provider proof packet | `guard-verify` / provider workflows | L3 | 有价值但引入 artifact 管理，需单独设计 |

## Reject / Observe

- Reject runtime：`tanweai/pua` 的压力话术和 hooks runtime，副作用强且与本仓库事实纪律冲突。
- Reject runtime：`anthropics/skills/claude-api` 这类大型供应商 API 手册式 skill，时效和供应商耦合高。
- Reject direct copy：`github/awesome-copilot/quality-playbook`，默认生成大量 artifact，不适合作为本仓库默认 guard。
- Observe：`github/awesome-copilot` external plugin marketplace、`shanraisshan` Claude Code 新字段表、`mksglu/context-mode` MCP runtime、`code-review-graph` SQLite/MCP runtime。

## Notes

- 部分上游有 forced update 或旧 hash 不在当前远端 history 中，已按本地旧指针与新 checkout 记录 range；后续落地 L3/L4 前需要再次逐项复核关键 diff。
- `K-Dense-AI/scientific-agent-skills` 和 `Owl-Listener/designer-skills` 是本轮之前新增 refs，本轮没有作为“其他 refs”重点展开。

# Refs Research 2026-05-27

本轮调研先基于 collector 提供的本地 remote-tracking range：`git -C <ref> log <old>..<remote> --oneline --stat`。用户随后批准联网刷新后，已对 `.gitmodules` 登记的 refs 执行逐路径 `git fetch`，并追加刷新后的 remote-tracking 差异。本文件不包含 session raw transcript 或 secret。

## 方法

- 初稿输入：`python3 scripts/skill_maintenance_collect.py --repo . --format json` 输出的 `refs` 列表。
- 初稿限制：初稿阶段未执行 `git fetch`、未执行 `git submodule update`，只代表当时本地 remote-tracking 状态。
- 联网刷新：用户批准 D-008 后，执行 `.gitmodules` 顶层路径逐个 `git -C <path> fetch`；`git submodule foreach --recursive` 因 `refs/forrestchang/andrej-karpathy-skills` 缺少 submodule mapping 中断，已记录为 refs metadata 异常。
- 刷新后新增证据：`ChromeDevTools/chrome-devtools-mcp` `081c9033..3ba70d35`，`mksglu/context-mode` `17587f6f..188833f8`，`nexu-io/open-design` `852a005b..a6a56099`。
- 证据方式：逐 ref 读取 `git -C <ref> log <old>..<remote> --oneline --stat`，并对照对应 `docs/refs-details/<owner>/<repo>.md`。

## 高优先级 refs

| Ref | 变更摘要 | [推断] 演进方向 | 本仓库关联 | 建议 | Severity |
|---|---|---|---|---|---|
| `vercel-labs/agent-skills` | 新增大型 `vercel-optimize` skill，包含 metrics collection、budget summary、deep dive、scanner-driven gates、claim extraction、fixtures/tests/libs，并多轮 harden scope preflight、redaction、data gap reporting、claim verification。 | [推断] 从前端最佳实践集合演进为带数据采集、验证、报告再生成的垂直诊断系统。 | `guard-verify`、`dev-operational-task`、`react-doctor`、`fe-ui-*`。 | 更新 refs-details；吸收 scope preflight、redaction、data gap reporting、claim verification 到复杂 verification/operational skill 规范；不复制 Vercel-specific fixtures。 | should |
| `gsd-build/get-shit-done` | 推进 CJS/SDK hard seam、shared manifests + generator、runtime bridge、Codex install surface、negative CLI harness、path traversal/security 修复、ship-ready argv subprocess。 | [推断] 从 workflow 文档/命令演进为 typed SDK + generated adapters + parity tests 的跨 runtime 系统。 | `think-plan`、`dev-tdd`、`guard-verify`、`guard-ship`、`kilo-config`、`scripts/verify_skills.py`。 | 更新 refs-details；吸收 generator/parity/runtime bridge 思路到本仓库校验体系调研，不导入全套 GSD workflow。 | should |
| `muratcankoylan/Agent-Skills-for-Context-Engineering` | 新增 researcher OS、claim ledger、benchmark runner、router benchmark、corpus hardening、harness-engineering skill。 | [推断] 把 skill description 和 routing 从经验写作推进到可评测资产。 | `skill-creator`、`agent-harness-creator`、`agent-health`、`think-*`、`assist-learn`。 | 更新 refs-details；建立关键 skill routing cases/holdout 测试的研究 backlog；不导入 launchd continuous loop。 | should |
| `pbakaus/impeccable` | 新增 detector architecture v2、browser/static-html/visual engines、CSS cascade、contrast、antipattern registry、detector lab、DeepSeek live E2E adapter。 | [推断] UI critique 从纯 LLM 评价转向静态/浏览器/视觉混合检测。 | `fe-ui-critique`、`fe-ui-lint-artifact`、`fe-ui-visual-iterate`。 | 更新 refs-details；提炼 deterministic UI artifact lint 候选规则，不复制多 provider 目录。 | should |
| `tw93/Waza` | 新增 `waza-routing` rule、structural check、Project Audit Mode、privacy-first read cascade、Python verifier/package validator、Pi health audits。 | [推断] 轻量 skill pack 演进为带 routing rule、verifier、host compatibility 的小型 harness。 | `scripts/verify_skills.py`、`guard-check`、`guard-review`、`agent-health`、`web-read`。 | 更新 refs-details；吸收“description auto-routing 不可靠时用显式 routing rule + verifier”的模式。 | should |
| `mksglu/context-mode` | 强化 projectDir-scoped memory、storage override、directory indexing、OpenCode native plugin、Codex cwd recovery、AGENTS rule capture、tool description audit、WebFetch refusal；联网刷新后 remote 到 `188833f8`，新增主要是 install stats、release title convention、跨平台 cwd assertion 测试。 | [推断] 从上下文压缩/检索扩展为跨 runtime session continuity、storage isolation、doctor 可诊断性和 tool routing safety 系统。 | `kilo-config`、context-surface boundary、hooks、session recall、`guard-secure`。 | 更新 refs-details；把 storage isolation/context-surface 风险加入安全/上下文边界检查；不吸收 install stats 噪音。 | should |
| `nexu-io/open-design` | 联网刷新显示大规模 plugin/marketplace/GenUI/atom pipeline 演进：plugin install/apply/trust/snapshot/doctor/verify/pack/search/publish，first-party atom `SKILL.md`，plugin event ring buffer/SSE tail，Helm/Docker/API token guard/S3 storage，近期补 GSAP skill bundle、Community/Ambassadors 与 agent report 精简。 | [推断] 设计生成系统正在从单体本地设计工作台演进为可验证、可分发、可观测的 plugin runtime。 | `plugin-creator`、`fe-ui-design-system`、`fe-ui-visual-iterate`、`readable-html-artifact`、`dev-operational-task`、`guard-secure`。 | 更新 refs-details；吸收文件化 plugin/atom protocol、manifest validation、author tooling、event observability 和 design artifact pipeline，不复制其完整 daemon/runtime。 | should |

## 中优先级 refs

| Ref | 变更摘要 | 本仓库关联 | 建议 | Severity |
|---|---|---|---|---|
| `nyldn/claude-octopus` | 新增 `octo council`、preflight/setup、provider version floors、directory-format skill migration、Mistral Vibe provider、execution-chain hardening。 | multi-agent workflow、provider checks、directory-format skill。 | 更新 refs-details；参考 provider CLI version floors 和 council gates，不导入完整 runtime。 | should |
| `Yeachan-Heo/oh-my-claudecode` | Windows/native hook hardening、HUD payload warnings、auto-update/plugin registry、worktree cleanup safety、ultragoal/goal workflow。 | `hive`、`dev-long-loop`、`guard-gitops`、agent runtime safety。 | 更新 refs-details；沉淀 Windows hook portability 和 worktree cleanup safety checklist。 | should |
| `github/awesome-copilot` | 大规模 external plugin workflow、legacy skill removal、visual-pr、skill-image-gen、efficiency skills、domain plugin expansion。 | plugin/skill marketplace、visual evidence、skill pruning policy。 | 更新 refs-details；只吸收 external plugin intake/validation 和 legacy pruning 思路。 | should |
| `tirth8205/code-review-graph` | 新增 context savings panel、deterministic eval pipeline、multi-hop benchmark、reproduction recipe。 | `think-context-map`、`guard-review`、context budget。 | 更新 refs-details；评估 CRG 类工具是否能辅助 impact map，不直接集成。 | should |
| `google-labs-code/stitch-skills` | 重构为 `plugins/stitch-*`，新增 Codex plugin metadata、DESIGN.md extract/manage/upload、static HTML security hardening。 | `fe-ui-design-system`、plugin packaging、HTML artifact security。 | 更新 refs-details；吸收 DESIGN.md 作为 UI 设计系统交换格式。 | should |
| `garrytan/gstack` | 新增 AskUserQuestion split、skill v2 budget/parity/e2e、`/spec` 5-phase、browser sidebar、design board、iOS device farm。 | 问用户边界、skill budget/parity tests、agent-browser、think-plan。 | 更新 refs-details；先吸收问用户边界和 skill 测试体系，不导入 runtime/daemon。 | should |
| `awslabs/agentcore-samples` | 大规模 memory restructure、payments/Pay for Data、market trends eval/dataset management、Entra auth deployable fixes。 | `guard-secure`、`dev-operational-task`、`guard-verify`、cloud side-effect boundary。 | 更新 refs-details；新增 memory/payments/eval 索引，不新增可执行 AWS skill。 | should |

## 低优先级 refs

| Ref | 变更摘要 | 建议 | Severity |
|---|---|---|---|
| `anthropics/skills` | `claude-api` Managed Agents self-hosted sandboxes 与 model config shape 修正。 | 补 recent-updates；不新增 skill。 | observe |
| `vercel-labs/agent-browser` | pnpm minimum release age / supply-chain release hardening。 | 补 refs-details 一句；不改 `agent-browser` skill 能力。 | observe |
| `vercel-labs/skills` | update cleanup upstream deleted skills、v2 well-known discovery、SSH URL lock preservation、GitHub token lazy use。 | 更新 refs-details；评估 well-known discovery。 | observe |
| `ChromeDevTools/chrome-devtools-mcp` | 联网刷新到 `3ba70d35`，包含 1.0/1.1 release、`pageId` 参数契约调整、`evaluate_script filePath`、roots realpath validation、unknown args reporting、stdin EOF/SIGTERM shutdown、性能 throttling 修复、extra headers emulation、plugin pinned version。 | 更新 refs-details；补 MCP/tool safety、tool schema 兼容、文件路径 realpath、进程关闭与 plugin 版本 pinning 参考。 | should |
| `K-Dense-AI/scientific-agent-skills` | BIDS、pacsomatic、SIMBAD 合并进 database-lookup、security report refresh。 | 更新 refs-details；吸收 taxonomy 合并和安全扫描模式。 | observe |
| `Owl-Listener/designer-skills` | 新增 visual-critique plugin、4 个 critique skills、`/critique-screen`。 | 合并 critique 维度到 `fe-ui-critique`，不新增 4 个同名 skill。 | observe |
| `addyosmani/agent-skills` | Copilot `*.agent.md` 命名、marketplace relative source、删除 plugin pinning version、低置信度 reason。 | 补 packaging 兼容和 reason 输出模式。 | observe |
| `awslabs/agent-plugins` | CI action bump、SageMaker skill description YAML quote 修复。 | 补 YAML-safe frontmatter 经验。 | observe |
| `notdp/hive` | context usage snapshots、`hive compact`、`--pane`。 | 更新 hive refs 和本地 `hive` skill 说明候选。 | observe |
| `notdp/.dotfiles` | stow config grouping、tmux/ghostty、HTML report rules、skill lock refresh。 | 更新 refs-details；检查 HTML report rules 是否影响 readable artifacts。 | observe |
| `Shubhamsaboo/awesome-llm-apps` | DeepSeek empty response guard、insurance demo follow-up logic。 | 当前 docs 足够；不吸收业务 demo。 | observe |

## 跨 ref 趋势

- Skill 生态从单个 `SKILL.md` 向 `SKILL.md + references + scripts + tests + fixtures` 的可执行 skill 包演进。
- Plugin 生态也在向 `plugin manifest + SKILL.md/atom prompt + validator + author CLI + event log` 演进，`open-design` 与 `ChromeDevTools` 都把可分发包元数据、版本 pinning 和验证工具前置。
- Routing 正在变成可测试接口：`router benchmark`、`waza-routing`、marketplace metadata、external plugin validation 都说明 description 不再只是文案。
- 复杂诊断 skill 更重视 scope preflight、redaction、data gap reporting、claim verification、dry-run/apply safety。
- UI 质量方向从 LLM critique 走向 deterministic detector、visual evidence、screenshot/DOM/contrast 混合证据。
- 多 runtime 兼容正在转向 manifest/generator/parity tests，而不是手写多份配置。
- 安全与供应链主题更前置：minimum release age、token lazy use、roots realpath、unknown args reporting、path traversal validation、YAML-safe frontmatter。

## 对本仓库的改进思路

| 类型 | affected asset | 参考 ref | 变更意图 | severity | 验证方式 |
|---|---|---|---|---|---|
| 更新 | `docs/refs-details/vercel-labs/agent-skills.md` | `vercel-labs/agent-skills` | 吸收 `vercel-optimize` 的可执行 skill 结构与 safety gates。 | should | `python3 scripts/verify_skills.py`，人工核对 commit range。 |
| 更新 | `docs/refs-details/gsd-build/get-shit-done.md` | `gsd-build/get-shit-done` | 吸收 generator/parity/runtime bridge 与 install contract。 | should | `python3 scripts/verify_skills.py`，人工核对 commit range。 |
| 更新 | `docs/refs-details/muratcankoylan/Agent-Skills-for-Context-Engineering.md` | `muratcankoylan/...` | 记录 routing benchmark/researcher OS，把 skill description 视为可评测接口。 | should | `python3 scripts/verify_skills.py`。 |
| 更新 | `docs/refs-details/pbakaus/impeccable.md` | `pbakaus/impeccable` | 吸收 detector v2 和 UI deterministic lint 方向。 | should | `python3 scripts/verify_skills.py`。 |
| 更新 | `docs/refs-details/tw93/Waza.md` | `tw93/Waza` | 吸收 routing rule + verifier + Project Audit Mode。 | should | `python3 scripts/verify_skills.py`。 |
| 更新 | `docs/refs-details/mksglu/context-mode.md` | `mksglu/context-mode` | 吸收 storage isolation/context-surface/tool routing safety。 | should | `python3 scripts/verify_skills.py`。 |
| 更新 | `docs/refs-details/ChromeDevTools/chrome-devtools-mcp.md` | `ChromeDevTools/chrome-devtools-mcp` | 吸收 tool schema/API contract、realpath validation、shutdown、plugin version pinning。 | should | `python3 scripts/verify_skills.py`，人工核对 refreshed range。 |
| 更新 | `docs/refs-details/nexu-io/open-design.md` | `nexu-io/open-design` | 记录 plugin runtime、first-party atom `SKILL.md`、event observability、author CLI 和 deployment/security guard。 | should | `python3 scripts/verify_skills.py`，人工核对 refreshed range。 |
| 新增 | routing cases/holdout 测试方案 | `muratcankoylan/...`, `tw93/Waza` | 建立关键 skill 触发准确率评估。 | should | 先写 docs/spec，再加脚本测试。 |
| 合并 | `fe-ui-critique` 检查表 | `Owl-Listener/designer-skills`, `pbakaus/impeccable` | 把 typography/composition/hierarchy/brand consistency 与 deterministic detector 维度合并进现有入口。 | observe | `python3 scripts/verify_skills.py`。 |
| 减少 | legacy `se-*` routing | session 分析 + 当前 catalog | 不做 alias，移除 legacy 触发；未知旧名进入校验/审查。 | should | `python3 -m unittest scripts.tests.test_skills_registry`。 |

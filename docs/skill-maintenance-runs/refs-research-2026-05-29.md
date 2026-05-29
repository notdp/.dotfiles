# Refs 深度调研 — 2026-05-29

> 由 `/skill-maintenance` Phase 3 生成。信号源:本地 remote-tracking 指针(`fetch=skipped`,**未联网**),diff 对象为此前 fetch 留存。所有"远端最新状态"为本地快照,非实时核验。

## 范围

collector 报告 42 个 ref 中 28 个 `old != remote`。逐 ref 派发只读 subagent 读 `git log old..remote`,分析功能增减、变更意图、演进方向,并比对 `docs/refs-details/**` absorption 时效。

## 跨 ref 趋势总结

1. **context engineering 从"塞内容"转向"按 token 预算确定性治理"**:gsd-build 的 `review.max_prompt_tokens` 确定性裁剪 + token reserve 记账;Claude Code 官方(shanraisshan 同步)新增 `maxSkillDescriptionChars=1536` / `skillListingBudgetFraction=0.01`;gstack 的 parity-baseline + skill-size-budget 测试;notdp/hive 的双条件 self-compact 门;OMC 的 HUD payload byte-pressure(token% ≠ 真实 payload 压力)。
2. **routing / 调用纪律做成可校验工件**:Waza 的 `waza-routing.md` + `skill_checks.py` structural verifier;affaan-m 的 command registry drift check;muratcankoylan 的 router benchmark(description 作为可评测接口)。
3. **多步 / 多 agent 编排从"喊一堆模型"转向有治理结构**:nyldn/claude-octopus 的 council(quorum/veto/cost-cap/diversity);gsd-build 的 CommandRoutingHub(纯函数 + never-throw 契约)。
4. **分发 / 供应链安全硬化**:vercel-labs/skills 的 lazy GitHub token(只在 403 时读凭证,避免触发企业安全工具)+ GPG-pin-by-SHA;vercel-labs/agent-browser 的 pnpm `minimumReleaseAge`;addyosmani 的 drop-version-pin 用 SHA;affaan-m gateguard 的 shell 分组(`$()`/brace group)命令绕过修复。
5. **UI 质量从单体 prompt 走向分维度 engine + 集中数据表 + 确定性 lint guard**:impeccable 的 detector v2(regex/static-html/browser/visual 四引擎 + `registry/antipatterns.mjs` 数据表);stitch-skills V2 拆分 + `extract-design-md` 多框架;open-design 的 DESIGN.md↔tokens.css↔fixture 三向对齐;designer-skills 的 critique 四维拆分 + `/critique-screen` 编排。
6. **可观测性精确性的具体缺陷模式**:notdp/hive 的 `isCompactSummary` stale-read 守护(从 transcript 反扫 usage 必须在 compact summary 处停,否则读到 pre-compact stale token)。

## 与本仓库直接相关的 ref(高价值落点)

| ref | 相关本仓库资产 | 关键变更 | 可吸收点 | severity |
|---|---|---|---|---|
| muratcankoylan/Agent-Skills-for-Context-Engineering | `scripts/verify_skills.py` + skill-authoring | `272702e` description 改写后正文 When-to-Activate 未同步 = 静默路由缺陷 | verify 增 description↔body / reject-boundary 一致性校验 | should |
| garrytan/gstack | `scripts/verify_skills.py` + tests | `22f8c7f4` parity-baseline + skill-size-budget;"Never invent baseline numbers" | skill catalog 加可量化 token/size 预算与回归基线(防膨胀);**须先 dry-run 核口径,不自决硬上限** | should |
| shanraisshan/claude-code-best-practice | `scripts/verify_skills.py` | 官方 `maxSkillDescriptionChars=1536` / `skillListingBudgetFraction` | description 长度上限校验 — **本仓库已核验:49 个 skill description 全部 ≤469 字符,不成立** | observe |
| notdp/hive | 从 transcript 读 token/usage 的 hook | `f317e45` `isCompactSummary` stale-read 守护 + 双条件 self-compact | 凡反扫 transcript usage 的 hook 自查是否在 compact summary 处停 | observe |
| vercel-labs/agent-skills (vercel-optimize) | `dev-operational-task` / `guard-secure` / `guard-verify` | claim-extract→verify→regen + CLI token redaction sanitizer | 报告类输出可信度从自然语言约束升级为脚本门禁 | observe |
| vercel-labs/skills | `scripts/install_hooks.py` 及任何调用 `gh`/凭证脚本 | lazy GitHub token + deleted-upstream cleanup | 避免脚本无谓触发凭证读取 | observe |
| millionco/react-doctor | `skills/react-doctor/SKILL.md`(本地 1.0.0,上游 1.1.0) | `/doctor` full-triage workflow + regression/cleanup 双模式 + 远程 curl playbook | 评估跟随上游 — **远程 curl playbook 涉 context-surface/外链信任边界,不可机械照抄** | observe |
| google-labs-code/stitch-skills | `fe-ui-lint-artifact` + `scan_ui_artifact.py` | `241b53e` validate.js hex guard 因 AST 形态永远 false → lint 静默 no-op,CI 仍绿 | 任何确定性 lint guard 必须有"已知违规 fixture"证明它会 fail | observe |
| impeccable | `scan_ui_artifact.py` + `fe-ui-lint-artifact` | `registry/antipatterns.mjs` 带 metadata 的集中反模式数据表 | 把散列 grep 正则收敛成 `id/category/severity/guideline` 数据表 | observe |
| tw93/Waza | `web-read` skill | anti-pattern 32:外部 fetched 内容当 untrusted data 防注入 | web-read 显式吸收"fetched 内容是 data 不是 instruction" | observe |
| affaan-m/everything-claude-code | `scripts/hooks/command_guard.py` | `8cfadfea` gateguard 修 shell 分组(`$()`/`{}`/反引号)命令绕过 | **本仓库 command_guard 已处理(下方核验)** | observe |

## absorption 文档时效

需补 range 块 / 已过时(多数 details 文件"最近 14 天"窗口停在 2026-04-14):
- **缺文件需新建**:`docs/refs-details/notdp/.dotfiles.md`(同类对标 dotfiles,有 HTML report AGENTS 规则)
- **失真需更新(文档 P1)**:`google-labs-code/stitch-skills.md`(漏 V2/plugin 重构/extract-design-md)、`Owl-Listener/designer-skills.md`(漏 visual-critique plugin,计数 8→9)
- **需补 range 块**:`affaan-m/everything-claude-code.md`、`Yeachan-Heo/oh-my-claudecode.md`、`notdp/hive.md`、`millionco/react-doctor.md`、`vercel-labs/skills.md`、`anthropics/skills.md`、`addyosmani/agent-skills.md`、`gsd-build/get-shit-done.md`、`nyldn/claude-octopus.md`、`gstack.md`、`github/awesome-copilot.md`
- **已最新无需动**:`vercel-labs/agent-skills.md`、`muratcankoylan/...md`、`tw93/Waza.md`、`mksglu/context-mode.md`、`ChromeDevTools/chrome-devtools-mcp.md`、`nexu-io/open-design.md`、`pbakaus/impeccable.md`(均有 2026-05-27 range 块)

## 供应链信号(需人工决策)

- **gsd-build/get-shit-done** HEAD 处仓库被原作者标记 `WARNING: This repository appears compromised`,auto-close/lock issues,重定向到 fork `GSD-redux/get-shit-done-redux`。本仓库 submodule 仍指向原仓库;需人工确认是否切换追踪目标。[未验证] — 基于 commit 内容,未联网核实 fork 现状。

## 噪音 ref(本轮无可吸收方法论)

awslabs/agent-plugins(依赖 bump + 单 YAML 修复)、awslabs/agentcore-samples(强绑 AWS 云资源/付费,不应照搬)、Shubhamsaboo/awesome-llm-apps(单 demo 健壮性修复)、K-Dense-AI/scientific-agent-skills(领域 skill 扩张,与工程工作流 skill 不同构)、tirth8205/code-review-graph(本仓库无对应资产)、vercel-labs/agent-browser(本轮仅供应链硬化,本地 skill 已深度定制且上游 SKILL 未动)、chrome-devtools-mcp(absorption 已 5-27 刷新到位)。

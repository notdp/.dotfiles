# EveryInc/compound-engineering-plugin

- 上游仓库：`https://github.com/EveryInc/compound-engineering-plugin`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/EveryInc/compound-engineering-plugin`
- 纳入 commit：`85987d496fdfdc8a18faf592fd53329e23266537`（2026-05-29 加入，本地 remote-tracking）
- 主分类：**研发流程 / 经验复利（compound engineering）工作流插件**
- 能力标签：`compound engineering`, `机构记忆`, `learnings 沉淀`, `code review`, `multi-agent`, `Bun/TypeScript`, `多平台分发`, `grep-first 检索`
- 一句话总结：Every（Kieran Klaassen）的多平台 AI 工程工作流插件（37+ skills、50+ agents，`ce-` 前缀），把"计划 → 执行 → 审查 → 沉淀"做成每跑一圈都让下一圈更省力的闭环；核心资产是 `docs/solutions/` 这个带受控 frontmatter、可被未来 agent grep 检索的机构记忆库。

## 能力概览

- 形态：根仓库是 Bun/TypeScript CLI + 多 plugin monorepo（`@every-env/compound-plugin` v3.9.3），CLI 把 Claude Code 原生 plugin 转换/安装到 Codex、Cursor、Copilot、Droid、Qwen、OpenCode、Gemini 等多平台。产品是 `plugins/compound-engineering/`。
- skills 是 orchestrator（slash 入口），agents 是被派发的只读 subagent（README:105 "you typically don't call these directly"），全部 flat 放在 `agents/ce-*.md`。
- 主张：每个工程动作应让后续动作更容易而非更难（README:10）；"80% 在 planning 和 review，20% 在 execution"（README:14）；复利落点是时间——同一问题第二次只花零头时间（ce-compound SKILL:534）。

## 设计理由（WHY）— compound 机制落在哪

针对的核心失败模式（`docs/skills/ce-compound.md:24-31` 明列 "The Problem"）：

| 失败模式 | 对应机制 |
|---|---|
| 知识不沉淀 / 每次从零 | `ce-compound` 在 context 最新鲜时（"that worked"/"it's fixed" 自动触发）写 `docs/solutions/[category]/[file].md` |
| 解决方案活在聊天里、一周后蒸发 | 强制写入 repo-tracked markdown + YAML frontmatter，而非 wiki |
| 写了但没人/没 agent 能发现 | **Discoverability Check**（SKILL:298-330）：每次检查项目 AGENTS.md/CLAUDE.md 是否引导未来 agent 去搜 `docs/solutions/`，不达标就提议补一行 |
| 同问题重复写、文档漂移 | Overlap detection 五维评分，高重叠时更新旧文档而非新建 |
| 教训过期、与代码漂移 | `ce-compound-refresh` 五态维护（Keep/Update/Consolidate/Replace/Delete），把记忆库当需要维护的资产 |
| review 不复用、错误重复犯 | `ce-learnings-researcher` 是 always-on persona：每次 review/plan/ideate 前先搜历史教训 |

[推断] 真正的复利不在"写文档"这个动作，而在 **read-side 被默认接入 plan 和 review 的前置 research**——沉淀只有被自动消费才产生复利，这个 plugin 把消费做成 always-on，而非靠人记得查。这是它与"只写 learning note"的本质区别。

## 特别技巧（非显然）

1. **教训结构化沉淀的双轨 schema**（`ce-compound/references/schema.yaml`）：`problem_type` 决定 track。Bug track 必填 `symptoms`/`root_cause`/`resolution_type`（受控 enum，如 `root_cause: missing_index|thread_violation|...`）；Knowledge track 必填 `module`/`date`/`problem_type`/`component`/`severity`。比自由文本 learning note 可检索性强得多。
2. **grep-first 检索协议**（`ce-learnings-researcher.md:67-99`）：按 frontmatter 字段并行预筛文件路径 → 只读候选前 30 行 frontmatter → 只全读通过相关性打分的文件。200 文件筛出 5-20 个候选，不把全部读进 context。
3. **YAML "fail loud" 校验脚本**（`scripts/validate-frontmatter.py`，纯 stdlib）：专抓静默腐败——未引号的 ` #`（注释截断）、未引号 `: `（mapping 混淆）、畸形 `---`。
4. **review-to-learning 闭环**（`ce-code-review`，899 行）：5 锚点置信度 `{0,25,50,75,100}`（每个数字有行为判据写死在 findings-schema.json）；confidence gate 故意最后跑，让 anchor-50 finding 先有机会被 cross-reviewer 协同提升（2+ reviewer 命中同一 fingerprint → 升档）；`autofix_class`（safe_auto/gated_auto/manual/advisory）与 severity 正交；per-finding 独立 validator subagent（而非 batch，避免重新引入 persona-bias）；finding 编号单调递增不重排（下游 skill 可按 `#` 引用）。
5. **Runtime vs Authoring Context 区分**（plugin AGENTS.md）：plugin 的 AGENTS.md/CLAUDE.md 是 authoring context，不随安装发货；治理 skill 运行时行为的规则必须写进 SKILL.md 或其 references/，共享行为靠**复制**而非跨 skill 引用（因 converter 把每个 skill 目录当独立单元 + 路径解析 bug）。
6. **Calibrate prescription level to failure mode**：deterministic safety 用 hard rules；judgment call 用 strong guidance + bad/good 例子；其余 trust。判据是"能否说出这条规则防止的具体坏结果"。
7. **Conditional and Late-Sequence Extraction**：SKILL 内容 trigger 后会被带进后续每个 message（成本随 session 复利），所以条件触发或晚序且占比 ≥20% 的块抽到 references/，主体只留 1-3 行 stub。
8. **`!` 预解析 shell 安全规则 + 测试强制**：`case`/`;`/`$(...)` 含双引号/`${var%pattern}` 等被 Claude Code 安全检查拒绝，由 `tests/skill-shell-safety.test.ts` 强制（把自然语言提醒降级为测试强制）。

## 与本仓库 agent skill 生态的关系

对照 `assist-learn` / `assist-retrospect` / `guard-review` / `agent-health` / `context_capsule`：

| 维度 | 本仓库现状 | compound 做法 | 借鉴点 |
|---|---|---|---|
| 沉淀写入 | `assist-learn` 产自由文本 learning note，落点未强制 | `ce-compound` 写 `docs/solutions/` + 受控 enum frontmatter | 双轨 frontmatter + grep 检索是本仓库缺失视角 |
| 复用读取 | [推断] 无 always-on "工作前先查历史教训" | `ce-learnings-researcher` 被 plan/review 默认前置调用 | **本仓库最大缺口**：有写入端无 read-side 自动接入 |
| 经验维护 | [未验证] 无明确老化/去重 | `ce-compound-refresh` 五态 + "delete don't archive" | 缺"教训会过期需维护"视角 |
| 可发现性 | learning 落点不强制 | Discoverability Check 自检并修 AGENTS.md | 可借鉴 |
| review | `guard-review` 产分级清单 | 锚点置信度 + cross-reviewer 提升 + autofix_class 正交路由 + 稳定编号 | 比单纯分级更精细 |

- **本仓库更强**：真 hook 强制层（compound 全靠测试 + SKILL 文本，无真 hook）；失误导向的 `assist-retrospect`（compound 几乎只沉淀成功解法）；`agent-health` 配置审计。
- **不建议吸收**：多平台 converter CLI、`ce-` 命名强制、release-please 版本治理（Every 分发场景特定需求）。

## 可吸收候选（L0-L5，建议先走 /think-plan）

| # | affected asset | 吸收形式 | level | 风险 |
|---|---|---|---|---|
| C1 | `assist-learn` 模板 + 新 schema | learning note 引入双轨 frontmatter（受控 enum problem_type/module/tags/component），让经验可 grep | L2 | 低 |
| C2 | `think-research` 或 `assist-learn` | grep-first 检索协议：frontmatter 预筛 → 读前 30 行 → 相关性打分后全读；作为"工作前查历史经验"的 read-side 入口 | L3 | 中（需定统一落点目录） |
| C3 | `assist-learn` | Discoverability 自检：写完检查 AGENTS.md 是否引导未来 agent 搜经验库 | L2/L3 | 低-中（契合本仓库 routing 文化） |
| C4 | 新 `assist-*` 或并入 `skill-maintenance` | 五态维护模型对经验库做老化（需先有 C1 结构化库） | L3 | 中 |
| C5 | `guard-review` | 5 锚点置信度 + cross-reviewer 协同 + autofix_class 正交路由 + 稳定编号 | L3 | 中-高（改 review 契约，需配套测试，防 scope 膨胀） |
| C6 | `skill-authoring.md` | 把"prescription level 三档校准"和"runtime vs authoring context"作为对照原则记入 | L1 | 极低 |

**最高价值单点**：C2（read-side 默认接入）。compound 的复利来自"写的东西被 plan/review 自动消费"；本仓库有 `assist-learn` 写入端，[推断] 缺"工作前自动查历史经验"的读取端，正是复利不闭合的断点。

## 吸收状态（2026-05-29，保守）

- **已吸收 → `skill-authoring.md` §0**：C6 的"按失败模式校准约束强度（hard rule / guidance / trust）"和"区分 runtime 与 authoring context"两条编写原则。纯文档、不改 runtime。
- **推迟（稳定优先）**：C1（assist-learn 结构化 frontmatter schema）、C2（grep-first learnings-researcher read-side 自动接入）、C3（Discoverability 自检）、C4（五态维护）、C5（guard-review 置信度锚点 + cross-reviewer + autofix 路由）。这些新增能力或改 review 契约，影响面大，按"稳定优先"暂不做。
- **最高价值 backlog**：C2 read-side 自动接入是 compound 复利闭环的关键，也是本仓库 `assist-learn` [推断] 的最大缺口；建议未来单独走 `/think-plan` 评估（需先定 C1 的统一 learning 落点与 schema），不在本轮保守改进内。

## 关键文件

- `README.md`、`AGENTS.md`、`CLAUDE.md`、`package.json`
- `plugins/compound-engineering/{README.md, AGENTS.md, plugin.json}`
- `plugins/compound-engineering/skills/ce-compound/`（SKILL + `references/schema.yaml`）
- `plugins/compound-engineering/skills/ce-code-review/`（SKILL + `references/persona-catalog.md` + `findings-schema.json`）
- `plugins/compound-engineering/skills/ce-compound-refresh/SKILL.md`
- `plugins/compound-engineering/agents/ce-learnings-researcher.md`、`ce-correctness-reviewer.md`
- `docs/skills/ce-compound.md`

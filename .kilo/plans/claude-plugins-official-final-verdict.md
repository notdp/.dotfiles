# claude-plugins-official refs 吸收最终裁决

## 背景

用户要求在理解本地机制后，基于新加入的 `refs/anthropics/claude-plugins-official` 给出最终裁决。本计划只做裁决与实施方案，不进入实现。

## Think Map

### 仓库定位

- [事实] `agents/harness-ops.md:28-37` 明确本 skill 体系设计为可在 kilo / opencode / Claude Code / droid / codex 等多种 coding agent 中使用。
- [事实] `agents/harness-ops.md:3-10` 明确分层：`AGENTS.md` 放全局硬约束，commands 放高频 inner-loop，skills 放领域能力 / 流程方法 / 专项约束，docs 放调研沉淀 / refs 分析 / 背景材料，能靠脚本 / hook / 测试强制的规则不要只写自然语言提醒。
- [事实] `docs/software-engineering-research/refs-absorption-methodology.md:3` 明确 refs 是证据源，不是待复制代码库；目标是让 agent 架构更稳定、更可验证，而不是扩大 skill 数量。

裁决含义：新 refs 只能作为跨 agent harness 参考源吸收，不能把仓库收窄为 Kilo 或 Claude Code 插件目录。

### 本地机制

| 机制 | 事实 | 证据 |
|---|---|---|
| Skill catalog | 已有 `coding-skills/catalog.json`，记录 name / path / domain / role / migration | `coding-skills/catalog.json:1-311` |
| Skill verifier | 已校验 catalog、frontmatter、trigger prefix、workflow quality、methodology why、broken refs、高风险能力 warning、模糊条件 warning 等 | `scripts/verify_skills.py:12-20`, `scripts/verify_skills.py:585-609` |
| Agent verifier | 已校验 `coding-agents/claude` 与 `coding-agents/opencode` 双 runtime，含工具白名单、permission 三态、只读角色权限 | `scripts/verify_agents.py:1-15`, `scripts/verify_agents.py:198-201` |
| Agent assets 分发 | 已把 commands / skills / AGENTS 链接到 Claude / Codex / Factory / OpenCode / Kilo | `scripts/install_hooks.py:653-674` |
| Agent assets 测试 | 已有跨 target symlink 测试和 `--yes` 保护 | `scripts/tests/test_install_hooks.py:676-719` |
| Skill maintenance collector | 已采集 preflight、inventory、refs、sessions、hook signals、deterministic findings、verify 输出 | `scripts/skill_maintenance_collect.py:44-79`, `scripts/skill_maintenance_collect.py:161-246` |
| Review skill | 已有 diff scope、hard stops、two-pass review、confidence calibration、drift signals | `coding-skills/guard-review/SKILL.md:31-185` |
| 大任务机制 | 已有 large delivery phase gate 与 operational contract | `coding-skills/dev-large-delivery/SKILL.md:22-68`, `coding-skills/dev-operational-task/SKILL.md:20-98` |
| 结构质量机制 | 已有 PIEV + Boundary/Locality/Convention/Explicitness/Testability/Diff Purity | `coding-skills/think-quality/SKILL.md:30-83` |

### 新 refs 信号

- [事实] `docs/refs-details/anthropics/claude-plugins-official.md:21-30` 记录本地快照：222 marketplace entries、36 internal plugins、15 external plugins、38 plugin.json、28 commands、24 agents、28 skills、16 `.mcp.json`。
- [事实] `docs/refs-details/anthropics/claude-plugins-official.md:34-50` 把最重要结构归纳为 marketplace registry、plugin structure、internal vs external boundary。
- [事实] `docs/refs-details/anthropics/claude-plugins-official.md:52-63` 记录候选吸收模式：asset registry + manifest 校验、PR review 专科化、类型 / invariant 评分卡、大型迁移 preflight gate、Business Rule Card、Hookify、Session report、FE aesthetic direction。
- [事实] `docs/refs-details/anthropics/claude-plugins-official.md:103-112` 记录主要风险：单 runtime 路径冲突、平行 workflow 冲突、MCP / 外部服务副作用、后台模型审查风险、review 误报放大、FE 创作过度。

### 技术栈 / 架构

- 主要实现语言：Python + Shell + Markdown。
- 核心资产：`agents/`、`commands/`、`coding-skills/`、`coding-agents/`、`scripts/`、`docs/refs-details/`、`refs/`。
- 验证入口：`bash scripts/run-verify.sh /Users/zhenninglang/.dotfiles`。
- 当前架构倾向：文档定义语义，Python verifier / tests / hooks 把可机械化部分下沉为门禁。

## Final Verdict

### 总裁决

吸收 `anthropics/claude-plugins-official` 的方式应是：增强本仓库已有跨 agent harness 的 catalog / verifier / review / preflight 机制，而不是引入 Claude Code plugin marketplace runtime，也不是安装或启用其插件。

### 立即吸收

1. 扩展现有 asset registry / verifier。
2. 增强 `guard-review` 为按 aspect 路由的 review router。

### 延后吸收

1. 大任务 preflight contract。
2. Business Rule Card。
3. Session 成本 / cache 报告。

### 暂不吸收

1. 直接安装 / 启用 `claude-plugins-official` 插件。
2. 新建完整 plugin marketplace / daemon / runtime。
3. 新建平行 `/review-pr` 或 `/feature-dev` 工作流。
4. 默认启用 external plugins 的 MCP / channel / external service 能力。
5. 自动把 Hookify 候选变成 block rule。

## Decision Matrix

| 候选项 | 裁决 | ROI | 投入 | 风险 | 理由 |
|---|---|---:|---:|---|---|
| Asset registry + verifier 扩展 | implement now | 最高 | M | 低 | 本地已有 catalog / verifier / collector，可小步扩展；收益覆盖所有后续 harness 维护 |
| `guard-review` aspect router | implement now | 最高 | M | 中 | 本地 review 已强，但仍是大 checklist；专科化能提升命中率并减少噪音 |
| 大任务 preflight contract | plan next | 高 | M | 低中 | 与现有 large-delivery / operational-task 同向，但不是当前最高瓶颈 |
| Business Rule Card | plan next | 高 | M | 中 | 对业务逻辑任务价值高，但需要先设计 confidence / secret masking / SME question 约束 |
| 审批型 harness rule generator | observe | 中高 | L | 中高 | 有复利价值，但自动规则过拟合风险高；先 proposal-only |
| Session 成本 / cache 报告 | observe | 中 | M | 低中 | 适合运营优化，但当前不是最高 ROI |
| FE aesthetic direction | reject for now | 低中 | S | 低 | 可作为 `fe-ui-design` 微调，不值得本轮单列 |
| 安装官方插件 | reject | 负 | ? | 高 | 单 runtime、MCP、secrets、外部服务、副作用边界均不匹配 |

## Implementation Plan

### Phase 1: Asset Registry / Verifier 扩展

目标：不新建 marketplace；扩展现有 catalog / verifier，让跨 agent assets 更可盘点、可校验、可维护。

建议改动：

- 扩展 `scripts/skill_maintenance_collect.py` 的 `inventory()`，把 `coding-agents`、`commands`、hook scripts、refs detail、`.kilo/agent` 纳入 asset inventory。
- 扩展或新增 verifier 模块，输出统一 asset summary：skills、commands、agents、hooks、refs detail、distribution links。
- 为 asset 增加风险标签 / runtime compatibility 检查，但第一版只做 deterministic warnings，不做强制失败。
- 添加脚本测试，覆盖：缺路径、重复 asset、runtime path 混用、MCP / hook / external service 缺风险标签。

边界：

- 不改 symlink 分发逻辑，除非测试暴露真实缺陷。
- 不把 `.claude-plugin/marketplace.json` 结构原样搬入本仓库。
- 不把 refs submodule 内容纳入 runtime catalog。

验收：

- `python3 scripts/verify_skills.py` 仍通过。
- `python3 scripts/verify_agents.py` 仍通过。
- `python3 -m unittest discover -s scripts/tests -p "test_*.py"` 通过。
- `bash scripts/run-verify.sh /Users/zhenninglang/.dotfiles` 通过。
- Collector 输出能看到 agents / commands / hooks / refs detail 的 asset inventory。

### Phase 2: `guard-review` Aspect Router

目标：在不新增平行 `/review-pr` 的情况下，把 review 拆成可路由专项。

建议改动：

- 在 `coding-skills/guard-review/SKILL.md` 中增加 Aspect Routing：`code`、`tests`、`errors`、`types`、`comments`、`simplify`。
- 定义每个 aspect 的触发条件：
  - `errors`: catch、fallback、retry、timeout、logging、silent failure、external calls。
  - `types`: 新增或修改 schema、domain model、API envelope、state machine、permission model。
  - `tests`: 新增行为、bug fix、测试文件变化、验证缺口。
  - `comments`: 新增注释 / docs 与代码事实可能漂移。
  - `simplify`: blocker 修完后，作为非阻塞 cleanup。
- 保留现有 severity evidence gate：无明确失败路径、触发条件、影响范围，不能升 Critical / Important。
- 增加 output 中的 Aspect Coverage 表，说明哪些 aspect 被触发、哪些被跳过、证据是什么。

边界：

- 不新增 `/review-pr`。
- 不直接复制上游 agent prompt。
- 不让 `simplify` 抢在 correctness / security blocker 前运行。
- 不把所有 diff 都全量跑所有 aspect。

验收：

- 对含 catch/fallback 的 diff，review plan 明确触发 `errors`。
- 对新增 schema / type 的 diff，review plan 明确触发 `types`。
- 对纯文档 diff，review plan 不触发无关 code/type checks。
- 输出仍保留 `Ready to merge?` 裁决。

### Phase 3: Preflight Contract

目标：把 `claude-plugins-official` 中 modernization preflight 的“完整 readiness report”吸收到现有 large-delivery / operational-task，而不是新增 modernization workflow。

建议改动：

- 在 `dev-large-delivery` 加 Phase 0 readiness contract。
- 在 `dev-operational-task` 的 contract 中补充 preflight output：Ready / Ready-with-gaps / Not ready。
- 可扩展 `scripts/scan_operational_task_contract.py`，检查 preflight 字段是否存在。

验收：

- 缺 toolchain / dry-run / rollback / data source 时，计划不能进入 apply。
- 输出 single most important fix。

### Phase 4: Business Rule Card

目标：让业务规则从代码证据转成可测试 contract case。

建议改动：

- 在 `think-map` / `think-architecture` / `dev-tdd` 中增加可选 Rule Card 模板。
- Rule Card 字段：Rule、Category、Evidence、Given、When、Then、Parameters、Confidence、SME question、Secret handling。
- 遇到 credential / token / secret 时，只记录 masked category 和 `file:line`。

验收：

- 复杂业务任务能从代码证据输出 Rule Card。
- `dev-tdd` 能把 Rule Card 转成 contract test 输入。

### Phase 5: Observe Backlog

不进入本轮实现，仅保留触发条件：

- Harness rule generator：只有当用户纠正 / 事故复盘 / review finding 重复出现时再做，并且必须 proposal-only + approval。
- Session report：只有当 session 成本、cache break、subagent 滥用成为实际痛点时再做。
- MCP risk matrix：可并入 asset registry 风险标签，不单独造大项。

## Non-goals

- 不更新 refs submodule pointer。
- 不运行联网 fetch / 外部插件安装。
- 不写 `.claude-plugin` marketplace runtime。
- 不修改 `AGENTS.md` 全局硬约束，除非后续实现发现必须新增 L5 规则。
- 不把 Kilo、Claude Code、OpenCode、Codex 任一 runtime 作为唯一目标。

## Risks

| 风险 | 缓解 |
|---|---|
| Asset registry 变成第二套 catalog | 基于现有 `coding-skills/catalog.json`、`verify_agents.py`、`install_hooks.py` 扩展，不另起 SSOT |
| Review aspect 增加误报 | 保留 `guard-review` 现有 evidence gate 和 confidence calibration |
| Runtime 路径混用 | Asset 字段必须显式记录 runtime compatibility / target path |
| 上游插件副作用被误吸收 | 所有 external plugin / MCP / channel access 默认 reject runtime，只作为 refs evidence |
| 计划过大 | 本轮只建议实施 Phase 1 + Phase 2；其余 backlog |

## Recommended Cut

本轮实施只做两项：

1. Asset registry / verifier 扩展。
2. `guard-review` aspect router。

理由：

- [推断] 这两项 ROI 最高，因为它们分别解决“仓库里有什么 / 是否漂移”和“review 如何精准命中”的基础问题。
- [推断] 它们都能落到现有机制，不引入平行 runtime。
- [推断] 它们能为后续 preflight、Rule Card、session report 提供结构化基础。

## Verification Plan

实现后必须运行：

```bash
python3 -m unittest discover -s scripts/tests -p "test_*.py"
python3 scripts/verify_skills.py
python3 scripts/verify_agents.py
bash scripts/run-verify.sh /Users/zhenninglang/.dotfiles
python3 scripts/scan_diff_residue.py
```

Acceptance verifier：

- Phase 1: Collector / verifier 能输出跨 agent asset inventory 和 warning。
- Phase 2: `guard-review` 文档具备 aspect routing、trigger、skip reason、coverage output，并且不复制上游 workflow。

## Final Decision

最终裁决：吸收，不移植；增强现有跨 agent harness，不建立 Claude plugin marketplace；本轮只实施 asset registry / verifier 扩展与 `guard-review` aspect router。
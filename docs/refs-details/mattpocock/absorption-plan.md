# mattpocock/skills 吸收改造计划

Source: `docs/refs-details/mattpocock/skills.md`、`docs/refs-details/mattpocock/skills-strengths-and-absorption-2026-06-04.md`
Date: 2026-06-04

---

## 总体判断

mattpocock/skills 的核心价值不在 skill 数量（14 个公开），而在把 agent 失败模式压缩成可治理的工程问题，并用具体机制约束行为：

1. **极致简洁**——SKILL.md 主体 <100 行，细节全部拆到支撑文件
2. **结构分离**——指令（做什么）和知识（怎么判断）用 XML tag 显式分层
3. **行为编码**——不靠抽象原则，而是用 WRONG/RIGHT 对比、_Avoid_ 词汇表、.out-of-scope 知识库来校准行为
4. **文档即工作流资产**——`CONTEXT.md` 管语言，`docs/adr/` 管承重决策，agent brief 管长期交接，`.out-of-scope/` 管拒绝理由

本仓库已吸收了部分高价值思想（`dev-tdd` 的 vertical slice、`dev-debug` 的反馈环优先、`dev-refactor` 的 deep module 判断）。后续重点不是复制同名 skill，而是把 prompt 结构、词汇治理、持久化交接和 scope 记忆机制放到本仓库现有分层中。

---

## 吸收项总表

### 新增

| 编号 | 新增项 | 落点 | 吸收层级 | 优先级 |
|---|---|---|---|---|
| MP-1 | 指令-知识分离模式 | `skill-patterns.md` 新模式 | L2 | P1 |
| MP-2 | 强制词汇表 + _Avoid_ 列表模板 | `skill-authoring.md` 推荐实践 | L2 | P1 |
| MP-3 | .out-of-scope 知识库模式 | `skill-patterns.md` 新模式 | L2 | P1 |
| MP-4 | Durability over precision（持久产物用行为契约） | `skill-patterns.md` 模式 C 补充 | L2 | P1 |
| MP-5 | Durable Agent Brief 模板 | `think-plan`、`dev-long-task-scaffold`、`dev-long-run-v2` | L4 | P2 |
| MP-6 | `manual-only` 语义 | `coding-skills/catalog.json`、`verify_skills.py`、`skill-authoring.md` | L3/L4 | P3 |
| MP-7 | Issue workflow commands (`/to-prd`、`/to-issues`、`/triage`) | `commands/` | L4 | P4 |

### 改善

| 编号 | 改善项 | 落点 | 吸收层级 | 优先级 |
|---|---|---|---|---|
| MP-8 | Grilling 一次一个问题 + 推荐答案 | `think-refine`、`think-scope` | L4 | P2 |
| MP-9 | Vertical Slice 可视化规则 | `dev-tdd` 支撑参考 | L2 | P1 |
| MP-10 | 领域术语冲突显式化 | `think-scope`、`think-refine`、`think-architecture` | L4 | P2 |
| MP-11 | ADR 触发条件（极简、承重才写） | `think-plan`、`think-architecture` | L4 | P2 |
| MP-12 | Vertical slice 计划语言 | `think-plan`、`dev-long-task-scaffold`、`dev-long-run-v2` | L4 | P2 |
| MP-13 | Good/Bad contract cases 适用规则 | `skill-authoring.md` | L2 | P1 |
| MP-14 | 危险 git 命令测试用例扩充 | `scripts/hooks/` 测试 | L3 | P3 |
| MP-15 | 长 skill progressive disclosure warning | `verify_skills.py` | L3 | P3 |

### 去掉坏影响

| 编号 | 坏影响 | 推荐动作 | 理由 |
|---|---|---|---|
| MP-X1 | 把参考方法塞进 `agents/AGENTS.md` | 不做；只保留极短全局原则 | 当前 AGENTS.md 已承担事实纪律、验证、边界、TDD、gitops，继续膨胀会削弱权威性 |
| MP-X2 | 直接复制 `.claude-plugin/plugin.json` | 不做；保持 `coding-skills/catalog.json` 为 SSOT | 双 registry 会制造漂移 |
| MP-X3 | 直接复制 Claude hook shell 脚本 | 不做；只吸收危险命令列表到 Python hook 测试 | 本仓库已有 `command_guard.py`，复制会产生规则冲突 |
| MP-X4 | 默认 inline 更新 CONTEXT / ADR | 改为"生成候选块，批准后写入" | 与 Surgical Changes 和先 scope 后实现的纪律有张力 |
| MP-X5 | 默认创建 `.out-of-scope/` 文件 | 只在重复出现、已裁决的 enhancement 上写 | 避免把 scope 控制变成新文档噪音 |
| MP-X6 | 吸收 `caveman` 人格 | 不吸收 | 与中文事实纪律、`readable-*` 体系冲突 |

### 明确不吸收

| 模式 | 拒绝理由 |
|---|---|
| 平坦目录结构 | 50+ skill 需要 domain-prefix 与 catalog 治理 |
| `.claude-plugin/plugin.json` 作为注册 SSOT | 已有 `coding-skills/catalog.json` 和 `verify_skills.py` |
| `link-skills.sh` 安装模型 | 面向 Claude Code 单平台，不适配多 agent dotfiles |
| `caveman` 角色人格 | 与中文事实纪律、验证证据、风险表达冲突 |
| HTML artifact 作为默认输出 | 已有 `readable-html-artifact` 覆盖 |
| 默认 inline 改文档 | 与 Surgical Changes 有张力，应改为候选块 + 批准后写入 |
| 直接复制 shell git hook | 已有 Python command guard，复制会造成双重规则 |

---

## 详细改造项

### MP-1: 指令-知识分离模式

**What**: 在 `skill-patterns.md` 新增模式，记录 `<what-to-do>` / `<supporting-info>` 两层结构。

**Why**: 当前 skill 正文常把"做什么"和"用什么标准判断"混在一起，agent 在执行时难以区分优先级。mattpocock 的 XML tag 分离是低成本高收益的结构化手段。

**How**:
- 在 `skill-patterns.md` 新增"模式 M: 指令-知识分离"
- 给出最小样例和适用场景（长 skill、指令和判断标准混杂的 skill）
- 来源：`mattpocock/skills` 的 `grill-with-docs`、`writing-beats`

**Impact**: `skill-patterns.md` 新增约 40 行

### MP-2: 强制词汇表 + _Avoid_ 列表模板

**What**: 在 `skill-authoring.md` §4 结构模板部分新增推荐实践。

**Why**: 本仓库 50+ skill 之间术语不统一（"验收"/"验证"/"verify"/"acceptance" 混用）。_Avoid_ 列表比单纯定义更有效——它告诉 agent "不要用什么替换词"，降低术语漂移。

**How**:
- 新增推荐实践："知识密集型 skill 可附 LANGUAGE.md 或词汇表节，每个核心术语配 _Avoid_ 列表"
- 模板包含：定义、_Avoid_ 列表、冲突处理、例句
- 不新增硬约束（不改 verify_skills.py）
- 来源：`mattpocock/skills` 的 `improve-codebase-architecture/LANGUAGE.md`

**Impact**: `skill-authoring.md` 新增约 20 行

### MP-3: .out-of-scope 知识库模式

**What**: 在 `skill-patterns.md` 新增模式。

**Why**: 本仓库有 `/guard-close` 做 scope 裁决，但缺少 project 层面"为什么不做这件事"的持久化机制。`.out-of-scope/` 目录 + triage 时自动检查，是低成本的 scope creep 防线——不只是说"不做"，而是把"为什么不做"写下来，避免同一个讨论反复发生。

**How**:
- 按 concept 记录 rejected enhancement，不按 issue 记录
- 限制：只记录重复出现、已裁决的 enhancement；不用于 bug
- 不强制所有项目采用
- 来源：`mattpocock/skills` 的 `.out-of-scope/` + `triage` 自动检查

**Impact**: `skill-patterns.md` 新增约 30 行

### MP-4: Durability over precision

**What**: 在 `skill-patterns.md` 模式 C（固定输出表格）中区分短期产物和持久化产物的写法。

**Why**: 短期 review finding 用 `file:line` 是对的；但长期 issue/brief/PRD 中的路径和行号会快速腐烂。mattpocock 的 `triage/AGENT-BRIEF.md` 用行为契约替代易腐路径。

**How**:
- 短期产物（review finding、verify 结果）保留 `file:line`
- 持久化产物（issue、PRD、agent brief、long task scaffold）优先写 current behavior、desired behavior、key interfaces、acceptance criteria、out of scope
- 来源：`mattpocock/skills` 的 `triage/AGENT-BRIEF.md`

**Impact**: `skill-patterns.md` 现有模式 C 下新增约 15 行

### MP-5: Durable Agent Brief 模板

**What**: 在 `think-plan`、`dev-long-task-scaffold`、`dev-long-run-v2` 中引入长期交接产物模板。

**Why**: 长期交接文档如果引用大量 file path 和 line number，后续很快过期。agent brief 应该成为合同，不是实现指南。

**How**:
- 模板字段：current behavior、desired behavior、key interfaces、acceptance criteria、out of scope
- 少写实现步骤和易腐路径
- 来源：`mattpocock/skills` 的 `triage/AGENT-BRIEF.md`

### MP-6: `manual-only` 语义

**What**: 在 `coding-skills/catalog.json` schema 中新增可选字段 `manual-only: true`。

**Why**: 某些 skill（反思类、危险操作准备类）不应被 agent 自动调用。mattpocock 的 `disable-model-invocation: true` 解决这个问题。本仓库的 `trigger-exempt` 只免除触发前缀校验，不控制运行时行为。

**How**:
- `catalog.json` 新增可选字段
- `skill-authoring.md` 新增一段说明何时使用
- `verify_skills.py` 可选校验

**Boundary facts**:
- Risk types: context-surface | schema-contract
- Callers: verify_skills.py, skill routing
- User approval: 需要确认——是否采用这个字段名，以及是否和 trigger-exempt 合并

### MP-7: Issue workflow commands

**What**: 新增 `/to-prd`、`/to-issues`、`/triage` 动词型 command。

**Why**: PRD/issue/triage 是高频工作流，且 mattpocock 的 vertical slice 拆分 + durable brief + .out-of-scope 检查组合在这个场景特别有效。

**How**:
- 默认 dry-run，只生成 markdown
- 触碰 GitHub/GitLab/Linear 前走 `guard-gitops`
- 输出以 vertical slice、durable brief、out-of-scope 为核心

**Boundary facts**:
- Risk types: operational-side-effect
- User approval: 远程创建前必须确认

### MP-8: Grilling 模式改善

**What**: 在 `think-refine`、`think-scope` 中加入三条核心约束。

**Why**: 当前 `think-refine` 会一次倒出多个问题，用户认知负担大。mattpocock 的 grilling 模式三条约束：
1. 每次只问一个问题
2. 每个问题附 agent 推荐答案（用户只需 confirm/redirect）
3. 能读代码回答的就不问用户

**Boundary facts**:
- Risk types: context-surface
- Callers: 用户手动调用，或 think-plan 前置路由

### MP-9: Vertical Slice 可视化规则

**What**: 在 `dev-tdd` 支撑参考中补充 WRONG/RIGHT ASCII 对比图。

**Why**: `dev-tdd` 已有 Red-Green-Refactor 循环但缺 vertical slice 显式规则。一张 ASCII 图比一段文字更能防止退化为 horizontal 模式。

**How**: 引用 mattpocock 的 ASCII 对比图 + vertical-slice-rules

### MP-10: 领域术语冲突显式化

**What**: 在 `think-scope`、`think-refine`、`think-architecture` 中，发现用户术语、代码术语、文档术语冲突时列为待决策。

**Why**: 术语静默错位会导致长期 token 浪费和沟通成本。

**How**: 输出 flagged ambiguity；需要时建议写入 CONTEXT 类文档（候选块，批准后写入）

### MP-11: ADR 触发条件

**What**: 在 `think-plan`、`think-architecture` 中加入极简 ADR 触发条件。

**Why**: ADR 如果变成模板填空会提高维护成本。mattpocock 把触发条件压得很窄：hard to reverse + surprising without context + real trade-off 三条同时成立才建议。ADR 可以只有 1-3 句。

### MP-12: Vertical slice 计划语言

**What**: 在 `think-plan`、`dev-long-task-scaffold`、`dev-long-run-v2` 中，phase/issue 拆分采用 vertical slice 语言。

**Why**: 按 UI/schema/API 水平拆的 phase 无法独立验证，增加交付风险。

**How**: 每个 phase 有可观察验收，窄但完整地穿过所有集成层

### MP-13: Good/Bad contract cases 适用规则

**What**: 在 `skill-authoring.md` 中补充"高风险规则配正反 contract cases + 恢复路径"的推荐实践。

**Why**: 抽象规则容易被模型泛化错。本仓库 `skill-patterns.md` 已有模式 J (Wrong / Should Happen)，但 `skill-authoring.md` 缺少"什么时候用"的适用规则。

### MP-14: 危险 git 命令测试用例

**What**: 扩充 `scripts/hooks/` 相关测试，加入参考项目列出的危险 git 命令样例。

**How**: 复核 `git branch -D`、`git checkout .`、`git restore .`、`git clean -fd` 等用例是否已覆盖

### MP-15: 长 skill progressive disclosure warning

**What**: `verify_skills.py` 对超过阈值行数的 skill 输出 warning（非硬失败）。

**Why**: mattpocock 的 <100 行标杆有道理，但本仓库的长 skill 有领域知识密度原因。warning 而非阻断，让大改时自然评估拆分可能。

---

## 按资产汇总

### `agents/AGENTS.md`

总体裁决：不做大改。可选微调 2 条短规则：
- 长期交接产物优先写行为契约和验收标准；短期 review finding 才用精确 `file:line`
- 发现用户术语、代码术语、文档术语冲突时，列为待决策，不静默替换

### `coding-skills/`

优先改善现有 skill，不新增同名 skill：

| 目标 skill | 改造 | 编号 | 优先级 |
|---|---|---|---|
| `think-refine` | 一次一个问题、每题给推荐答案、能读代码就不问用户 | MP-8 | P2 |
| `think-scope` | 术语冲突显式化 + grilling 约束 | MP-8, MP-10 | P2 |
| `think-plan` | vertical slice phase + durable brief 模板 + 极简 ADR 触发 | MP-5, MP-11, MP-12 | P2 |
| `think-architecture` | 极简 ADR 触发条件 + 术语冲突检查 | MP-10, MP-11 | P2 |
| `think-quality` | 补充 deep module 语言：deletion test、locality、leverage | 来自已有文档分析 | P2 |
| `dev-tdd` | 补 vertical slice ASCII 对比图 | MP-9 | P1 |
| `dev-long-task-scaffold` | 输出 durable agent brief，避免易腐 line number | MP-5 | P2 |
| `guard-close` | 支持可选 out-of-scope 记录建议（不默认写文件） | MP-3 | P2 |

### `commands/`

| Command | 作用 | 副作用边界 | 优先级 |
|---|---|---|---|
| `/to-prd` | 把当前上下文整理成 PRD | 默认只生成 markdown；发布 issue 前走 `guard-gitops` | P4 |
| `/to-issues` | 把已批准 plan 拆成 vertical slice issues | 默认 dry-run；远程创建前确认 | P4 |
| `/triage` | 对 issue 做状态机判断 | 默认输出建议；改 label/comment/close 前确认 | P4 |
| `/zoom-out` | 手动请求更高层上下文说明 | manual-only，不自动触发 | P4 |

### `scripts/hooks/` 与验证脚本

| 资产 | 改造 | 编号 | 优先级 |
|---|---|---|---|
| `verify_skills.py` | 可选支持 `manual-only` 字段校验 | MP-6 | P3 |
| `verify_skills.py` | 对长 skill 输出 progressive disclosure warning | MP-15 | P3 |
| hooks 测试 | 加入危险 git 命令样例 | MP-14 | P3 |

### `docs/software-engineering-research/`

| 文件 | 改造 | 编号 | 优先级 |
|---|---|---|---|
| `skill-patterns.md` | 新增模式 M (指令-知识分离)、模式 N (.out-of-scope)、模式 C 补充 (durability) | MP-1, MP-3, MP-4 | P1 |
| `skill-authoring.md` | 新增词汇表模板推荐、Good/Bad contract cases 适用规则 | MP-2, MP-13 | P1 |

---

## 分阶段执行路线

### Phase 1: 文档层吸收（不改运行时）

目标：把可复用模式写清楚，避免直接改 skill 造成 prompt surface 变化。

产物：
- `skill-patterns.md` 新增 3 个模式 + 模式 C 补充
- `skill-authoring.md` 新增词汇表推荐 + contract cases 适用规则
- `dev-tdd` 补 vertical slice ASCII 对比图

涉及编号：MP-1, MP-2, MP-3, MP-4, MP-9, MP-13

验收：
- `python3 scripts/verify_skills.py` 通过
- 文档中明确"不默认创建 CONTEXT/ADR/out-of-scope"

### Phase 2: 低风险 skill 改善

目标：改善需求澄清、计划拆分和长期交接。

产物：
- `think-refine` 加入 grilling 三条核心约束
- `think-scope` 加入术语冲突显式化
- `think-plan` 加入 vertical slice phase + durable brief 模板 + 极简 ADR 触发
- `think-architecture` 加入极简 ADR 触发 + 术语冲突检查
- `think-quality` 补充 deep module 语言
- `dev-long-task-scaffold` 输出 durable brief
- `guard-close` 增加 out-of-scope 候选记录（不默认写文件）

涉及编号：MP-5, MP-8, MP-10, MP-11, MP-12

验收：
- `python3 scripts/verify_skills.py` 通过
- 用 2-3 个模拟任务检查：小修复不会被过度追问，大任务会形成更清晰的 scope 和验收标准

### Phase 3: schema 与 hook 层

目标：把能机器检查的规则下沉。

产物：
- 设计 `manual-only` 字段是否进入 `coding-skills/catalog.json`
- 若批准，更新 `verify_skills.py` 和相关测试
- 扩充 command guard 危险 git 命令测试用例
- 长 skill progressive disclosure warning

涉及编号：MP-6, MP-14, MP-15

验收：
- `python3 -m unittest discover -s scripts/tests -p "test_*.py"` 通过
- `python3 scripts/verify_skills.py` 通过

### Phase 4: issue workflow 命令

目标：把 PRD、issue、triage 做成用户显式触发的 command。

产物：
- `/to-prd` dry-run command
- `/to-issues` dry-run command
- `/triage` recommendation command
- 可选 `/zoom-out` manual-only command

涉及编号：MP-7

验收：
- 默认不触碰远程 issue tracker
- 远程写入前必须进入 `guard-gitops`
- 输出以 vertical slice、durable brief、out-of-scope 为核心

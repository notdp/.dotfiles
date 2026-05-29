# Skill Authoring Guide

本文档规定本仓库 `skills/*/SKILL.md` 的编写约束。违反触发语义硬约束的 skill 无法通过 `scripts/verify_skills.py`。

其它推荐项（结构模板、输入输出格式）放在本文档后续节（由 PR2 补充）和 `skill-patterns.md`。

---

## 0. Harness Engineering 分层原则

Skill 的价值不是把 agent 训练成脚本执行器，而是把某类任务的判断力、边界和验收标准外化出来。

| 层 | 放什么 | 不放什么 |
|---|---|---|
| `agents/AGENTS.md` | 身份、长期偏好、事实纪律、所有任务都成立的红线 | 高频流程细节、领域长清单、具体命令顺序 |
| `skills/` | 任务契约、触发场景、输出形态、证据门、停止/升级条件 | 固定到某个项目路径或某个旧工具链的机械步骤 |
| `refs/` / `docs/` | 长清单、审美细则、背景调研、可追溯参考 | 每次触发都必须读完的主流程 |
| `scripts/` / CI / hook | 可确定性检查的硬门：lint、测试、扫描、预检 | 需要模型判断的审美、架构和 trade-off |
| MCP / tools | 真实系统、数据和外部状态访问 | 可直接写在仓库内的规则说明 |

### Skill / Command 边界

借鉴 `refs/Owl-Listener/designer-skills` 的分层：**skill 是名词型知识单元，command 是动词型工作流**。

| 类型 | 放什么 | 不放什么 |
|---|---|---|
| Skill | 领域知识、判断标准、风险信号、验收证据、输出格式 | 高频命令入口、一次性任务清单、跨多个领域的编排脚本 |
| Command | 串联多个 skill 的高频 workflow、参数入口、执行顺序、收口提示 | 大段领域知识正文、复制多个 skill 的规则、长期背景材料 |

Command 可以引用多个 skill；本仓库不采用“禁止跨插件引用”的硬规则。是否跨域编排由任务风险、复用性和可 review 性决定。

### 好 skill / 坏 skill

| 好 skill | 坏 skill |
|---|---|
| 说明这类任务要交付什么、什么证据算数 | 规定不看上下文也照做的固定路径 |
| 定义风险信号、停止条件、升级路径 | 把历史经验写成“永远先 A 再 B 再 C” |
| 给出结构化输出，让 review 和验证可扫描 | 把长篇产品手册或工具文档复制进正文 |
| 把可自动化部分下沉给脚本/CI | 依赖模型自觉执行可脚本化检查 |

### 外部吸收的编写原则（shaping-skills / compound-engineering）

参考：`docs/refs-details/rjs/shaping-skills.md`、`docs/refs-details/EveryInc/compound-engineering-plugin.md`。以下是从两个 ref 提炼、广泛适用且不改 runtime 的编写原则（保守吸收，L2）：

- **按失败模式校准约束强度**（compound）：deterministic safety（数据、远程、不可逆）写 hard rule；judgment call 写 strong guidance + 一对 good/bad 例子；其余给 trust，不要过度规定。判据：能否说出这条规则防止的具体坏结果；说不出就别写成硬规则。
- **区分 runtime 与 authoring context**（compound）：治理 skill **运行时行为**的规则必须写进 `SKILL.md`（每次触发都加载），不能只写在编写期才读的文档里；rationale 只在"会改变运行时行为"时才进 SKILL.md，否则进 commit message / docs，避免每次加载的正文膨胀。
- **结构化产物以表/schema 为唯一事实源**（shaping）：复杂产物（依赖表、状态机、规则表、流程草图）让表/schema 当 SSOT，图和散文是派生视图；改动先改 SSOT 再改派生，禁止只在派生视图里加未登记内容。
- **二元判定 + 显式 unknown**（shaping）：高风险判定用二元（满足/不满足），把"知道 what 不知道 how"显式标为未完成而非乐观标过，与 Truth Directive 的 `[推断]/[未验证]` 同源；不确定项必须挂后续动作（spike / 验证）。

工作流型 skill 新增或大改时，正文必须至少包含以下一类质量门：

- Evidence / 验证 / 验收：什么证据能支持结论或交付
- Stop / 退出 / 停止：什么时候可以停，什么时候必须继续
- Risk / Gotchas / 禁止：什么风险出现时要升级或阻断

原则：可以规定流程纪律和验收标准，不要微操具体操作路径。

### Prompt pressure 与诚实失败路径

参考：`docs/software-engineering-research/prompt-pressure-risk.md`。

工作流型 skill 可以有严格门禁，但每个强约束都必须配一个诚实失败路径，避免把 agent 压成“必须成功”的单一路径。

写作检查：

- 写 `必须`、`不允许`、`直到通过`、`cannot`、`must` 时，是否同时定义了 `blocked`、`partial`、`verification: none`、AskUser 澄清或结构化退出？
- 如果任务目标、测试、权限或输入矛盾，skill 是否允许报告矛盾和证据，而不是绕过约束？
- 如果提到 forbidden behavior，是否在同段给出安全替代动作？
- 验证证据是否尽量来自工具输出、文件、截图、日志、git diff 或结构化 artifact，而不是 assistant 自述？
- 用户-only 信息、授权缺口、缺少凭据、外部副作用和不可逆动作是否被视为合法 stop / escalate 条件？

### 条件边界控制（高风险）

参考：`docs/software-engineering-research/conditional-control-risk.md`。免责声明、否定句、触发词、"以下只是反例"这类高层限定，模型不一定稳定学会限定条件；高风险行为只靠一句限定来隔离并不可靠。

写作规则（仅针对高风险条件边界：危险动作、反例、例外路径、"只有 X 时才做"）：

- 把条件边界写成正反 contract cases：同时给"满足条件 + 允许行为"和"不满足条件 + 拒绝行为"，不要只展示被限定的行为本身。
- 限定词靠近被限定的动作（`仅在 <condition> 成立时执行 <action>`），不要只放段首或文档开头。
- 必须提到 forbidden behavior 时，同段给替代动作（与上一节诚实失败路径一致）。
- 高风险行为不能只靠模型自控；保留模型外的检测、权限门、验证或回滚（可下沉到 hook / 脚本 / 测试）。

过度外推警告：这条不等于"否定句无用"。更窄的结论是：限定信息需要正反样本、局部限定和模型外验证共同支撑，而不是单靠一句免责声明。

### 正向规则与稳定语气

负向指令会提高被禁止行为的显著性。新增或大改 skill 时，优先把风格、流程和输出格式约束写成正向替代动作；只有安全、数据、远程副作用、事实声明等 hard stop 才保留明确禁止。

写作规则：

- 用 `Use / Prefer / Check / Proceed only when / If missing, report ...` 描述目标行为、证据门和 fallback。
- 提到 forbidden behavior 时，同段给出替代动作，例如：`缺截图时，报告 partial 并补 Capture`。
- 避免连续堆叠 `不要 / 禁止 / 不允许 / DON'T / NEVER`；把长反例清单改成质量门、状态机或检查表。
- 避免 ALL CAPS、训斥、嘲讽或情绪化评价；用可观察质量问题替代“偷懒、俗气、廉价”这类词。
- 保留 hard stop 时写清触发条件、阻断状态和恢复路径，而不是只写禁止句。

改写示例：

| 原写法 | 推荐写法 |
|---|---|
| `不要啰嗦` | `用 5 个 bullet，每个不超过 20 字` |
| `不要像营销文案` | `用朴素、具体、像工程复盘的语气` |
| `没有截图不准交付` | `UI verified 需要截图、overflow 和交互状态证据；缺证据时状态为 partial` |
| `DON'T: 默认暗色 + 发光` | `暗色和发光需要服务阅读、氛围或状态表达，并给出设计依据` |

---

## 1. frontmatter 触发语义（硬约束）

### 1.1 规范

frontmatter 的 `description` 字段必须分两段，以触发词开头：

```
<触发词> <场景描述段>；<能力描述段>
```

三个组成部分的职责：

| 组成 | 写什么 | 不写什么 |
|---|---|---|
| 触发词 | 固定前缀（见 1.2），让 agent 能做路由决策 | 自由措辞 |
| 场景描述段 | 代码状态、任务性质、情境特征 | "用户是否明示请求"、"用户要求 X" |
| 能力描述段 | skill 做什么、输出什么 | 详细操作步骤（放 SKILL.md 正文） |

**分段符号**：中文场景用 `；`，英文场景用 `.` 或 `;`。

### 1.2 允许的触发词（四选一）

```
Use when ...
Invoke when ...
用于 ... 时
当 ... 时使用
```

`scripts/verify_skills.py` 校验 `description` 以上述 4 种前缀之一开头（允许前导空白）。

**不接受**的写法：

- `<skill 名>。<描述>`（如 `代码重构。支持分支比较...`）
- `<能力描述>。<触发条件>`（触发条件放后面）
- `Run after ...`（不在白名单）
- `After <某事件>, use ...`（不在白名单）

### 1.3 场景化 vs 用户行为化（关键硬约束）

`description` 描述**何时该被调用的客观场景**，不描述**"用户是否明示请求"**。

这一条是硬约束，因为：

- "用户要求 X 时使用" 会让 agent 把自主判断让渡给用户的显式措辞
- agent 在日常工作中应能基于代码状态、任务性质**自主决定**是否调用 skill
- 能让 skill 在 `commands/*.md` 路由、agent 隐式选择、用户显式触发三种场景下一致生效

#### 正反对比

| ❌ 用户行为化 | ✅ 场景化 |
|---|---|
| `用户要求重构、简化、清理重复时使用` | `当代码出现重复、结构债、可读性下降或需要调整模块边界时使用` |
| `用户要求 review、审查代码变更时使用` | `当存在未 review 的代码变更或需要在合并前把关时使用` |
| `用户要求提交、发布时使用` | `当改动已完成、需要创建 PR 或推送到远端时使用` |
| `用户要求技术选型时使用` | `当实现前需要技术选型、方案对比或可行性评估时使用` |
| `用户要求了解项目结构时使用` | `当接手陌生仓库、需要分析代码结构或梳理依赖关系时使用` |
| `用户要求安全审查时使用` | `当改动触及认证、授权、数据处理或外部依赖边界时使用` |

#### 允许保留"用户触发"的例外

只有当触发**本质上**依赖用户主观判断（而不是客观代码状态）时，可以在能力描述段提到"用户可触发"，但**触发词段仍必须是场景**：

```
✅ 当对话进展停滞、agent 路径漂移或需要结构化排查时使用；也接受用户手动触发。
```

### 1.4 豁免机制（trigger-exempt）

当一条 skill **改写后会丢失原 description 携带的关键语义**（如时序感、外部依赖契约、原 prompt 触发词法），允许在 `skills/catalog.json` 中标注豁免：

```json
{
  "name": "react-doctor",
  "path": "skills/react-doctor",
  "domain": "ui",
  "role": "brand-exception",
  "trigger-exempt": true
}
```

豁免规则：

- `trigger-exempt: true` 时，`verify_skills.py` 跳过对该 skill 的触发前缀校验
- 仅用于改写会丢失原信息的真实情况，不是逃避规范的口子
- 必须在 `commit message` 或仓库说明里写清豁免理由
- `role: brand-exception` 的外挂 skill（如 `agent-browser`、`hive`）默认豁免（无需显式标 `trigger-exempt`）

当前已知豁免案例：

| skill | 理由 |
|---|---|
| `agent-browser` | 外挂 brand-exception，由上游维护 |
| `hive` | 外挂 brand-exception，由上游维护 |
| `react-doctor` | 原 `Run after making React changes ...` 的"after"时序感无法用 4 种触发词无损表达 |

### 1.4 能力描述段约束

- 压缩到一行内，不展开步骤
- 可以标注"与 X skill 的边界"，但必须放能力描述段，不放触发段
- 例：`当改动涉及多文件或影响面不明时使用；改动前画文件地图 + 风险 checklist（与 think-map 的区别是它聚焦仓库全局，本 skill 聚焦单次任务）`

---

## 2. 检查清单（提交前自检）

- [ ] description 以 4 种触发前缀之一开头
- [ ] 触发段描述"场景/代码状态/任务性质"，不含"用户要求 X"
- [ ] 有 `；` 或 `.` 分隔触发段和能力段
- [ ] 能力段压缩成一行，不展开步骤
- [ ] 与其它 skill 有职责边界时已在能力段标注
- [ ] 负向规则已改成正向替代动作、证据门或 fallback；hard stop 已写清恢复路径
- [ ] 语气稳定，未使用 ALL CAPS、训斥或情绪化评价来承载规则
- [ ] `python3 scripts/verify_skills.py` 通过

---

## 3. 自动校验

`scripts/verify_skills.py` 在启动时读取每个 skill，执行以下低误报检查：

- catalog、name/path/domain/role/frontmatter 一致
- `description` 触发前缀合规
- `refs/`、`scripts/` 等引用存在
- 仓库根 `scripts/*.sh` / `scripts/*.py` 带执行位
- 长工作流型 skill 有 Evidence / Stop / Risk / Gotchas 等质量门标题
- `description` 或正文中写“与 X 区别”时，X 必须是 catalog 中存在的 skill

触发前缀不合规时：

```
DESCRIPTION TRIGGER PREFIX VIOLATION: <skill-name> description must start with one of:
  - Use when ...
  - Invoke when ...
  - 用于 ... 时
  - 当 ... 时使用
got: "..."
```

校验规则不检查场景化 vs 用户行为化（这部分由人工 review 把关），也不判断正文质量是否“足够好”；脚本只拦截明显结构缺口。

---

## 4. SKILL.md 结构模板（推荐，不强制）

本仓库的 skill 按规模大致分三类骨架。**这是推荐，不是硬约束**——现有 skill 保持现状，只在新增或大改时参考。

### 4.1 动作型骨架（20-60 行）

单一任务、步骤清晰、可在一次 agent 调用内完成。

```markdown
---
name: <skill-name>
description: 当 ... 时使用；<能力摘要>。
---

## Role

简短角色声明（1-3 句）。

## Task

1. 第一步
2. 第二步
3. ...
```

样例：`review-and-refactor`（awesome-copilot，15 行）、`create-readme`（awesome-copilot，21 行）。

### 4.2 工作流型骨架（60-200 行）

方法论型 skill，含核心循环、判断启发式、禁止项、扩展阅读、关联技能。

```markdown
---
name: <skill-name>
description: 当 ... 时使用；<能力摘要>。
---

# <Skill 标题>

## 核心循环
...

## 判断启发式
| 场景 | 走哪条 |

## Evidence / Stop / Risk
...

## 跳过条件
...

## Gotchas
...

## 关联技能
...
```

样例：本仓库 `dev-tdd`、`dev-debug`、`guard-check`。

### 4.3 领域分册型骨架（80-200 行入口 + refs/scripts）

适用于科学计算、设计系统、合规、安全、数据平台等知识密度高、引用资料多、示例代码多的领域能力。参考 `refs/K-Dense-AI/scientific-agent-skills` 的 `SKILL.md + references + scripts` 结构。

原则：

- `SKILL.md` 只放触发条件、能力边界、核心工作流、风险门、验证方式。
- 长 API 文档、库用法、分类清单、标准条文放 `refs/` 或 skill-local `references/`。
- 可确定性检查、转换、扫描、生成放 `scripts/`，并在正文中只引用入口和预期证据。
- 涉及 network、secrets、外部 API、医疗/临床、数据库写入或运行时副作用时，必须写 Risk / Evidence / Guardrails，不得只写使用教程。

```markdown
---
name: <skill-name>
description: 当 ... 时使用；<能力摘要>。
---

# <Skill 标题>

## Goal
<这类任务要达成什么，什么不算完成>

## Use
1. <读取输入和边界>
2. <选择 references 中的分册>
3. <执行或生成>
4. <验证证据>

## References
- `refs/<topic>.md` — <何时读>
- `references/<topic>.md` — <何时读>

## Scripts
- `scripts/<tool>.py` — <输入/输出/验证证据>

## Risk / Evidence
- <高风险能力>
- <必须给出的证据>
```

### 4.4 反向提问型骨架（30-60 行）

在执行前强制 agent 先声明信息需求，避免盲推。

```markdown
---
name: <skill-name>
description: 当 ... 时使用；<能力摘要>。
---

# <Skill 标题>

Before <doing something>, <声明信息需求>.

## Input
{{task_description}}

## Instructions
1. ...
2. ...

## Output Format
\`\`\`markdown
## <固定输出表格或结构>
| ... | ... |
\`\`\`

Do not proceed with implementation until this is reviewed.
```

样例：awesome-copilot `what-context-needed`（39 行）、`context-map`（52 行）。

---

## 5. 输入输出模板（可选）

### 5.1 `{{var}}` 输入占位

当 skill 需要用户在调用时传入参数（任务描述、URL、问题等），用 `{{var_name}}` 作为占位符。

- agent 使用时会把 `{{var_name}}` 替换成实际内容
- 占位符紧邻其所属段落，不放 frontmatter
- 多个占位符各自独立段落

```markdown
## 我的问题

{{question}}

## 任务

{{task_description}}
```

### 5.2 固定输出表格

当 skill 的输出本该结构化（review findings、verify 结果、文件清单等），在 SKILL.md 末尾附"输出格式"节，给出精确的 markdown 表头。

```markdown
## Output Format

\`\`\`markdown
## Findings

| Priority | File | Line | Issue |
|---|---|---|---|
| P0/P1/P2/P3 | path | N | 一句话 + 证据 |

## 验收
- [ ] 无 P0/P1
- [ ] 验证已通过
\`\`\`
```

收益：

- agent 每次输出同一结构，跨次对比可扫描
- 可作为下游脚本/自动化的输入
- 避免自由叙述带来的遗漏（"我忘了写 Line 列"）

### 5.3 何时用 vs 不用

| 场景 | 是否用 |
|---|---|
| skill 输出本来就是表格/清单（review、verify、map） | ✅ 强烈推荐 |
| skill 输出是自由叙述（解释、方案讨论、架构说明） | ❌ 不强制，表格会束缚表达 |
| skill 输出是代码（scaffold、generate） | ❌ 不适用 |

完整样例见 `skill-patterns.md`。

---

## 6. 外部 Skill 适配规则

从 refs 吸收外部 skill 时，只吸收结构和已验证的规则，不直接照搬会冲突的行为：

- 吸收前先读 `docs/software-engineering-research/refs-absorption-methodology.md`，按其中 L0-L5 层级、Decision Matrix 和 Risk Gates 做裁决。
- 外部 prompt 写“Ask for clarification”时，改成本仓库的 `AskUser` 工具纪律。
- 外部 prompt 写“save as markdown document”时，改为用户明确要求后才创建文档；不得默认写 `docs/` 或 README。
- 外部仓库的安全扫描结果只能作为对应提交的历史证据；不能当作当前安全状态。
- 外部 skill 如果触及网络、secrets、外部 API、数据库、医疗/临床、实验室自动化或文件写入，默认需要 `/guard-secure` 或 `/guard-gitops` 介入。

---

## 7. 检查清单（新增/大改 skill 时）

- [ ] frontmatter：`name` 与目录名一致
- [ ] frontmatter：`description` 通过 1.1-1.4 的硬约束
- [ ] 按 4.1/4.2/4.3/4.4 之一选骨架（推荐，非强制）
- [ ] 工作流型 skill 有 Evidence / Stop / Risk / Gotchas 等质量门
- [ ] 机械步骤和长清单已尽量下沉到 `refs/`、`docs/` 或 `scripts/`
- [ ] `SKILL.md` 主体只保留高频判断；低频细节拆到 reference，避免一次加载过多上下文
- [ ] 引用链最多一层深；不要让 agent 读 A 时再被迫追 B、C、D
- [ ] 可确定性操作已优先下沉脚本，而不是每次让 agent 生成临时代码
- [ ] 如需输入参数，按 5.1 用 `{{var}}`
- [ ] 如输出本应结构化，按 5.2 附固定表格
- [ ] 如引用 `scripts/*.sh` 或 `scripts/*.py`（仓库根），脚本必须 `chmod +x`
- [ ] `python3 scripts/verify_skills.py` 通过
- [ ] `python3 -m unittest scripts.tests.test_skills_registry` 通过

## 8. Tool-backed skill（可选但推荐）

当 skill 有重复、机械、可自动化的步骤（探测命令、扫描 diff、预检 git 状态），把这部分下沉成仓库根的脚本，让 skill 正文引用。

现有 tool-backed skills：

| skill | 脚本 | 作用 |
|-------|------|------|
| `guard-verify` | `scripts/run-verify.sh` | 自动探测项目 test/lint/build 并运行，输出固定表 |
| `guard-review` | `scripts/collect_diff.py` | 打印 diff overview + 敏感信息/调试遗留 flags |
| `guard-ship` | `scripts/preflight.sh` | 分支/工作树/敏感/远端同步/追踪 secret 预检 |
| `guard-diff-scan` | `scripts/scan_diff_residue.py` | 扫描新增 diff 行和未追踪文件中的调试遗留；默认排除 Markdown、测试 fixture 和扫描器自身 |
| `agent-health` | `skills/agent-health/scripts/collect_data.sh` | 收集 agent 配置审计数据 |

规范：

- 引用路径从仓库根开始写（如 `scripts/preflight.sh`），校验脚本会按 skill-local → repo-root 顺序解析
- 仓库根的 `.sh` / `.py` 必须 `chmod +x`，`verify_skills.py` 会强制校验
- 脚本输出尽量用 Markdown 表格，方便 agent 直接贴进最终报告

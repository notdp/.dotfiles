# Skill Patterns

从 `refs/github/awesome-copilot/skills/` 和本仓库现有 skill 提炼的可复用 prompt 模式。本文档给**完整样例**，`skill-authoring.md` 给**规范约束**——两份配合看。

所有样例路径（`refs/github/awesome-copilot/skills/...`）都来自本仓库的 submodule，点开即看。

---

## 模式 A：反向提问型（Before-Answer）

在 agent 回答/动手之前，强制它先声明"我需要看什么"或"我还不确定什么"。避免盲推、避免 agent 在信息不足时硬撑。

### 用它的场景

- 复杂代码问题，agent 可能仅凭局部代码给出错误答案
- 多文件改动前，避免 agent 漏看依赖
- 需求模糊，先把需要澄清的点列出来再动手

### 最小样例：`what-context-needed`（39 行）

`refs/github/awesome-copilot/skills/what-context-needed/SKILL.md`

```markdown
---
name: what-context-needed
description: 'Ask Copilot what files it needs to see before answering a question'
---

# What Context Do You Need?

Before answering my question, tell me what files you need to see.

## My Question

{{question}}

## Instructions

1. Based on my question, list the files you would need to examine
2. Explain why each file is relevant
3. Note any files you've already seen in this conversation
4. Identify what you're uncertain about

## Output Format

\`\`\`markdown
## Files I Need

### Must See (required for accurate answer)
- `path/to/file.ts` — [why needed]

### Should See (helpful for complete answer)
- `path/to/file.ts` — [why helpful]

### Already Have
- `path/to/file.ts` — [from earlier in conversation]

### Uncertainties
- [What I'm not sure about without seeing the code]
\`\`\`

After I provide these files, I'll ask my question again.
```

### 复杂样例：`context-map`（52 行）

`refs/github/awesome-copilot/skills/context-map/SKILL.md` 在 A 的基础上加了：

- `{{task_description}}` 占位
- 四张固定输出表（Files to Modify / Dependencies / Test Files / Reference Patterns）
- 风险 checklist

### 在本仓库的映射

- 可新增 `skills/think-ask-context/` 直接搬 A
- 可新增 `skills/think-context-map/` 搬复杂样例，聚焦"单次任务的文件地图"（与 `think-map` 全局仓库地图职责区分）

---

## 模式 B：`{{var}}` 输入占位

让用户在调用 skill 时把具体参数注入 prompt，避免每次都重新解释背景。

### 用它的场景

- skill 输入是明确的一段文本（任务描述、URL、问题、代码片段）
- 同一个 skill 被反复调用，每次上下文不同

### 样例

```markdown
## Task

{{task_description}}

## Instructions

1. Search the codebase for files related to this task
2. ...
```

### 约定

- 占位符紧邻其所属段落，不放 frontmatter
- 命名用 `snake_case`（`task_description` / `question` / `file_path`）
- 每个占位符独立段落，方便 agent 替换

### 在本仓库的映射

现有 skill 基本都是自由叙述式，`{{var}}` 未使用。新增 `think-ask-context` / `think-context-map` 时适用。

---

## 模式 C：固定输出表格

强制 agent 以固定 markdown 表格输出，而不是自由叙述。结果可扫描、可 diff、可作为下游自动化的输入。

### 用它的场景

- skill 输出本该结构化：review findings、verify 结果、文件清单、依赖图
- 需要跨次对比（例如多轮 review 同一 PR，看是否收敛）
- 输出会被脚本进一步处理

### 不适用

- 自由叙述型输出（架构说明、方案讨论、解释）
- 表格会束缚表达

### 样例：review findings

```markdown
## Findings

| Priority | File | Line | Issue |
|---|---|---|---|
| P1 | src/auth.ts | 42 | 一句话 + 证据 |
| P2 | src/cache.ts | 118 | 一句话 + 证据 |

## 验收
- [ ] 无 P0/P1
- [ ] 验证已通过
```

### 样例：verify 结果

```markdown
## 验证结果

| Check | 命令 | 结果 | 证据 |
|---|---|---|---|
| tests | `pytest` | pass | 42 passed in 3.1s |
| lint | `ruff` | pass | No issues found |
| typecheck | `mypy .` | skip | 未配置 |
```

### 样例：文件依赖地图

```markdown
## Context Map

### Files to Modify
| File | Purpose | Changes Needed |
|------|---------|----------------|
| src/auth.ts | 认证入口 | 加 rate limit |

### Dependencies
| File | Relationship |
|------|--------------|
| src/middleware.ts | imports auth |
```

### 在本仓库的映射

- PR4 里 `guard-review`、`guard-verify` 会按此模式附输出表
- 新增 `think-context-map` 原生采用

---

## 模式 D：Micro-Prompt 提醒（10-20 行）

把一条行为准则压成 10-20 行的独立 skill，比塞进 `AGENTS.md` 更精准、更易按任务类型触发。

### 用它的场景

- 某类任务下需要的固定准则（如"用 REPL 优先"、"先写失败测试"）
- 准则独立、可复用、不依赖 workflow
- 希望 agent 在特定场景下被提醒，而不是每次对话都加载

### 样例：`remember-interactive-programming`（13 行）

`refs/github/awesome-copilot/skills/remember-interactive-programming/SKILL.md`

```markdown
---
name: remember-interactive-programming
description: '...'
---

Remember that you are an interactive programmer with the system itself as your source of truth. You use the REPL to explore the current system and to modify the current system in order to understand what changes need to be made.

Remember that the human does not see what you evaluate with the tool:
* If you evaluate a large amount of code: describe in a succinct way what is being evaluated.

When editing files you prefer to use the structural editing tools.

Also remember to tend your todo list.
```

### 本仓库目前无此类

可作为未来增量考虑。

---

## 模式 E：交互式 Refinement（30-60 行）

在执行前先和用户来回澄清，直到需求明确。与反向提问型（A）的区别：A 是 agent 单向提信息需求，E 是双向对话 refinement。

### 用它的场景

- 需求模糊，有多种合理解释
- 用户提出的是方案而非问题（XY problem 警觉）
- 边界不清，需要先确定 goals / non-goals

### 样例：`first-ask`（30 行）

`refs/github/awesome-copilot/skills/first-ask/SKILL.md` 用 Joyride 的 `joyride_request_human_input` 工具做交互循环：先澄清、再展示 plan、最后执行。

### 在本仓库的映射

- `think-plan` 已经包含类似流程但更重（180 行）
- 可新增 `skills/think-refine/` 作为更轻的前置澄清 skill，完成后转接 `think-plan` 或直接执行

---

## 模式 F：Task Contract（目标契约型）

把 skill 写成“任务契约”，而不是 SOP。它规定任务必须产出什么、什么证据算数、什么风险要停下；具体文件、命令、工具路径由 agent 根据当前仓库和可用工具决定。

### 用它的场景

- 工作流型 skill 容易变成长步骤清单
- 任务质量取决于证据、边界和验收，而不是固定操作顺序
- 细则会过时，适合放到 `refs/` 或脚本里

### 最小骨架

```markdown
---
name: <skill-name>
description: 当 ... 时使用；<能力摘要>。
---

# <Skill>

## Goal
这类任务要交付什么，什么不算完成。

## Inputs
- 当前任务 / diff / URL / 截图 / 日志等

## Output Contract
- 必须输出哪些字段、表格或裁决

## Evidence Gate
- 哪些证据能支持结论
- 哪些证据缺失时只能标 partial / blocked

## Stop / Escalate
- 什么时候可以停止
- 什么时候必须转其它 skill、问用户或报告 blocker

## Refs / Tools
- 长清单和机械检查放这里，不放主流程
```

### 写法对比

| 推荐 | 避免 |
|---|---|
| “交付前必须给出测试/截图/路径证据” | “先运行固定命令 A，再打开固定文件 B” |
| “如果证据不足，输出 partial 并说明缺口” | “不管项目如何，都按 20 步走完” |
| “优先沿用项目已有工具，找不到再说明 blocker” | “假设某个 CLI 一定存在” |
| “长规则见 refs，由当前任务按需读取” | “把所有设计禁忌复制到 SKILL.md 主体” |

### 在本仓库的映射

- `guard-verify` 的三层证据门是强样例
- `fe-ui-visual-iterate` 应保留截图证据和差异表，但避免把循环写成不可适配的机械脚本
- `dev-large-delivery` 应强调 Phase contract，而不是把所有团队都锁进同一执行顺序

---

## 模式 G：Progressive Disclosure

把常用判断放在 `SKILL.md`，把低频细节、长清单、示例和确定性操作下沉到 reference 或 scripts。目标是让 skill 触发时加载最小必要上下文。

### 用它的场景

- skill 正文开始超过 100-160 行
- 内容包含多个低频分支、长格式模板或大量示例
- 某些步骤可以用脚本稳定执行

### 写法

```markdown
## Core Rules
- 高频规则 1
- 高频规则 2

## Refs / Tools
- 详细模板见 `docs/.../reference.md`
- 机械扫描用 `scripts/check_x.py`
```

### 规则

- 主体只保留路由后立即需要的判断。
- reference 只引用一层，不做多级追链。
- 可确定性操作优先脚本化，脚本输出 Markdown 表格。
- reference 不是垃圾桶；过期材料应删，不是继续拆。

---

## 模式 H：领域分册型 Skill

把知识密集型能力拆成短入口和多个分册：`SKILL.md` 负责触发、边界、流程和风险门；`references/` 或 `refs/` 负责 API、标准、分类表、示例；`scripts/` 负责可确定性检查或转换。

### 用它的场景

- 科学计算、医学/临床、合规、安全、设计系统等领域知识密集
- 单个 skill 需要覆盖多个库、API、标准或文件格式
- 需要保留示例脚本，但不希望每次触发都加载所有细节

### 参考样例

- `refs/K-Dense-AI/scientific-agent-skills/scientific-skills/rdkit/SKILL.md`
- `refs/K-Dense-AI/scientific-agent-skills/scientific-skills/scanpy/references/standard_workflow.md`
- `refs/K-Dense-AI/scientific-agent-skills/scientific-skills/database-lookup/references/pubchem.md`
- `refs/K-Dense-AI/scientific-agent-skills/scientific-skills/hugging-science/scripts/fetch_catalog.py`

### 在本仓库的映射

- 新增领域 skill 时优先采用 `SKILL.md + refs/references + scripts`，不要把长手册塞进正文。
- 涉及 network、secrets、外部 API、医疗/临床或数据写入时，必须写 Risk / Evidence / Guardrails，并让 `verify_skills.py` 风险提示可见。
- 外部安全报告只能作为对应提交的历史证据；当前引入仍需本仓库自己的验证。

---

## 模式 I：Command 编排型 Workflow

Command 只负责把多个 skill 串成高频动作，不复制每个 skill 的知识正文。这个模式来自 `refs/Owl-Listener/designer-skills`：skills 是名词型知识单元，commands 是动词型工作流。

### 用它的场景

- 多个 skill 经常按固定顺序一起使用
- 用户需要短命令入口，而不是记住多个 skill 名称
- 工作流本身稳定，但各 skill 的知识正文需要独立演进

### 参考样例

- `refs/Owl-Listener/designer-skills/design-research/commands/discover.md`
- `refs/Owl-Listener/designer-skills/design-research/skills/user-persona/SKILL.md`
- `refs/Owl-Listener/designer-skills/scripts/build-gemini.sh`

### 在本仓库的映射

- `commands/` 可以保留高频 inner-loop 编排，例如先调研、再计划、再验证。
- `commands/` 不应复制 `skills/` 的长规则，只引用 skill 名称和执行顺序。
- 外部 prompt 中的自然语言澄清要改成 `AskUser`；默认保存文档要改成用户明确授权后再写。
- 本仓库不采用“禁止跨插件引用”作为硬规则；跨域编排由风险、复用性和可 review 性决定。

---

## 模式 J：Wrong / Should Happen 反例库

用成对反例训练 agent 的判断边界：先展示常见错误输出，再展示同一任务下应发生的行为。这个模式来自 `refs/forrestchang/andrej-karpathy-skills/EXAMPLES.md`，比抽象原则更容易迁移到 review、simplify 和 TDD。

### 用它的场景

- 抽象规则容易被 agent 口头同意，但在 diff 中仍然犯错
- 需要说明“为什么这个看似最佳实践的做法在当前任务中过度设计”
- 需要把 scope drift、未请求抽象、风格漂移、未复现就修 bug 等失败模式写成可 review 的检查项

### 最小结构

```markdown
### Example: <失败模式>

**User Request:** "<具体请求>"

**Wrong**

<最小错误 diff / 代码 / agent 计划>

Problems:
- <为什么越界、过度设计或不可验证>

**Should Happen**

<更小、更可验证、更贴近现有风格的版本>

Only changed:
- <每个改动如何映射到用户请求 / 验证 / cleanup>
```

### 推荐反例类型

| 类型 | Wrong | Should Happen |
|---|---|---|
| Hidden assumptions | 静默选择字段、范围、数据源或输出形态 | 列假设、先自查，关键决策缺失时 AskUser |
| Over-abstraction | 为单次需求新增 strategy、adapter、config、fallback | 用当前需求需要的最小函数 / 分支，复杂度出现后再抽象 |
| Surgical drift | 顺手改注释、quote style、类型标注、无关校验 | 只改触发 bug 或需求所需的行，沿用现有风格 |
| Goal ambiguity | “我会改进 X”但无验收 | 写成 `目标 -> 验证`，先复现或定义 acceptance verifier |

### 在本仓库的映射

- `guard-review` 用反例库校准 Drift Signals，避免把风格漂移包装成“顺手优化”。
- `dev-simplify` 用反例库识别 speculative abstraction、unrequested flexibility、untraceable change。
- `dev-tdd` 用反例库强调先复现 bug，再修复并跑回归。
- 反例库应放在 `docs/` 或 skill 的 `refs/`，不要把长示例塞进 `AGENTS.md`。

---

## 模式 K：MCP 工具发现替代硬编码 schema

> 来源吸收：`docs/refs-absorption-plan-2026-06-02.md` A18，源 ComposioHQ/awesome-claude-skills（composio-skills）。

### 用它的场景

skill 要驱动外部工具/MCP（SaaS API、Composio toolkit），而上游 API/工具 schema 会演进。把工具名、参数 schema 硬编码进 SKILL.md，上游一改 skill 就静默腐烂。

### 写法

- 正文不写死工具 schema，而是让 agent 在运行时通过 MCP `ToolSearch` / 工具发现拿到当前 schema 再调用。
- 配一份 `known-pitfalls` 清单（哪些工具有坑、参数顺序、鉴权前置），用确定性文字补运行时发现的不确定性。

### 张力与边界

运行时发现增加不确定性，和本仓库"事实驱动 / 显式化"有张力。仅用于"工具 schema 必然漂移"的外部集成；本仓库内部能力不要为了"灵活"放弃显式 schema。

---

## 模式 L：否定式护栏 command

> 来源吸收：`docs/refs-absorption-plan-2026-06-02.md` A18b，源 ComposioHQ（connect-apps-plugin setup.md）。

### 用它的场景

install / config / setup 型流程容易发散（agent 反复搜索、连环追问、试错）。用一组"不要做"的否定式护栏 + 时限收紧流程，比正向 SOP 更能止血。

### 写法

- 列 `Do NOT ...` 清单：如 `Do NOT 反复多轮追问`、`Do NOT 无界搜索`，配明确时限/步数上限。
- 措辞必须改写以符合本仓库 Truth Directive：源项目的 `Ignore pretrained data` 这类原话不能照搬（与事实纪律冲突），只吸收"否定式 + 时限"的结构。

### 反模式

照搬外部护栏原话（`Ignore pretrained data` / `Do NOT search config`）——见本文末"反模式"第 5 条与第 6 条。

---

## 模式汇总表

| 模式 | 代表样例 | 行数 | 何时用 |
|---|---|---|---|
| A 反向提问型 | `what-context-needed` / `context-map` | 30-60 | agent 需要先声明信息需求 |
| B `{{var}}` 输入 | 几乎所有 awesome-copilot 短 skill | 混入 | 有明确输入参数 |
| C 固定输出表格 | `context-map` / review skills | 混入 | 输出本该结构化 |
| D Micro-prompt 提醒 | `remember-interactive-programming` | 10-20 | 单条准则独立化 |
| E 交互式 Refinement | `first-ask` | 30-60 | 需求模糊需对话澄清 |
| F Task Contract | `guard-verify` / 工作流型 skills | 40-160 | 需要目标、证据、停止条件而非固定 SOP |
| G Progressive Disclosure | `write-a-skill` / 本仓库 tool-backed skills | 混入 | 主流程要短，细节按需加载 |
| H 领域分册型 Skill | `scientific-agent-skills` | 80-200 + 分册 | 知识密集、引用多、示例脚本多 |
| I Command 编排型 Workflow | `designer-skills` commands | 10-80 | 高频串联多个 skill |
| J Wrong / Should Happen 反例库 | `andrej-karpathy-skills/EXAMPLES.md` | 混入 | 用对照反例校准行为边界 |
| K MCP 工具发现 | composio-skills | 混入 | 驱动会漂移的外部工具/MCP，避免硬编码 schema |
| L 否定式护栏 command | connect-apps-plugin setup | 10-40 | install/config 流程发散，用 Do NOT + 时限止血 |

---

## 反模式（不要做）

1. **把产品手册压进 SKILL.md**（awesome-copilot 的 `gh-cli` 2187 行是极端例子）——应该让 agent 去查文档，不是在 skill 里复刻
2. **正文反复说"何时调用"**——触发语义已经在 description 里硬约束，正文再写就重复
3. **自由叙述伪装成表格**（表格列都叫"说明"）——不如不用表格
4. **`{{var}}` 用太多**（5 个以上占位符）——会变成填空题，退化成 mad libs
5. **照搬外部 agent 行为**——如“Ask for clarification”“save as markdown document”，必须先适配本仓库 AskUser 和文档创建纪律

# mattpocock/skills

| 字段 | 值 |
|---|---|
| URL | https://github.com/mattpocock/skills |
| 作者 | Matt Pocock (Total TypeScript 创始人) |
| 分类 | 研发流程 / Skill 工程 |
| 分析日期 | 2026-06-04 |
| 一句话总结 | "小、可组合、可 hack"的 Claude Code skill 集合，核心价值在于 prompt 结构设计和工程纪律编码方式 |

## 结构概览

```
mattpocock-skills/
├── CLAUDE.md / CONTEXT.md / README.md
├── .claude-plugin/plugin.json          # skill 注册清单
├── .out-of-scope/                      # 被拒绝的 feature request 知识库
├── docs/adr/                           # 架构决策记录
├── scripts/                            # list-skills.sh, link-skills.sh
└── skills/
    ├── engineering/   (10 skills)      # diagnose, grill-with-docs, improve-codebase-architecture,
    │                                   # prototype, setup-matt-pocock-skills, tdd, to-issues,
    │                                   # to-prd, triage, zoom-out
    ├── productivity/  (4 skills)       # caveman, grill-me, handoff, write-a-skill
    ├── misc/          (4 skills)       # git-guardrails-claude-code, migrate-to-shoehorn,
    │                                   # scaffold-exercises, setup-pre-commit
    ├── personal/                       # 私人工具，不发布
    ├── in-progress/                    # 开发中草稿 (review, teach, writing-*)
    └── deprecated/                     # 已废弃
```

每个 skill 是一个目录，入口 `SKILL.md` + 支撑文件平铺同目录。

## 哲学与设计原则

### P1: Skill 即契约，不是脚本

SKILL.md 主体目标 <100 行，只写"做什么、交付什么、什么不能做"。细节拆到同目录的支撑文件（如 `tdd/tests.md`、`tdd/mocking.md`、`tdd/refactoring.md`），agent 按需加载。

与本仓库 Pattern G (Progressive Disclosure) 同源，但 mattpocock 执行得更极致——几乎没有超过 120 行的 SKILL.md。

### P2: 指令和知识分离

独特的 `<what-to-do>` / `<supporting-info>` XML tag 结构：

```markdown
<what-to-do>
核心指令：做什么、怎么做、什么顺序
</what-to-do>

<supporting-info>
辅助知识：定义、格式规范、边界规则
</supporting-info>
```

Agent 优先执行 `<what-to-do>` 中的流程，遇到细节时查 `<supporting-info>`。出现在 `grill-with-docs`、`writing-beats`、`writing-fragments` 等 skill 中。

### P3: Vertical Slice 作为基本工作单元

贯穿 `tdd`、`to-issues`、`to-prd`。用 ASCII 图强制纠偏：

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED->GREEN: test1->impl1
  RED->GREEN: test2->impl2
```

`to-issues` 明确规则：每个 slice 必须窄但完整地穿过所有层，完成后可独立演示或验证。

### P4: Grilling 模式——让 AI 主动追问

`grill-me` 和 `grill-with-docs` 的核心创新：

> "Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one."

三条关键约束：
- "Ask the questions one at a time"——防止一次倒出 20 个问题
- "For each question, provide your recommended answer"——agent 不只提问，还给建议
- "If a question can be answered by exploring the codebase, explore the codebase instead"——减少不必要的人工交互

这种模式被嵌入到其他 skill 中（`triage` 第 4 步、`improve-codebase-architecture` 第 3 步）。

### P5: Anti-pattern 先行 + 具体对比

几乎每个复杂 skill 都有明确的反模式说明，用 `WRONG` vs `RIGHT`、`Good` vs `Bad`、`Not:` vs `Yes:` 的成对例子而非抽象规则：

- `tdd`: `WRONG` 和 `RIGHT` 的 ASCII 工作流对比图
- `triage/AGENT-BRIEF.md`: 完整的 Good brief + Bad brief 对比，逐条解释差异
- `write-a-skill`: Good description vs Bad description
- `tdd/tests.md`: Good test 和 Bad test 的代码对比 + red flags 清单

### P6: 强制词汇表 + Avoid 列表

`improve-codebase-architecture/LANGUAGE.md` 定义 8 个核心术语，每个术语有精确定义和 `_Avoid_` 列表：

```markdown
**Module** — A named unit that encapsulates ...
_Avoid_: component, service, unit, ...
```

还有 "Rejected framings" 章节明确说不使用什么词。`CONTEXT.md` 在项目层面做领域词汇表，且项目自身 dogfooding（CONTEXT.md 在根目录就有）。

### P7: .out-of-scope 知识库

被拒绝的 feature request 持久化为 `.out-of-scope/*.md` 文件。`triage` skill 在处理 issue 时会自动检查这个目录。这是一个制度化的 scope 防线——不只是说"不做"，而是把"为什么不做"写下来，避免同一个讨论反复发生。

### P8: Side-effect Inline

对话进行中直接修改文档，不等对话结束：

> "When a term is resolved, update CONTEXT.md right there. Don't batch these up -- capture them as they happen."

### P9: Durability Over Precision

`triage/AGENT-BRIEF.md` 的 issue 模板禁止写文件路径和行号：

> "Do describe interfaces, types, and behavioral contracts"
> "Don't reference file paths -- they go stale"

所有 issue 描述必须用行为契约而非代码位置。

### P10: HTML Artifact 绕过终端限制

`improve-codebase-architecture` 和 `teach` 生成 self-contained HTML（Tailwind CDN + Mermaid CDN）到临时目录再 `open`。适合需要可视化的架构审查、教学场景。

## 独特技术细节

### frontmatter 扩展字段

| 字段 | 作用 | 示例 |
|---|---|---|
| `argument-hint` | 提示用户传什么参数 | `handoff`, `teach` |
| `disable-model-invocation: true` | 禁止 model 自动调用，只允许用户手动触发 | `zoom-out`, `teach` |

### Checklist Gate 模式

关键节点设置检查门，用 `Do not proceed` 作为硬门禁：

```markdown
- [ ] Test describes behavior, not implementation
- [ ] Test uses public interface only
- [ ] Test would survive internal refactor

Do not proceed to Phase 2 until you have a loop you believe in.
```

### Lazy Creation

> "Create files lazily -- only when you have something to write."
> "Create the docs/adr/ directory lazily -- only when the first ADR is needed."

### 角色人格设定

`caveman` skill 直接改变语言行为，但有 Auto-Clarity Exception：安全警告、不可逆操作、多步骤序列时自动退出。

## 与本仓库的维度对比

| 维度 | mattpocock/skills | 本仓库 |
|---|---|---|
| 规模 | 14 个公开 skill | 50+ 个 skill |
| 单 skill 行数 | SKILL.md 目标 <100 行 | 60-300 行 |
| 触发方式 | description 中 "Use when" | description 中 "当...时使用" |
| 分层 | 2 层: SKILL.md + 支撑文件 | 3 层: AGENTS.md > skills > docs/refs |
| 词汇控制 | CONTEXT.md + LANGUAGE.md + _Avoid_ 列表 | 无系统化词汇控制 |
| 指令结构 | `<what-to-do>` + `<supporting-info>` XML tag | 无统一 tag 结构 |
| Anti-pattern | 每个 skill 内联具体例子（WRONG/RIGHT） | 分散在 AGENTS.md 和各 skill |
| 验证要求 | 轻量 checklist gate | 重量级（四条红线、boundary decisions） |
| Scope 控制 | .out-of-scope/ 目录 + triage 自动检查 | /guard-close skill |
| Progressive Disclosure | 极致：主体 <100 行，细节全拆 | 中度：部分 skill 200+ 行 |
| Issue/PRD 管理 | 深度集成 (triage/to-issues/to-prd) | 不在 skill 体系内 |
| 跨工具兼容 | 主要面向 Claude Code | 明确跨 droid/CC/Cursor/Aider |
| Dogfooding | 项目自身使用所有 pattern | 部分 dogfooding |

## 可吸收的模式（按 refs-absorption-methodology L0-L5）

### L2 候选（写入规范/模式文档）

| 编号 | 模式 | 映射资产 | 理由 |
|---|---|---|---|
| MP-1 | `<what-to-do>` / `<supporting-info>` 指令-知识分离 | `skill-patterns.md` 新模式 | 解决 skill 正文指令和知识混杂的问题；比随意分段更结构化 |
| MP-2 | 强制词汇表 + _Avoid_ 列表 | `skill-authoring.md` 推荐实践 | 解决 skill 间术语不一致；比单纯定义更有约束力 |
| MP-3 | .out-of-scope 知识库 | `skill-authoring.md` 推荐实践 | scope creep 的制度化防线；补充 /guard-close 的 project 层面 |
| MP-4 | Durability over precision（issue 描述禁路径行号） | `skill-patterns.md` 写法建议 | 解决 issue 内容快速腐烂的问题 |
| MP-5 | Vertical Slice 可视化规则 | `dev-tdd` 支撑参考 | 已有 TDD 循环但缺 vertical slice 的显式规则和图示 |

### L4 候选（新增/修改 skill 或 command）

| 编号 | 模式 | 映射资产 | 理由 |
|---|---|---|---|
| MP-6 | Grilling 模式的"逐个问 + 给推荐答案" | `think-refine` skill 改进 | 当前 think-refine 缺少"一次只问一个 + agent 给推荐答案"的约束 |
| MP-7 | `disable-model-invocation` 概念 | `skill-authoring.md` + catalog.json | 部分 skill 不适合 agent 自动调用（如 zoom-out 类的反思 skill） |

### 不吸收

| 模式 | 理由 |
|---|---|
| 平坦目录结构 | 本仓库 50+ skill 需要分类；mattpocock 14 个 skill 才能扁平 |
| `caveman` 角色人格 | 与本仓库"稳定语气、不用情绪化评价"原则冲突 |
| HTML artifact 作为默认输出 | 本仓库已有 `readable-html-artifact` skill 覆盖；无需改为默认 |
| `.claude-plugin/plugin.json` 注册 | 本仓库已有 `skills/catalog.json`，职责重叠 |
| Side-effect inline（对话中直接改文档） | 与本仓库"Surgical Changes"原则存在张力；按需评估 |

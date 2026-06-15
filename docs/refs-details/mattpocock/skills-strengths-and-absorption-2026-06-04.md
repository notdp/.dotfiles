# mattpocock/skills 长处分析与本仓库吸收计划

分析对象：`refs/mattpocock/skills`

分析日期：2026-06-04

本次目标：关注 `refs/mattpocock/skills` 的思路哲学、特殊技巧、why/how，并判断哪些优势可吸收到本仓库的 `agents/AGENTS.md`、`coding-skills/`、`commands/`、`scripts/hooks/`，同时区分新增、改善、去掉坏影响和明确不吸收项。

## 摘要

`mattpocock/skills` 的核心价值不是 skill 数量，而是把软件工程常见失败模式压缩成一组小型、可组合、低上下文开销的行为契约。

它最强的地方有三点：

- 把 agent 失败归因到可治理的工程问题：需求未对齐、领域语言不一致、反馈环不足、架构退化。
- 用具体机制约束 agent 行为：一次一个问题、给推荐答案、vertical slice、行为测试、反馈环目录、Good/Bad 对比、`_Avoid_` 词汇表、`.out-of-scope/` 记忆库。
- 把文档当作工作流资产而非装饰：`CONTEXT.md` 管语言，`docs/adr/` 管承重决策，agent brief 管长期交接，`.out-of-scope/` 管拒绝理由。

本仓库已经吸收了部分高价值思想，例如 `dev-tdd` 的 vertical slice、`dev-debug` 的反馈环优先、`dev-refactor` 的 deep module 判断、`agents/AGENTS.md` 的 TDD 和验证红线。因此后续重点不是复制同名 skill，而是把它的 prompt 结构、词汇治理、持久化交接和 scope 记忆机制，放到本仓库现有分层中。

## 参考项目结构

本次读取到的结构如下：

```text
refs/mattpocock/skills/
├── CLAUDE.md
├── CONTEXT.md
├── README.md
├── .claude-plugin/plugin.json
├── .out-of-scope/
├── docs/adr/
├── scripts/
└── skills/
    ├── engineering/
    ├── productivity/
    ├── misc/
    ├── personal/
    └── deprecated/
```

关键证据：

| 资产 | 作用 | 证据路径 |
|---|---|---|
| `README.md` | 解释为什么这些 skill 存在，并把失败模式映射到 skill | `refs/mattpocock/skills/README.md` |
| `CLAUDE.md` | 规定 bucket、README、plugin manifest 的同步规则 | `refs/mattpocock/skills/CLAUDE.md` |
| `CONTEXT.md` | 项目自己的领域词汇表，属于 dogfooding | `refs/mattpocock/skills/CONTEXT.md` |
| `.out-of-scope/` | 记录被拒绝的需求概念 | `refs/mattpocock/skills/.out-of-scope/` |
| `docs/adr/` | 记录少量承重决策 | `refs/mattpocock/skills/docs/adr/` |
| `skills/engineering/tdd` | vertical slice TDD 和测试哲学 | `refs/mattpocock/skills/skills/engineering/tdd/` |
| `skills/engineering/diagnose` | 调试反馈环目录 | `refs/mattpocock/skills/skills/engineering/diagnose/SKILL.md` |
| `skills/engineering/grill-with-docs` | 追问、术语、ADR 联动 | `refs/mattpocock/skills/skills/engineering/grill-with-docs/SKILL.md` |
| `skills/engineering/improve-codebase-architecture` | deep module 架构语言 | `refs/mattpocock/skills/skills/engineering/improve-codebase-architecture/` |
| `skills/engineering/triage` | issue triage 状态机、agent brief、out-of-scope 检查 | `refs/mattpocock/skills/skills/engineering/triage/` |

## 思路哲学

### 1. 小技能优先，不让框架接管流程

Why：复杂流程框架容易拿走开发者控制权，一旦流程本身有 bug，用户很难修。参考项目在 `README.md` 中明确说这些 skills 是 small、easy to adapt、composable。

How：每个 skill 聚焦一个摩擦点，而不是把“调研、规划、开发、测试、交付”塞进一个大流程。例如：

- `grill-me` / `grill-with-docs` 只解决需求对齐。
- `tdd` 只解决测试先行与小步反馈。
- `diagnose` 只解决调试反馈环与根因定位。
- `improve-codebase-architecture` 只解决架构 deepening。
- `to-issues` 只解决把计划拆成垂直切片 issue。

对本仓库的启发：本仓库已经采用 `think-*`、`dev-*`、`guard-*` 分层，应该继续保持“按需触发”，不要把 mattpocock 的全部流程塞进 `agents/AGENTS.md`。

### 2. 失败模式先行，而不是功能清单先行

Why：agent 的问题不是抽象的“模型不够好”，而是具体失败模式：没有对齐、太啰嗦、代码不工作、架构变泥球。

How：参考项目把失败模式直接映射到 skill：

| 失败模式 | Skill 机制 | 证据路径 |
|---|---|---|
| 需求未对齐 | `grill-me` / `grill-with-docs` 追问设计树 | `README.md`、`skills/productivity/grill-me/SKILL.md` |
| 语言不一致导致啰嗦 | `CONTEXT.md` 做领域语言 SSOT | `README.md`、`CONTEXT.md` |
| 代码不工作 | `tdd` 与 `diagnose` 建立反馈环 | `skills/engineering/tdd/`、`skills/engineering/diagnose/SKILL.md` |
| 架构退化 | deep module、deletion test、locality | `skills/engineering/improve-codebase-architecture/` |

对本仓库的启发：新增或大改 skill 时，先写“这条 skill 防哪类失败”，再写步骤。否则容易制造一批看起来完整但无法判断强弱的流程规则。

### 3. 共享语言是降低长期 token 和沟通成本的核心工具

Why：领域语言不统一会让 agent 用很多字解释一个概念，也会让命名漂移、文件难找、代码难导航。

How：参考项目用 `CONTEXT.md` 定义 canonical term、avoid aliases、relationships、flagged ambiguities。`grill-with-docs` 还要求遇到用户术语和代码术语冲突时当场指出。

特殊技巧：`_Avoid_` 列表不是普通词汇表。它告诉 agent 哪些近义词不要用，降低术语漂移。

对本仓库的启发：本仓库 `agents/AGENTS.md` 已有 Ubiquitous Language 原则，但缺少项目/skill 级的词汇治理模板。适合吸收到 `skill-authoring.md`、`skill-patterns.md`，并在 `think-scope`、`think-plan`、`think-architecture` 中作为可选产物。

### 4. 文档只记录承重信息，避免文档仪式化

Why：ADR 如果变成模板填空，会提高维护成本并降低可信度。参考项目把 ADR 的触发条件压得很窄。

How：`grill-with-docs` 只在三个条件同时成立时建议 ADR：hard to reverse、surprising without context、real trade-off。ADR 可以只有 1-3 句。

对本仓库的启发：这与本仓库“不要把解释性内容堆进 `AGENTS.md`”一致。应吸收的是 ADR 触发条件和极简格式，而不是每次规划都创建文档。

### 5. 反馈环是速度上限

Why：没有可重复运行的 pass/fail signal，agent 只能靠猜测。参考项目把 debugging 和 TDD 的第一任务都设为构造反馈。

How：`diagnose` 提供反馈环优先级：失败测试、HTTP 脚本、CLI fixture、headless browser、trace replay、throwaway harness、property/fuzz、bisection、differential loop、HITL 脚本。

对本仓库的启发：本仓库 `dev-debug` 已经吸收这套结构。后续应维护为 debug skill 的核心合同，不再退化成“读错误、猜原因、改代码”。

### 6. Vertical slice 是 TDD 和任务拆分的共同单位

Why：horizontal slicing 会让 agent 先写一批想象中的测试或基础设施，再补实现，最后测试锁住的是结构而不是行为。

How：`tdd` 要求一个可观察行为对应一轮 `RED -> GREEN`；`to-issues` 要求每个 issue 窄但完整地穿过所有集成层，完成后可独立 demo 或验证。

对本仓库的启发：`dev-tdd` 已经吸收 vertical slice。还可以把同一语言扩散到 `think-plan`、`dev-long-task-scaffold`、`dev-long-run`，让 phase/issue 也以可验收垂直切片为单位。

### 7. 具体 Good/Bad 对比比抽象原则更能约束 agent

Why：抽象规则容易被模型泛化错。具体反例和正例能减少歧义。

How：参考项目大量使用 `WRONG/RIGHT`、`Good/Bad`、`Not/Yes`：

- `tdd` 用 ASCII 图展示 horizontal vs vertical。
- `tdd/tests.md` 给 good test / bad test 对照。
- `triage/AGENT-BRIEF.md` 给 good brief / bad brief 对照。
- `write-a-skill` 给 good description / bad description。

对本仓库的启发：本仓库已有一些正反例，但不系统。后续大改 skill 时，应优先把长反面清单改成“正反 contract cases + 恢复路径”。

### 8. `.out-of-scope/` 把拒绝变成知识资产

Why：长期维护项目里，重复讨论“为什么不做 X”会消耗大量上下文。只记录要做什么，不记录不做什么，会让 scope creep 反复出现。

How：参考项目按 concept 记录 rejected enhancement，不按 issue 记录。triage 时先查 `.out-of-scope/`，相似需求可以引用历史决策。

对本仓库的启发：本仓库已有 `guard-close` 做停止裁决，但缺少“拒绝理由持久化”。适合新增可选 `docs/out-of-scope/` 模式，限制为长期重复出现的 enhancement，不用于 bug。

### 9. Durable Agent Brief 用行为契约替代易腐路径

Why：长期交接文档如果引用大量 file path 和 line number，后续很快过期。agent brief 应该成为合同，而不是实现指南。

How：`triage/AGENT-BRIEF.md` 强调 current behavior、desired behavior、key interfaces、acceptance criteria、out of scope，少写实现步骤和易腐路径。

对本仓库的启发：短期 review finding 仍应保留 `file:line`，但长期 PRD、issue、handoff、long task scaffold 应优先写行为契约和验收标准。

### 10. 平台特定能力做得清楚，但不该直接复制

Why：参考项目面向 Claude Code plugin、`~/.claude/skills`、`.claude-plugin/plugin.json` 和 Claude hooks。本仓库是多 agent dotfiles，SSOT 是 `coding-skills/catalog.json`、`scripts/verify_skills.py`、`commands/`、`scripts/hooks/`。

How：参考项目用 `disable-model-invocation: true` 表达某些 skill 只允许用户手动触发，用 `git-guardrails-claude-code` 安装 Claude Code hook。

对本仓库的启发：吸收语义，不复制实现。`manual-only` 可以进入 catalog 设计；git guardrail 可以转成 `command_guard.py` 测试用例，而不是复制 shell hook。

## 本仓库现状对比

| 维度 | `mattpocock/skills` | 本仓库现状 | 裁决 |
|---|---|---|---|
| 全局规则 | `CLAUDE.md` 较轻，聚焦 repo 维护 | `agents/AGENTS.md` 已很重，含事实纪律、TDD、边界、验证、gitops | 不把长方法论加进 `AGENTS.md` |
| Skill 注册 | `.claude-plugin/plugin.json` | `coding-skills/catalog.json` + `scripts/verify_skills.py` | 不吸收 plugin manifest 作为 SSOT |
| Skill 粒度 | 小、可组合、主体短 | 多 domain，部分长 skill | 吸收 progressive disclosure，但不硬套 100 行 |
| TDD | vertical slice / tracer bullet | `dev-tdd` 已吸收 | 保持，扩散到 plan/issue 拆分语言 |
| Debug | 反馈环目录 | `dev-debug` 已吸收 | 保持为硬门控 |
| 领域语言 | `CONTEXT.md` + `_Avoid_` | 全局有原则，缺少系统模板 | 新增 authoring/pattern 文档 |
| ADR | 极简、承重才写 | 有相关 docs，skill 中可更明确 | 改善 think-plan/architecture 输出 |
| Scope 记忆 | `.out-of-scope/` | `guard-close` 做当次裁决 | 新增可选持久化模式 |
| Issue workflow | triage/to-prd/to-issues | 当前 commands 不覆盖 issue tracker | 可新增 command，但必须 guard-gitops |
| Hooks | Claude hook shell 脚本 | Python hooks 更细粒度 | 只吸收测试用例和语义 |

## 可吸收项分类

### 新增

| 新增项 | 推荐落点 | 为什么吸收 | 怎么吸收 |
|---|---|---|---|
| `docs/out-of-scope/` 或 `.out-of-scope/` 模式 | `docs/software-engineering-research/skill-patterns.md`、`guard-close` | 记录长期重复的“不做什么”，减少 scope creep | 先作为可选模式，不自动创建；一个 concept 一个文件 |
| Durable Agent Brief 模板 | `think-plan`、`guard-ship`、`dev-long-task-scaffold`、`dev-long-run` | 改善长期交接，减少 line number 腐烂 | 模板包含 current behavior、desired behavior、key interfaces、acceptance criteria、out of scope |
| `manual-only` 语义 | `coding-skills/catalog.json`、`scripts/verify_skills.py`、`skill-authoring.md` | 某些 skill 不应被 agent 自动调用 | 先做 schema 设计；只用于 zoom-out、危险操作准备、反思类 skill |
| Issue workflow commands | `commands/to-prd.md`、`commands/to-issues.md`、`commands/triage.md` | PRD/issue/triage 是动词型工作流，且可能有远程副作用 | 默认 dry-run；触碰 GitHub/GitLab 前走 `guard-gitops` |
| Skill 级 `LANGUAGE.md` 模板 | `skill-authoring.md`、部分知识密集 skill 目录 | 降低术语漂移 | 每个术语包含定义、Avoid、冲突处理、例句 |

### 改善

| 改善项 | 推荐落点 | 为什么改善 | 怎么改善 |
|---|---|---|---|
| 指令-知识分离 | `skill-patterns.md`，后续用于长 skill | 长 skill 容易把流程、判断、背景混在一起 | 对复杂 skill 采用 `<what-to-do>` / `<supporting-info>` 或等价结构 |
| Grilling 一次一个问题 + 推荐答案 | `think-refine`、`think-scope`、`think-plan` | 降低用户认知负担，减少一次倒出十几个问题 | 只问阻塞决策；每问附推荐答案；能读代码就不问用户 |
| 领域术语冲突显式化 | `think-scope`、`think-refine`、`think-architecture` | 避免用户词、代码词、文档词静默错位 | 输出 flagged ambiguity；需要时建议写入 CONTEXT 类文档 |
| ADR 触发条件 | `think-plan`、`think-architecture` | 记录为什么，不制造文档仪式 | 只在 hard to reverse、surprising、real trade-off 同时成立时建议 ADR |
| Vertical slice 计划语言 | `think-plan`、`dev-long-task-scaffold`、`dev-long-run` | phase/issue 如果不可独立验证，会增加交付风险 | 每个 phase 有可观察验收，不按 UI/schema/API 水平拆 |
| Good/Bad 对比 | `skill-authoring.md`、重点 skill 支撑文件 | 抽象原则不够稳定 | 高风险规则配正反 contract cases 和恢复路径 |
| Hooks guardrail 测试 | `scripts/tests/test_*command_guard*` | 参考项目列出危险 git 命令 | 复核 `git branch -D`、`git checkout .`、`git restore .`、`git clean -fd` 等用例 |

### 去掉坏影响

| 坏影响 | 推荐动作 | 理由 |
|---|---|---|
| 把所有参考方法塞进 `agents/AGENTS.md` | 不做；只保留极短全局原则 | 当前 `AGENTS.md` 已承担事实纪律、验证、边界、TDD、gitops，继续膨胀会削弱权威性 |
| 直接复制 `.claude-plugin/plugin.json` | 不做；保持 `coding-skills/catalog.json` 为 SSOT | 双 registry 会制造漂移 |
| 直接复制 Claude hook shell 脚本 | 不做；只吸收危险命令列表到 Python hook 测试 | 本仓库已有 `command_guard.py`，复制 shell hook 会产生规则冲突 |
| 默认 inline 更新 `CONTEXT.md` / ADR | 改为“建议候选块，批准后写入” | 与 Surgical Changes 和先 scope 后实现的纪律有张力 |
| 默认创建 `.out-of-scope/` 文件 | 只在重复出现、已裁决的 enhancement 上写 | 避免把 scope 控制变成新文档噪音 |
| 吸收 `caveman` 人格 | 不吸收 | 与中文事实纪律、风险表达、`readable-*` 体系冲突 |

## 按资产的改造计划

### `agents/AGENTS.md`

总体裁决：不做大改。

可选微调：

- 增加一条短规则：长期交接产物优先写行为契约、接口和验收标准；短期 review finding 才使用精确 `file:line`。
- 增加一条短规则：发现用户术语、代码术语、文档术语冲突时，列为待决策，不静默替换。

不建议加入：

- `grill-with-docs` 全流程。
- deep module 词汇表全文。
- `.out-of-scope/` 写入规则全文。
- issue tracker triage 细节。

理由：`agents/AGENTS.md` 已明确“细则优先下沉，避免全局上下文膨胀”。这些内容都可以放到 skills 或 docs。

### `coding-skills/`

优先改善现有 skill，不新增同名 skill。

| 目标 skill | 改造 | 类型 | 优先级 |
|---|---|---|---|
| `think-refine` | 加入“一次一个问题、每题给推荐答案、能读代码就不问用户” | 改善 | P1 |
| `think-scope` | 稳定术语冲突输出，必要时建议 CONTEXT 候选块 | 改善 | P1 |
| `think-plan` | phase 拆分采用 vertical slice，长期 handoff 用 Durable Brief 模板 | 改善 | P1 |
| `think-architecture` | 加入极简 ADR 触发条件和术语冲突检查 | 改善 | P2 |
| `think-quality` | 补充 deep module 语言、deletion test、locality、leverage | 改善 | P2 |
| `dev-long-task-scaffold` | 输出长期 agent brief，避免易腐 line number | 改善 | P2 |
| `guard-close` | 支持可选 out-of-scope 记录建议 | 新增能力 | P2 |
| `dev-tdd` | 已吸收 vertical slice；只维护，不扩写 | 保持 | P3 |
| `dev-debug` | 已吸收反馈环目录；只维护，不扩写 | 保持 | P3 |

### `commands/`

适合新增动词型入口，但要默认 dry-run。

| Command | 作用 | 副作用边界 | 优先级 |
|---|---|---|---|
| `/to-prd` | 把当前上下文整理成 PRD | 默认只生成 markdown；发布 issue 前走 `guard-gitops` | P3 |
| `/to-issues` | 把已批准 plan 拆成 vertical slice issues | 默认 dry-run；远程创建前确认 | P3 |
| `/triage` | 对 issue 做状态机判断 | 默认输出建议；改 label/comment/close 前确认 | P3 |
| `/zoom-out` | 手动请求更高层上下文说明 | manual-only，不自动触发 | P3 |

不建议新增 `/caveman`。本仓库已有 `readable-final-answer`，而且全局要求中文和事实纪律。

### `scripts/hooks/` 与验证脚本

| 资产 | 改造 | 类型 | 优先级 |
|---|---|---|---|
| `scripts/verify_skills.py` | 可选支持 `manual-only` 字段校验 | 新增 | P2 |
| `scripts/verify_skills.py` | 对长 skill 输出 progressive disclosure warning，而不是硬失败 | 改善 | P2 |
| `scripts/hooks/command_guard.py` 测试 | 加入参考项目危险 git 命令样例 | 改善 | P1 |
| `scripts/hooks/context_capsule.py` | 只注入短 capsule，不注入长方法论 | 去坏影响 | P2 |
| 新 scanner | 扫 durable brief 是否缺 acceptance criteria、长期 brief 是否过度依赖 line number | 新增 | P3 |
| 新 scanner | 扫 out-of-scope 文件格式 | 新增 | P3 |

## 分阶段执行路线

### Phase 1：文档层吸收，不改运行时

目标：先把可复用模式写清楚，避免直接改 skill 造成 prompt surface 变化。

产物：

- 在 `docs/software-engineering-research/skill-patterns.md` 增加指令-知识分离、out-of-scope 记忆库、durable brief 写法。
- 在 `docs/software-engineering-research/skill-authoring.md` 增加 `LANGUAGE.md` / `_Avoid_` 词汇表推荐实践。
- 在 `docs/software-engineering-research/skill-authoring.md` 增加 Good/Bad contract cases 的适用规则。

验收：

- `python3 scripts/verify_skills.py` 通过。
- 文档中明确“不默认创建 CONTEXT/ADR/out-of-scope”。

### Phase 2：低风险 skill 改善

目标：改善需求澄清、计划拆分和长期交接。

产物：

- `think-refine` 加入 grilling 的三条核心约束。
- `think-plan` 加入 vertical slice phase 和 durable brief 模板。
- `think-architecture` 加入极简 ADR 触发条件。
- `guard-close` 增加 out-of-scope 候选记录，但不默认写文件。

验收：

- `python3 scripts/verify_skills.py` 通过。
- 用 2-3 个模拟任务检查：小修复不会被过度追问，大任务会形成更清晰的 scope 和验收标准。

### Phase 3：schema 与 hook 层

目标：把能机器检查的规则下沉，不靠自然语言提醒。

产物：

- 设计 `manual-only` 字段是否进入 `coding-skills/catalog.json`。
- 若批准，更新 `scripts/verify_skills.py` 和相关测试。
- 扩充 command guard 的危险 git 命令用例。
- 可选新增 durable brief / out-of-scope scanner。

验收：

- `python3 -m unittest discover -s scripts/tests -p "test_*.py"` 通过。
- `python3 scripts/verify_skills.py` 通过。
- 新增 scanner 若存在，必须有 fixture 覆盖通过/失败样例。

### Phase 4：issue workflow 命令

目标：把 PRD、issue、triage 做成用户显式触发的 command，而非自动 skill。

产物：

- `/to-prd` dry-run command。
- `/to-issues` dry-run command。
- `/triage` recommendation command。

验收：

- 默认不触碰远程 issue tracker。
- 需要写 GitHub/GitLab/Linear 前必须进入 `guard-gitops`。
- 输出以 vertical slice、durable brief、out-of-scope 为核心，而不是按代码层水平拆任务。

## 明确不吸收

| 项目 | 不吸收原因 |
|---|---|
| 平坦 skill 目录 | 本仓库 50+ skill 需要 domain-prefix 与 catalog 治理 |
| `.claude-plugin/plugin.json` 作为注册 SSOT | 本仓库已有 `coding-skills/catalog.json` 和 `scripts/verify_skills.py` |
| `link-skills.sh` 安装模型 | 面向 Claude Code，不适配多 agent dotfiles |
| `caveman` | 与中文事实纪律、验证证据、风险表达冲突 |
| 默认 HTML artifact | 本仓库已有 `readable-html-artifact`，且 HTML 只适合复杂可视化产物 |
| 默认 inline 改文档 | 与 Surgical Changes 有张力，应改为候选块 + 批准后写入 |
| 直接复制 shell git hook | 本仓库已有 Python command guard，复制会造成双重规则 |

## 最终裁决

优先吸收的不是 skill 名称，而是以下 6 个机制：

1. 指令和知识分离：让长 skill 的执行路径更清晰。
2. 一次一个问题 + 推荐答案：让澄清成为低负担交互。
3. 领域词汇表 + `_Avoid_`：降低术语漂移和上下文浪费。
4. Durable Brief：让长期交接围绕行为契约，而不是易腐路径。
5. `.out-of-scope/`：把“不做什么”变成可追溯资产。
6. Manual-only 语义：让反思类、危险操作类能力只由用户显式触发。

本仓库已经具备更强的验证、边界、gitops 和跨 agent 约束，因此不应被 `mattpocock/skills` 替换。正确路线是：保留本仓库分层治理，把参考项目的轻量 prompt 技巧和文档记忆机制吸收到 docs、skills、commands、hooks 的对应层级。

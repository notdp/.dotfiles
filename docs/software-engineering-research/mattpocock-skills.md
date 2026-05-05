# mattpocock/skills 调研

调研对象：`refs/mattpocock/skills`，来源为 `https://github.com/mattpocock/skills`，本次读取 commit `b843cb5`。

## 项目定位

该项目把 agent 能力拆成小型、可组合、可移植的 skills，而不是用一个大流程框架接管开发。核心目标是减少常见失败模式：

1. 需求未对齐：用 `grill-me` / `grill-with-docs` 做高强度澄清。
2. 领域语言不一致：用 `CONTEXT.md` 做项目术语 SSOT。
3. 代码反馈环不足：用 `tdd` 和 `diagnose` 强制测试、复现、验证。
4. 架构退化：用 `improve-codebase-architecture` 定期寻找深模块机会。

## 结构与安装模型

主要结构：

- `README.md`：quickstart、设计动机、skill 清单。
- `CLAUDE.md`：该 repo 的维护约定。
- `CONTEXT.md`：该 repo 自己的领域术语。
- `.claude-plugin/plugin.json`：Claude plugin 发布清单。
- `skills/engineering/`：日常工程 skill。
- `skills/productivity/`：生产力 skill。
- `skills/misc/`：低频工具 skill。
- `skills/personal/`：个人环境相关 skill。
- `skills/deprecated/`：废弃 skill。
- `scripts/list-skills.sh`、`scripts/link-skills.sh`：本地列举和 symlink 安装辅助脚本。

安装路径面向 Claude Code：

```bash
npx skills@latest add mattpocock/skills
```

随后运行 `setup-matt-pocock-skills`，写入 agent 配置和项目级文档，包括 issue tracker、triage labels、domain docs。

该安装模型不要直接搬进本仓库：它面向 Claude Code plugin / hooks，本仓库的 SSOT 是 `skills/catalog.json` 与 `scripts/verify_skills.py`。

## Skill 清单

### Engineering

| Skill | 作用 | 关键文件 |
|---|---|---|
| `diagnose` | 困难 bug / 性能回归诊断：反馈环、复现、假设、插桩、修复、回归测试 | `skills/engineering/diagnose/SKILL.md` |
| `tdd` | Red-Green-Refactor，按 vertical slice 增量开发 | `skills/engineering/tdd/SKILL.md` |
| `grill-with-docs` | 追问计划，同时维护 `CONTEXT.md` 和 ADR | `skills/engineering/grill-with-docs/SKILL.md` |
| `improve-codebase-architecture` | 找 shallow module，提出 deepening opportunities | `skills/engineering/improve-codebase-architecture/SKILL.md` |
| `triage` | issue triage 状态机 | `skills/engineering/triage/SKILL.md` |
| `to-prd` | 把当前对话整理成 PRD 并提交到 issue tracker | `skills/engineering/to-prd/SKILL.md` |
| `to-issues` | 把 PRD / plan 拆成 vertical-slice issues | `skills/engineering/to-issues/SKILL.md` |
| `zoom-out` | 请求 agent 给出更高层代码地图与上下文 | `skills/engineering/zoom-out/SKILL.md` |
| `setup-matt-pocock-skills` | 初始化项目级 agent docs 和 issue tracker 配置 | `skills/engineering/setup-matt-pocock-skills/SKILL.md` |

### Productivity

| Skill | 作用 | 关键文件 |
|---|---|---|
| `grill-me` | 非代码场景的高强度计划追问 | `skills/productivity/grill-me/SKILL.md` |
| `caveman` | 极简沟通模式，减少输出冗余 | `skills/productivity/caveman/SKILL.md` |
| `write-a-skill` | 编写新 skill 的结构、description、progressive disclosure 规范 | `skills/productivity/write-a-skill/SKILL.md` |

### Misc / Personal / Deprecated

`misc` 包含 Claude Code git hooks、Husky pre-commit、Total TypeScript 生态迁移、课程 exercise scaffold。`personal` 和 `deprecated` 更偏作者个人流程或历史遗留，不适合直接吸收。

## 可复用机制

### 1. 反馈环优先的诊断模型

`diagnose` 的核心不是“想原因”，而是先构造 agent 可反复运行的 pass/fail signal。它给出反馈环优先级：

1. 失败测试。
2. `curl` / HTTP script。
3. CLI fixture + stdout diff。
4. Headless browser script。
5. captured trace replay。
6. throwaway harness。
7. property / fuzz loop。
8. bisection harness。
9. differential loop。
10. HITL bash script。

这个机制比单纯“先复现”更可执行。它还要求 debug log 带唯一 prefix，收尾时 grep 清理，能减少临时日志遗留。

### 2. Vertical slice TDD

`tdd` 明确反对 horizontal slicing：

- 错误：先写一批测试，再写一批实现。
- 正确：一个行为一轮 `RED -> GREEN`，再进入下一个行为。

该项目把每个测试看成 tracer bullet：测试要验证 public interface 的 observable behavior，不测私有实现，不 mock 内部协作者。

### 3. 领域术语 SSOT + 极简 ADR

`grill-with-docs` 的关键机制：

- `CONTEXT.md` 只记录 domain expert 有意义的术语。
- 术语冲突要进入 `Flagged ambiguities`。
- 发现模糊词时立即要求精确化。
- 决策只有同时满足 hard to reverse、surprising without context、real trade-off 时才写 ADR。
- ADR 可以只有 1-3 句，避免模板化文档负担。

这与本仓库“命名即文档”“DDD 统一语言”“不要过度堆 AGENTS.md”的原则一致。

### 4. 架构 deepening 语言体系

`improve-codebase-architecture` 以一套固定词汇审视架构：

- Module：有 interface 和 implementation 的任何单元。
- Interface：调用者必须知道的一切，不只是签名。
- Depth：接口杠杆，一小块 interface 背后承载大量行为。
- Leverage：调用者从 depth 获得的能力。
- Locality：维护者从 depth 获得的变更集中度。

最有价值的判断是 deletion test：假设删除一个模块，复杂度是消失，还是扩散回 N 个调用方。前者说明模块可能只是 pass-through，后者说明模块在隐藏复杂度。

### 5. Durable Agent Brief

`triage/AGENT-BRIEF.md` 把 issue 上给 AFK agent 的说明当作 contract。重点：

- 描述行为和接口，不写过程。
- 不引用 line number，少引用易过期 file path。
- 写 current behavior、desired behavior、key interfaces、acceptance criteria、out of scope。

这适合吸收到本仓库的计划、PR、issue 交接模板中。

### 6. Out-of-scope 知识库

`.out-of-scope/*.md` 和 `triage/OUT-OF-SCOPE.md` 把拒绝过的 feature request 沉淀下来，后续 triage 先查旧决策，避免重复讨论。

这适合和 `guard-close` 的 scope 控制结合，但应作为可选记录，而不是每次任务默认创建文档。

### 7. Skill authoring 的 progressive disclosure

`write-a-skill` 的可吸收点：

- `description` 是 agent 路由 skill 的主要依据，必须写清触发条件。
- `SKILL.md` 超过约 100 行时拆 reference。
- 确定性操作下沉到 scripts。
- bundled resources 只做一层引用，避免 skill 加载时带入过多上下文。

本仓库已有类似规范，可借鉴其更短的 checklist。

## 建议吸收到本仓库的内容

### 高优先级

| 吸收项 | 落点 | 原因 |
|---|---|---|
| 反馈环优先级列表 | `skills/dev-debug/SKILL.md`、`docs/software-engineering-research/debug.md` | 让调试从“复现”升级为“构造可运行信号” |
| debug log 唯一 prefix + 收尾 grep 清理 | `skills/dev-debug/SKILL.md`、`guard-diff-scan` | 降低临时插桩遗留风险 |
| 禁止 horizontal TDD | `skills/dev-tdd/SKILL.md`、`docs/software-engineering-research/tdd.md` | 防止批量写测试导致测试脱离真实实现 |
| 测试 public interface 的 observable behavior | `skills/dev-tdd/SKILL.md` | 强化“行为而非实现” |
| `CONTEXT.md` 格式和冲突术语规则 | `think-refine`、`think-plan`、`think-architecture` | 支撑统一语言和命名质量 |
| 极简 ADR 触发条件 | `think-architecture`、`think-plan` | 避免过度文档化，同时记录不可见约束 |
| deletion test、depth、locality | `think-quality`、`dev-refactor` | 给重构和架构评审提供更可执行的判断标准 |

### 中优先级

| 吸收项 | 落点 | 原因 |
|---|---|---|
| Durable Agent Brief 模板 | `think-plan`、`guard-ship` | 适合 issue / PR / session handoff |
| Out-of-scope 决策记录 | `guard-close`、未来 issue workflow | 减少相同需求反复进入讨论 |
| 3+ radically different interface designs | `think-compare`、`dev-refactor` | 适合接口重构前做方案分叉 |
| skill authoring checklist 精简版 | `docs/software-engineering-research/skill-authoring.md` | 可增强现有 skill 编写规范的可执行性 |

### 低优先级或不建议直接吸收

| 内容 | 原因 |
|---|---|
| `.claude-plugin/plugin.json`、`link-skills.sh` | 面向 Claude Code，不符合本仓库 `skills/catalog.json` 和 Factory/Droid 约定 |
| `setup-pre-commit` | Node/Husky 生态特定 |
| `migrate-to-shoehorn`、`scaffold-exercises` | 作者课程 / Total TypeScript 生态特定 |
| `obsidian-vault` | 个人路径和个人工作流特定 |
| `caveman` | 与中文输出、`readable-*` skill 体系重叠，风格过度压缩 |

## 兼容性注意事项

1. skill 命名不兼容：参考 repo 使用 `tdd`、`diagnose`，本仓库使用 `dev-*` / `think-*` / `guard-*` 等前缀。
2. description 规范不兼容：本仓库由 `scripts/verify_skills.py` 强制触发前缀，不能直接搬 frontmatter。
3. 平台不兼容：参考 repo 面向 Claude Code plugin 和 hooks，本仓库应以 Factory/Droid skill catalog 为 SSOT。
4. 交互模式需改造：`grill-*` 强依赖“一次一个问题”，本仓库在执行任务时应优先自查代码，只有关键决策缺失才 AskUser。
5. 文档生成需 lazy create：只有用户要求沉淀或 skill 明确产物为文档时才创建 docs，不能默认扩 scope。
6. 远程 issue 操作必须过 `guard-gitops`：`to-prd`、`to-issues`、`triage` 都可能修改仓库外状态。

## 推荐吸收路线

1. 更新 `docs/software-engineering-research/debug.md`：加入反馈环优先级、非确定性 bug 提升复现率、debug prefix 清理。
2. 更新 `docs/software-engineering-research/tdd.md`：加入 vertical slice TDD 和 horizontal slicing 反模式。
3. 增强 `skills/dev-debug/SKILL.md`：把“构造反馈环”设为 Phase 1，未建立反馈环前不进入猜测。
4. 增强 `skills/dev-tdd/SKILL.md`：明确一次只写一个行为测试，禁止批量 RED。
5. 增强 `skills/think-quality/SKILL.md` 或 `skills/dev-refactor/SKILL.md`：加入 deletion test、depth、locality 判断。
6. 可选新增或并入现有 skill：领域术语 SSOT 与极简 ADR 规则，优先放入 `think-refine` / `think-plan`，不要新增长期文档负担。

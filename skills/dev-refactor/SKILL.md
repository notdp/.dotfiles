---
name: dev-refactor
description: 当代码出现重复、结构债、可读性下降或需要基于历史摩擦点定位重构对象时使用；产出可勾选的 Refactor Spec / Todo List 与重构范围裁决。
argument-hint: <branch|uncommitted|history|文件/目录/符号名>
---

# Refactor

定位：**先判断哪里值得改、再判断怎么改、最后才动手**。重构的本质是降低后续修改成本，不是把代码变得"更优雅"。

## 1. 确定范围

解析 `$ARGUMENTS`：

| 模式 | 触发 | 含义 |
|---|---|---|
| `branch` 或分支名 | `main` / `develop` / ... | 比较当前分支与目标分支差异 |
| `uncommitted` | `uncommitted` | 重构当前未提交变更（staged + unstaged） |
| `history` | `history` 或 `history:<N>` | **基于 git 历史摩擦点**找重构对象（默认窗口 200 commit / 6 个月） |
| 路径 / 符号 | 文件/目录/类名/函数名 | 直接以该对象为目标 |
| 留空 | — | 询问用户选哪种模式；如能从对话推断范围（"简化登录模块"），先确认再继续 |

### 范围红线

- 工作树必须干净。dirty working directory 上重构会让 diff 失真，先 `commit` / `stash`。
- 范围太大（>20 文件且非 history 模式）必须先收窄；否则回到 `/think-quality` 或 `/think-map` 缩 scope。

## 2. 历史摩擦点分析（history 模式）

**触发**：范围 = `history`，或用户希望"找该重构的地方"而非指定具体文件。

### 派发只读子任务

派发**只读子任务**（subagent / parallel agent / sub-call，按当前 agent 平台能力命名；纯 LLM 模式可降级为主流程顺序执行）。契约如下：

```
Goal: 在 <scope=仓库或子路径> 的 <window=最近 N 提交 / M 个月> 内，找出 refactor hotspots。
Constraints:
  - 只读，不修改任何文件
  - 不调用 web，只用 git log + 代码读取 + Grep
  - 输出 top-K（K=10）截断，避免冗长
Steps:
  1. git log --pretty=format: --name-only --since=<window>  → churn 排序
  2. git log --name-only --pretty=format:"%H"               → 同 commit 共变文件对（≥3 次共现）
  3. git log --grep='fix\\|bug\\|hotfix' --name-only         → bug 修复触及最多的文件
  4. 对 top-K 文件读代码 + 简单复杂度估计（行数、嵌套深度、分支数、函数长度）
  5. 标注每个 hotspot 的推断 smell（基于代码读取，不是仅基于数字）
Return（固定格式）:
  | 文件 | churn | 共变邻居 | 复杂度 | bug 触及 | 推断 smell |
```

#### Token / 工具调用预算（硬约束）

子任务必须在以下预算内完成，否则截断输出：

- 工具调用 ≤ 5 次（git log 命令 + 必要的 Read/Grep，超过即收尾）
- 输出 ≤ 800 tokens（超过用 top-K 截断 + 省略号）
- 默认先跑 `git log` 概览（churn / co-change / bug-touch 三条），**不要**直接读全文件；只对 top-K 候选做选择性 Read
- 输出固定使用上面的卡片表格，**不要**自由叙述、不要分章节、不要添加结论性建议

预算耗尽时的优雅降级：
- 已完成 churn 排序但未做共变分析 → 输出仅含 churn 列的简表，标注 `[预算截断: 共变 / bug-touch 未跑]`
- top-K 文件未全部 Read → 只填能填的 smell 列，未读的标 `[未读]`

### 自动降级

- 历史 < 30 commit → 提示"历史信号不足，回退到结构分析"，跳过本节
- squash-merge-only 仓库 → 在报告里标 `[未验证]`，churn 信号会失真
- 大仓库默认窗口超时 → 缩到 100 commit / 3 个月

### 主流程裁决

子任务的输出**只是证据**，不是结论。主流程必须：

1. 读 hotspot 文件代码，确认 smell 真实存在
2. 排除"高 churn 但本来就该频繁改"的文件（如 i18n 资源、配置中心）
3. 选 top P0/P1 hotspot 进入第 3 步

## 3. 结构分析

对每个候选目标：

- 读代码，理解职责和调用关系
- Grep / Glob 搜索所有引用点（不凭记忆）
- 检查测试覆盖：关键路径无测试 → 进入第 4 步
- 必要时调用 `/think-quality`，按 PIEV（Predictable / Isolated / Explicit / Verifiable）和六维度（Boundary / Locality / Convention / Explicitness / Testability / Diff Purity）归因

每条候选必须同时满足，否则不入 spec：

1. **有明确 smell** —— 能指出具体问题，不是"感觉可以更好"
2. **收益 > 风险** —— 改完确实更好读或更好改
3. **范围可控** —— 影响的文件和调用者数量合理
4. **不需同时改行为** —— 必须改行为才能重构的，拆成两步

### Deepening 候选判断

当候选目标是一组浅模块或过度拆碎的函数时，额外检查：

- **Deletion test**：删除该模块后，复杂度是消失，还是扩散到多个调用者？
- **接口杠杆**：调用者学习少量接口，是否能获得大量行为？
- **局部性**：bug、规则、验证是否能集中到一个接口后面？
- **接口位置真实性**：是否存在至少两种真实适配器，还是只为了测试增加间接层？
- **依赖类别**：in-process / local-substitutable / remote but owned / true external，决定 characterization 测试方式。

如果 deepening 成立，重构方向优先是“把规则收进更深模块，并通过该模块接口测试”，而不是继续给浅模块堆更多单测。

## 4. 安全网评估

行为不变是重构的硬约束，验证手段必须先于动手决定。

| 现有测试 | 改动风险 | 安全网决策 |
|---|---|---|
| 已覆盖关键路径 | 低 | 直接重构，改后跑测试 |
| 已覆盖关键路径 | 中 / 高 | 重构前跑基线、记录输出，逐步对比 |
| 无 / 弱覆盖 | 低 | 直接重构 + 改后 smoke 验证 |
| 无 / 弱覆盖 | 中 / 高 | **先写 Characterization / Golden Master 测试**，再开始重构 |

### Characterization 测试模板（无测试时使用）

```
1. 找几组真实 input（生产样本、最近 bug 复现 case、边界值）
2. 当前实现 → 跑出 output → 锁存为期望值（视为"现状契约"）
3. 重构每一步后跑同一组 input，diff 期望与实际
4. 重构完成后，characterization 测试可保留或替换为更精确的单元测试
```

参考：Feathers《Working Effectively with Legacy Code》、Tornhill《Your Code as a Crime Scene》。

## 5. 输出 Refactor Spec（核心产出）

**不在本步执行任何修改**。产出可勾选的 todo list / spec，等用户批准后再进入第 6 步。

### 固定输出格式

```markdown
## Refactor Spec

### 摘要
- 范围：<branch / uncommitted / history / 路径>
- 总条目：<N>（P0=<x> / P1=<y> / P2=<z> / P3=<w>）
- 估计 diff 规模：<行数 / 文件数>
- 安全网状态：<已就绪 / 需先补 characterization / 风险低无需安全网>

### Hotspot 证据（仅 history 模式）
| 文件 | churn | 共变邻居 | 复杂度 | bug 触及 | 推断 smell |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

### Todo List
| # | 优先级 | 文件:行 | Smell | Fowler 手法 | 改善维度 | 安全网 | 验证方式 | 依赖项 |
|---|---|---|---|---|---|---|---|---|
| 1 | P0 | path:42-78 | 长函数+混合职责 | Extract Function / Move Function | Boundary, Locality | 已有 unit | 跑 X 测试 | — |
| 2 | P1 | ... | ... | ... | ... | 需 characterization | ... | 依赖 1 |

### Deepening 评估（如适用）
| 候选模块 | Deletion test | 接口杠杆 | 局部性 | 依赖类别 | 测试策略 |
|---|---|---|---|---|---|
| ... | 复杂度会扩散到 N 个调用者 | 高 / 中 / 低 | 高 / 中 / 低 | in-process / local-substitutable / remote-owned / external | ... |

### 执行顺序
1. 先建安全网（characterization / golden master）
2. **Tidy First**：机械整理（rename / extract / 删死代码 / 收敛命名）
3. 结构变更（move / split / merge / replace conditional with polymorphism）
4. 二次清理（内联、消重复、删冗余防御）

### 不做的事（Out of Scope）
- 任何行为变更
- <按需列出：性能优化、新增功能、跨模块重组等>
```

### Fowler 手法速查（与速查表对齐 Fowler 命名）

| Smell | Fowler 手法 |
|---|---|
| 函数太长，有独立逻辑块 | **Extract Function** |
| 同样代码出现多次 | **Extract Function** + **Parameterize Function** |
| 一堆 if-else / switch 做类似事 | **Replace Conditional with Polymorphism** / **Replace Type Code with Subclasses** / 数据驱动表 |
| 命名不清或前后不统一 | **Rename Variable / Function / Class**（含注释、i18n） |
| 文件太长，职责混杂 | **Split Phase** / **Extract Class** / **Move Function** |
| 嵌套太深 | **Replace Nested Conditional with Guard Clauses** |
| 单调用点函数无复用价值 | **Inline Function** |
| 多余注释 | 删除或改写 |
| 冗余防御性代码 | 移除不可触发分支 |
| 死代码 | 删除（先全局 Grep 确认） |
| 跨文件高耦合（共变信号强） | **Move Function** / **Move Field** / **Combine Functions into Class** |

### 用户确认方式

- **P0/P1**：逐条确认或整体批准
- **P2/P3**：作为一组，用户选择全部 / 挑选 / 跳过
- **不批准**的条目移入"Out of Scope"，不要静默执行

## 6. 执行

每条 todo 都是一个原子变更，遵守以下铁律：

### 铁律

- **行为不变** —— 只改结构，不改功能。任何行为变更必须拆出独立 commit/PR。
- **Tidy First**（参 Beck《Tidy First?》）—— Tidying（整理）和 behavior change（行为修改）分 commit；同 PR 内也要分开顺序提交。
- **先搜后改** —— 改任何符号前先 Grep 确认所有位置，包括注释、文档、i18n、动态字符串。
- **小步前进** —— 一次一条 todo，改完立即跑该路径下最小验证集。
- **不混杂** —— 顺手优化、顺手加 try/catch、顺手补类型，全部排到下一条 todo 或 backlog。

### Commit 约定

```
refactor(scope): <Fowler 手法> <symbol>
# 例
refactor(auth): Extract Function validateToken from login
refactor(billing): Replace Conditional with Polymorphism (PaymentMethod)
```

### 每步自检

- 可读性变好了？密度高但不牺牲清晰度
- 数据/常量集中了？没有散落各处
- 命名统一？全局名详细、局部名精简
- 没引入不需要的抽象？（YAGNI）
- 耦合变松、依赖方向更合理？
- 后续修改是否更局部、更显式、更易验证，而不是只是"看起来更优雅"？

## 7. 验证（行为不变）

### 自动探测项目验证命令

查 `package.json` scripts、`Makefile`、`pyproject.toml`、`Cargo.toml` 等，跑 typecheck / lint / test，全部通过。

### 行为对比

- 有 characterization / golden master：跑同一组 input，diff 期望与实际，**期望为空**
- 有原有测试：所有用例仍绿，且没有用例被悄悄改写或删除
- 二者都没有：在执行前应已识别出"先补安全网"的 todo；如果没补就直接做了，回退

### Diff 审查

逐 commit 看 git diff：

- 每个 commit 单一目的（Tidy 与 behavior 不混）
- 没有意外删除或新增逻辑分支
- 引用全部更新（包括注释、i18n、文档）
- diff 体量与 spec 估计一致；过大说明 scope 失控，回退切片

### 收尾问句

重构后的代码比之前更易读、更易改吗？如果不是，回退。

## Gotchas

- 行为变更和重构混在同一 diff 里，会让 review 和回归验证失真
- 不要因为"看着丑"就动手；先确认 smell、收益和影响面
- 不要在冷代码（极少修改的稳定模块）上做美化式重构，是浪费
- 命名、提取、删除死代码前必须全局搜索引用
- 改完验证成本反而更高，通常不是好重构
- history 模式下 churn ≠ 一定要改；hotspot 是**候选**，主流程裁决才是结论
- 子任务的输出永远是证据不是判断；不要直接采纳为重构计划

## 跨 agent 适配

派发子任务的具体形式按当前 agent 平台能力命名：

- 有只读子任务能力的平台：把上述契约作为完整 prompt 派发给只读分析单元
- 无并行子任务能力的平台：主流程顺序执行（先跑 git log 概览，再选择性 Read）
- 子任务命名、调用方式、工具白名单由当前 agent 平台决定，不在 skill 内硬编码
- 任何模式下"只读 + 预算 + 固定输出格式"三条不可降级

## 扩展阅读

- `docs/software-engineering-research/architecture-deepening.md`

### Framework-aware dead code 白名单

删死代码前，必须排除以下模式（这些不是死代码，仅看显式引用会误删）：

- ORM 基类继承（SQLAlchemy `declarative_base`、Django `Model`、Pydantic `BaseModel`）—— 框架按元类/注册表收集，不靠 import
- IaC 资源类（CDK `Stack`、Terraform module）—— 由 synth/apply 阶段实例化
- React/JSX 组件 —— 即使没有显式 import，也可能在路由表、动态加载点、字符串映射中被使用
- 装饰器注册（`@app.route`、`@register`、`@hook` 类）—— 引用发生在装饰器执行期
- 通过 `importlib` / `require` / `__import__` 等动态加载的模块
- 测试 fixture（pytest fixtures、jest setup）—— conftest.py 名字本身就是契约
- 类型定义文件（`.d.ts`、stub 文件）—— 只在编译/类型检查阶段被使用

判断流程：先搜框架特征（基类、装饰器、约定路径），再搜显式引用。两类都没命中，再判定为死代码。

## 禁止

- 重构中夹带功能变更
- 无安全网下做中高风险重构
- 凭记忆改代码不搜索
- 为"优雅"引入不必要的抽象
- dirty working directory 上重构（先 commit/stash）
- 在 hotspot 之外做美化式重构
- 直接执行子任务输出的"重构清单"，跳过主流程裁决

## 关联技能

- 范围或结构问题不清 → `/think-quality` / `/think-map`
- 行为变更（非纯重构）→ `/dev-tdd`
- 重构完成 → `/guard-verify` 验证行为不变
- 重构后交付 → `/guard-review` → `/guard-ship`
- 大型跨阶段重构 → `/dev-large-delivery`
- 连续失败 2 次 → `/think-unstuck`

## 扩展阅读

- Fowler《Refactoring》（手法目录）
- Beck《Tidy First?》（Tidy 与 behavior change 分离）
- Tornhill《Your Code as a Crime Scene》/ code-maat（hotspot 分析）
- Feathers《Working Effectively with Legacy Code》（characterization 测试）

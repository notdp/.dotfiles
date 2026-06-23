---
name: dev-tdd
description: 当新增单个功能、修复 bug 或调整某个可观察行为前使用；以 Red→Green→Refactor 循环驱动测试先行的开发（inner-loop verifier）。不用于纯配置/文档/样式（事后补测）；想要 spec→code→review→verify 完备链改用 /dev-complete，多 phase 长任务改用 /dev-long-run，跨子系统/不可逆大交付改用 /dev-large-delivery。
argument-hint: <功能点|bug 描述|行为变更>
---

当任务属于以下场景时使用本 skill（除非用户明确说不要）：

- 新增功能/函数/模块
- Bug 修复
- 行为变更（非纯重构）

## 核心循环

TDD 的单位是 vertical slice / tracer bullet：一个可观察行为对应一轮 RED→GREEN。不要把 RED 理解成“先批量写完所有测试”。

TDD 是 inner-loop verifier：它证明局部实现行为正确，不等于用户最终目标已经达成。用户可见功能、数据任务、模型/评测任务、复杂 Agent 流程在 TDD 通过后，仍必须用 `/guard-verify` 给出 acceptance verifier 证据。

为什么用 RED→GREEN→REFACTOR：这个循环把“先想象实现结构”改成“先定义一个可观察行为，再用最小实现证明它成立”。RED 防止测试只是复述现有代码，GREEN 防止顺手加料，REFACTOR 防止在未验证状态下清理结构。

```
RED    → 写一个失败测试（一个行为、名字说清行为）
       → 跑测试，确认失败原因是"功能缺失"而非 typo
GREEN  → 写最少的代码让测试通过（不加料、不优化）
       → 跑测试，确认通过 + 其他测试不挂
REFACTOR → 消除重复、改名、提取（保持绿灯）
```

## 判断启发式

能在写实现之前写 `expect(fn(input)).toBe(output)` → TDD

不能（UI 布局、配置、胶水代码、原型探索）→ 标准流程，事后补测试

### 禁止 Horizontal Slicing

错误做法：

```text
RED:   一次写 test1, test2, test3, test4
GREEN: 一次写 impl1, impl2, impl3, impl4
```

正确做法：

```text
RED→GREEN: test1→impl1
RED→GREEN: test2→impl2
RED→GREEN: test3→impl3
```

原因：批量测试通常验证想象中的结构，而不是刚刚确认过的真实行为；它更容易测试数据形状、函数签名和内部协作，而不是用户或调用方可观察到的结果。

## 跳过条件

用户明确说以下任一时，不强制 TDD：
- "不要 TDD" / "跳过测试" / "先探索"
- AGENTS.md 或项目配置中禁用了 TDD
- 纯配置/文档/样式变更

## Spec Contract 消费

如果上游 spec 中存在 `# spec-contract` YAML 块（通常来自 /think-plan），在进入 RED→GREEN 循环前：

1. 读取 checks 列表，每条 check 对应至少一个测试用例或显式 skip 理由
2. 读取 non_goals 列表，确认不为排除项写测试
3. 读取 validation_commands，在 GREEN 阶段末尾额外运行这些命令

如果没有 spec-contract 块，按现有流程从对话上下文提取验收标准。

## 测试质量

- 测试 public interface 的 observable behavior，不测实现细节
- 一个测试一个概念
- Mock 只在外部边界使用（fs/http/db），不 mock 内部纯函数
- 优先通过真实接口验证结果；不要绕过接口直接查内部状态
- 提交模式：`test(scope): failing test` → `feat(scope): implement`

### 好测试信号

- 名字描述“系统能做什么”，不是“调用了哪个内部函数”
- 重构内部实现时不需要改测试
- 断言具体行为或结果，不只断言存在
- 测试 setup 体现业务场景，而不是复刻实现结构

## 测试分层（避免只测底层）

vertical slice 不等于"只测最底层"。一个功能点该测在哪一层，取决于它的**可观察面**，不是取决于哪层最好写：

| 层级 | 锁住什么 | 什么时候必须有 |
|---|---|---|
| 功能点级 | 用户/调用方可观察的行为、端到端结果 | 新增/改用户可见功能；修 bug 的复现场景 |
| 集成级 | 多模块/边界协作（DB、IO、跨函数契约） | 改动跨模块或涉及外部边界 |
| 单元级 | 纯函数、算法、边界条件 | 有独立逻辑分支或边界值 |

规则：

- 优先写锁住"功能点"的测试——它防回归最有效；不要用一堆单元测试冒充功能覆盖。
- **修 bug 必须先有一个功能点级或集成级的复现测试（红）再修**；只补单元测试不算覆盖了这个 bug。
- 不是每个改动都要三层全覆盖。每个功能点映射到**最能锁住其行为的那一层**，其余层显式说明为何不需要（重构/胶水/纯配置）。这是"映射 + 缺口说明"，不是"每层都加测试"的配额。

## Anti-Rationalization Guard

不要在 RED 之前给自己找退出借口。常见借口与反驳：

| 借口 | 反驳 |
|---|---|
| "代码太简单不用测" | 简单代码也会坏，写一个测试只要 30 秒 |
| "先实现再补测试更快" | 那叫 "test-after"，不叫 TDD |
| "这只是 spike，不需要 TDD" | 把它标成 spike，不要混进 main |
| "测试通过了 = 任务完成" | TDD 只完成 inner-loop；还需要 refactor 和 acceptance verifier |
| "外部接口我控不了，没法测" | mock 边界即可，不要让"难"代替"不做" |

发现自己在用以上句式说服自己跳过 RED，停一步：要么诚实标记 spike（隔离分支、不进 main），要么按 RED→GREEN→REFACTOR 走完。

## Gotchas

- 先写实现、再补测试，不叫 TDD
- 先批量写完所有测试、再批量实现，也不叫有效 TDD
- 红灯必须因为“行为缺失/不符合预期”，不能只是 typo 或测试本身坏掉
- 不允许用“新增单元测试通过”直接替代端到端、holdout/unseen 或人工可观察验收
- UI 探索、样式调整、纯配置改动不要生搬硬套 TDD
- GREEN 阶段只做让测试过的最小实现，不顺手优化、不顺手重构

## 完成门禁

所有 RED→GREEN→REFACTOR 循环完成、准备声称"TDD 完成"前，逐项确认：

| # | 检查项 | 证据 | 为什么 |
|---|--------|------|--------|
| 1 | 所有测试通过 | test runner 输出（pass count + 0 failures） | 避免 GREEN 阶段遗漏未跑测试 |
| 2 | 无新增 lint/typecheck 错误 | lint/typecheck 输出或"项目无 lint 配置" | 避免 RED→GREEN 只管测试、不管代码质量 |
| 3 | 每条 spec-contract check 有对应测试或显式 skip 理由 | check-to-test 映射表（如有 spec-contract） | 避免测试只覆盖 agent 想到的场景，遗漏 spec 约定 |
| 4 | 新增代码无 TODO/FIXME（或已关联 issue） | grep 结果 | 避免临时桩混入 main |
| 5 | 每个功能点映射到对应测试层级 | 功能点→层级映射（功能点/集成/单元，或显式豁免理由） | 避免测试只堆在单元层，漏掉用户可观察行为与回归防护 |

任一项不满足 → 回到对应步骤修复，不声称完成。

完成门禁不替代 `/guard-verify`；它只覆盖 dev-tdd 自身范围内的 inner-loop 证据。

## 扩展阅读

- `docs/software-engineering-research/tdd.md`

## 关联技能

- 发现边界混乱、规则不显式、难以落测试时 → 先 `/think-quality` 或 `/think-plan`
- TDD 完成后 → `/guard-verify` 最终验证
- 连续失败 2 次 → `/think-unstuck`

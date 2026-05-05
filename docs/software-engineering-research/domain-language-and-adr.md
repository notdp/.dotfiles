# Domain Language 与 ADR-lite

来源：`refs/mattpocock/skills/skills/engineering/grill-with-docs/CONTEXT-FORMAT.md`、`ADR-FORMAT.md`。

## 推荐方案

[确认] 领域语言文档只记录项目语境里的业务概念，不记录通用编程概念。它的目标是让人和 agent 使用同一套词，减少解释成本和命名漂移。

## CONTEXT.md 格式

```md
# {Context Name}

{一到两句说明这个 context 是什么、为什么存在。}

## Language

**Canonical Term**:
一句话定义这个概念是什么。
_Avoid_: 旧词、歧义词、别名

## Relationships

- 一个 **A** 可以产生多个 **B**
- 一个 **B** 只属于一个 **A**

## Example dialogue

> **Dev:** “这里用 **A** 还是 **B**？”
> **Domain expert:** “这里必须是 **A**，因为 ...”

## Flagged ambiguities

- “account” 曾同时表示 **Customer** 和 **User**；决议：两者分开。
```

## 写入规则

- [确认] 只写 domain expert 也会使用的概念。
- [确认] 多词同义时选一个 canonical term，其它写进 `_Avoid_`。
- [确认] 一词多义时进入 `Flagged ambiguities`，必须写清决议。
- [确认] 定义最多一句话，说明“是什么”，不要写实现细节。
- [确认] 自然出现多个上下文时，用 `CONTEXT-MAP.md` 指向各 context。
- [确认] lazy create：没有内容要写时，不提前创建空文档。

## ADR-lite

ADR 只在三条同时成立时建议创建：

1. **难回退**：以后改回来的成本明显。
2. **缺上下文会令人意外**：未来读者会问“为什么这样做”。
3. **真实 trade-off**：存在合理备选，且做了取舍。

不满足三条时，不写 ADR。ADR 可以只有 1-3 句：

```md
# {Short decision title}

{背景是什么；决定是什么；为什么这样决定。}
```

## 不要自造轮子

- 不要为每个小决定套完整 ADR 模板。
- 不要把项目百科、API 文档、实现细节塞进 `CONTEXT.md`。
- 不要默认创建文档；只有用户要求沉淀或当前 skill 明确交付文档时才创建。

## 风险与坑

- [确认] 如果术语冲突未显式解决，后续命名、测试名和 spec 会继续漂移。
- [推断] 如果把领域语言做成独立 mandatory workflow，会增加小任务摩擦；当前更适合做 `think-plan` / `think-refine` / `think-architecture` 的可选机制。

# Micro Refs Index

本文件登记短但关键的参考资料。Micro refs 是一等输入源，不混入大型 `refs/` submodule 更新流程；每条都必须有来源、状态、影响资产和复核时间。

## Fields

| Field | Meaning |
|---|---|
| `id` | 稳定短 ID，例如 `micro-2026-05-26-context-preload` |
| `source` | URL、本地路径或引用来源 |
| `captured_at` | 纳入时间 |
| `owner` | 谁加入 |
| `category` | `routing` / `hooks` / `skill-authoring` / `review` / `UI` / `security` / `context` / `workflow` |
| `summary` | 1-3 句事实摘要 |
| `key claim` | 参考真正重要的主张 |
| `evidence level` | `source` / `anecdote` / `practice` / `benchmark` / `official` |
| `mapped assets` | 可能影响的 skill、command、hook 或 doc |
| `absorption level` | L0-L5，沿用 `docs/software-engineering-research/refs-absorption-methodology.md` |
| `status` | `observe` / `candidate` / `absorbed` / `rejected` / `stale` |
| `last_checked` | 最近复核时间 |

## Status Rules

| Status | Meaning | Next action |
|---|---|---|
| `observe` | 只记录，证据不足或暂不适配 | 下轮复核是否仍相关 |
| `candidate` | 可进入 review packet | 输出证据、风险和 human decision |
| `absorbed` | 已进入本仓库某个资产 | 保留证据和落点 |
| `rejected` | 明确不吸收 | 记录原因，避免重复讨论 |
| `stale` | 来源失效或长期未复核 | 重新检查或归档 |

## Conservative Gates

- Micro ref 不因为短就默认更可信。
- Unofficial / anecdote 只能进入 `observe` 或 `candidate`。
- `key claim` 必须映射到具体 failure mode 或 target asset，否则只记录不吸收。
- 与现有规则冲突时进入 human gate，不由 agent 沉默选边。
- URL 类型刷新内容前，必须由用户明确批准联网；默认 `/skill-maintenance` 不联网。

## Registry

Template example, not part of the registry and not included in stale checks:

```markdown
| `micro-template` | `<URL or local path>` | `YYYY-MM-DD` | `<name>` | `workflow` | `<1-3 sentence factual summary>` | `<important claim>` | `source` | `<skill/command/hook/doc>` | `L0` | `observe` | `YYYY-MM-DD` |
```

| id | source | captured_at | owner | category | summary | key claim | evidence level | mapped assets | absorption level | status | last_checked |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `micro-none-2026-05-27` | `local maintenance review` | `2026-05-27` | `Kilo` | `workflow` | 当前没有已批准进入本 registry 的 active micro refs；本行用于区分“空表已复核”和“尚未启用”。 | 空 registry 必须显式记录状态，否则维护审查无法判断是否漏填。 | `practice` | `/skill-maintenance`, `docs/refs-micro-index.md` | `L1` | `observe` | `2026-05-27` |

## Review Output

每轮 `/skill-maintenance` 处理 micro refs 时，把结论合并进固定四节输出中的 `## 发现的问题`、`## 建议本轮修复` 或 `## 待你决策`：

```markdown
| id | Status | Evidence | Mapped assets | Decision | Reason | Next check |
|---|---|---|---|---|---|---|
```

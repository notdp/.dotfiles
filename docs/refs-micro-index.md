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
| `micro-2026-05-29-conditional-control-risk` | `user excerpt; original title and URL not provided` | `2026-05-29` | `Kilo` | `skill-authoring` | [未验证] 摘录把否定忽略、接种式提示和后门不鲁棒归纳为同一类条件边界学习风险：模型可能吸收被限定的行为，而没有稳定学会免责声明、触发词或否定条件。 | 高风险 prompt / skill 不能只靠免责声明式控制；应使用正反 contract cases、局部限定、替代动作和模型外验证。 | `anecdote` | `docs/software-engineering-research/conditional-control-risk.md`, `docs/software-engineering-research/skill-authoring.md`（已反向引用）, `skills/guard-verify/SKILL.md` | `L2` | `absorbed` | `2026-05-29` |
| `micro-2026-05-29-correlated-decisions` | `user excerpt; original title and URL not provided` | `2026-05-29` | `Claude` | `workflow` | [未验证] 用相关决策视角解释坏习惯："就这一次"其实代表一整类未来选择，因为未来的你会复用同一套决策算法；定位为自我管理技巧而非严格决策理论。 | 把"破例一次"重述为"我正在决定这类场景的默认算法"；映射到 AI 编程纪律：跳过测试/让 AI 糊一下/不读 diff/开新坑都是在训练未来的坏默认。 | `anecdote` | `docs/software-engineering-research/correlated-decisions.md`, `skills/guard-close/SKILL.md`（observe 映射，未改 skill） | `L1` | `observe` | `2026-05-29` |
| `micro-2026-06-15-agentic-code-review` | `https://addyosmani.com/blog/agentic-code-review/` | `2026-06-15` | `Claude` | `review` | Addy Osmani 基于 2026 四组独立数据集（Faros 22k 开发者、CodeRabbit 470 PRs、GitClear 产出分析、GitHub 6000 万次 review）论证：AI 让代码产出 4x 但真实价值仅 +12%，review 成为瓶颈（review 时长 +441%、零 review 合入 +31%、代码 churn +861%）。提出按 blast radius 分级 review 深度、要求 AI PR 附意图/证据/验证、用异构多 reviewer（93.4% finding 只被一个工具发现）、人退到 "human on the loop" 做高风险门控。 | Review 的对象从"检查作者推理"变成"重建从未存在的意图"，这是根本性变化；人应按 blast radius 分配注意力，低风险交给 AI + 自动化，高风险保留人类判断。 | `benchmark` | `coding-skills/guard-review/SKILL.md`, `coding-skills/guard-check/SKILL.md`, `docs/software-engineering-research/review.md` | `L0` | `candidate` | `2026-06-15` |

## Review Output

每轮 `/skill-maintenance` 处理 micro refs 时，把结论合并进固定四节输出中的 `## 发现的问题`、`## 建议本轮修复` 或 `## 待你决策`：

```markdown
| id | Status | Evidence | Mapped assets | Decision | Reason | Next check |
|---|---|---|---|---|---|---|
```

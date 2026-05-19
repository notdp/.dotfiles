---
name: dev-operational-task
description: 当任务涉及长耗时批处理、数据同步/回填/修复、迁移脚本、复杂 CLI、dry-run/apply 或可中断运行时使用；定义效率、可恢复、可观测、健壮性、CLI UX 和数据准确性合同。
argument-hint: <任务目标|脚本路径|数据操作说明>
---

# Dev Operational Task

本 skill 管的是“会跑很久、会处理大量数据、会改变外部/数据状态、或命令复杂到难以安全使用”的实现纪律。它不替代 `/dev-tdd`，而是在写代码前规定 operational contract；局部行为仍按 `/dev-tdd` 做 Red→Green→Refactor。

## 触发信号

满足任一项即进入本 skill：

- 批处理、回填、迁移、修复数据、同步外部系统、run-until-empty。
- 命令含 `--dry-run`、`--apply`、`--batch-size`、`--concurrency`、`--dev-db`、profile/env 等高认知负担参数。
- 任务可中断、可重跑、会处理未知规模数据，或用户可能让它 unattended 运行。
- dry-run 的价值取决于数据准确性，而不是“命令能跑通”。

## Contract

### 1. Efficiency

- 默认设计 bounded concurrency，而不是无限并发或完全串行。
- 参数必须有清晰上限：batch size、concurrency、rate limit、timeout。
- 外部 API/DB/队列要考虑 backpressure；失败时降速或暂停，而不是继续放大压力。
- 如果不能并行，写出原因：顺序依赖、锁、幂等风险、外部 rate limit 等。

### 2. Resumability

- 长任务必须有 checkpoint/cursor/state file/idempotency key 中至少一种。
- 中断后应能从已完成位置继续，避免重复消耗已经成功的工作。
- 每个 batch 的完成边界要明确：何时写 checkpoint，失败时是否回滚或保留 failed set。
- 重跑必须安全：重复执行不应导致重复写、重复通知、重复扣费或重复外部副作用。

### 3. Observability

运行时输出必须能回答：

| 问题 | 必需信息 |
|---|---|
| 现在在哪个阶段？ | phase/stage 名称 |
| 总量多少？ | total 或 unknown reason |
| 当前进度多少？ | current/total 和百分比 |
| 速度如何？ | rate 或 batch latency |
| 还要多久？ | ETA；无法估算时说明原因 |
| 是否还活着？ | heartbeat / last successful item |
| 哪里失败？ | failed count、样本、错误分类 |

禁止只打印“started”然后长时间无输出。长任务必须周期性 heartbeat。

### 4. Robustness

- 外部调用要有 timeout、retry、backoff 和最大重试次数。
- 部分失败必须可追踪：failed set、dead-letter 文件、错误样本或 retry queue。
- 错误不能静默吞掉；失败要有退出码、summary 和下一步建议。
- 校验失败默认阻断 apply，不允许“有点不一致但继续跑完”。

### 5. CLI UX

复杂 CLI 必须降低认知负担：

- 提供安全默认值或 preset，例如 `--profile local-prod-safe`。
- 高风险参数用交互式 wizard 询问；每个选项解释影响、风险和默认推荐。
- wizard 最后必须打印等价底层命令，方便下次复制执行。
- `--apply` 不能被默认打开；需要显式确认或 `--yes`。
- 环境、profile、DB、OSS/S3、并发、batch size、验证重试这类参数必须有 help 文案。

## Dry-run / Data Accuracy Gate

dry-run 不是 smoke test。合格 dry-run 至少输出以下证据：

| 证据 | 说明 |
|---|---|
| planned count | 将新增/更新/删除/跳过多少 |
| sample | 代表性样本，包含成功、失败、异常边界和随机样本 |
| holdout/unseen sample | 未参与调试或规则调参的数据样本；数据/模型/评测任务必须提供，无法提供时说明替代证据 |
| diff/aggregation | 新旧值差异、分布变化或聚合对比 |
| invariants | 总数守恒、唯一性、外键/租户边界、权限边界等 |
| failure examples | 无法处理的数据样本与原因 |
| apply readiness | 是否允许 apply；不允许时列出阻断原因 |

如果 dry-run 只能证明“流程没崩”，报告必须写 `dry-run: smoke only -- data accuracy not verified`，且不能据此进入 apply。

数据、模型、推荐、评测、分类、生成质量类任务必须区分：

- tuning/dev cases：实现、调参、debug 期间看过的样本。
- holdout/unseen cases：未参与调试的样本，用来证明方案没有只适配已知样本。
- regression cases：历史错误、边界场景和关键路径样本。

没有 holdout 数据时，必须降级为抽样复核方案：随机样本、边界样本、失败样本和人工 spot-check，且在报告中标注剩余风险。

## Apply Safety

- `--apply`、数据库写入、远端状态变更、第三方系统写入、生产数据修复必须先过本 skill 的 operational gate；只有涉及声明式 SSOT、部署产物、远程机器配置、线上漂移修复或仓库外状态需要回写时，才升级到 `/guard-gitops`。
- apply 前必须有 dry-run evidence；apply 后必须有 post-apply verification。
- destructive 操作需要备份/回滚路径；无法回滚时必须显式写入风险和人工确认点。

## Critical / Cloud Cost Operations

用户的自然语言操作词不能直接映射到 API。涉及费用、生产、数据、权限或不可逆状态时，先还原真实目的，再选择手段。

| 用户词 | 可能语义 |
|---|---|
| 关掉 | 停机 / 停止计费 / 下线服务 / 释放资源 |
| 回收 | 停用 / 删除 / 释放 / 归档 |
| 不用了 | 暂停 / 降配 / 删除 / 到期不续 |
| 降成本 | 停计费 / 降配 / 包年包月调整 / 生命周期策略 |
| 停掉 | 停服务 / 停实例 / 停账单 / 停任务 |

| Action | Trigger | Owner | Verification |
|---|---|---|---|
| Critical 操作先澄清目的 | 用户说“关掉/停掉/回收/释放/降配/不用了”，且涉及费用、生产、数据、权限或不可逆操作 | Agent | 回复中出现目标、验收标准、保留资产、回滚方式 |
| 云资源操作解释计费影响 | 操作 ECS/GPU/OSS/Kafka/RDS 等云资源 | Agent | 执行前列出计费影响和副作用 |
| ECS/GPU 停机即时验收 | 执行 ECS/GPU 停机后 | Agent | 输出 `Status` 和 `StoppedMode`，且目标为省钱时必须是 `StopCharging` |
| 账单延迟验收 | 停用/降配/释放云资源后的次日 | Agent/用户 | 查询实例账单，确认目标费用为 0 或列出残留计费 |
| Skill / 流程沉淀 | 本次复盘后 | 用户 | skill 中包含 critical 定义、澄清模板、即时/延迟验证规则 |
| 禁止把 `Stopped` 等同于不计费 | 任何云资源状态变更报告 | Agent | 报告里明确“状态”和“计费状态”是两个字段 |

## Spec / Plan 输出格式

```markdown
## Operational Contract
| 维度 | 决策 | 证据/实现点 |
|---|---|---|
| Efficiency | ... | ... |
| Resumability | ... | ... |
| Observability | ... | ... |
| Robustness | ... | ... |
| CLI UX | ... | ... |
| Dry-run data accuracy | ... | ... |
| Apply safety | ... | ... |

## Runbook
- Dry-run command:
- Expected dry-run evidence:
- Holdout / unseen validation:
- Apply command:
- Resume command:
- Stop / rollback:
- Verification:
```

## Deterministic scan

本仓库提供 advisory scanner：

```bash
scripts/scan_operational_task_contract.py --strict
```

默认扫描 staged、unstaged 和 untracked diff 中 operational-looking 文件。第一版是启发式检查，不替代人工判断；误报时在交付说明中解释。

## Stop / 升级条件

- 无法证明数据准确性 → 停止，不进入 apply。
- 无法安全 resume → 降低范围或先补 checkpoint。
- 无法观察进度 → 先补日志/heartbeat，再跑长任务。
- 触碰远程、DB、部署、secrets、第三方写入 → 先过本 skill 的 operational gate；涉及声明式 SSOT、部署产物、远程机器配置、线上漂移修复或仓库外状态需要回写时再升级到 `/guard-gitops`。
- 连续失败 2 次 → `/think-unstuck`。

## Gotchas

- “加个 dry-run”不等于安全；dry-run 必须有信息量。
- “命令给高级用户用”不是复杂 CLI 的借口；复杂命令更需要 preset/wizard。
- “先跑一次看看”对数据任务不够；数据失败常常是 silent fail。
- 并发不是越大越好；无上限并发会把效率问题变成事故。

## 关联技能

- 单个行为实现 → `/dev-tdd`
- 大型 Phase 交付 → `/dev-large-delivery`
- 最终验证 → `/guard-verify`
- 远端/DB/部署副作用 → `/guard-gitops`
- 交付前总检查 → `/guard-check`

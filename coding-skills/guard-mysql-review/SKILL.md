---
name: guard-mysql-review
description: 当 diff 涉及 MySQL/InnoDB DDL、索引、迁移 SQL 或查询性能审查时使用；按 Must/Should/Exception 分级输出 finding、仓库 convention 冲突和性能反模式裁决。
argument-hint: <diff|SQL 文件|DDL 片段|迁移说明>
---

# MySQL Review

审查 MySQL/InnoDB schema、索引、迁移 SQL 和查询访问路径。只适用于 MySQL/InnoDB；其他 SQL 方言必须停止使用本 skill，改用目标仓库规范。

详细规则见 `refs/mysql-review-checklist.md`。主流程负责范围、证据门和输出格式；不要把 checklist 当成不看上下文的机械 lint。

## 1. Scope

适用于：

- MySQL/InnoDB DDL、migration、schema diff。
- 索引新增、删除、调整。
- 涉及查询性能、写入成本、表结构命名、字段类型的 review。
- 需要判断反范式、字段冗余、少 join、无物理外键是否合理的场景。

不适用于：

- PostgreSQL、SQLite、Oracle、SQL Server 等其他方言。
- 不涉及数据库结构或 SQL 访问路径的普通代码 diff。
- 真实数据库 apply、回填、迁移执行；这类操作先走 operational / gitops 流程。

## 2. Review Flow

1. **确认方言**：只有确认是 MySQL/InnoDB 才继续；无法确认时标注 `[未验证]`。
2. **识别仓库 convention**：先看同仓库已有 schema、迁移、命名、索引模式。
3. **读取 checklist**：按 `Must / Should / Exceptions / Anti-patterns` 审查。
4. **处理冲突**：如果 checklist 与仓库 convention 冲突，输出 `Convention conflict`，不要沉默选边。
5. **要求证据**：Exception 和允许的反模式必须有收益、成本、失败模式和补偿机制。
6. **输出裁决**：给出 finding 表和是否可合并 / 可继续的判断。

## 3. Severity

| Level | 含义 | 裁决 |
|---|---|---|
| Must | 团队硬规范或安全硬门 | 默认阻断，除非命中明确 Exception |
| Should | 推荐规范 / 性能启发式 | 不一定阻断，但必须说明 trade-off |
| Exception | 合理偏离规范 | 必须有上下文证据和责任边界 |
| Anti-pattern | 常规上不推荐但可换性能/简单度 | 必须说明收益、失败模式和补偿 |
| Convention conflict | checklist 与仓库惯例冲突 | 不直接判错，要求用户或项目规范拍板 |

## 4. Evidence Gate

每条 finding 必须包含：

- `file:line`、SQL 片段或 diff 片段。
- 规则级别：`Must / Should / Exception / Anti-pattern / Convention conflict`。
- 失败路径或维护成本，不能只写“看起来不规范”。
- 修复建议或需要补充的证据。

索引相关结论优先要求查询模式、数据量级、写入频率、`EXPLAIN` 或等价查询计划。没有这些证据时，标注为 `[未验证]`，不要把推测写成事实。

## 5. Output Format

```markdown
## MySQL Review

### Scope
- 方言: MySQL/InnoDB / [未验证]
- 范围: <文件 / diff / SQL 片段>
- 仓库 convention: <已识别 / 未识别>

### Findings
| Level | File:Line | Issue | Evidence | Decision | Fix / Next |
|---|---|---|---|---|---|
| Must | path.sql:12 | ... | ... | Block | ... |
| Convention conflict | path.sql:20 | ... | ... | Ask | ... |

### Allowed Exceptions / Anti-patterns
| Pattern | Evidence | Benefit | Cost / Failure mode | Compensation |
|---|---|---|---|---|
| 字段冗余 | ... | 减少 join | 数据漂移 | 应用层同步 / 巡检 |

### Assessment
- Ready?: Yes / No / With fixes / Need decision
- Blockers:
- Follow-up:
```

## 6. Stop / Escalation

- 不是 MySQL/InnoDB：停止使用本 skill。
- 命中未参数化 SQL 或字符串拼接 SQL：升级为安全 hard stop。
- 需要执行迁移、回填、apply、生产数据修改：先走 operational / gitops 流程。
- checklist 与仓库 convention 冲突且影响 schema 契约：输出 `Need decision`，不要自行决定。
- 缺少数据量、查询模式或写入频率证据：可以报告风险，但必须标注 `[未验证]`。

## Gotchas

- `索引列必须 NOT NULL` 是团队硬规范，不是 MySQL 语法限制。
- `表名小写` 是跨平台和团队规范；不要引用为所有 MySQL 环境的官方强制要求。
- 反范式不是免审理由；只有收益、成本和补偿都清楚时才允许。
- 小表阈值、大表阈值是团队 review 门槛，不是数据库引擎限制。

## References

- `refs/mysql-review-checklist.md`

## 关联技能

- 交付前总检查命中 MySQL/InnoDB DDL、migration、索引或查询性能 → 由 `/guard-check` 路由到本 skill
- 普通代码 review 命中 MySQL/InnoDB schema / index diff → 由 `/guard-review` 追加本 skill
- 命中 SQL injection、未参数化 SQL 或敏感数据流 → 升级 `/guard-secure`
- 迁移执行、回填、apply、生产数据库副作用 → 先走 `/dev-operational-task`；涉及仓库外状态回写时再走 `/guard-gitops`

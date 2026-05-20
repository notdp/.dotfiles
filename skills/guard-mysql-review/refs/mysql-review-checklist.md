# MySQL/InnoDB Review Checklist

本 checklist 只覆盖 MySQL/InnoDB。规则分为：

- `MySQL fact`：可由 MySQL 文档或引擎行为确认。
- `Team rule`：团队硬规范，默认阻断。
- `Heuristic`：经验性建议，需要结合数据量、查询模式和写入成本判断。

## Must

| Rule | Type | Evidence to check | Exception |
|---|---|---|---|
| 大表必须评估修改时间列索引。团队阈值：预估超过 1w 行。 | Team rule | 表预估行数、是否存在 `updated_at` / 修改时间字段、增量扫描或同步路径 | 修改时间列不参与查询、归档、同步、增量扫描，并有替代访问路径 |
| 创建时间使用 `DEFAULT CURRENT_TIMESTAMP`；修改时间使用 `DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`。 | MySQL fact + Team rule | DDL 中 `created_at` / `updated_at` 定义 | 旧仓库已有统一时间字段 convention，先报 `Convention conflict` |
| 每张表必须有明确主键；默认优先自增整数 ID。 | MySQL fact + Team rule | `PRIMARY KEY`、`AUTO_INCREMENT`、ID 类型 | 分布式 ID、外部幂等 ID、离线导入、跨库生成，但需说明索引局部性和存储成本 |
| 不使用物理外键。 | Team rule | `FOREIGN KEY` / `CONSTRAINT` | 已有仓库强制使用物理外键时，先报 `Convention conflict` |
| 逻辑外键字段跨表命名一致。 | Team rule | 同一业务实体在不同表中的字段名 | 已有仓库 convention 冲突时，先报 `Convention conflict` |
| 相同语义字段跨表命名一致。 | Team rule | `created_at`、`updated_at`、状态字段、索引名 | 已有仓库 convention 冲突时，先报 `Convention conflict` |
| 表名必须小写，不能包含大写字母。 | Team rule | `CREATE TABLE` / migration 文件中的表名 | 已有历史表名大写时，新表仍应避免；改旧表需单独评估兼容成本 |
| 索引列必须 `NOT NULL`。 | Team rule | 索引定义和列定义 | nullable 字段确需进入索引时，必须说明语义、查询条件和替代设计为什么不适用 |
| SQL 必须参数化，禁止拼接用户输入。 | Security hard stop | query builder、raw SQL、字符串插值 | 无例外；命中时升级安全审查 |

## Should

| Rule | Type | Evidence to check | Notes |
|---|---|---|---|
| 小表去掉不必要二级索引。团队阈值：预估小于 1000 行。 | Heuristic | 表行数、唯一性约束、查询路径 | 通常只保留主键和唯一键；高频查询可例外 |
| 单表二级索引推荐不超过 5 个。 | Heuristic | 索引数量、写入频率、查询模式 | 超过时要求解释每个索引服务的查询 |
| 单个组合索引推荐不超过 5 列。 | Heuristic | 组合索引列、最左前缀、选择性、排序需求 | 超过时要求 `EXPLAIN` 或等价证据 |
| 优先用 `VARCHAR` 或明确长度字段，除非必要不要用 `TEXT`。 | Heuristic | 字段最大长度、是否过滤/排序/索引 | `TEXT` 索引需要前缀长度；长正文可例外 |
| 状态机字段优先用可读字符串，例如 `status VARCHAR(20)` / `VARCHAR(32)`。 | Team rule + Heuristic | 字段是否表达多状态流转、是否只有 true/false、应用层状态常量 | 纯布尔继续用 `TINYINT(1)`；数值状态码需有强 convention 或外部协议约束 |
| 低基数字段不默认单独建索引，包括 `status` 和布尔字段。 | Heuristic | 状态分布、查询条件、排序/分页、组合索引顺序、`EXPLAIN` | 只有明显偏斜状态、稀有状态扫描或组合访问路径明确时才建 |
| 表名推荐单数形式。 | Team rule | 表名 | 若仓库已有复数 convention，报 `Convention conflict` |
| 索引围绕真实查询条件、排序、分页设计。 | Heuristic | 业务查询、DAO/repository、慢查询、`EXPLAIN` | 不按“可能会查”预建索引 |
| 新增或删除重要索引时提供查询计划证据。 | Heuristic | `EXPLAIN`、慢查询、线上指标、压测 | 没证据时标注 `[未验证]` |
| 索引命名应与语义一致，并在相同字段上跨表对齐。 | Team rule | `idx_*`、`uk_*` 命名 | 仓库已有命名模板优先 |

## Exceptions

例外必须同时写清：

1. 为什么默认规则不适用。
2. 当前选择的收益。
3. 失败模式或维护成本。
4. 补偿机制或后续验证方式。

常见例外：

- 大表无修改时间索引：该列不参与增量查询、同步、归档、分页或筛选。
- 小表保留额外索引：高频路径、唯一性约束、排序/分页关键路径、覆盖查询收益明确。
- 非自增主键：分布式写入、外部幂等、离线导入、跨库生成；需说明索引局部性和存储成本。
- `TEXT`：确实超过 `VARCHAR` 适用范围，且不用于完整过滤、排序或普通索引。
- 状态字段使用数值：已有仓库统一数值状态码、外部协议使用数值码、极高写入/存储压力且有统一映射层。
- 状态字段使用 MySQL `ENUM`：状态集合极稳定、团队接受变更状态需要 DDL，并且应用层有清晰枚举映射。否则优先 `VARCHAR`。
- `status` 单列索引：目标查询主要扫描稀有状态，或状态分布明显偏斜，并有 `EXPLAIN` / 指标证明收益。
- nullable 字段进入索引：业务语义必须区分未知/未设置，查询明确处理 `IS NULL`，或迁移成本高于收益。
- 仓库 convention 冲突：目标仓库已有统一命名、时间字段、表名、索引命名或外键策略。

## Anti-patterns Allowed With Evidence

这些做法常规上需要警惕，但为了性能或复杂度可以接受。允许条件是证据完整，而不是“为了性能”一句话带过。

| Anti-pattern | 可接受收益 | 必须说明的成本 | 补偿机制 |
|---|---|---|---|
| 字段冗余减少 join | 降低查询复杂度、减少热点 join | 数据漂移、更新路径变多 | 应用层同步、事务边界、异步修复、巡检 |
| 不使用物理外键 | 降低迁移和写入耦合、避免级联副作用 | 孤儿数据、跨表一致性弱 | 逻辑命名、写入校验、定期一致性检查 |
| 反范式汇总字段 / 计数字段 | 减少聚合查询成本 | 计数不准、并发更新复杂 | 重算任务、校验 SQL、幂等更新 |
| 宽表替代过度拆表 | 减少 join、简化读取路径 | 行变宽、冷热字段混杂、迁移成本 | 字段增长评估、冷热路径拆分预案 |
| 少建索引换写入性能 | 降低写放大和存储成本 | 查询退化、排序变慢 | 替代访问路径、分页限制、查询计划证据 |
| 存储派生状态 | 简化查询和状态判断 | 状态源漂移 | 单一写入口、状态机校验、修复脚本 |
| 字符串存储状态 | 可读性、审查友好、减少 int-code 映射漂移 | 比 `TINYINT` / `ENUM` 更占存储，索引更宽 | 限制长度、集中状态常量、必要时用组合索引验证 |

## Status Field Rules

状态字段不要默认当成布尔或数值码处理：

- 多状态流转字段优先使用可读字符串：`status VARCHAR(20)` 或 `status VARCHAR(32)`，并设为 `NOT NULL`。
- 纯布尔标志继续使用 `TINYINT(1)`，例如 `include_sub_depts`、`confirmed_high_risk`。
- 不推荐为“未来可能扩展”的状态用布尔字段；`is_deleted` 这类软删除需结合仓库 convention 判断。
- 不推荐默认用 int 存储业务状态，除非已有强 convention、外部协议要求、存储压力明确，且有唯一映射层避免 magic number。
- MySQL `ENUM` 比字符串更紧凑，但新增状态通常涉及 DDL；只有状态集合稳定且团队接受迁移成本时使用。
- `status` 不默认单独建索引。低基数字段只有在状态分布明显偏斜、查询目标是稀有状态，或作为组合索引的一部分服务真实访问路径时才有意义。
- 常见组合索引形态应来自查询，而不是固定模板，例如 `(tenant_id, status, updated_at)`、`(status, updated_at)` 或 `(status, id)` 必须分别说明过滤、排序和分页收益。
- 如果 `status` 进入索引，仍遵守“索引列必须 `NOT NULL`”规则。

## Convention Conflict Rules

如果 checklist 与仓库已有 convention 冲突：

1. 不直接判为错误。
2. 输出 `Convention conflict`。
3. 列出 checklist 规则、仓库现状、影响范围。
4. 给出推荐，但要求用户或项目规范拍板。

示例：

| Conflict | 不应做 | 应输出 |
|---|---|---|
| 仓库统一用 `gmt_create` / `gmt_modified` | 直接要求改成 `created_at` / `updated_at` | `Convention conflict`: 本 checklist 推荐 `created_at`，但仓库统一使用 `gmt_*` |
| 仓库历史表名为复数 | 直接批量要求单数化 | 新表建议单数；旧表是否改名需单独迁移评估 |
| 仓库使用物理外键 | 直接删除外键 | 说明团队规范冲突，要求项目 owner 裁决 |

## Review Questions

- 表预估数据量是多少？大表 / 小表阈值是否命中？
- 真实查询条件、排序、分页、增量扫描路径是什么？
- 写入频率高不高？新增索引会不会明显增加写放大？
- 索引列是否 `NOT NULL`？nullable 是否有明确业务语义？
- 状态字段是纯布尔，还是未来可能扩展的状态机？
- `status` 是否需要索引？状态分布是否偏斜？目标查询是否扫描稀有状态或依赖组合索引排序/分页？
- 是否有同语义字段在别的表中使用不同名称？
- 是否有仓库 convention 与 checklist 冲突？
- 是否使用了反范式或冗余？补偿机制是什么？
- 是否有 `EXPLAIN`、慢查询、压测或线上指标支撑索引判断？

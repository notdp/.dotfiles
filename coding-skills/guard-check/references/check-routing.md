# Check routing

## 路由原则

1. 先看当前 diff 的范围和风险
2. 默认调用 `guard-review`
3. 满足以下任一条件时追加 `guard-secure`
   - 身份认证
   - 权限控制
   - 外部输入
   - secrets / tokens / headers / cookies
   - 供应链、依赖升级、CI/CD、IaC、container 或 cloud config
   - MCP / tool permission / hook / prompt / capsule / agent context surface
   - 安全工具执行、外部目标扫描、exploit、C2、phishing simulation、credential access、lateral movement、暴力测试或绕过认证
   - 仅在 diff、PR 描述或任务上下文有证据时触发；不要只因普通关键词扩大为重安全审查
4. 满足以下任一条件时追加 `guard-mysql-review`
   - MySQL/InnoDB DDL 或 migration
   - 表结构、字段类型、时间字段、主键、逻辑外键命名变更
   - 索引新增、删除、组合索引调整
   - 查询性能、反范式、冗余字段、减少 join 的设计取舍
5. 用户要求“验证通过 / 可以交付 / 可以合并”时追加 `guard-verify`
6. 需要 PR、发布、交付动作时切到 `guard-ship`
7. 如果 diff、PR 描述或任务上下文引用了 spec / plan / prompt artifact，追加 intent alignment 检查：
   - 目标是否仍匹配 artifact
   - Non-goals 是否被突破
   - 关键领域术语、结构边界、验证策略是否发生未说明变化
   - 若实现偏离 artifact，先要求更新 artifact 或说明偏离理由，再给交付裁决

## 输出要求

- 明确本次走了哪些链路
- 给出最终裁决：`Ready` / `With fixes` / `Blocked`
- 如果没走某条链路，要写原因
- 如果执行了 intent alignment，要写出对齐结论和引用的 artifact 路径

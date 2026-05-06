# Check routing

## 路由原则

1. 先看当前 diff 的范围和风险
2. 默认调用 `guard-review`
3. 满足以下任一条件时追加 `guard-secure`
   - 身份认证
   - 权限控制
   - 外部输入
   - secrets / tokens / headers / cookies
4. 用户要求“验证通过 / 可以交付 / 可以合并”时追加 `guard-verify`
5. 需要 PR、发布、交付动作时切到 `guard-ship`
6. 如果 diff、PR 描述或任务上下文引用了 spec / plan / prompt artifact，追加 intent alignment 检查：
   - 目标是否仍匹配 artifact
   - Non-goals 是否被突破
   - 关键领域术语、结构边界、验证策略是否发生未说明变化
   - 若实现偏离 artifact，先要求更新 artifact 或说明偏离理由，再给交付裁决

## 输出要求

- 明确本次走了哪些链路
- 给出最终裁决：`Ready` / `With fixes` / `Blocked`
- 如果没走某条链路，要写原因
- 如果执行了 intent alignment，要写出对齐结论和引用的 artifact 路径

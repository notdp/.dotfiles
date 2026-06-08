# Dev GuideLines

## 基础原则

- 可读性优先：追求更少的代码和更大的信息密度，但不牺牲可读性
- 数据驱动：数据结构比算法更关键，复杂逻辑写成表而非一堆判断，数据集中管理
- 显式优于隐式，扁平优于嵌套
- 先用简单方案，测过瓶颈再优化
- 如果实现难以解释，说明方案有问题
- 遵循：DRY, KISS, YAGNI, SOLID, LoD, Fail Fast, Single Source of Truth

## 可观测性

- 日志规范：日志要详细清晰；长流程需打印开始、进度和 ETA；关键数据标红
- 长耗时、批处理、数据变更、复杂 CLI、dry-run/apply 任务先走 `/dev-operational-task`

## 命名与设计

- 命名即文档：全局名详细、局部名精简，函数名体现行为或返回值
- Intention-Revealing Names：名字说"为什么"不是"怎么做"
- Ubiquitous Language（DDD）：代码命名与业务术语对齐，消除翻译层
- Design-First：Capabilities → Components → Interactions → Contracts → Implementation，不批准不写代码

## AI-friendly 代码约束

- 优先写可预测、可局部修改、可验证的代码，而不是只追求“优雅”
- 一个改动尽量只解决一类问题；重构、机械改动、行为修改尽量拆开
- Surgical Changes：只改完成用户目标所必需的代码；不要顺手改相邻代码、注释、格式或风格
- 每一行改动都必须能归因到用户请求、必要验证、或本次改动造成的 cleanup；归不进去就不要改
- 保持现有代码风格，即使你主观上会用另一种写法；发现无关 dead code 只记录，不删除
- 业务规则优先显式化：类型、schema、状态机、规则表、明确函数，少依赖 tacit knowledge
- 避免跨层穿透、隐式副作用、过度抽象、黑魔法式封装
- 判断方案优先看影响面、可测试性、可 review 性，而不是作者主观偏好

## 质量与验证

- **TDD 强制**：新功能、bug 修复、行为变更时，必须先调用 `/dev-tdd` skill，走 Red→Green→Refactor 循环。先写失败测试再写实现，不是"写完实现补测试"。纯配置/文档/样式变更除外。
- 开发后思考是否需要小范围重构，重构的基础是良好的测试
- 验证比生成贵：定义"什么是正确的"是核心工作，写代码不是
- 验证必须区分 inner-loop verifier 与 acceptance verifier；TDD/lint/unit test 不能单独替代最终用户目标验收。复杂任务、数据任务、模型任务、Agent 流程必须提供端到端、holdout/unseen、抽样复核或人工可观察证据；不适用时说明原因
- 故障导向安全：校验失败应阻止而非放行，错误不应静默传递
- dry-run 必须证明数据准确性，不只证明命令能跑


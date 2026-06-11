---
name: dev-large-delivery
description: 当改动跨 Phase、跨子系统或动基础设施时使用；以"双跑+人工验收+回滚剧本"框架驱动大型交付（日常小改动用 /dev-tdd，不走本 skill）。
argument-hint: <项目名|改动范围|当前 Phase>
---

# Large Delivery

## 1. 判断是否属于"大型交付"

满足下列任一条件，走本 skill；否则用 `/dev-tdd` 就够：

- 跨 **2+ 子系统**（例如同时动 `ordo_ai` + 新引入 Cube + Metabase）
- 涉及**数据管道 / schema 迁移 / 权限模型**这类不可逆改动
- 引入**新基础设施**（新中间件、新服务、新存储）
- 预期**多 Phase** 推进（≥2 个阶段，每阶段有独立可见成果）
- 一旦 prod 出事**回滚成本显著高于前滚**（数据已写脏、schema 已改、同步已跑）
- 影响**多租户 / 权限 / 计费**等高风险面

用户主动声明"这是大型交付"时，不再判断，直接走。

## 2. 核心原则：outer-loop 节奏

`/dev-tdd` 管一次代码改动的 inner-loop。本 skill 管一个 Phase 的 outer-loop，以及跨 Phase 的推进节奏。两者配合，不替代。

每个 Phase 必须满足下面的 contract。默认按顺序推进；如果项目已有等价发布流程，可以调整顺序，但不能降低证据要求。

```
1. 写验收用例       （自动化为主，手工 checklist 兜底）
2. 改代码           （局部变更各自走 /dev-tdd 完成）
3. 部署到 test 环境  （必须 prod 等价配置，不是简化版）
4. 跑验收 + 回归     （含上一 Phase 没回退）
5. 发现问题回到 2    （在 test 解决，不等 prod 暴露）
6. 获取验收确认       （人工验收优先；用户可明确授权等价自动化/书面验收）
7. 准备回滚剧本      （Phase 级别的 rollback，不是单次 commit 级）
8. 合 prod，灰度放量 （能灰度就灰度；feature flag / 按租户 / 按角色）
```

## 3. 硬约束（红线）

| 约束 | 违反的后果 |
|------|-----------|
| prod 部署前必须有 **test 等价演练** | 没踩过的坑直接进 prod |
| **用户人工验收** 才能进下一阶段 | 交付方单方面宣布完成 |
| **新旧双跑先在 test 完成一轮** 再谈 prod | 拿 prod 数据当测试集 |
| **备份 / 恢复演练在 test 做**，不是 prod | prod 第一次恢复 = 第一次发现备份坏掉 |
| **每个 Phase 必须有回滚剧本**（不只是 git revert，包括数据 / schema / 灰度开关） | 出事时手忙脚乱 |
| **业务侧可见成果** 是每个 Phase 的退出条件 | 技术完成 ≠ 交付完成 |

例外只允许一类：**纯文档改动**（spec、盘点文档、README 等），不走 test。
schema 改一行、lint 规则调整、feature flag 默认值改动——**都不算例外**。

## 4. Phase 的出口 checklist

每个 Phase 结束前过一遍；有一项缺证据就不能进入下一 Phase。

- [ ] test 环境部署完成，配置与 prod 等价
- [ ] 自动化验收全部通过
- [ ] 回归测试通过（前序 Phase 没回退）
- [ ] 手工 checklist 跑完（UI、权限、数据对比等自动化测不到的）
- [ ] 新旧对照（如适用）：diff 在可接受范围内
- [ ] 回滚剧本就绪：触发条件、操作步骤、预期恢复时间都明确
- [ ] **用户人工验收通过**，或用户明确授权以自动化/书面验收替代
- [ ] Feature flag / 灰度机制可用（能按需切回）
- [ ] 可见成果对齐：业务侧能看到什么
- [ ] Phase 的 contract 与下一 Phase 的依赖已对齐

跳过某项只能基于明确的“不适用”理由或等价证据，不能因为麻烦而省略。

## 5. 和其他 skill 的边界

| 场景 | 走哪个 |
|------|--------|
| 一次代码改动（一个 feature / bug fix） | `/dev-tdd` |
| 目标明确、可拆 phase、需要多轮循环执行 | `/dev-long-run-v2` |
| Phase 内的数据脚本 / 批处理 / 复杂 CLI 设计 | `/dev-operational-task` |
| 大型交付的**一个 Phase 整体推进** | 本 skill |
| 大型交付的**交付 / PR / 发布动作** | `/guard-ship`（本 skill 调用它） |
| Phase 级**验证是否真的完成** | `/guard-verify`（本 skill 调用它） |
| 写 Phase 规划 / spec 本身 | `/think-plan` |
| 设计架构 | `/think-architecture` |
| 出 bug 要排查 | `/dev-debug` |
| 触碰远程 / 部署产物 / 线上状态 | `/guard-gitops`（每次 prod 动作前必过） |

本 skill **不重新实现** 这些能力，只把它们编排成 Phase 级节奏。

### 与 `/dev-long-run-v2` 的区别

`/dev-long-run-v2` 是长任务执行工作流：用 `.long-loop/` 工作区保存 spec overview、fix plan、qa 和 logs，由对话 agent 调度 planner/coder/reviewer 逐 phase 实现、commit 并过完成门禁。

本 skill 是交付治理：定义 Phase 出口、test 等价演练、人工验收、回滚剧本和 prod 灰度。大型交付可以在某个 Phase 内使用 long-run 做多轮实现，但 Phase 是否完成仍由本 skill 的 checklist 裁决。

### 与 `/dev-operational-task` 的区别

`/dev-operational-task` 管单个长任务/数据脚本/复杂 CLI 的效率、resume、可观测、dry-run 数据准确性和 apply 安全。本 skill 管 Phase 级交付节奏；Phase 内可以要求脚本满足 operational contract，但 Phase 是否能进入下一阶段仍按本 skill 的出口 checklist 裁决。

## 6. 常见反模式（出现即停下）

- **"test 差不多就上 prod，prod 再修"**：外部副作用不可逆，这个思维会炸。
- **"回滚就是 git revert"**：数据变更、schema 变更、同步任务、外部状态都要 revert。单靠 git revert 无法回滚。
- **"我自己跑过了，用户就不用看了"**：人工验收的价值是"第三方确认符合业务预期"，不是复核代码。
- **"先迁完再补测试"**：迁移本身就是高风险动作，没有验收用例支撑的迁移是赌博。
- **"两个 Phase 的改动一起上"**：Phase 合并 = 回滚粒度变大 = 出事 blast radius 变大。
- **"feature flag 之后再加"**：上了 prod 才加 feature flag 等于没有。
- **"只做 sunny path 验收"**：权限越权、跨租户、空数据、极值场景，这些才是 prod 出事的源头。

## 7. 与全局纪律的一致性

本 skill 是全局 `AGENTS.md` 四条红线的 **Phase 级应用**：

- **闭环验证** → 每个 Phase 必须给出 test 环境的验证证据
- **事实驱动** → 数据异常 / 口径差异时先查事实，不猜
- **穷尽方案** → 连续失败 2 次转 `/think-unstuck`
- **SSOT** → prod 变更前过 `/guard-gitops`，仓库为事实源

## 8. Gotchas

- 本 skill 只管 **节奏**，不管 **代码实现**；实现细节走 `/dev-tdd` / `/dev-debug`。
- Phase 的粒度由 spec 决定（`/think-plan` 产出），不是本 skill 自由裁量。
- "人工验收"要具体到 **谁、看什么、过不过的判据**，不能只写"用户看一眼"。
- 第一次做大型交付的团队，Phase 0 通常就是**盘点 + 搭骨架**，别跳过直接做 Phase 1。
- 回滚剧本要实际**演练过一次**，写在文档里没演练等于没有。
- 用户说 "先跑通再说" 时也不能放弃 test 先行，但可以把 test 验收用例缩到最小集。

## 9. 触发本 skill 的副产物

执行本 skill 期间，建议产出：

- **交付 checklist**（每个 Phase 一份，可挂在 spec 附近或 project dashboard）
- **回滚剧本**（每个 Phase 一份，随 spec 版本化）
- **人工验收记录**（每次验收一条，最少含：时间、验收人、过不过、发现的问题）
- **新旧对照表**（如适用，Phase 结束归档）

归档位置由 project 决定；本 skill 不强制路径。

## 关联技能

- 规划 Phase / 写 spec → `/think-plan`
- 架构设计 → `/think-architecture`
- Phase 内单次代码改动 → `/dev-tdd`
- 排查 bug → `/dev-debug`
- 重构 → `/dev-refactor`
- Phase 级验证 → `/guard-verify`
- Phase 级交付 → `/guard-ship`
- 触碰远程 / 部署 → `/guard-gitops`
- 长任务循环执行 → `/dev-long-run-v2`
- 完成前总检查 → `/guard-check`
- 连续失败 2 次 → `/think-unstuck`
- 完成后经验沉淀 → `/assist-learn`

---
name: dev-simplify
description: 当刚完成一段实现、需要从复用/质量/效率三个维度扫一遍并直接修复时使用；比 dev-refactor 轻，比 guard-review 主动。
argument-hint: <留空=最近变更|文件/目录|--diff <range>>
---

# Simplify

定位：**实现完成后的轻量清理**。比 `/dev-refactor` 轻量（不做范围裁决和 spec），比 `/guard-review` 主动（直接修，不只报告）。适合 TDD 走完 Green 阶段、刚做完一个 feature 或修完一个 bug 的清理点。

## 1. 识别变更

解析 `$ARGUMENTS`：

| 模式 | 触发 | 范围 |
|------|------|------|
| 留空 | 默认 | `git diff` + `git diff --staged`；如全空则取本会话最近编辑的文件 |
| 路径 | 文件/目录 | 仅该范围 |
| `--diff <range>` | `--diff main..HEAD` | 指定 commit range |

### 范围红线

- 单次 simplify 范围 ≤ 10 文件；超过先收窄或回退到 `/dev-refactor`
- 工作树脏度无要求（与 refactor 不同）；但建议先 commit 一个 baseline，方便对比
- 不在测试代码上做"美化式" simplify；测试只修明显的 reuse / efficiency 问题

## 2. 派发三视角并行子任务

为什么拆成三视角：实现刚完成时，agent 容易被自己刚写的方案锚定，只看语法和局部正确性。Reuse / Quality / Efficiency 分开扫描，可以分别暴露“已有能力没复用”“结构变难改”“热路径多做事”三类不同失败模式；聚合后再修，是为了过滤重复和 false positive，避免边扫边改导致 scope 失控。

派发三个独立的**只读子任务**（subagent / parallel agent / sub-call，按当前 agent 平台能力命名；纯 LLM 模式降级为顺序处理）。每个子任务收到完整 diff 和扫描指令。

### 子任务 1：Reuse Review

目标：找出"这段新代码已经在仓库其他地方有现成实现"的情况。为什么：避免新增平行 utility、重复常量或手写已有能力，让后续维护者只需要理解一个 canonical 实现。

检查项：

- 新写的工具函数是否在 `utils/` / `lib/` / `helpers/` / `shared/` 已存在
- 内联逻辑是否可以替换为现有 utility（字符串处理、路径处理、日期格式化、环境检测、类型守卫）
- 重复的 import 路径或常量定义
- 已有的高阶组件 / 自定义 hook / decorator / mixin 没被复用，反而手写了

返回格式：

```
| file:line | 新代码片段 | 推荐替换 (现有路径) | 置信度 |
```

### 子任务 2：Quality Review

目标：找出"hacky"模式，但不要演变成全面重构。为什么：刚完成的代码最容易夹带为赶进度写下的短期形状；此视角只清理会降低可读性、可预测性或边界清晰度的问题。

检查项：

- **Redundant state**：state 重复了已有 state、cached 值可以从 props/parent 派生、observer/effect 可以是直接调用
- **Parameter sprawl**：函数加新参数而不是重组
- **Copy-paste with slight variation**：近似代码块没抽公共
- **Leaky abstraction**：暴露内部细节、破坏既有边界
- **Stringly-typed**：用 raw string 而仓库已有 const / enum / branded type
- **Unnecessary nesting**：JSX wrapper Box / div 没承担布局职责
- **Magic number / 硬编码**：应来自 token / config
- **Speculative abstraction**：为单次使用代码新增抽象、接口、配置或扩展点
- **Unrequested flexibility**：加入用户没有要求的参数、模式、fallback 或配置
- **Untraceable change**：改动无法映射到用户请求、必要验证或本次改动造成的 cleanup

返回格式：

```
| file:line | 问题类型 | 简述 | 建议 fix |
```

### 子任务 3：Efficiency Review

目标：找出 hot-path bloat 和不必要的工作。为什么：功能正确不代表运行路径合理；此视角专门防止重复计算、串行等待、无界资源和 per-request / per-render 额外负担被“测试通过”掩盖。

检查项：

- **Unnecessary work**：重复计算、重复读文件、重复 API 调用、N+1
- **Missed concurrency**：独立操作串行（应 `Promise.all` / `asyncio.gather` / `tokio::join`）
- **Hot-path bloat**：startup / per-request / per-render 加了阻塞工作
- **Recurring no-op updates**：polling / interval / event 处理里无脑写 store，没加变更检测
- **Unnecessary existence check**：先 `exists()` 再操作（TOCTOU 反模式）
- **Memory**：无界数据结构、未清理监听器、未关闭资源
- **Overly broad operations**：读整文件而只需片段、加载全量再过滤

返回格式：

```
| file:line | 问题类型 | 影响 | 建议 fix |
```

## 3. 聚合 + 直接修复

收齐三个子任务的 finding 后：

1. **去重**：同一 file:line 多个子任务都报 → 取最严重的，合并描述
2. **过滤 false positive**：如果某条 finding 与项目约定冲突（如刻意保留的 verbose 写法）、或证据不足，跳过并简短说明 `[skipped: 原因]`
3. **直接修**：剩余 finding 逐条改。每条改动是一个原子变更，但不强制单独 commit（与 refactor 不同）
4. **不扩 scope**：发现"顺手可以重构"的更大问题，记入 backlog 不动手；如果范围超出 simplify 边界，建议路由到 `/dev-refactor`

### 修复规则

- 行为不变是默认（与 refactor 一致）；如果发现 efficiency 修复涉及行为变化（如改成异步），单独 flag 给用户决定
- 不夹带类型重写、API 改名、新增抽象 —— 这些不是 simplify
- 只删除/调整本次改动造成的 unused imports / vars / functions；既有 dead code 只列 backlog，不动手
- 修完跑一次最小验证（typecheck / lint / 受影响测试）

## 4. 输出

```markdown
### Simplify 报告
- 范围：<文件数 / commit / diff range>

### Reuse Findings
| file:line | 替换 | 状态 (fixed/skipped) |
| ... | ... | ... |

### Quality Findings
| file:line | 问题 | 状态 |
| ... | ... | ... |

### Efficiency Findings
| file:line | 问题 | 状态 |
| ... | ... | ... |

### Summary
- Fixed: N
- Skipped: M（原因汇总）
- 触发 backlog（建议路由）：<空 / `/dev-refactor` 项 / `/dev-tdd` 项>

### 验证
- typecheck: <pass/fail>
- lint: <pass/fail>
- 受影响测试: <pass/fail>
```

### 完成确认

输出 Simplify 报告前确认：

1. Fixed 项的验证已通过（typecheck + lint + 受影响测试）
2. 无行为变化混入 simplify diff（如有，已单独 flag 给用户）
3. Skipped 项都有 `[skipped: 原因]` 标注
4. Backlog 项（建议路由到 `/dev-refactor` 或 `/dev-tdd`）已列出

任一项不满足 → 补完再输出报告。

## 5. 跨 agent 适配

派发并行子任务的具体形式按当前 agent 平台命名：

- 有并行子任务能力的平台：把 reuse / quality / efficiency 三份契约分别派发给独立只读分析单元
- 无并行子任务能力的平台：主流程顺序跑三个视角（顺序：reuse → quality → efficiency），每完成一个汇总到 finding 列表
- 子任务命名、调用方式、工具白名单由当前 agent 平台决定，不在 skill 内硬编码
- 任何模式下"只读 + 三视角独立 + 聚合后再修"不可降级

## Gotchas

- 不要把 simplify 当成 refactor：simplify 不做范围裁决、不写 spec、不强制 Tidy First commit 拆分
- 不要把 simplify 当成 review：simplify 直接改，不只是报告
- false positive 跳过即可，不要和子任务"辩论"，浪费上下文
- 修完不跑验证 = 没修
- 范围超出 10 文件，结果通常会变成无序的小改动堆叠；先收窄

## 禁止

- 在 simplify 阶段引入新抽象 / 新 API / 新依赖
- 修改测试断言（仅修测试代码的明显 reuse / efficiency 问题）
- 把行为变化（功能、性能 trade-off）藏在 simplify diff 里
- 跳过验证就声明完成

## 关联技能

- 实现完成 / TDD Green 后清理 → `/dev-tdd` → `/dev-simplify` → `/guard-verify`
- 范围超出 simplify 边界 → `/dev-refactor`
- 发现的问题需要测试保护 → `/dev-tdd`
- simplify 通过后 → `/guard-verify` → `/guard-ship`

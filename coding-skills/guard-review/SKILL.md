---
name: guard-review
description: 当存在未 review 的代码变更或需要在合并前把关时使用；对 diff 做正确性/架构/测试/可观测性/scope drift 审查，产出带 file:line 的分级问题清单(Hard Stop/Critical/Important/Minor)与 Ready to merge 裁决，支持 --deep / --two-pass。不用于专项安全漏洞与 STRIDE 攻击面评估→改用 guard-secure；不用于给自己交付物出验证证据→改用 guard-verify；不做交付前多 guard 编排→改用 guard-check。
argument-hint: <分支名|commit-range|--deep|--two-pass|留空=未提交变更>
---

# Review

## 1. 确定范围

解析 `$ARGUMENTS`：

- 分支名 → `git diff $(git merge-base HEAD <branch>)..HEAD`
- diff 范围（如 `a1b2c3..HEAD`）→ 使用指定 commit range
- `--deep` → 启用多模型对抗性审查
- `--two-pass` → 启用候选生成 + 二次验证流水线；可与分支名 / commit range 组合（如 `main --two-pass`）
- 留空 → 审查未提交变更

### 工具化前置

进入正式审查前，先跑 dotfiles helper 拿一份结构化摘要；不要假设目标项目有 `scripts/collect_diff.py`：

```
python3 "<dotfiles_root>/scripts/collect_diff.py"              # 未提交变更
python3 "<dotfiles_root>/scripts/collect_diff.py" <branch>     # branch..HEAD
python3 "<dotfiles_root>/scripts/collect_diff.py" a1b2..HEAD   # commit 范围
```

输出：文件/增删行数表 + Flags（敏感信息疑似、TODO/FIXME/console.log 等）。作为 review 的 overview，不替代人工判断。

## 2. Simple Review（默认）

派发单个只读子任务审查 diff，输出结构化报告：

### 默认聚焦策略

- **先看 diff，再看直接影响面**：默认只审查改动文件、同模块调用链、被改测试和明显受影响的配置/脚本。
- **不要一上来做 repo-wide 猎巫**：范围外的担忧可以记录，但不能和当前 diff 里的确定性问题混在一起。
- **严重度要有证据门槛**：只有存在明确失败路径、触发条件、影响范围时，才能升到 `Critical` / `Important`。
- **数据库专项路由**：命中 MySQL/InnoDB DDL、migration、索引、表结构命名或查询性能设计时，追加 `/guard-mysql-review`；本 skill 只汇总裁决，不复制 MySQL checklist。

### 审查维度

先做 **Aspect Routing**，再展开细查。不要把所有 diff 都默认升级成全量专项 review；每个 aspect 必须有触发证据或明确 skip reason。

| Aspect | 触发信号 | 路由 / 重点 | Skip reason 示例 |
|---|---|---|---|
| `code` | 默认适用；有代码、脚本、配置行为变化 | 正确性、边界、需求、回归；沿用本 skill 默认维度 | 纯 docs / refs 分析，且不改变 runtime 行为 |
| `tests` | 新增行为、bug fix、测试文件变化、验证缺口、用户声称已完成 | 测试覆盖关键路径、行为而非实现；必要时回到 `/dev-tdd` | 纯文档或只读 refs 登记，无行为变化 |
| `errors` | catch / fallback / retry / timeout / logging / 外部调用 / 状态变更 / silent failure 相关 diff | 错误是否可发现、是否带上下文、是否有 heartbeat / summary；细则见 `/dev-observe` | diff 不触及错误路径、外部调用或状态变更 |
| `types` | schema、domain model、API envelope、状态机、权限模型、数据结构或类型定义新增/修改 | invariant 是否显式、构造/变更点是否 enforce、非法状态是否可被创建；复杂结构可转 `/think-quality` | 无新增/修改类型或数据 contract |
| `comments` | 新增/修改注释、README、docs、示例、inline explanation | 注释是否和代码事实一致、是否会 comment rot、是否暗示未实现行为 | 没有说明性文本变更 |
| `simplify` | blocker 修完后、review 基本通过但 diff 可读性/重复/局部性仍有改进空间 | 路由到 `/dev-simplify`；只做轻量 cleanup，不改变目标边界 | 存在 Critical / Important blocker，或 cleanup 会混入行为变化 |

Aspect 选择规则：

- `code` 是默认基线，但 docs-only / refs-only 变更可以 skip，避免伪 review。
- `errors` 命中时，必须检查 silent failure，而不是只看 happy path。
- `types` 命中时，按 invariant 语言审查：encapsulation、expression、usefulness、enforcement；不要为了“更强类型”破坏项目 convention 或 YAGNI。
- `simplify` 永远排在 correctness/security/test blocker 之后；它不能抢先改代码，也不能把 review 变成重构建议会。
- 对每个未运行的 aspect 写一句 skip reason，让读者知道是基于 diff 裁剪，而不是遗漏。

- [ ] 正确性：逻辑、边界、错误处理
- [ ] 可观测性：错误路径是否静默吞错、错误是否带定位上下文、外部调用/状态变更/关键分支是否可观测、新增观测点是否分级合理（不过度埋点）；细则见 `/dev-observe`
- [ ] 架构：关注点分离、耦合度、依赖方向
- [ ] 安全：输入验证、敏感数据、注入风险
- [ ] 测试：覆盖关键路径、测试行为而非实现；**测试重写红旗**——diff 同时修改了实现和测试，且测试变更仅将 assertion expected 值改为匹配新行为（未新增 case、未验证边界）→ Important 起步，要求确认新 assertion 是否正确
- [ ] 需求：变更是否满足目标
- [ ] MySQL/InnoDB 专项（仅当 DDL / migration / 索引 / 查询性能 diff 命中）：是否已按 `/guard-mysql-review` 输出 Must / Should / Exception / Convention conflict / Anti-pattern 裁决
- [ ] UI 专项（仅当前端/UI/CSS diff 命中）：
  - [ ] 新增颜色是否来自 token，是否出现默认 indigo/purple 或 trust gradient
  - [ ] 是否新增硬编码 spacing/radius/shadow，破坏既有 design system
  - [ ] 是否固定宽高或滥用 `overflow-hidden`，导致文字溢出被掩盖
  - [ ] 是否缺 `focus-visible`、`prefers-reduced-motion`、mobile touch target
  - [ ] 是否出现卡片嵌套、glassmorphism、emoji icon、filler copy、无来源指标
  - [ ] 状态样式是否覆盖 loading/error/disabled/empty 中适用状态
- [ ] Drift Signals（scope drift 自动检查，命中任意一条 → Important 起步）：
  - [ ] diff 含与 PR 标题/描述无关的文件
  - [ ] 纯重构与行为变更混合在同一 commit
  - [ ] 引入 PR 描述未提及的新依赖
  - [ ] 删除看似不相关的代码
  - [ ] 引入未被本次需求要求的新抽象 / 封装层
  - [ ] 修改与需求无关的注释、格式、空白、quote style、import 排序或命名风格
  - [ ] 未经要求加入类型重写、docstring、额外校验、fallback、配置项或兼容层
  - [ ] 删除既有 dead code，而不是只清理本次改动造成的 unused / orphan
- [ ] 可修改性：改动是否局部、规则是否显式、是否破坏既有 convention、diff 是否足够单一

### Hard Stops（必须阻断 merge，优先级高于 Critical）

命中任意一条 → 结论必须是 `Ready to merge? No`，不能用 `With fixes` 兜底：

- **Destructive auto-execution**：diff 引入了 `rm -rf`、`DROP TABLE`、强制覆盖远端等无交互直接执行的破坏性命令
- **Hallucinated identifier**：diff 引用的函数 / 变量 / 模块 / 路径在仓库中不存在（LLM 幻觉典型，必须 Grep 验证）
- **Injection 风险**：SQL / shell command / HTML / 路径拼接未做转义或参数化
- **依赖未锁定**：新增依赖未同步出现在 lock 文件（`package-lock.json` / `pnpm-lock.yaml` / `poetry.lock` / `Cargo.lock` / `go.sum` 等）
- **悄悄删除测试 / release artifact**：删除既有测试、CI 配置、release 产物或 changelog，且 PR 描述无对应说明
- **CI config weakening**：diff 修改了 CI 配置（`.github/workflows/*`、`jest.config*`、`.eslintrc*`、`tsconfig*`、`biome.json`、`.prettierrc*` 等）中的阈值、skip、ignore 规则，使检查变宽松
- **Coverage threshold lowered**：diff 降低了 coverage 阈值或增加了 `coveragePathIgnorePatterns` / `istanbul ignore` 等排除规则

### 输出格式

```markdown
### Diff Overview（来自 scripts/collect_diff.py）
- 范围: `...`
- 文件: N
- +Added / -Removed

### Aspect Coverage
| Aspect | Status | Evidence / Skip reason |
|---|---|---|
| code | run / skipped | <改动含代码文件 / 纯 docs-only> |
| tests | run / skipped | <行为变化 / 无行为变化> |
| errors | run / skipped | <catch/fallback/retry/logging 命中 / 未触及错误路径> |
| types | run / skipped | <schema/domain/API envelope 命中 / 无类型或数据 contract 变化> |
| comments | run / skipped | <docs/comment 变化 / 无说明性文本变更> |
| simplify | run / skipped | <blocker 已清 / blocker 未清或不适用> |

### Hard Stops
- [ ] Destructive auto-execution
- [ ] Hallucinated identifier
- [ ] Injection 风险
- [ ] 新增依赖未在 lock 文件中
- [ ] 删除测试 / release artifact 无说明
（任一命中 → Ready to merge? No）

### Strengths
- [具体优点，带 file:line]

### Issues
| Priority | File:Line | Issue | 影响 | 修复建议 |
|----------|-----------|-------|------|----------|
| Hard Stop | path:7 | <一句话> | <失败路径> | <建议> |
| Critical | path:42 | <一句话> | <失败路径> | <建议> |
| Important | path:118 | ... | ... | ... |
| Minor | path:200 | ... | ... | ... |

### Drift Signals
- [ ] 文件与 PR 标题无关
- [ ] 重构与行为变更混合
- [ ] 新依赖未在描述中提及
- [ ] 不相关代码被删除
- [ ] 新增未要求的抽象层
- [ ] 无关注释 / 格式 / 风格漂移
- [ ] 未要求的类型重写 / docstring / 额外校验 / fallback / 配置项
- [ ] 删除非本次改动造成的 dead code

### Out-of-scope observations
- [范围外但值得记录的观察；不影响当前 Ready to merge 结论]

### Structural assessment
- Boundary / Locality / Convention / Explicitness / Testability / Diff Purity 中，哪些维度在退化，哪些在改善

### Human Attention（如果只看 5 处）
1. path:line — 一句话原因
2. path:line — ...
3. path:line — ...
4. path:line — ...
5. path:line — ...

### Assessment
Ready to merge? Yes / No / With fixes
（命中 Hard Stop → 必须 No；命中 Drift Signal → 不能 Yes）
```

## 3. Two-pass Review（--two-pass，大 PR 推荐）

**触发**：diff > 15 文件，或包含安全 / 数据库 / 认证模块。借鉴两阶段流水线，提高召回 + 控制误报。

### Pass 1：候选生成（按文件分组并行）

1. **分组**：按模块/职责把改动文件聚成 3-6 组（同模块的代码 + 测试一起；安全敏感文件独立成组；migrations 独立成组）
2. **并行派发**：每组派发独立的只读 review 子任务，prompt 包含该组的 file list + diff 切片 + Reporting Gate + Bug Patterns（见第 2 节）
3. **收集**：每个子任务返回 JSON findings 数组：`{priority, path, line, title, why, suggestion?}`

跨 agent 适配：有并行子任务能力的平台按其原生命名派发；无并行子任务能力的平台降级为顺序处理（保留分组，但顺序跑）。

### Pass 2：验证 + 去重

主流程对所有候选做二次过滤：

- **Reporting Gate 复检**：拒绝速度性 / 风格性 / 锚点失效 / 已报告过的 finding
- **Confidence-based 过滤**：
  - **P0**：trigger path 验证通过即放行
  - **P1**：能独立验证逻辑或安全错误才放行
  - **P2**：默认拒绝；只有同时满足三条件才放行——(1) 可独立验证 bug 真实存在；(2) 有具体触发路径；(3) 不是 edge case / defensive coding / 风格
- **严格去重**：
  - 候选间：同一 root cause 即使锚点不同，只保留 anchor 最佳 + 解释最清晰的一条，其余标 `duplicate of #N`
  - 与已有 PR 评论：重复的剔除
  - 同 file + 重叠 line range + 同 issue = duplicate（即使措辞不同）

### Pass 1 + Pass 2 输出格式

沿用第 2 节的输出格式，在 `### Diff Overview` 后追加：

```markdown
### Two-pass 统计
- 分组数：N
- Pass 1 候选总数：M
- Pass 2 通过：K（拒绝 M-K：去重 X / 证据不足 Y / 锚点失效 Z）
```

## 4. Deep Review（--deep）

多个独立子任务（不同模型或独立 prompt）审查相同 diff，汇总为：

- **Agreed Strengths** — 2+ reviewer 都提到的优点
- **Agreed Concerns** — 2+ reviewer 都提到的问题（最高优先级）
- **Divergent Views** — 分歧点（值得深入调查）

每个 reviewer 的独立报告附在后面供参考。

## 5. Confidence Calibration

严重度认定标准（与第 2 节"严重度证据门槛"配套使用）：

| 级别 | 认定条件 | 报告倾向 |
|---|---|---|
| **P0 (Hard Stop / Critical)** | 确定 crash / exploit / data loss，trigger path 已验证 | 必报 |
| **P1 (Important)** | 高置信度的逻辑或安全错误，触发路径清晰 | 必报 |
| **P2 (Minor)** | 真实 bug 但影响有限，或可疑但无法完全验证 trigger path | 默认拒绝；满足三条件才报：可独立验证 + 具体触发路径 + 非 edge case |
| **P3** | 真实但极小影响 | 仅作 backlog 项，不阻塞 merge |

宁可漏报 P2，不要误报 P0/P1。

## 6. 接收反馈

对审查发现的问题：

1. 对照代码库验证（先 grep，不盲目接受）
2. 技术上合理 → 实施修复，每条单独测试
3. 不合理 → 带理由推回（破坏现有功能 / 违反 YAGNI / 技术不适用）
4. 不明确 → 全部澄清后再动手

## 7. Anti-Rationalization Guard

review 时常见的"放行借口"，命中即拒绝放行：

| 借口 | 反驳 |
|---|---|
| "这只是小重构" | 重构和行为变更不能混 commit；先拆 |
| "测试在临时文件先验证一下" | 临时文件测试不算数，必须落到仓库测试套件 |
| "现在没时间补测试" | 风险高于测试成本时不允许跳过 |
| "agent 应该知道我意图" | 沉默选边禁止；意图必须在 PR 描述/commit message 显式表达 |
| "审过类似的 PR 这次也行" | 每个 diff 独立审，不能继承上一次结论 |

## 8. Gotchas

- 没有明确失败路径、触发条件和影响面，不要上升到 `Critical` / `Important`
- review 的对象默认是当前 diff，不是借题发挥做全仓库猎巫
- 没有 `file:line` 或明确 diff 片段的意见，价值很低
- “建议更优雅”不等于问题；优先判断是否影响正确性、需求、结构质量或可维护性

## 扩展阅读

- `docs/software-engineering-research/review.md`

## 禁止

- 表演性回应（"Great point!", "You're absolutely right!"）
- 不验证就实施 reviewer 建议
- 模糊反馈（"这里可以优化"没有 file:line 和具体建议）
- 没有明确失败路径就上升严重度
- 把 repo 级猜测混进当前 diff 的主结论
- 没有裁决的审查（必须给出 Ready to merge? 结论）

## 关联技能

- Critical issues 涉及安全 → `/guard-secure` 深入审查
- MySQL/InnoDB DDL、migration、索引、表结构或查询性能取舍 → `/guard-mysql-review`
- 需要统一结构质量语言 → `/think-quality`
- 发现需要重构 → `/dev-refactor`
- Review 通过后交付 → `/guard-ship`

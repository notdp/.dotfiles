---
name: guard-verify
description: 当准备报告"已完成/已修复/可交付"、需要为自己交付物逐条给证据时使用；跑 test/build/lint 并按 L1 存在/L2 实质/L3 接通三层级 + Inner-loop/Acceptance/Holdout 分层输出验证证据与剩余缺口。不用于审查他人/未合并 diff 的代码质量→改用 guard-review；不用于做安全漏洞与攻击面评估→改用 guard-secure；不用于裁决停/继续→改用 guard-close。
argument-hint: <交付物|验证范围>
---

调用本 skill 后，先提供验证证据；缺少验证结果时，报告状态写为 `partial` 或 `verification: none -- structural gap`。

## 触发时机

适用于即将向用户报告”已完成”/”已修复”/”已实现”的场景。

## Spec Contract 消费

如果上游 spec 中存在 `# spec-contract` YAML 块：

1. 将 checks 列表作为 Deliverables 表的初始行（每条 check 对应一行）
2. 将 non_goals 列表加入验证报告的”显式排除项”
3. 运行 validation_commands 中的命令，结果纳入”自动验证”表
4. 在验证证据分层中，标注 checks 覆盖了哪个层级（Inner-loop / Acceptance）

如果没有 spec-contract 块，从对话上下文提取验收标准（现有行为不变）。

## 验证清单

1. **提取可验证交付物** — 先把用户要求拆成 1-N 条“现在应该能够做到什么”，作为后续验收清单
2. **自动跑 test/build/lint** — 优先用 `${HOME}/.dotfiles/scripts/run-verify.sh` 一键探测并运行；不适配时手动跑项目对应命令
3. **功能验证** — 对每条交付物执行验证命令或操作，确认预期行为
4. **回归检查** — 确认没有破坏已有功能
5. **结构性验证** — 若本次改动涉及架构/重构/大 diff，补充说明影响面是否合理、验证护栏是否足够；必要时引用 `/think-quality` 结论

## 验证证据分层

测试通过不等于用户目标达成。验证报告必须区分以下层级：

| 层级 | 作用 | 示例 | 是否可单独宣称完成 |
|---|---|---|---|
| Inner-loop | 实现局部正确性 | unit test、lint、typecheck、mocked test | 仅适合纯局部改动 |
| Integration | 模块协作正确性 | API + DB、CLI dry-run、服务间调用 | 视任务边界而定 |
| Acceptance | 用户目标达成 | E2E、真实输入、holdout、人工观察、回归样例 | 复杂任务必须有 |
| Regression | 未破坏已有能力 | 历史样例、关键路径、快照对比 | 重要任务必须考虑 |

复杂任务、用户可见功能、数据任务、模型/评测任务、Agent 流程需要 acceptance evidence 才能标 verified。若 acceptance verifier 不适用，说明原因和剩余风险。

最终报告必须显式列出：

- `Inner-loop evidence`
- `Acceptance evidence`
- `Holdout / unseen evidence`（不适用则说明）
- `Known gaps`

## UI 任务额外门禁

当交付物涉及 UI、CSS、React/Vue/Svelte 组件、页面、设计系统或视觉调整时，自动验证不够。必须补充视觉证据：

| Check | 必需证据 |
|---|---|
| 页面入口 | URL、本地 route、Storybook story 或组件预览入口 |
| Viewport | 至少 mobile + desktop；建议 `390x844`、`1280x900` |
| Screenshot | 每个关键 viewport 的截图路径 |
| DOM snapshot | 关键区域 snapshot 或 selector 查询结果 |
| Horizontal overflow | `scrollWidth <= innerWidth` 或等价检查 |
| Text overflow | 聚焦区域无截断、遮挡、按钮撑破的证据 |
| Interaction state | 关键控件 hover/focus/disabled/loading/error 中适用状态 |
| DESIGN.md adherence | 若存在 `DESIGN.md`，说明已读取并给出 token / direction 遵守证据；若偏离，说明理由 |
| Reference diff | 有参考图时引用 `/fe-ui-visual-iterate` 差异表 |

UI verified 状态只在截图、overflow 和适用交互状态证据齐备时成立。缺截图或 overflow 证据时，UI 交付物状态写为 `partial`。

## 代码可观测性门禁（错误路径 / 外部调用 / 状态变更的改动）

当本次改动引入或修改了错误处理、外部调用（DB/HTTP/MQ/文件/子进程）、状态变更或关键分支时，验证可观测性是否到位（细则与分级见 `/dev-observe`）：

| Check | 必需证据 |
|---|---|
| 错误可发现 | 新增/改动的 catch、失败分支不静默吞错；错误带定位上下文（关键变量，不含 secret） |
| 关键路径可观测 | 外部调用、写操作、关键分支有日志或 trace，能还原一次执行 |
| 分级合理 | 观测强度匹配影响面，未在热路径制造逐行噪音，未引入平行 logger |
| 无敏感泄露 | 日志/trace/metric label 不含 secret、token、完整 PII |

纯文档/配置/样式改动，或无错误路径/外部调用/状态变更的纯内部纯函数改动，此门禁标 `not applicable` 并说明原因。

## Data / Operational 任务额外门禁

当交付物涉及长耗时批处理、数据同步/回填/修复、迁移脚本、复杂 CLI、`dry-run/apply` 时，必须补充 operational evidence：

| Check | 必需证据 |
|---|---|
| dry-run data accuracy | planned count、sample、diff/aggregation、invariants、failure examples、holdout/unseen sample |
| progress observability | phase、current/total、percent、rate 或 ETA、heartbeat |
| resumability | checkpoint/cursor/state file/idempotency key；中断后 resume 命令 |
| robustness | retry/backoff、timeout、failed set 或 partial failure summary |
| CLI UX | preset/default/wizard/help；复杂 wizard 必须打印底层可复制命令 |
| apply safety | apply confirmation、post-apply verification、必要时 `/guard-gitops` evidence |

数据任务 verified 状态需要 dry-run 数据准确性证据。dry-run 缺少数据准确性证据时，写：

```text
dry-run: smoke only -- data accuracy not verified
```

数据、模型、推荐、分类、生成质量、评测类任务必须区分 tuning/dev cases 与 holdout/unseen cases。没有 holdout 时，必须提供替代证据：随机抽样、边界样例、历史回归样例或人工复核记录。

## 工具化步骤

```
bash "${HOME}/.dotfiles/scripts/run-verify.sh" "<target_repo_root>"
```

- 自动探测 package.json / pyproject.toml / Cargo.toml / Makefile / go.mod 等并运行对应 test / lint / typecheck / build
- 输出固定 Markdown 表，agent 直接贴进报告作为 Evidence
- exit code 0=全绿，1=有失败，2=无任何可检测命令（需要手动补）
- `${HOME}/.dotfiles/scripts/run-verify.sh` 来自 dotfiles；目标项目路径作为参数传入

### Verification: None 强制声明

当出现以下任一情况时，报告状态使用 `verification: none -- structural gap`：

- `${HOME}/.dotfiles/scripts/run-verify.sh` 退出码为 `2`（无任何可探测的 test / lint / build 命令）
- 没有探测到自动化测试入口，且本次也未补 characterization
- 仅靠"看上去对"或"本地手动跑过一次"作为证据

此时必须在报告中显式输出一行：

```
verification: none -- structural gap
```

并把"补可执行验证"列入"待补 / Followups"。

## 验证三层级（每条 Deliverable 都必须分别给 L1/L2/L3 证据）

文件 / 函数能找到 ≠ 实现到位。三层级齐备时才算 verified：

| 层级 | 含义 | 不充分的反例 |
|---|---|---|
| **L1 Exists** | 目标文件 / 函数 / 路由 / 配置 / 命令在仓库里真实存在 | 只能找到名字但函数体是 `pass` / `TODO` |
| **L2 Substantive** | 实现非空、有真实逻辑、不是 stub / placeholder / 抛 NotImplemented | 函数返回硬编码常量、永远走 happy path |
| **L3 Wired** | 调用方真的接到了：被路由注册、被前端引用、被 CLI 暴露、CI 真的会跑 | 实现存在但没人调用，孤岛代码 |

每条 must-have 必须分别提供：

- L1 证据：`Grep` / `Glob` / `LS` 命中（路径 + 行号）
- L2 证据：函数体片段、关键分支或具体行为说明
- L3 证据：调用点、注册位置、入口绑定（路径 + 行号）

任意层级缺证据 → 该条交付物状态为 `partial`。

## 输出格式

完成报告必须包含以下固定结构：

```markdown
## 验证结果

### Deliverables（三层级，缺一不可）
| # | 交付物 | L1 Exists | L2 Substantive | L3 Wired | 状态 |
|---|--------|-----------|----------------|----------|------|
| 1 | <用户要求 1> | path:line | 行为/逻辑片段 | 调用点 path:line | verified / partial |
| 2 | <用户要求 2> | ... | ... | ... | ... |

### 自动验证（${HOME}/.dotfiles/scripts/run-verify.sh）
| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| tests | `...` | pass (Ns) | N passed |
| lint  | `...` | pass | ... |

（若 exit=2 / 未探测到测试命令 / 无 characterization：在此节末尾追加 `verification: none -- structural gap`）

### 验证证据分层
| 层级 | Result | Evidence |
|------|--------|----------|
| Inner-loop evidence | pass/partial/none | unit/lint/typecheck/mock 等证据 |
| Integration evidence | pass/partial/none | 模块协作、CLI、API、DB 等证据 |
| Acceptance evidence | pass/partial/none | E2E、真实输入、用户路径、人工观察等证据 |
| Holdout / unseen evidence | pass/partial/not applicable | 未参与调试的样例、随机样本、边界样本、历史回归样例；不适用时说明原因 |
| Known gaps | none/list | 未覆盖风险、无法验证项、需人工验收项 |

### UI 视觉验证（仅 UI 任务）
| Check | Result | Evidence |
|-------|--------|----------|
| viewport | pass/partial | `390x844`, `1280x900` |
| screenshot | pass/partial | `/tmp/.../page.png` |
| horizontal overflow | pass/partial | `scrollWidth <= innerWidth` |
| text overflow | pass/partial | selector / screenshot region |
| interaction states | pass/partial | selector / screenshot / snapshot |
| DESIGN.md adherence | pass/partial | `DESIGN.md` path + token/direction evidence |

### 代码可观测性验证（含错误路径 / 外部调用 / 状态变更的改动）
| Check | Result | Evidence |
|-------|--------|----------|
| 错误可发现 | pass/partial/n.a. | 静默吞错检查 / 错误上下文 |
| 关键路径可观测 | pass/partial/n.a. | 外部调用 / 写操作的日志或 trace |
| 分级合理 | pass/partial/n.a. | 未制造噪音 / 未引入平行 logger |
| 无敏感泄露 | pass/partial/n.a. | 日志无 secret/PII |

### Data / Operational 验证（仅长任务 / 数据任务 / 复杂 CLI）
| Check | Result | Evidence |
|-------|--------|----------|
| dry-run data accuracy | pass/partial | count / sample / diff / invariants |
| progress observability | pass/partial | phase / current / total / percent / ETA / heartbeat |
| resumability | pass/partial | checkpoint / cursor / resume command |
| robustness | pass/partial | retry / failed set / timeout behavior |
| CLI UX | pass/partial | preset / wizard / copyable command |
| apply safety | pass/partial | confirmation / post-apply verification / guard-gitops |

### 结构性评估
- 影响面: ...
- 护栏是否足够: yes / no（理由）
- 是否需要 `/think-quality`: yes / no
```

### Long-loop 每轮验证（仅 long-loop 任务）

当交付物来自 `.long-loop/` 工作流时，额外输出：

```markdown
### Long-loop 轮次验证
| Iteration | Plan item | Agent result | Verify | Diff scan | State update | Verdict |
|---|---|---|---|---|---|---|
| 1 | ... | pass/fail | pass/fail | pass/fail | pass/fail | continue/stop |

### Stop check
- [ ] 未超过 max_iterations
- [ ] `.long-loop/logs.md` 已更新
- [ ] `.long-loop/fix_plan.md` 已更新
- [ ] `.long-loop/state.json` 已更新
- [ ] 未触发远端副作用
```

## 规则

- 报告完成状态前先跑对应验证命令
- 测试/构建通过 ≠ 用户可感知行为已经成立；交付物必须单独验收
- 验证失败 → 修复 → 重新验证，直到通过

## Anti-Rationalization Guard

声称"已验证"前常见的放行借口，命中时改写为 `partial` 或 `verification: none -- structural gap`：

| 借口 | 反驳 |
|---|---|
| "本地手测过了" | 必须在仓库测试套件里跑通；本地一次性手测不算证据 |
| "测试改了但意图不变" | 测试改写需独立 review，不能既当被验证对象又当验证者 |
| "没探测到测试命令但能编译" | 编译 ≠ 验证；走 `verification: none -- structural gap` 流程 |
| "之前同类改过没问题" | 每次必须重跑当前 diff，不能继承上次结论 |

对抗式姿态：声称"已验证/已完成"前，先假设产物**仍有缺陷**，主动找一条能**反驳**完成声明的证据（边界输入、回归、未覆盖路径）。找不到反证才算通过；找到就如实降级为 `partial`。

## Gotchas

- 测试通过不等于交付物成立；用户要求必须逐条验收
- 报告“已完成”时附上证据截图、命令输出或可复现步骤
- 文档/配置类改动也要验证链接、路径、命令和引用是否仍然成立
- 若验证发现范围外回归，必须回退到对应 skill 修复，而不是在总结里弱化问题

## 关联技能

- 需要补结构性判断 → `/think-quality`
- 验证通过 → 可进入 `/guard-ship` 交付
- 验证失败 → 回到对应 skill 修复（`/dev-debug`、`/dev-tdd`）

# Long-Running Agent 调研

调研对象：本地文章草稿 `草稿_20260430_Long-Running-Agent/article.html`。详细摘录见 `refs/long-running-agent/README.md`。

## 新版文章补充

[确认] 新版文章把“如何开始”明确拆成三档：

1. **Ralph Loop**：最小可用，一行 bash + `PROMPT.md` / `fix_plan.md` / `AGENT.md`。
2. **CC / Codex 原生扩展点**：规则文件、hooks、subagents、headless/action/SDK，分别对应状态、上下文和验证。
3. **规模化形态**：Managed Agents、Background Agents、Devin、OpenHands、Planner/Worker/Judge。

[确认] 新版还强调“边界 / 验收 / 预算”必须落到磁盘。对本仓库来说，这比直接追求 daemon 或多 agent 调度更重要。

## 推荐方案

[推断] 本仓库要支持 long loop run，第一步不应直接做后台 daemon 或无限循环，而应先提供“文件系统驱动的手动 harness”：

1. 生成 `.long-loop/` workspace。
2. 把边界、验收、预算写入磁盘。
3. 每轮只执行一个 todo。
4. 每轮后由独立验证链判断继续 / 停止。

这样能先解决长任务的三堵墙：上下文腐化、无持久状态、无自我验证。

## 架构模型

| 层 | 职责 | 本仓库候选实现 |
|---|---|---|
| Brain | 决策和下一步选择 | Droid 非交互执行、skills、custom droids |
| Hands | 执行动作 | 文件工具、shell、browser/TUI skills、scripts |
| Memory | 持久状态 | `.long-loop/` 下的 prompt、plan、assert、progress、logs |
| Judge | 独立验证 | `guard-verify`、`guard-diff-scan`、`guard-review`、测试脚本 |

## 最小 workspace

```text
.long-loop/
├── PROMPT.md
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── ASSERT.md
├── progress.md
├── logs/
│   └── YYYY-MM-DD.md
└── state.json
```

| 文件 | 内容 |
|---|---|
| `PROMPT.md` | 每轮静态指令，引用 plan/assert/progress，不放长状态报告 |
| `SPEC.md` | 目标、边界、非目标、验收标准；运行前人工审批的主要对象 |
| `IMPLEMENTATION_PLAN.md` | 按优先级排序的 todo，一轮只做一个 |
| `ASSERT.md` | 验收命令、边界、预算、禁止项 |
| `progress.md` | 当前状态、最近一轮结果、下一步 |
| `logs/` | append-only 事件日志 |
| `state.json` | 轮数、开始时间、最近 commit、预算消耗 |

## 每轮协议

0. `plan` 生成工作区后，人工审核 `SPEC.md` / `IMPLEMENTATION_PLAN.md` / `ASSERT.md`，执行 `approve` 后才允许 `run`。
1. 读取 `PROMPT.md` / `SPEC.md` / `IMPLEMENTATION_PLAN.md` / `ASSERT.md`。
2. 选择最高优先级未完成 item。
3. 执行前确认当前工作树和上一轮状态。
4. 完成一个 item，不扩 scope。
5. 运行该 item 的最小验证。
6. 更新 plan / progress / logs。
7. 运行 Judge：verify、diff scan、必要时 review。
8. 满足 stop 条件则退出；否则进入下一轮。

## Stop 条件

- plan 已无未完成 item。
- 连续 2 次验证失败。
- 轮数 / 时间 / 预算到上限。
- Judge 发现未处理 P0/P1 风险。
- 人工 `pause` 介入，等待更新计划并重新 `approve`。
- 需要用户产品判断或外部副作用授权。
- 工作树出现非本轮来源的不明修改。

## 不要自造轮子

- 已有验证：复用 `scripts/run-verify.sh`。
- 已有残留扫描：复用 `scripts/scan_diff_residue.py`。
- 已有交付前预检：复用 `scripts/preflight.sh`。
- 已有复杂交付：复用 `dev-large-delivery` 的 phase 思路。
- 已有卡住升级：复用 `think-unstuck` 的 handoff 格式。

## 风险与坑

- [确认] 无限循环必须禁止；long loop 必须是有预算的循环。
- [确认] 状态不能写进规则文件；规则、计划、进度、日志必须分文件。
- [确认] 一轮多个 todo 会让回归验证和回滚变困难。
- [推断] 初版不应默认 push；push 是远端副作用，应走 `guard-gitops` / `guard-ship`。
- [推断] 如果 Judge 在关键路径上负责合并结果，会变成 Integrator 瓶颈；Judge 应只判继续 / 停止。

## 建议吸收项

| 类别 | 建议 | 落点 |
|---|---|---|
| 新增 | `dev-long-loop` skill 或 command，用于生成 `.long-loop/` 三件套和执行协议 | `skills/` 或 `commands/` |
| 新增 | `scripts/long_loop.sh` 轻量 harness，支持 max iterations / time budget | `scripts/` |
| 修改增强 | `dev-large-delivery` 增加 Brain/Hands/Memory/Judge 术语和 `.long-loop/` handoff | `skills/dev-large-delivery/SKILL.md` |
| 修改增强 | `guard-verify` 增加 long-loop 每轮验证表 | `skills/guard-verify/SKILL.md` |
| 新增测试 | long-loop script 的预算、stop、resume 行为测试 | `scripts/tests/` |

## 推荐路线

1. 先实现 command/skill 生成 `.long-loop/` workspace，不自动执行。
2. 再实现脚本化单轮 runner，只跑一轮并输出结果。
3. 最后才做多轮 loop，默认 `max_iterations` 很小，并禁止默认 push。

## 本仓库落地用法

推荐入口：

```bash
/long-loop help
/long-loop plan "实现 X 长任务"
/long-loop approve
/long-loop run --once --agent-cmd '<agent command>'
/long-loop run --max-iterations 3 --max-minutes 45 --agent-cmd '<agent command>'
/long-loop status
/long-loop status --json
/long-loop tail --lines 80
/long-loop watch --interval 10
/long-loop watch --interval 10 --iterations 1
/long-loop pause --reason "调整计划"
/long-loop stop --reason "需要人工判断"
```

底层脚本：

```bash
scripts/long_loop.py plan --goal "实现 X 长任务"
scripts/long_loop.py help
scripts/long_loop.py approve
scripts/long_loop.py run --once --agent-cmd '<agent command>'
scripts/long_loop.py status
```

原则：

- `run` 必须显式传 `--agent-cmd`，不猜具体 agent CLI。
- `help` 是默认入口：输出状态转移图；若工作区已存在，则同时输出当前状态和下一条建议命令。
- 未 `approve` 前 `run` 必须拒绝执行；`pause` 后也要重新 `approve`。
- 默认 `max_iterations=1`。
- 每轮后复用 `scripts/run-verify.sh` 和 `scripts/scan_diff_residue.py`。
- 初版不默认 commit / push。

---
name: dev-long-loop
description: 当任务目标明确但预计需要多轮自主执行、跨会话状态或长时间推进时使用；生成并执行有预算、有验收、有停止条件的 long-loop 工作流。
argument-hint: <help|plan|approve|run|status|tail|watch|pause|stop|resume> <目标或参数>
---

# Long Loop

用于把长任务从“靠 agent 记忆连续跑”改成“靠磁盘状态、安全预算和 Judge 链路推进”。

## Activation Guard

- 只有用户明确请求 `plan` / `init` / `approve` / `run` / `resume`，或明确说“进入 long-loop”，才按执行工作流推进。
- 如果入口是 `/long-loop help`，只解释帮助并停止；不得创建 `.long-loop/`，不得调用本 skill 继续任务，不得把当前上下文推断成计划。
- 如果入口是 `status` / `tail` / `watch`，只读状态或日志，不得修改 workspace。
- 未看到 `approval=approved` 前，不得执行任何任务迭代。

## 适用场景

- 目标明确，能拆成多个独立 todo
- 验收命令明确，能每轮验证
- 任务可能跨多个会话或持续较长时间
- 需要把边界、验收、预算写到磁盘，防止上下文漂移

不适用：

- 开放探索任务
- 没有验收标准的“试试看”
- 需要频繁产品判断或人工授权
- 外部副作用未授权（push、部署、数据库、第三方系统）

## 架构

| 层 | 本仓库实现 |
|---|---|
| Brain | agent 命令读取 `.long-loop/PROMPT.md` |
| Hands | 当前工具层和 `scripts/` |
| Memory | `.long-loop/state.json` + `fix_plan.md` + structured logs |
| Judge | `validator.md` item validator + full guard + 必要时 `guard-review` |

## 用法

先解析脚本绝对路径。不要因为当前工作目录没有 `./scripts/long_loop.py` 就判断脚本缺失；本 dotfiles 仓库的 fallback 是 `$HOME/.dotfiles/scripts/long_loop.py`。

```bash
LONG_LOOP_SCRIPT="$HOME/.dotfiles/scripts/long_loop.py"
python3 "$LONG_LOOP_SCRIPT" help
```

```bash
python3 "$LONG_LOOP_SCRIPT" help
python3 "$LONG_LOOP_SCRIPT" init --goal "实现 X"
python3 "$LONG_LOOP_SCRIPT" plan --goal "实现 X"
python3 "$LONG_LOOP_SCRIPT" approve
python3 "$LONG_LOOP_SCRIPT" status
python3 "$LONG_LOOP_SCRIPT" tail --lines 80
python3 "$LONG_LOOP_SCRIPT" watch --interval 10
python3 "$LONG_LOOP_SCRIPT" watch --interval 10 --iterations 1
python3 "$LONG_LOOP_SCRIPT" run --once --agent-cmd '<agent command>'
python3 "$LONG_LOOP_SCRIPT" run --max-iterations 3 --max-minutes 45 --agent-cmd '<agent command>'
python3 "$LONG_LOOP_SCRIPT" pause --reason "我要调整计划"
python3 "$LONG_LOOP_SCRIPT" stop --reason "需要人工判断"
```

对应 command 入口：`/long-loop help|plan|approve|run|status|tail|watch|pause|stop|resume`。

## 降低认知负担

默认先跑 `help`。它会输出状态转移图；如果 `.long-loop/state.json` 已存在，还会显示当前状态和下一条建议命令。

```text
plan -> awaiting_approval -> approve -> approved -> run -> running
running -> stopped     [max iterations, max minutes, validation failure]
running -> done        [no remaining todo]
running -> pause -> paused -> edit plan -> approve -> approved
stopped -> approve -> approved -> resume -> running
```

## Ralph Loop Contract

目标工作流：

```text
question -> context -> ask/research -> plan -> await approval -> iterate -> verify -> summarize -> update -> stop/done
```

规则：

1. 信息不足时先调研或用 AskUser 提问，不得直接实现。
2. 信息足够时先产出计划，让用户批准。
3. 用户批准前只允许创建/更新计划 workspace，不允许执行任务。
4. 用户批准后才进入迭代；一轮只做一个 plan item。
5. 每轮结束必须输出阶段总结，并写入 `progress.md` 与 `logs/YYYY-MM-DD.md`。
6. 阶段总结至少包含：本轮 plan item、执行结果、验证结果、状态变化、下一步。

## Fresh Iteration Contract

每轮必须重新开始，避免旧 context 干扰：

1. 只加载 `PROMPT.md`、`specs/main.md`、当前 `fix_plan.md` item、`validator.md`、最近一条阶段总结。
2. 不把上一轮完整 stdout / stderr 或长对话历史放回 prompt。
3. 不依赖上一轮模型记忆判断 item 状态。
4. 动手前重新搜索代码，确认当前 item 是否已经实现。
5. 新发现写回 `fix_plan.md` 或结构化 log，不写进 `PROMPT.md`。

## Validator-first Contract

1. `validator.md` 是 Judge SSOT。
2. 每轮必须有 item validator；缺失时停止并补 validator，不进入实现。
3. 行为变更优先走 Red → Green：先确认 validator 对当前缺口有检测价值，再实现。
4. 实现后重跑 item validator；失败就在本轮修。
5. item validator 通过后再跑 full guard。
6. validator 结果写入 `validator-results.json` 和 `events.jsonl`。

## Structured Log Contract

append-only log 只记录关键事件，不做状态垃圾桶。

标题格式：

```text
YYYY-MM-DDTHH:MM:SSZ | iteration-N | event-type | item summary
```

每块只记录 event、item、command、exit code、duration、evidence tail 或 artifact path、decision / next step。

禁止记录：

- 全量工具输出
- 重复 todo dump
- 可从 `state.json` / `fix_plan.md` 推导出的状态
- 状态报告式长文

## 审批门禁

`plan` / `init` 只生成 `.long-loop/` 工作区，状态为 `awaiting_approval`。未执行 `approve` 前，`run` 必须拒绝执行。

`pause` 会把状态改回 `paused` + `approval=pending`。人工修改 `SPEC.md` / `IMPLEMENTATION_PLAN.md` / `ASSERT.md` 后，必须重新 `approve` 才能继续。

## 每轮协议

1. 读取 `.long-loop/PROMPT.md`、`IMPLEMENTATION_PLAN.md`、`ASSERT.md`
2. 只选择最高优先级的一个未完成 item
3. 执行该 item，不扩 scope
4. 运行最小验证
5. 更新 plan / progress / logs / state
6. 运行 Judge：`run-verify.sh`、`scan_diff_residue.py`
7. 满足 stop 条件则退出，否则进入下一轮

## Stop 条件

- `IMPLEMENTATION_PLAN.md` 没有未完成 item
- 达到最大轮数或最大时间
- 验证失败
- diff scan 命中调试残留
- 连续失败 2 次
- 工作树出现不明冲突
- 需要用户判断或远端副作用授权

## 文件契约

```text
.long-loop/
├── PROMPT.md
├── specs/
│   └── main.md
├── fix_plan.md
├── validator.md
├── validator-results.json
├── events.jsonl
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── ASSERT.md
├── progress.md
├── logs/
│   └── YYYY-MM-DD.md
└── state.json
```

- `PROMPT.md`：规则文件，不写状态报告
- `specs/main.md`：当前任务规格
- `fix_plan.md`：任务与学习的 SSOT
- `validator.md`：item validator 与 full guard 契约
- `validator-results.json`：validator 结构化结果
- `events.jsonl`：机器可检索事件流
- `SPEC.md`：兼容旧 workspace 的长任务目标文件；新 workspace 优先读 `specs/main.md`
- `IMPLEMENTATION_PLAN.md`：兼容旧 workspace 的 todo 文件；新 workspace 优先读 `fix_plan.md`
- `ASSERT.md`：兼容旧 workspace 的验收文件；新 workspace 优先读 `validator.md`
- `progress.md`：当前状态和最近一轮结果
- `logs/`：append-only 事件日志
- `state.json`：机器可读状态

## 可观测性 contract

| 等级 | 命令 | 作用 |
|---|---|---|
| 状态可查 | `status` / `status --json` | 状态、审批、轮数、剩余 todo、最近验证 |
| 日志可追 | `tail --lines N` | 查看最近 append-only 日志 |
| 运行可看 | `watch --interval N` | 定期刷新状态和最近日志 |
| 人工可干预 | `pause` + 编辑文件 + `approve` | 暂停执行、人工调整计划、重新批准后继续 |

## Gotchas

- long loop 不是无限循环；没有预算上限就不要跑。
- 不默认 push；push 必须走 `/guard-ship` / `/guard-gitops`。
- 不把状态写进 `PROMPT.md` 或 `ASSERT.md`。
- 一轮多个 todo 会让回滚和验证变困难。

## 扩展阅读

- `docs/software-engineering-research/long-running-agent.md`

## 关联技能

- 写长任务 spec → `/think-plan`
- 技术不确定 → `/think-research`
- 每轮代码实现 → `/dev-tdd`
- 每轮验证 → `/guard-verify`
- 卡住 → `/think-unstuck`
- 远端副作用 → `/guard-gitops`

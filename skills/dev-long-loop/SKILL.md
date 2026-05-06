---
name: dev-long-loop
description: 当任务目标明确但预计需要多轮自主执行、跨会话状态或长时间推进时使用；生成并执行有预算、有验收、有停止条件的 long-loop 工作流。
argument-hint: <help|plan|approve|run|status|tail|watch|pause|stop|resume> <目标或参数>
---

# Long Loop

用于把长任务从“靠 agent 记忆连续跑”改成“靠磁盘状态、安全预算和 Judge 链路推进”。

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
| Memory | `.long-loop/` 文件系统状态 |
| Judge | `scripts/run-verify.sh` + `scripts/scan_diff_residue.py` + 必要时 `guard-review` |

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
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── ASSERT.md
├── progress.md
├── logs/
│   └── YYYY-MM-DD.md
└── state.json
```

- `PROMPT.md`：规则文件，不写状态报告
- `SPEC.md`：长任务目标、边界、非目标、验收标准
- `IMPLEMENTATION_PLAN.md`：todo SSOT，一轮只做一个
- `ASSERT.md`：验收命令、预算、禁止项
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

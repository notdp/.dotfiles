---
description: 规划、批准、运行、观察和停止长任务 long-loop 工作流；基于 .long-loop/<日期>_主题/ 文件系统状态、预算和验证链路。
argument-hint: <help|plan|approve|run|status|tail|watch|pause|stop|resume> [目标或参数]
---

# Long Loop

长任务工作流入口。它不是无限循环器，而是有边界、有验收、有预算、有停止条件的执行 harness。

## 命令路由规则

当前调用参数：

```text
$ARGUMENTS
```

第一段是子命令，其余内容原样作为该子命令参数。必须按这里的实际参数路由；如果参数为空，等同于 `help`。

按用户显式给出的子命令执行，不得把一个子命令推断成另一个子命令。

- `help` 是终止命令：只输出帮助，然后停止。
- `help` 不得创建 `.long-loop/` 或任务工作区，不得调用 `dev-long-loop`，不得根据上下文生成计划。
- `status` / `tail` / `watch` 只读，不得创建或修改 workspace。
- `plan` / `init` 只生成审批前 workspace：默认目录是 `.long-loop/<YYYY-MM-DD>_<topic>/`，状态必须是 `awaiting_approval` + `approval=pending`，并把关键文件 review bundle 打印到屏幕。
- `plan` / `init` 必须检查仓库根目录 `.gitignore`；若没有忽略 `.long-loop/`，自动追加 `.long-loop/`。
- 初始计划处于 `awaiting_approval` 时，用户直接执行 `run` 等同于显式批准并立即运行；独立 `approve` 仍保留给只想先解锁、不马上执行的场景。
- `run` / `resume` 除上述初始计划快捷路径外，只有在 `approval=approved` 后才能执行。
- `fix_plan.md` 是任务 SSOT；每轮只取最高优先级 item。
- `validator.md` 是 Judge SSOT；没有 item validator 不得进入实现。
- 每轮按 Fresh Iteration 重新加载最小上下文，不复用旧对话记忆。
- 每轮结束必须输出阶段总结，并写入当前任务工作区的 `progress.md`、`events.jsonl` 与 append-only log。

## 用法

```bash
/long-loop help
/long-loop plan "实现 X 长任务"
/long-loop approve
/long-loop status
/long-loop tail --lines 80
/long-loop watch --interval 10
/long-loop watch --interval 10 --iterations 1
/long-loop run --once --agent-cmd '<agent command>'
/long-loop run --max-iterations 3 --max-minutes 45 --agent-cmd '<agent command>'
/long-loop pause --reason "我要调整计划"
/long-loop stop --reason "需要人工判断"
/long-loop resume --max-iterations 2 --agent-cmd '<agent command>'
```

## 适用

- 目标明确
- 验收命令明确
- 可以拆成多个独立 todo
- 需要跨会话保存状态

## 不适用

- 开放探索
- 无验收标准
- 需要频繁产品判断
- 外部副作用未授权

## 执行方式

脚本在本仓库维护为 `scripts/long_loop.py`。执行时先解析绝对路径，不要只用当前工作目录判断脚本是否存在；只要下面任一路径存在，就直接调用脚本，不要弹 AskUser：

```bash
COMMAND_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"

if [ -n "$COMMAND_DIR" ] && [ -x "$COMMAND_DIR/../scripts/long_loop.py" ]; then
  LONG_LOOP_SCRIPT="$COMMAND_DIR/../scripts/long_loop.py"
elif [ -x "$HOME/.dotfiles/scripts/long_loop.py" ]; then
  LONG_LOOP_SCRIPT="$HOME/.dotfiles/scripts/long_loop.py"
else
  echo "missing long-loop script: scripts/long_loop.py" >&2
  exit 1
fi

python3 "$LONG_LOOP_SCRIPT" <subcommand> <args>
```

子命令映射：

| `/long-loop` | 脚本 |
|---|---|
| `help` | `python3 "$LONG_LOOP_SCRIPT" help` |
| `plan "goal"` | `python3 "$LONG_LOOP_SCRIPT" plan --goal "goal"` |
| `init "goal"` | `python3 "$LONG_LOOP_SCRIPT" init --goal "goal"`（兼容入口） |
| `approve` | `python3 "$LONG_LOOP_SCRIPT" approve` |
| `status` | `python3 "$LONG_LOOP_SCRIPT" status` |
| `tail ...` | `python3 "$LONG_LOOP_SCRIPT" tail ...` |
| `watch ...` | `python3 "$LONG_LOOP_SCRIPT" watch ...` |
| `run ...` | `python3 "$LONG_LOOP_SCRIPT" run ...` |
| `resume ...` | `python3 "$LONG_LOOP_SCRIPT" run ...` |
| `pause --reason "..."` | `python3 "$LONG_LOOP_SCRIPT" pause --reason "..."` |
| `stop --reason "..."` | `python3 "$LONG_LOOP_SCRIPT" stop --reason "..."` |

## Side-effect contract

| 子命令 | 可写 `.long-loop/` | 可执行任务 | 说明 |
|---|---:|---:|---|
| `help` | no | no | 终止命令，只显示帮助 |
| `status` | no | no | 只读状态 |
| `tail` / `watch` | no | no | 只读日志和状态 |
| `plan` / `init` | yes | no | 生成 `.long-loop/<日期>_主题/` 计划、打印 review bundle，同时维护 `.gitignore` |
| `approve` | yes | no | 显式批准计划 |
| `run` / `resume` | yes | yes | 执行 bounded iterations；对初始 `awaiting_approval` 计划，`run` 同时批准 |
| `pause` / `stop` | yes | no | 人工干预或停止 |

## 生成文件

```text
.long-loop/
├── current
└── YYYY-MM-DD_topic/
    ├── PROMPT.md
    ├── SPEC.md
    ├── specs/
    │   └── main.md
    ├── IMPLEMENTATION_PLAN.md
    ├── fix_plan.md
    ├── ASSERT.md
    ├── validator.md
    ├── validator-results.json
    ├── events.jsonl
    ├── progress.md
    ├── logs/
    └── state.json
```

## Fresh Iteration

每轮重新开始，只加载最小必要上下文：

- `PROMPT.md`
- `specs/main.md`
- 当前 `fix_plan.md` 最高优先级 item
- `validator.md`
- 最近一条阶段总结

不得把上一轮完整 stdout / stderr 或长对话历史塞回本轮 prompt；旧输出只允许以结构化摘要进入 `progress.md` / `events.jsonl` / append-only log。

## Validator contract

1. 每轮先读取 `validator.md` 的 item validator。
2. validator 缺失时停止，不进入实现。
3. 实现后重跑 item validator，失败就在本轮修。
4. item validator 通过后，再跑 full guard。
5. validator 结果写入 `validator-results.json` 和 `events.jsonl`。

## Structured append log

append log 只记录关键事件，标题格式固定为：

```text
YYYY-MM-DDTHH:MM:SSZ | iteration-N | event-type | item summary
```

避免记录全量工具输出、重复 todo dump 或可从 `state.json` / `fix_plan.md` 推导出的状态。

## 状态转移图

先看 `help`，再按当前状态执行下一步：

```text
plan -> awaiting_approval -> run -> approved -> running
plan -> awaiting_approval -> approve -> approved -> run -> running
running -> stopped     [max iterations, max minutes, validation failure]
running -> done        [no remaining todo]
running -> pause -> paused -> edit plan -> approve -> approved
stopped -> approve -> approved -> resume -> running
```

## 规则

1. 先 `plan`，review 屏幕输出；如果没问题可直接 `run`，`run` 会批准初始计划并执行；`approve` 只用于先解锁不执行。
2. 一轮只做一个 `fix_plan.md` item。
3. 每轮后必须跑 item validator 和 full guard。
4. 每轮结束给出阶段总结：本轮动作、验证结果、状态变化、下一步。
5. `PROMPT.md` / `ASSERT.md` 只放规则，不放状态报告。
6. 默认不 push。
7. 触碰远端、部署、数据库、secrets 前必须停下，转 `/guard-gitops`。

## Stop 条件

- 计划完成
- 达到轮数 / 时间预算
- 验证失败
- diff scan 命中
- pause / 人工干预
- 需要用户判断
- 工作树出现不明冲突

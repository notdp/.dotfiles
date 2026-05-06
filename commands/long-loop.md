---
description: 规划、批准、运行、观察和停止长任务 long-loop 工作流；基于 .long-loop/ 文件系统状态、预算和验证链路。
argument-hint: <help|plan|approve|run|status|tail|watch|pause|stop|resume> [目标或参数]
---

# Long Loop

长任务工作流入口。它不是无限循环器，而是有边界、有验收、有预算、有停止条件的执行 harness。

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
| `init "goal"` | `python3 "$LONG_LOOP_SCRIPT" init --goal "goal"`（兼容入口，同样需要 approve） |
| `approve` | `python3 "$LONG_LOOP_SCRIPT" approve` |
| `status` | `python3 "$LONG_LOOP_SCRIPT" status` |
| `tail ...` | `python3 "$LONG_LOOP_SCRIPT" tail ...` |
| `watch ...` | `python3 "$LONG_LOOP_SCRIPT" watch ...` |
| `run ...` | `python3 "$LONG_LOOP_SCRIPT" run ...` |
| `resume ...` | `python3 "$LONG_LOOP_SCRIPT" run ...` |
| `pause --reason "..."` | `python3 "$LONG_LOOP_SCRIPT" pause --reason "..."` |
| `stop --reason "..."` | `python3 "$LONG_LOOP_SCRIPT" stop --reason "..."` |

## 生成文件

```text
.long-loop/
├── PROMPT.md
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── ASSERT.md
├── progress.md
├── logs/
└── state.json
```

## 状态转移图

先看 `help`，再按当前状态执行下一步：

```text
plan -> awaiting_approval -> approve -> approved -> run -> running
running -> stopped     [max iterations, max minutes, validation failure]
running -> done        [no remaining todo]
running -> pause -> paused -> edit plan -> approve -> approved
stopped -> approve -> approved -> resume -> running
```

## 规则

1. 先 `plan`，再 `approve`，最后才能 `run`。
2. 一轮只做一个 `IMPLEMENTATION_PLAN.md` item。
3. 每轮后必须跑验证。
4. `PROMPT.md` / `ASSERT.md` 只放规则，不放状态报告。
5. 默认不 push。
6. 触碰远端、部署、数据库、secrets 前必须停下，转 `/guard-gitops`。

## Stop 条件

- 计划完成
- 达到轮数 / 时间预算
- 验证失败
- diff scan 命中
- pause / 人工干预
- 需要用户判断
- 工作树出现不明冲突

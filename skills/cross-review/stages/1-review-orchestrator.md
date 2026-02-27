# 阶段 1: 并行 PR 审查 - Orchestrator

## 前置条件

- 调用方已执行 `cr-init.sh` 初始化 workspace
- 调用方已执行 `cr-spawn.sh orchestrator` 启动你（你在 tmux pane 0 中运行）
- `$CR_WORKSPACE` 环境变量已设置

## 禁止操作

- 不要执行 `cr-init.sh`（调用方已完成）
- 不要执行 `cr-spawn.sh orchestrator`（你就是 orchestrator）

## 概述

启动 Claude 和 GPT 并行审查 PR。

## 执行

```bash
echo "1" > "$CR_WORKSPACE/state/stage"

MODEL_CLAUDE="${CR_MODEL_CLAUDE:-custom:claude-opus-4-6}"
MODEL_GPT="${CR_MODEL_GPT:-custom:gpt-5.3-codex}"

# 启动两个 Agent（仅 claude 和 gpt，不要 spawn orchestrator）
$HOME/.factory/skills/cross-review/scripts/cr-spawn.sh claude "$MODEL_CLAUDE"
$HOME/.factory/skills/cross-review/scripts/cr-spawn.sh gpt "$MODEL_GPT"
```

## 发送任务

为每个 Agent 写入任务文件，包含必要上下文：

```bash
REPO=$(cat "$CR_WORKSPACE/state/repo")
PR_NUMBER=$(cat "$CR_WORKSPACE/state/pr-number")
BASE=$(cat "$CR_WORKSPACE/state/base")
BRANCH=$(cat "$CR_WORKSPACE/state/branch")

for AGENT in claude gpt; do
  cat > "$CR_WORKSPACE/tasks/${AGENT}-review.md" << EOF
<system-instruction>
你是 ${AGENT}，cross-review 审查者。
⛔ FIRST STEP: load skill: cross-review
</system-instruction>

# PR Review Task

You are reviewing PR #$PR_NUMBER in $REPO ($BRANCH → $BASE).

## Instructions

Read ~/.factory/skills/cross-review/stages/1-review-agent.md for detailed review guidelines.

## Context

- Repository: $REPO
- PR: #$PR_NUMBER
- Branch: $BRANCH → $BASE
- Workspace: $CR_WORKSPACE
- Your agent name: $AGENT

## Required Output

1. Write review findings to: $CR_WORKSPACE/results/${AGENT}-r1.md
2. When FULLY complete, run: touch $CR_WORKSPACE/results/${AGENT}-r1.done
EOF

  # Read pane target and send to agent (-l and Enter must be separate calls)
  PANE=$(cat "$CR_WORKSPACE/state/pane-${AGENT}")
  tmux send-keys -t "$PANE" -l "Read and execute $CR_WORKSPACE/tasks/${AGENT}-review.md"
  tmux send-keys -t "$PANE" Enter
done
```

## 等待

```bash
$HOME/.factory/skills/cross-review/scripts/cr-wait.sh claude r1 600 &
$HOME/.factory/skills/cross-review/scripts/cr-wait.sh gpt r1 600 &
wait
```

两个 Agent 都完成后，读取结果并进入阶段 2。

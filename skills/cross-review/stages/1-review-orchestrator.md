# 阶段 1: 并行 PR 审查 - Orchestrator

## 前置条件

- 调用方已通过 `mission create --workspace ... --state ...` 初始化 workspace
- `$CR_WORKSPACE` 和 `$CR_TEAM` 环境变量已设置
- mission team 已创建（`mission create "$CR_TEAM" ...`）

## 禁止操作

- 不要重新执行 `mission create`（调用方已完成）
- 不要直接操作 tmux

## 概述

启动 Claude 和 GPT 并行审查 PR。

## 执行

```bash
echo "1" > "$CR_WORKSPACE/state/stage"

# 检测 orchestrator 自身的 session ID（必须在 spawn 前执行，此时最新 session 就是自己）
ORCH_SESSION=$(python3 -c "
import os, pathlib
cwd = os.getcwd()
d = pathlib.Path.home() / '.factory' / 'sessions' / ('-' + cwd.lstrip('/').replace('/', '-'))
f = max(d.glob('*.settings.json'), key=lambda p: p.stat().st_birthtime)
print(f.name.removesuffix('.settings.json'))
")
echo "$ORCH_SESSION" > "$CR_WORKSPACE/state/orch-session"

MODEL_CLAUDE="${CR_MODEL_CLAUDE:-custom:claude-opus-4-6}"
MODEL_GPT="${CR_MODEL_GPT:-custom:gpt-5.3-codex}"

# 启动两个 Agent
mission spawn claude -t "$CR_TEAM" -m "$MODEL_CLAUDE" --skill cross-review -e "CR_WORKSPACE=$CR_WORKSPACE"
mission spawn gpt -t "$CR_TEAM" -m "$MODEL_GPT" --skill cross-review -e "CR_WORKSPACE=$CR_WORKSPACE"
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

  mission type "$AGENT" "Read and execute $CR_WORKSPACE/tasks/${AGENT}-review.md" -t "$CR_TEAM"
done
```

## 等待

```bash
mission wait claude r1 -t "$CR_TEAM" --workspace "$CR_WORKSPACE" --timeout 600 &
mission wait gpt r1 -t "$CR_TEAM" --workspace "$CR_WORKSPACE" --timeout 600 &
wait
```

两个 Agent 都完成后，读取结果并进入阶段 2。

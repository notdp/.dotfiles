# 阶段 4: 修复验证 - Orchestrator

## 禁止操作

- 不要执行 `cr-spawn.sh orchestrator`

## 概述

协调 Claude 修复和 GPT 验证，最多 5 轮。

```
Claude 修复 → 推送 → GPT 验证 → 通过/失败 → (失败则重复)
```

## 执行

```bash
echo "4" > "$CR_WORKSPACE/state/stage"
echo "1" > "$CR_WORKSPACE/state/s4-round"
```

### 通知 Claude 修复

```bash
REPO=$(cat "$CR_WORKSPACE/state/repo")
PR_NUMBER=$(cat "$CR_WORKSPACE/state/pr-number")
BASE=$(cat "$CR_WORKSPACE/state/base")
BRANCH=$(cat "$CR_WORKSPACE/state/branch")

# 收集需修复的问题 (来自阶段 2 的 same_issues 或阶段 3 的交叉确认结果)
FIX_ISSUES=$(cat "$CR_WORKSPACE/results/crosscheck-summary.md" 2>/dev/null || \
             cat "$CR_WORKSPACE/results/claude-r1.md")

cat > "$CR_WORKSPACE/tasks/claude-fix.md" << 'TASK'
<system-instruction>
你是 claude，cross-review 修复者。
</system-instruction>

# Fix Task

Read ~/.factory/skills/cross-review/stages/4-fix-agent.md for guidelines.

## Issues to Fix
TASK

# Append issues (agent output — must NOT go through heredoc expansion)
printf '%s\n' "$FIX_ISSUES" >> "$CR_WORKSPACE/tasks/claude-fix.md"

cat >> "$CR_WORKSPACE/tasks/claude-fix.md" << TASK_FOOTER

## Context
- Repo: $REPO
- PR: #$PR_NUMBER ($BRANCH → $BASE)
- Workspace: $CR_WORKSPACE
- Your agent name: claude

## Required Output
1. Create fix branch, make changes, commit, push
2. Write fix summary to: $CR_WORKSPACE/results/claude-fix.md
3. When done: touch $CR_WORKSPACE/results/claude-fix.done
TASK_FOOTER

PANE_CLAUDE=$(cat "$CR_WORKSPACE/state/pane-claude")
tmux send-keys -t "$PANE_CLAUDE" -l "Read and execute $CR_WORKSPACE/tasks/claude-fix.md"
tmux send-keys -t "$PANE_CLAUDE" Enter
```

### 等待修复 → 通知 GPT 验证

```bash
$HOME/.factory/skills/cross-review/scripts/cr-wait.sh claude fix 600

FIX_RESULT=$(cat "$CR_WORKSPACE/results/claude-fix.md")
FIX_BRANCH=$(cat "$CR_WORKSPACE/state/s4-branch")

cat > "$CR_WORKSPACE/tasks/gpt-verify.md" << 'TASK'
<system-instruction>
你是 gpt，cross-review 验证者。
</system-instruction>

# Verify Task

Read ~/.factory/skills/cross-review/stages/4-verify-agent.md for guidelines.

## Fix Details
TASK

# Append fix result (agent output — must NOT go through heredoc expansion)
printf '%s\n' "$FIX_RESULT" >> "$CR_WORKSPACE/tasks/gpt-verify.md"

cat >> "$CR_WORKSPACE/tasks/gpt-verify.md" << TASK_FOOTER

## Context
- Fix branch: $FIX_BRANCH
- Base: $BASE
- Workspace: $CR_WORKSPACE
- Your agent name: gpt

## Required Output
1. Review the fix diff
2. Write result to: $CR_WORKSPACE/results/gpt-verify.md
3. When done: touch $CR_WORKSPACE/results/gpt-verify.done
TASK_FOOTER

PANE_GPT=$(cat "$CR_WORKSPACE/state/pane-gpt")
tmux send-keys -t "$PANE_GPT" -l "Read and execute $CR_WORKSPACE/tasks/gpt-verify.md"
tmux send-keys -t "$PANE_GPT" Enter
```

### 处理验证结果

```bash
$HOME/.factory/skills/cross-review/scripts/cr-wait.sh gpt verify 300
```

- 通过 → 阶段 5
- 失败 + 轮数 < 5 → 增加轮数，重新修复
- 失败 + 轮数 >= 5 → 阶段 5（标记修复未完成）

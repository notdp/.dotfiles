# 阶段 3: 交叉确认 - Orchestrator

## 禁止操作

- 不要执行 `cr-spawn.sh orchestrator`

## 概述

让 Claude 和 GPT 讨论分歧，Orchestrator 做消息中继。

```
Claude tmux ←── Orchestrator (中继) ──→ GPT tmux
```

Orchestrator 读 Claude 的回复，转发给 GPT；读 GPT 的回复，转发给 Claude。最多 5 轮。

## 执行

```bash
echo "3" > "$CR_WORKSPACE/state/stage"
```

### 准备上下文

```bash
CLAUDE_RESULT=$(cat "$CR_WORKSPACE/results/claude-r1.md")
GPT_RESULT=$(cat "$CR_WORKSPACE/results/gpt-r1.md")
```

### 轮次循环 (最多 5 轮)

```bash
MAX_ROUNDS=5

for ROUND in $(seq 1 $MAX_ROUNDS); do
  echo "--- Round $ROUND ---"

  # === Claude 分析 ===
  if [[ $ROUND -eq 1 ]]; then
    CONTEXT="## Your Review (Claude)\n$(cat "$CR_WORKSPACE/results/claude-r1.md")\n\n## Other Review (GPT)\n$(cat "$CR_WORKSPACE/results/gpt-r1.md")"
  else
    PREV=$((ROUND - 1))
    CONTEXT="## GPT's Response (Round $PREV)\n$(cat "$CR_WORKSPACE/results/gpt-crosscheck-round${PREV}.md")"
  fi

  # Write task header (quoted heredoc — no shell expansion)
  cat > "$CR_WORKSPACE/tasks/claude-crosscheck-round${ROUND}.md" << 'TASK'
<system-instruction>
你是 claude，cross-review 审查者。
</system-instruction>

# Cross-Check Task

Read ~/.factory/skills/cross-review/stages/3-crosscheck-agent.md for guidelines.

TASK

  # Append context (agent output — must NOT go through heredoc expansion)
  printf '%s\n' "$CONTEXT" >> "$CR_WORKSPACE/tasks/claude-crosscheck-round${ROUND}.md"

  cat >> "$CR_WORKSPACE/tasks/claude-crosscheck-round${ROUND}.md" << TASK_FOOTER

## Instructions
Analyze and respond. For each issue, decide: 🔧 Fix or ⏭️ Skip.
Write to: $CR_WORKSPACE/results/claude-crosscheck-round${ROUND}.md
When done: touch $CR_WORKSPACE/results/claude-crosscheck-round${ROUND}.done
TASK_FOOTER

  PANE_CLAUDE=$(cat "$CR_WORKSPACE/state/pane-claude")
  tmux -S "$CR_SOCKET" send-keys -t "$PANE_CLAUDE" -l "Read and execute $CR_WORKSPACE/tasks/claude-crosscheck-round${ROUND}.md"
  tmux -S "$CR_SOCKET" send-keys -t "$PANE_CLAUDE" Enter

  $HOME/.factory/skills/cross-review/scripts/cr-wait.sh claude "crosscheck-round${ROUND}" 300

  # === GPT 回应 ===
  CLAUDE_RESPONSE=$(cat "$CR_WORKSPACE/results/claude-crosscheck-round${ROUND}.md")

  # Write task header (quoted heredoc — no shell expansion)
  cat > "$CR_WORKSPACE/tasks/gpt-crosscheck-round${ROUND}.md" << 'TASK'
<system-instruction>
你是 gpt，cross-review 审查者。
</system-instruction>

# Cross-Check Response

Read ~/.factory/skills/cross-review/stages/3-crosscheck-agent.md for guidelines.

Claude's analysis:
TASK

  # Append Claude's response (agent output — must NOT go through heredoc expansion)
  printf '%s\n' "$CLAUDE_RESPONSE" >> "$CR_WORKSPACE/tasks/gpt-crosscheck-round${ROUND}.md"

  cat >> "$CR_WORKSPACE/tasks/gpt-crosscheck-round${ROUND}.md" << TASK_FOOTER

Provide your counter-analysis. For each issue: 🔧 Fix or ⏭️ Skip.
Write to: $CR_WORKSPACE/results/gpt-crosscheck-round${ROUND}.md
When done: touch $CR_WORKSPACE/results/gpt-crosscheck-round${ROUND}.done
TASK_FOOTER

  PANE_GPT=$(cat "$CR_WORKSPACE/state/pane-gpt")
  tmux -S "$CR_SOCKET" send-keys -t "$PANE_GPT" -l "Read and execute $CR_WORKSPACE/tasks/gpt-crosscheck-round${ROUND}.md"
  tmux -S "$CR_SOCKET" send-keys -t "$PANE_GPT" Enter

  $HOME/.factory/skills/cross-review/scripts/cr-wait.sh gpt "crosscheck-round${ROUND}" 300

  # === Orchestrator 判断是否达成共识 ===
  # 读取双方本轮结果，分析是否所有问题都有一致判断
  CLAUDE_ROUND=$(cat "$CR_WORKSPACE/results/claude-crosscheck-round${ROUND}.md")
  GPT_ROUND=$(cat "$CR_WORKSPACE/results/gpt-crosscheck-round${ROUND}.md")

  # Orchestrator 在此分析 CLAUDE_ROUND 和 GPT_ROUND
  # 如果所有问题已达成共识 (全部 Fix 或 Skip 一致)，break
  # 否则继续下一轮
done
```

## 判断共识

读取最后一轮双方结果，对每个问题整理最终状态：

| 问题 | 状态 | 说明 |
|------|------|------|
| ... | 🔧 Fix | 双方同意修复 |
| ... | ⏭️ Skip | 双方同意跳过 |
| ... | ⚠️ Deadlock | 5 轮未达成一致，需人工审查 |

## 结果处理

```bash
# 写入最终交叉确认结果
cat > "$CR_WORKSPACE/results/crosscheck-summary.md" << 'SUMMARY'
| Issue | Status | Detail |
|-------|--------|--------|
| ... | 🔧 Fix / ⏭️ Skip / ⚠️ Deadlock | ... |
SUMMARY
```

- 有 Fix 问题 → 阶段 4
- 全部 Skip → 阶段 5
- 有 Deadlock → 阶段 5（标记需人工审查）

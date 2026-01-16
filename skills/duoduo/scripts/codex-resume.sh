#!/bin/bash
# 恢复 Codex 会话继续任务
# 用法: codex-resume.sh <SESSION_ID> <PROMPT>

SESSION_ID=$1
PROMPT=$2

droid exec -s "$SESSION_ID" -m gpt-5.1-codex-max --auto high --output-format json "$PROMPT"

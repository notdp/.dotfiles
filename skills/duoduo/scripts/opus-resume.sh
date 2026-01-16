#!/bin/bash
# 恢复 Opus 会话继续任务
# 用法: opus-resume.sh <SESSION_ID> <PROMPT>

SESSION_ID=$1
PROMPT=$2

droid exec -s "$SESSION_ID" -m claude-opus-4-5-20251101 --auto high --output-format json "$PROMPT"

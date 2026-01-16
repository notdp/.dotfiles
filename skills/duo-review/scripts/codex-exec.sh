#!/bin/bash
# 调用 Codex (GPT-5.1 Codex Max) 执行任务
# 用法: codex-exec.sh <PR_NUMBER> <PROMPT>
# 完成后自动写入 Redis: s1:codex:status, s1:codex:session, s1:codex:conclusion

PR_NUMBER=$1
PROMPT=$2
S=$(dirname "$0")

# 构建带身份的 prompt
FULL_PROMPT="<system-instruction>
你是 Codex (GPT-5.1 Codex Max)，duo-review 流程中的审查者。
首先 load skill: duo-review
</system-instruction>

$PROMPT"

# 执行 Codex
OUTPUT=$(droid exec -m gpt-5.1-codex-max -r high --auto high --output-format json "$FULL_PROMPT")

# 解析结果
SESSION_ID=$(echo "$OUTPUT" | jq -r '.session_id // empty')
IS_ERROR=$(echo "$OUTPUT" | jq -r '.is_error // false')
RESULT=$(echo "$OUTPUT" | jq -r '.result // empty')

# 判断结论（从 result 文本中提取）
if [ "$IS_ERROR" = "true" ]; then
  CONCLUSION="error"
elif echo "$RESULT" | grep -qiE '(p0|critical|严重)'; then
  CONCLUSION="p0"
elif echo "$RESULT" | grep -qiE '(p1|major|重大)'; then
  CONCLUSION="p1"
elif echo "$RESULT" | grep -qiE '(p2|minor|次要)'; then
  CONCLUSION="p2"
elif echo "$RESULT" | grep -qiE '(p3|trivial|建议)'; then
  CONCLUSION="p3"
else
  CONCLUSION="ok"
fi

# 写入 Redis
$S/duo-set.sh "$PR_NUMBER" s1:codex:status done
$S/duo-set.sh "$PR_NUMBER" s1:codex:session "$SESSION_ID"
$S/duo-set.sh "$PR_NUMBER" s1:codex:conclusion "$CONCLUSION"

echo "Codex done: session=$SESSION_ID, conclusion=$CONCLUSION"

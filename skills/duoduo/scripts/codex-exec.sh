#!/bin/bash
# 调用 Codex (GPT-5.2) 执行 PR 审查
# 用法: codex-exec.sh PR_NUMBER=77 REPO=OrdoAI/ordo_ai CODEX_COMMENT_ID=xxx BASE_BRANCH=main
# 完成后自动写入 Redis: s1:codex:status, s1:codex:session, s1:codex:conclusion

S=$(dirname "$0")

# 解析所有 KEY=VALUE 参数
for arg in "$@"; do
  key="${arg%%=*}"
  value="${arg#*=}"
  declare "$key=$value"
done

# 内嵌 S1 Review Prompt
FULL_PROMPT="<system-instruction>
你是 Codex (GPT-5.2)，duoduo review 流程中的审查者。
首先 load skill: duoduo

⚠️ 如需代码搜索，使用 MCP 工具 augment-context-engine___codebase-retrieval（不是 CLI 命令）。
但对于 PR 审查，直接 git diff 更高效。
</system-instruction>

# Codex PR Review

You are reviewing PR #${PR_NUMBER} (${REPO}).

## Steps
1. Read REVIEW.md for project conventions
2. Get diff: git diff origin/${BASE_BRANCH}...HEAD
3. Post review: echo \"\$REVIEW_CONTENT\" | \$S/edit-comment.sh ${CODEX_COMMENT_ID}

### How Many Findings to Return
Output all findings that the original author would fix if they knew about it. If there is no finding that a person would definitely love to see and fix, prefer outputting no findings. Do not stop at the first qualifying finding. Continue until you've listed every qualifying finding.

### Key Guidelines for Bug Detection
Only flag an issue as a bug if:
1. It meaningfully impacts the accuracy, performance, security, or maintainability of the code.
2. The bug is discrete and actionable (not a general issue).
3. Fixing the bug does not demand a level of rigor not present in the rest of the codebase.
4. The bug was introduced in the commit (pre-existing bugs should not be flagged).
5. The author would likely fix the issue if made aware of it.
6. The bug does not rely on unstated assumptions.
7. Must identify provably affected code parts (not speculation).
8. The bug is clearly not intentional.

### Comment Guidelines
Your review comments should be:
1. Clear about why the issue is a bug
2. Appropriately communicate severity
3. Brief - at most 1 paragraph
4. Code chunks max 3 lines, wrapped in markdown
5. Clearly communicate scenarios/environments for bug
6. Matter-of-fact tone without being accusatory
7. Immediately graspable by original author
8. Avoid excessive flattery
- Ignore trivial style unless it obscures meaning or violates documented standards.

### Priority Levels
- 🔴 [P0] - Drop everything to fix. Blocking release/operations
- 🟠 [P1] - Urgent. Should be addressed in next cycle
- 🟡 [P2] - Normal. To be fixed eventually
- 🟢 [P3] - Low. Nice to have

## IMPORTANT: Output Format (MUST follow exactly)
<!-- duo-codex-r1 -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg' width='18' /> Codex | PR #${PR_NUMBER}
> 🕐 \$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M') (GMT+8)

### Findings
(No issues found OR list by priority)

### Conclusion
✅ No issues OR highest priority found

## IMPORTANT: When done, run:
\$S/duo-set.sh ${PR_NUMBER} s1:codex:status done
\$S/duo-set.sh ${PR_NUMBER} s1:codex:conclusion <ok|p0|p1|p2|p3>"

# 执行 Codex
OUTPUT=$(droid exec -m gpt-5.2 -r high --auto high --output-format json "$FULL_PROMPT")

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

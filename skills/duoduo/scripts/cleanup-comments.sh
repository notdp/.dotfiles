#!/bin/bash
# 清理所有 duo 评论（包括 progress）
# 用法: cleanup-comments.sh <PR_NUMBER> <REPO>

PR_NUMBER=$1
REPO=$2

if [ -n "$GH_TOKEN" ]; then
  export GH_TOKEN
fi

# 禁用 pager
export GH_PAGER=""

echo "清理 PR #$PR_NUMBER 的所有 duo 评论..."

# 获取所有 duo 评论 ID（匹配 duo- 或 duoduo-）
IDS=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json comments -q '
  .comments[] | select(.body | test("<!-- duo")) | .id
')

if [ -z "$IDS" ]; then
  echo "没有需要清理的评论"
  exit 0
fi

# 并行删除
echo "$IDS" | xargs -P 4 -I {} sh -c 'echo "删除: {}"; gh api graphql -f query="mutation { deleteIssueComment(input: {id: \"{}\"}) { clientMutationId } }" >/dev/null 2>&1'

echo "清理完成"

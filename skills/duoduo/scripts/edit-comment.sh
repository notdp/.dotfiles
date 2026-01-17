#!/bin/bash
# 编辑评论
# 用法: echo "$CONTENT" | edit-comment.sh <COMMENT_NODE_ID>
#   或: edit-comment.sh <COMMENT_NODE_ID> <CONTENT>

COMMENT_ID=$1
NEW_BODY=$2

# 如果没有第二个参数，从 stdin 读取
if [ -z "$NEW_BODY" ]; then
  NEW_BODY=$(cat)
fi

if [ -z "$COMMENT_ID" ] || [ -z "$NEW_BODY" ]; then
  echo "用法: echo \"\$CONTENT\" | edit-comment.sh <COMMENT_NODE_ID>"
  exit 1
fi

if [ -n "$GH_TOKEN" ]; then
  export GH_TOKEN
fi

gh api graphql -f query="mutation { updateIssueComment(input: {id: \"$COMMENT_ID\", body: $(echo "$NEW_BODY" | jq -Rs .)}) { issueComment { id } } }"

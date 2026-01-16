#!/bin/bash
# 编辑评论（从 stdin 读取内容）
# 用法: echo "内容" | edit-comment.sh <COMMENT_ID>

COMMENT_ID=$1
NEW_BODY=$(cat)

if [ -z "$COMMENT_ID" ] || [ -z "$NEW_BODY" ]; then
  echo "用法: echo \"内容\" | edit-comment.sh <COMMENT_ID>"
  exit 1
fi

if [ -n "$GH_TOKEN" ]; then
  export GH_TOKEN
fi

gh api graphql -f query="mutation { updateIssueComment(input: {id: \"$COMMENT_ID\", body: $(echo "$NEW_BODY" | jq -Rs .)}) { issueComment { id } } }"

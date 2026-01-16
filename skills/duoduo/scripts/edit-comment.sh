#!/bin/bash
# 编辑评论
# 用法: edit-comment.sh <COMMENT_NODE_ID> <CONTENT>

COMMENT_ID=$1
NEW_BODY=$2

if [ -z "$COMMENT_ID" ] || [ -z "$NEW_BODY" ]; then
  echo "用法: edit-comment.sh <COMMENT_NODE_ID> <CONTENT>"
  exit 1
fi

if [ -n "$GH_TOKEN" ]; then
  export GH_TOKEN
fi

gh api graphql -f query="mutation { updateIssueComment(input: {id: \"$COMMENT_ID\", body: $(echo "$NEW_BODY" | jq -Rs .)}) { issueComment { id } } }"

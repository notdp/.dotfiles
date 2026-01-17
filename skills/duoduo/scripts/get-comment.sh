#!/bin/bash
# get-comment.sh <pr_number> <repo> <marker>
# 获取包含指定 marker 的评论内容
# marker 例如: duo-opus-r1, duo-codex-r1

PR=$1
REPO=$2
MARKER=$3

if [ -n "$GH_TOKEN" ]; then
  export GH_TOKEN
fi

# 查找包含 marker 的评论并返回内容
gh pr view "$PR" --repo "$REPO" --json comments -q "
  .comments[] | select(.body | contains(\"<!-- $MARKER -->\")) | .body
"

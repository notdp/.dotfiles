#!/bin/bash
# 发布评论并返回评论 ID
# 用法: post-comment.sh <PR_NUMBER> <REPO> <BODY>
#
# 图标（用于评论格式）:
# - Codex: <img src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg" />
# - Opus: <img src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg" />

PR_NUMBER=$1
REPO=$2
BODY=$3

# 使用 GH_TOKEN 环境变量（GitHub Actions 中为 bot 身份）
# 如果没设置，使用本地 gh auth 的身份
if [ -n "$GH_TOKEN" ]; then
  export GH_TOKEN
fi

# 发布评论（URL 输出到 stderr）
URL=$(gh pr comment "$PR_NUMBER" --repo "$REPO" --body "$BODY")
echo "$URL" >&2

# 获取刚发布的评论 node_id（最新一条评论）
NODE_ID=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json comments -q '.comments[-1].id')

# 只输出 node_id 到 stdout
echo "$NODE_ID"

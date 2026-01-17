#!/bin/bash
# 初始化 Redis 状态
# 用法: duo-init.sh <PR_NUMBER> <REPO> <PR_BRANCH> <BASE_BRANCH> [RUNNER]
# RUNNER: local（本地运行）或 GitHub Actions runner 名称

PR=$1
REPO=$2
BRANCH=$3
BASE=$4
RUNNER=${5:-local}

KEY="duo:$PR"

# 不 DEL，只 HSET（保留已存储的 session 信息）
redis-cli HSET "$KEY" \
  repo "$REPO" \
  pr "$PR" \
  branch "$BRANCH" \
  base "$BASE" \
  runner "$RUNNER" \
  stage 1 \
  started_at "$(date +%s)" \
  > /dev/null

redis-cli EXPIRE "$KEY" 7200  # 2小时过期

echo "$KEY"

#!/bin/bash
# 初始化 Redis 状态
# 用法: duo-init.sh <PR_NUMBER> <REPO> <PR_BRANCH> <BASE_BRANCH>

PR=$1
REPO=$2
BRANCH=$3
BASE=$4
KEY="duo:$PR"

redis-cli DEL "$KEY" > /dev/null
redis-cli HSET "$KEY" \
  repo "$REPO" \
  pr "$PR" \
  branch "$BRANCH" \
  base "$BASE" \
  stage 1 \
  started_at "$(date +%s)" \
  s1:codex:status pending \
  s1:opus:status pending \
  > /dev/null

redis-cli EXPIRE "$KEY" 7200  # 2小时过期

echo "$KEY"

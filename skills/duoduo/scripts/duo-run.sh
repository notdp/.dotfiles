#!/bin/bash
# duo-run.sh - 启动 duoduo review 流程
# 用法: duo-run.sh [repo] [pr_number]
# 环境变量: RUNNER (默认 local), PR_BRANCH, BASE_BRANCH (Actions 模式传入)

set -e

S=~/.dotfiles/skills/duoduo/scripts
export RUNNER=${RUNNER:-local}

# local/droid 模式：从 gh 获取 PR 信息
# Actions 模式：从参数和环境变量读取
if [ "$RUNNER" = "local" ] || [ "$RUNNER" = "droid" ]; then
  PR_INFO=$(gh pr view ${1:-} --json number,baseRefName,headRefName,headRepositoryOwner,headRepository 2>/dev/null || echo "")
  if [ -z "$PR_INFO" ]; then
    echo "Error: 无法获取 PR 信息，请在 PR 分支上运行或指定 PR 号"
    exit 1
  fi
  export PR_NUMBER=$(echo "$PR_INFO" | jq -r .number)
  export BASE_BRANCH=$(echo "$PR_INFO" | jq -r .baseRefName)
  export PR_BRANCH=$(echo "$PR_INFO" | jq -r .headRefName)
  export REPO=$(echo "$PR_INFO" | jq -r '.headRepositoryOwner.login + "/" + .headRepository.name')
else
  # Actions 模式：从参数读取 (pr_number, repo, base_branch)，PR_BRANCH 从环境变量读取
  export PR_NUMBER=$1
  export REPO=$2
  export BASE_BRANCH=$3
  # PR_BRANCH 已由 workflow env 设置
fi

echo "🚀 Duo Review"
echo "   PR: #$PR_NUMBER ($PR_BRANCH → $BASE_BRANCH)"
echo "   Repo: $REPO"
echo "   Runner: $RUNNER"
echo ""

# 清理旧进程和评论
pkill -f "session-start.py.*$PR_NUMBER" 2>/dev/null || true
rm -f /tmp/duo-$PR_NUMBER-* 2>/dev/null || true
redis-cli DEL duo:$PR_NUMBER >/dev/null 2>&1 || true
$S/cleanup-comments.sh $PR_NUMBER $REPO >/dev/null 2>&1 || true

# 启动 Orchestrator
$S/orchestrator-start.py $PR_NUMBER $REPO $PR_BRANCH $BASE_BRANCH $RUNNER

SESSION_ID=$(redis-cli HGET duo:$PR_NUMBER orchestrator:session)
echo "   Orchestrator: droid --resume $SESSION_ID"
echo "   Log: tail -f /tmp/duo-$PR_NUMBER-orchestrator.log"
echo ""

# 进度轮询
trap 'echo ""; echo "⚠️  已退出监控，Orchestrator 仍在后台运行"; exit 0' INT

LAST_STAGE=""
STAGE_NAMES=([1]="并行审查" [2]="判断共识" [3]="交叉确认" [4]="修复验证" [5]="汇总")

while true; do
    STAGE=$($S/duo-get.sh $PR_NUMBER stage 2>/dev/null || echo "1")
    
    if [ "$STAGE" != "$LAST_STAGE" ]; then
        if [ "$STAGE" = "done" ]; then
            RESULT=$($S/duo-get.sh $PR_NUMBER s2:result 2>/dev/null || echo "")
            echo "✅ 完成: $RESULT"
            echo ""
            echo "   查看详情: https://github.com/$REPO/pull/$PR_NUMBER"
            echo ""
            echo "📋 Status"
            redis-cli HGETALL "duo:$PR_NUMBER" | awk 'NR%2==1 {key=$0} NR%2==0 {printf "   %-25s %s\n", key, $0}'
            break
        else
            echo "⏳ 阶段 $STAGE: ${STAGE_NAMES[$STAGE]}中..."
        fi
        LAST_STAGE="$STAGE"
    fi
    sleep 2
done

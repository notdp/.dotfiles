#!/usr/bin/env bash
# preflight.sh — guard-ship 的交付前预检
# 用法：bash scripts/preflight.sh
# 检查：分支状态、git status、敏感信息扫描、远端同步、commits to push
# 输出：Markdown 表格；exit 0=全绿，1=有警告/失败，2=严重阻断（敏感信息）

set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: not a git repository"
  exit 2
}

BRANCH=$(git rev-parse --abbrev-ref HEAD)
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

RESULTS=()
SEVERE_FAIL=0
SOFT_FAIL=0

push_result() {
  # name | status | detail
  RESULTS+=("$1|$2|$3")
}

# 1. 分支状态
if [[ "$BRANCH" == "$DEFAULT_BRANCH" ]]; then
  push_result "branch" "info" "on default branch ($BRANCH)"
else
  push_result "branch" "info" "on feature branch $BRANCH (default: $DEFAULT_BRANCH)"
fi

# 2. 工作树干净度
STATUS_LINES=$(git status --porcelain)
if [[ -z "$STATUS_LINES" ]]; then
  push_result "working tree" "pass" "clean"
else
  COUNT=$(echo "$STATUS_LINES" | wc -l | tr -d ' ')
  push_result "working tree" "warn" "$COUNT uncommitted file(s); run git status"
  SOFT_FAIL=1
fi

# 3. 敏感信息扫描（暂存区 + 工作树 diff HEAD）
SENSITIVE=$(git diff HEAD 2>/dev/null | grep -E -i "^\+.*(api[_-]?key|secret|token|password)[[:space:]]*[=:][[:space:]]*[\"'][^[:space:]\"']{6,}" || true)
PRIVKEY=$(git diff HEAD 2>/dev/null | grep -E '^\+.*-----BEGIN (RSA |EC )?PRIVATE KEY-----' || true)
if [[ -n "$SENSITIVE" || -n "$PRIVKEY" ]]; then
  push_result "sensitive scan" "FAIL" "possible secret in diff — review before ship"
  SEVERE_FAIL=1
else
  push_result "sensitive scan" "pass" "no hardcoded secrets detected"
fi

# 4. 远端同步状态
if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
  AHEAD=$(git rev-list --count "origin/$BRANCH..HEAD")
  BEHIND=$(git rev-list --count "HEAD..origin/$BRANCH")
  if [[ "$AHEAD" == "0" && "$BEHIND" == "0" ]]; then
    push_result "remote sync" "pass" "in sync with origin/$BRANCH"
  elif [[ "$BEHIND" != "0" ]]; then
    push_result "remote sync" "warn" "behind origin by $BEHIND commit(s); pull --rebase first"
    SOFT_FAIL=1
  else
    push_result "remote sync" "info" "ahead of origin by $AHEAD commit(s) to push"
  fi
else
  push_result "remote sync" "info" "no remote branch origin/$BRANCH; will create on push"
fi

# 5. 待 push commit 范围
if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
  TO_PUSH=$(git log --oneline "origin/$BRANCH..HEAD" 2>/dev/null | head -n 5 | tr '\n' ';' | sed 's/;$//')
else
  TO_PUSH=$(git log --oneline "origin/$DEFAULT_BRANCH..HEAD" 2>/dev/null | head -n 5 | tr '\n' ';' | sed 's/;$//' || echo "")
fi
if [[ -n "$TO_PUSH" ]]; then
  push_result "commits to push" "info" "$TO_PUSH"
fi

# 6. 是否存在 .env / *.key / *.pem 等敏感文件被追踪
TRACKED_SECRETS=$(git ls-files | grep -E '(\.env(\..+)?$|\.key$|\.pem$|id_rsa$|credentials\.json$)' || true)
if [[ -n "$TRACKED_SECRETS" ]]; then
  push_result "tracked secret files" "warn" "$(echo "$TRACKED_SECRETS" | tr '\n' ' ')"
  SOFT_FAIL=1
else
  push_result "tracked secret files" "pass" "none"
fi

# 输出
echo "## Preflight 检查"
echo ""
echo "| Check | Status | Detail |"
echo "|-------|--------|--------|"
for line in "${RESULTS[@]}"; do
  # shellcheck disable=SC2001
  echo "| $(echo "$line" | sed 's/|/ | /g') |"
done
echo ""
echo "## 总结"
if [[ $SEVERE_FAIL -eq 1 ]]; then
  echo "- ❌ 严重阻断：请先处理 FAIL 项再 ship"
  exit 2
elif [[ $SOFT_FAIL -eq 1 ]]; then
  echo "- ⚠️ 有警告，请确认无误再 ship"
  exit 1
else
  echo "- ✅ 全部通过，可以 ship"
  exit 0
fi

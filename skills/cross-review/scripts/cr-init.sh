#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: cr-init.sh <repo> <pr_number> <base> <branch> <pr_node_id>

Initialize cross-review workspace.

Arguments:
  repo          Repository (owner/repo)
  pr_number     PR number
  base          Base branch name
  branch        PR branch name
  pr_node_id    PR GraphQL node ID
USAGE
}

if [[ $# -lt 5 ]]; then
  usage
  exit 1
fi

REPO="$1"
PR_NUMBER="$2"
BASE="$3"
BRANCH="$4"
PR_NODE_ID="$5"

SAFE_REPO="$(echo "$REPO" | tr '/' '-')"
WORKSPACE="/tmp/cr-${SAFE_REPO}-${PR_NUMBER}"

# Cleanup previous run
rm -rf "$WORKSPACE"

# Create directories
mkdir -p "$WORKSPACE"/{state,tasks,results,comments}

# Write state
echo "$REPO"       > "$WORKSPACE/state/repo"
echo "$PR_NUMBER"  > "$WORKSPACE/state/pr-number"
echo "$BASE"       > "$WORKSPACE/state/base"
echo "$BRANCH"     > "$WORKSPACE/state/branch"
echo "$PR_NODE_ID" > "$WORKSPACE/state/pr-node-id"
echo "1"           > "$WORKSPACE/state/stage"

echo "CR_WORKSPACE=$WORKSPACE"
echo "Workspace initialized: $WORKSPACE"

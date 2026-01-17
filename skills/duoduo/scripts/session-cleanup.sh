#!/bin/bash
# session-cleanup.sh <pr_number>
# 清理 PR 的所有 session（orchestrator/codex/opus）

PR=$1
S=$(dirname "$0")

echo "Cleaning up all sessions for PR $PR..."

for NAME in orchestrator codex opus; do
  $S/session-stop.sh "$NAME" "$PR"
done

echo "All sessions cleaned up"

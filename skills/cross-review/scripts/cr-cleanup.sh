#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: cr-cleanup.sh [--keep-workspace]

Kill agent panes and optionally remove workspace.

Options:
  --keep-workspace    Don't remove workspace directory

Environment (required):
  CR_WORKSPACE    Workspace path
USAGE
}

KEEP_WORKSPACE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-workspace) KEEP_WORKSPACE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "${CR_WORKSPACE:-}" ]]; then
  echo "Error: CR_WORKSPACE not set" >&2
  exit 1
fi

# Kill agent panes (stored as pane IDs in state/)
for f in "$CR_WORKSPACE"/state/pane-*; do
  [[ -f "$f" ]] || continue
  AGENT=$(basename "$f" | sed 's/^pane-//')
  PANE_ID=$(cat "$f")
  if tmux has-session 2>/dev/null && tmux list-panes -a -F '#{pane_id}' | grep -q "^${PANE_ID}$"; then
    echo "Killing $AGENT pane ($PANE_ID)..."
    tmux kill-pane -t "$PANE_ID" 2>/dev/null || true
  fi
done

# Remove workspace
if [[ "$KEEP_WORKSPACE" == "false" ]]; then
  echo "Removing workspace: $CR_WORKSPACE"
  rm -rf "$CR_WORKSPACE"
else
  echo "Workspace preserved: $CR_WORKSPACE"
fi

echo "Cleanup complete"

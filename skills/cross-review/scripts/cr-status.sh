#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CR_WORKSPACE:-}" ]]; then
  echo "Error: CR_WORKSPACE not set" >&2
  exit 1
fi

echo "=== Cross Review Status ==="
echo ""

# State
echo "--- State ---"
for f in "$CR_WORKSPACE/state/"*; do
  [[ -f "$f" ]] || continue
  KEY=$(basename "$f")
  VALUE=$(cat "$f")
  printf "  %-15s %s\n" "$KEY:" "$VALUE"
done
echo ""

# Agent panes
echo "--- Agent Panes ---"
for f in "$CR_WORKSPACE"/state/pane-*; do
  [[ -f "$f" ]] || continue
  AGENT=$(basename "$f" | sed 's/^pane-//')
  PANE_ID=$(cat "$f")
  ALIVE="dead"
  if tmux list-panes -a -F '#{pane_id}' 2>/dev/null | grep -q "^${PANE_ID}$"; then
    ALIVE="alive"
  fi
  printf "  %-10s %s (%s)\n" "$AGENT:" "$PANE_ID" "$ALIVE"
done
echo ""

# Results
echo "--- Results ---"
if ls "$CR_WORKSPACE/results/"*.md 2>/dev/null; then
  for f in "$CR_WORKSPACE/results/"*.md; do
    LINES=$(wc -l < "$f")
    DONE=""
    [[ -f "${f%.md}.done" ]] && DONE=" [DONE]"
    echo "  $(basename "$f") (${LINES} lines)${DONE}"
  done
else
  echo "  (no results yet)"
fi

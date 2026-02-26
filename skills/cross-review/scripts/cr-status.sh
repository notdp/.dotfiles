#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CR_WORKSPACE:-}" ]]; then
  echo "Error: CR_WORKSPACE not set" >&2
  exit 1
fi

CR_SOCKET="${CR_SOCKET:-$(cat "$CR_WORKSPACE/socket.path")}"

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

# Pane layout
echo "--- Agent Panes ---"
if tmux -S "$CR_SOCKET" has-session -t cr 2>/dev/null; then
  tmux -S "$CR_SOCKET" list-panes -t cr:0 \
    -F '  pane #{pane_index}: #{pane_width}x#{pane_height} pid=#{pane_pid} dead=#{pane_dead}' 2>/dev/null || true
  echo ""
  echo "  Attach: tmux -S \"$CR_SOCKET\" attach -t cr"
else
  echo "  (no tmux session running)"
fi
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
echo ""

# Comments
echo "--- PR Comments ---"
if ls "$CR_WORKSPACE/comments/"*.id 2>/dev/null; then
  for f in "$CR_WORKSPACE/comments/"*.id; do
    MARKER=$(basename "$f" .id)
    ID=$(cat "$f")
    echo "  $MARKER: $ID"
  done
else
  echo "  (no comments tracked)"
fi

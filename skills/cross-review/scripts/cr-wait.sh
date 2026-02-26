#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: cr-wait.sh <agent_name> <stage_tag> [timeout_seconds]

Wait for an agent to complete by polling for sentinel file.

The sentinel file is: $CR_WORKSPACE/results/{agent}-{stage_tag}.done
The pane target is read from: $CR_WORKSPACE/state/pane-{agent}

Arguments:
  agent_name      Agent name (e.g., claude, gpt)
  stage_tag       Stage identifier (e.g., r1, crosscheck, fix, verify)
  timeout_seconds Timeout in seconds (default: 600)

Environment (required):
  CR_WORKSPACE    Workspace path
  CR_SOCKET       tmux socket path (or reads from $CR_WORKSPACE/socket.path)
USAGE
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

AGENT="$1"
STAGE_TAG="$2"
TIMEOUT="${3:-600}"

if [[ -z "${CR_WORKSPACE:-}" ]]; then
  echo "Error: CR_WORKSPACE not set" >&2
  exit 1
fi

CR_SOCKET="${CR_SOCKET:-$(cat "$CR_WORKSPACE/socket.path")}"

PANE_TARGET="$(cat "$CR_WORKSPACE/state/pane-${AGENT}" 2>/dev/null || echo "")"
if [[ -z "$PANE_TARGET" ]]; then
  echo "Error: no pane target for $AGENT (missing state/pane-${AGENT})" >&2
  exit 1
fi

SENTINEL="$CR_WORKSPACE/results/${AGENT}-${STAGE_TAG}.done"
RESULT="$CR_WORKSPACE/results/${AGENT}-${STAGE_TAG}.md"

START=$(date +%s)
DEADLINE=$((START + TIMEOUT))

echo "Waiting for $AGENT ($STAGE_TAG)... [timeout: ${TIMEOUT}s]"

while true; do
  if [[ -f "$SENTINEL" ]]; then
    echo "$AGENT ($STAGE_TAG): DONE"
    if [[ -f "$RESULT" ]]; then
      echo "Result: $RESULT ($(wc -l < "$RESULT") lines)"
    fi
    exit 0
  fi

  # Check if pane process is dead (remain-on-exit keeps pane alive after crash)
  PANE_DEAD=$(tmux -S "$CR_SOCKET" display-message -t "$PANE_TARGET" -p '#{pane_dead}' 2>/dev/null || echo "1")
  if [[ "$PANE_DEAD" == "1" ]]; then
    echo "Error: $AGENT pane process has died" >&2
    echo "Last pane output:" >&2
    tmux -S "$CR_SOCKET" capture-pane -p -J -t "$PANE_TARGET" -S -30 2>/dev/null >&2 || true
    exit 1
  fi

  NOW=$(date +%s)
  if (( NOW >= DEADLINE )); then
    echo "Timed out after ${TIMEOUT}s waiting for $AGENT ($STAGE_TAG)" >&2
    echo "Last pane output:" >&2
    tmux -S "$CR_SOCKET" capture-pane -p -J -t "$PANE_TARGET" -S -30 2>/dev/null >&2 || true
    exit 1
  fi

  ELAPSED=$((NOW - START))
  if (( ELAPSED % 30 == 0 && ELAPSED > 0 )); then
    echo "  ... ${ELAPSED}s elapsed"
  fi

  sleep 1
done

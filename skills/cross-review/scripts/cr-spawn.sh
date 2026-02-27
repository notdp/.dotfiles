#!/usr/bin/env bash
set -euo pipefail

SETTINGS_FILE="$HOME/.factory/settings.json"

usage() {
  cat <<'USAGE'
Usage: cr-spawn.sh <agent_name> <model>

Split the current tmux window and start a droid in the new pane.
The current pane (orchestrator) stays untouched; agents appear beside it.

Arguments:
  agent_name    Pane identifier (e.g., claude, gpt)
  model         Custom model ID (e.g., custom:claude-opus-4-6)

Environment (required):
  CR_WORKSPACE  Workspace path
  TMUX          Must be running inside tmux
USAGE
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

AGENT="$1"
MODEL="$2"

if [[ -z "${CR_WORKSPACE:-}" ]]; then
  echo "Error: CR_WORKSPACE not set" >&2
  exit 1
fi

if [[ -z "${TMUX:-}" ]]; then
  echo "Error: not running inside tmux" >&2
  exit 1
fi

# Count existing panes to decide split direction
PANE_COUNT=$(tmux list-panes -F '#{pane_index}' | wc -l)
if [[ "$PANE_COUNT" -eq 1 ]]; then
  # First agent: split right, orchestrator keeps 50%
  tmux split-window -h -d -l 50%
else
  # Subsequent agents: split the last agent pane vertically, equal share
  LAST_PANE=$((PANE_COUNT - 1))
  tmux split-window -v -d -l 50% -t ":.${LAST_PANE}"
fi

# The new pane is the highest index
NEW_PANE_IDX=$(tmux list-panes -F '#{pane_index}' | tail -1)
PANE_TARGET=":.${NEW_PANE_IDX}"

# Store pane ID (stable across layout changes, unlike index)
PANE_ID=$(tmux display-message -t "$PANE_TARGET" -p '#{pane_id}')
echo "$PANE_ID" > "$CR_WORKSPACE/state/pane-${AGENT}"

# Propagate environment to the new pane
for VAR in CR_WORKSPACE GH_TOKEN GITHUB_TOKEN \
           CR_MODEL_CLAUDE CR_MODEL_GPT \
           DROID_PR_NUMBER DROID_REPO DROID_BRANCH DROID_BASE; do
  if [[ -n "${!VAR:-}" ]]; then
    tmux set-environment "$VAR" "${!VAR}"
  fi
done

# Configure settings.json (model + spec mode) and mcp.json (disable auggie)
TARGET_ID=$(CR_MODEL="$MODEL" CR_SETTINGS="$SETTINGS_FILE" python3 -c "
import json, sys, os

model_arg = os.environ['CR_MODEL']
settings_path = os.environ['CR_SETTINGS']
mcp_path = os.path.expanduser('~/.factory/mcp.json')

if os.path.isfile(settings_path):
    with open(settings_path) as f:
        s = json.load(f)
    base = model_arg.replace('custom:', '', 1)
    target_id = model_arg
    for m in s.get('customModels', []):
        if m.get('model', '') == base or m.get('displayName', '') == base:
            target_id = m['id']
            break
    s.setdefault('sessionDefaultSettings', {})
    s['sessionDefaultSettings']['model'] = target_id
    s['sessionDefaultSettings']['specMode'] = False
    s['sessionDefaultSettings']['reasoningEffort'] = os.environ.get('CR_REASONING_EFFORT', 'high')
    with open(settings_path, 'w') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    print(target_id)
else:
    print(model_arg)

if os.path.isfile(mcp_path):
    with open(mcp_path) as f:
        m = json.load(f)
    changed = False
    for srv in m.get('mcpServers', {}).values():
        if 'auggie' in srv.get('command', ''):
            srv['disabled'] = True
            changed = True
    if changed:
        with open(mcp_path, 'w') as f:
            json.dump(m, f, indent=2)
" 2>/dev/null || echo "$MODEL")

echo "Setting default model to: $TARGET_ID"

# Start droid in the new pane
WORK_DIR="$(pwd)"
tmux send-keys -t "$PANE_ID" "cd \"${WORK_DIR}\" && droid" Enter

# Wait for droid to initialize
echo "Waiting for droid to initialize ($AGENT)..."
READY=false
for i in $(seq 1 60); do
  PANE="$(tmux capture-pane -p -J -t "$PANE_ID" -S -20 2>/dev/null || true)"
  if echo "$PANE" | grep -qE '(ctrl\+N to cycle|shift\+tab to cycle|\? for help|MCP)'; then
    READY=true
    echo "Droid TUI detected as ready."
    break
  fi
  if echo "$PANE" | grep -qE 'v[0-9]+\.[0-9]+\.[0-9]+'; then
    READY=true
    echo "Droid ready (banner detected after ${i}s)."
    break
  fi
  sleep 1
done

if [[ "$READY" != "true" ]]; then
  echo "Warning: droid may not be fully initialized" >&2
fi

echo "Agent '$AGENT' started in pane $PANE_ID (model: $MODEL)"

#!/usr/bin/env bash
set -euo pipefail

SETTINGS_FILE="$HOME/.factory/settings.json"
SESSION="cr"

usage() {
  cat <<'USAGE'
Usage: cr-spawn.sh <agent_name> <model>

Start an interactive droid in a tmux pane within the shared "cr" session.
First agent creates the session; subsequent agents split a new pane.
User can watch both agents with: tmux -S "$CR_SOCKET" attach -t cr

Arguments:
  agent_name    Pane label (e.g., claude, gpt)
  model         Custom model ID (required, e.g., custom:claude-opus-4-6)

Environment (required):
  CR_WORKSPACE  Workspace path
  CR_SOCKET     tmux socket path (or reads from $CR_WORKSPACE/socket.path)
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

CR_SOCKET="${CR_SOCKET:-$(cat "$CR_WORKSPACE/socket.path")}"

# Determine pane target: first agent creates session, subsequent agents split
if ! tmux -S "$CR_SOCKET" has-session -t "$SESSION" 2>/dev/null; then
  tmux -S "$CR_SOCKET" new-session -d -s "$SESSION" -n main -x 200 -y 50
  tmux -S "$CR_SOCKET" set-option -t "$SESSION" remain-on-exit on
  PANE_TARGET="$SESSION:0.0"
else
  # Count existing panes to decide split direction
  PANE_COUNT=$(tmux -S "$CR_SOCKET" list-panes -t "$SESSION:0" -F '#{pane_index}' | wc -l)
  if [[ "$PANE_COUNT" -eq 1 ]]; then
    # Second agent: split horizontally (left/right with orchestrator)
    tmux -S "$CR_SOCKET" split-window -h -t "$SESSION:0"
  else
    # Third+ agent: split the right pane vertically (stack agents)
    LAST_PANE=$((PANE_COUNT - 1))
    tmux -S "$CR_SOCKET" split-window -v -t "$SESSION:0.$LAST_PANE"
  fi
  tmux -S "$CR_SOCKET" select-layout -t "$SESSION:0" main-vertical
  PANE_IDX=$(tmux -S "$CR_SOCKET" display-message -t "$SESSION:0" -p '#{pane_index}')
  PANE_TARGET="$SESSION:0.$PANE_IDX"
fi

# Store pane target so orchestrator/cr-wait can address this agent
echo "$PANE_TARGET" > "$CR_WORKSPACE/state/pane-${AGENT}"

# Propagate key environment variables
for VAR in CR_WORKSPACE CR_SOCKET GH_TOKEN GITHUB_TOKEN \
           CR_MODEL_CLAUDE CR_MODEL_GPT \
           DROID_PR_NUMBER DROID_REPO DROID_BRANCH DROID_BASE; do
  if [[ -n "${!VAR:-}" ]]; then
    tmux -S "$CR_SOCKET" set-environment -t "$SESSION" "$VAR" "${!VAR}"
  fi
done

# Configure settings.json (model + spec mode) and mcp.json (disable auggie)
TARGET_ID=$(CR_MODEL="$MODEL" CR_SETTINGS="$SETTINGS_FILE" python3 -c "
import json, sys, os

model_arg = os.environ['CR_MODEL']
settings_path = os.environ['CR_SETTINGS']
mcp_path = os.path.expanduser('~/.factory/mcp.json')

# --- settings.json: set model + disable spec mode ---
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
    with open(settings_path, 'w') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    print(target_id)
else:
    print(model_arg)

# --- mcp.json: disable auggie to prevent EIO ---
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

# Start interactive droid in this pane
WORK_DIR="$(pwd)"
tmux -S "$CR_SOCKET" send-keys -t "$PANE_TARGET" \
  "cd \"${WORK_DIR}\" && droid" Enter

# Wait for droid to initialize
echo "Waiting for droid to initialize ($AGENT)..."
READY=false
for i in $(seq 1 60); do
  PANE="$(tmux -S "$CR_SOCKET" capture-pane -p -J -t "$PANE_TARGET" -S -20 2>/dev/null || true)"
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

echo ""
echo "Agent '$AGENT' started in pane $PANE_TARGET (model: $MODEL)"
echo ""
echo "To watch all agents:"
echo "  tmux -S \"$CR_SOCKET\" attach -t $SESSION"

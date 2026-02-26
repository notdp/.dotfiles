#!/usr/bin/env bash
set -euo pipefail

SETTINGS_FILE="$HOME/.factory/settings.json"

usage() {
  cat <<'USAGE'
Usage: cr-spawn.sh <agent_name> <model>

Start an interactive droid in a tmux session with the specified model.
Model is set by temporarily updating settings.json before droid starts.

Arguments:
  agent_name    Session name (e.g., claude, gpt)
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

# Kill existing session if any
tmux -S "$CR_SOCKET" kill-session -t "$AGENT" 2>/dev/null || true

# Create new session with generous size for TUI rendering
tmux -S "$CR_SOCKET" new-session -d -s "$AGENT" -n main -x 160 -y 50
# Keep pane alive even if droid exits, so we can inspect the output
tmux -S "$CR_SOCKET" set-option -t "$AGENT" remain-on-exit on

# Propagate key environment variables into the tmux session
for VAR in CR_WORKSPACE CR_SOCKET GH_TOKEN GITHUB_TOKEN \
           CR_MODEL_CLAUDE CR_MODEL_GPT \
           DROID_PR_NUMBER DROID_REPO DROID_BRANCH DROID_BASE; do
  if [[ -n "${!VAR:-}" ]]; then
    tmux -S "$CR_SOCKET" set-environment -t "$AGENT" "$VAR" "${!VAR}"
  fi
done

# Configure settings.json (model + spec mode) and mcp.json (disable auggie)
# in a single python3 call to minimize startup latency
TARGET_ID=$(CR_MODEL="$MODEL" CR_SETTINGS="$SETTINGS_FILE" python3 -c "
import json, sys, os

model_arg = os.environ['CR_MODEL']
settings_path = os.environ['CR_SETTINGS']
mcp_path = os.path.expanduser('~/.factory/mcp.json')

# --- settings.json: set model + disable spec mode ---
if os.path.isfile(settings_path):
    with open(settings_path) as f:
        s = json.load(f)
    # Resolve custom model ID
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
    print('Spec mode disabled', file=sys.stderr)
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
        print('Disabled auggie MCP', file=sys.stderr)
" 2>/dev/null || echo "$MODEL")

echo "Setting default model to: $TARGET_ID"

# Start interactive droid (reads model from settings.json)
# Auggie MCP is disabled above, so no need for script(1) PTY wrapper
WORK_DIR="$(pwd)"
tmux -S "$CR_SOCKET" send-keys -t "$AGENT":0.0 \
  "cd \"${WORK_DIR}\" && droid" Enter

# Wait for droid to initialize
echo "Waiting for droid to initialize in session '$AGENT'..."
READY=false
for i in $(seq 1 60); do
  PANE="$(tmux -S "$CR_SOCKET" capture-pane -p -J -t "$AGENT":0.0 -S -20 2>/dev/null || true)"
  if echo "$PANE" | grep -qE '(ctrl\+N to cycle|shift\+tab to cycle|\? for help|MCP)'; then
    READY=true
    echo "Droid TUI detected as ready."
    break
  fi
  # Check if droid process started (banner visible = process running)
  if echo "$PANE" | grep -qE 'v[0-9]+\.[0-9]+\.[0-9]+'; then
    READY=true
    echo "Droid ready (banner detected after ${i}s)."
    break
  fi
  sleep 1
done

if [[ "$READY" != "true" ]]; then
  echo "Warning: droid may not be fully initialized" >&2
  tmux -S "$CR_SOCKET" capture-pane -p -J -t "$AGENT":0.0 -S -10 2>/dev/null || true
fi

echo ""
echo "Agent '$AGENT' started (model: $MODEL)"
echo ""
echo "To monitor:"
echo "  tmux -S \"$CR_SOCKET\" attach -t $AGENT"
echo "  tmux -S \"$CR_SOCKET\" capture-pane -p -J -t $AGENT:0.0 -S -200"

#!/usr/bin/env bash

set -u

APP=""
EVENT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)
      APP="${2:-}"
      shift 2
      ;;
    --event)
      EVENT="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

sound_for() {
  local app_key event_key specific_var specific_sound
  app_key="$(printf '%s' "$APP" | tr '[:lower:]-' '[:upper:]_')"
  event_key="$(printf '%s' "$EVENT" | tr '[:lower:]-' '[:upper:]_')"
  specific_var="NOTIFY_TMUX_TITLE_SOUND_${app_key}_${event_key}"
  specific_sound="$(printenv "$specific_var" 2>/dev/null || true)"

  if [[ -n "$specific_sound" ]]; then
    echo "$specific_sound"
    return 0
  fi
  if [[ -n "${NOTIFY_TMUX_TITLE_SOUND:-}" ]]; then
    echo "$NOTIFY_TMUX_TITLE_SOUND"
    return 0
  fi

  case "$APP:$EVENT" in
    droid:stop) echo "${HOME}/.factory/sounds/fx-ok01.wav" ;;
    droid:notification) echo "${HOME}/.factory/sounds/fx-ack01.wav" ;;
    cc:stop) echo "/System/Library/Sounds/Ping.aiff" ;;
    cc:notification) echo "/System/Library/Sounds/Funk.aiff" ;;
    *)
      echo "unsupported app/event: $APP/$EVENT" >&2
      return 2
      ;;
  esac
}

fallback_sound="$(sound_for)" || exit $?
title=""

if [[ -n "${TMUX_PANE:-}" ]] && command -v tmux >/dev/null 2>&1; then
  title="$(tmux display-message -p -t "$TMUX_PANE" '#W' 2>/dev/null || true)"
fi

if [[ -n "$title" ]]; then
  if [[ "${NOTIFY_TMUX_TITLE_DRY_RUN:-}" == "1" ]]; then
    printf 'say:%s\n' "$title"
  else
    /usr/bin/say "$title"
  fi
else
  if [[ "${NOTIFY_TMUX_TITLE_DRY_RUN:-}" == "1" ]]; then
    printf 'sound:%s\n' "$fallback_sound"
  else
    /usr/bin/afplay "$fallback_sound"
  fi
fi

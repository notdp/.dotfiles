#!/bin/bash
input=$(cat)
MODEL=$(echo "$input" | jq -r '.model.display_name')
CWD=$(echo "$input" | jq -r '.cwd')
SID=$(echo "$input" | jq -r '.session_id // empty')
SHORT_SID="${SID:0:8}"
IS_CC=$(echo "$input" | jq -e '.context_window' >/dev/null 2>&1 && echo 1 || echo 0)

SHORT_CWD="${CWD/#$HOME/~}"
COLS=$(stty size 2>/dev/null </dev/tty | awk '{print $2}')
[ -z "$COLS" ] && COLS=120

SEP='\033[0m · '
OSC_START='\033]8;;'
OSC_END='\033\\'

# --- Factory usage + plan (stale-while-revalidate, 600s TTL) ---
USAGE_CACHE="/tmp/droid_statusline_usage"
LAST_GOOD_USAGE_CACHE="${USAGE_CACHE}.last_good"
USAGE_STR=""
_has_valid_usage_data() {
  [ -f "$1" ] && [ -s "$1" ] || return 1
  jq -e '
    (.usage.standard.totalAllowance // 0) > 0 and
    (.schedule | type == "array") and
    (.schedule | length > 0) and
    ((.schedule[0].plan.name // "") | length > 0)
  ' "$1" >/dev/null 2>&1
}
_store_last_good_usage_cache() {
  _has_valid_usage_data "$1" || return 1
  cp -f "$1" "$LAST_GOOD_USAGE_CACHE" 2>/dev/null
}
_restore_last_good_usage_cache() {
  _has_valid_usage_data "$LAST_GOOD_USAGE_CACHE" || return 1
  cp -f "$LAST_GOOD_USAGE_CACHE" "$USAGE_CACHE" 2>/dev/null
}
_mtime_seconds() {
  local value
  value=$(stat -f %m "$1" 2>/dev/null)
  case "$value" in
    ''|*[!0-9]*) ;;
    *) printf "%s\n" "$value"; return ;;
  esac
  value=$(stat -c %Y "$1" 2>/dev/null)
  case "$value" in
    ''|*[!0-9]*) printf "0\n" ;;
    *) printf "%s\n" "$value" ;;
  esac
}
_fetch_usage() {
  local tok tmp
  # Try auth.v2 (AES-256-GCM encrypted) first, fall back to legacy auth.encrypted
  if [ -f "$HOME/.factory/auth.v2.file" ] && [ -f "$HOME/.factory/auth.v2.key" ]; then
    tok=$(node -e "
      const c=require('crypto'),f=require('fs'),p=require('path'),h=process.env.HOME;
      const k=Buffer.from(f.readFileSync(p.join(h,'.factory/auth.v2.key'),'utf8').trim(),'base64');
      const d=f.readFileSync(p.join(h,'.factory/auth.v2.file'),'utf8').trim().split(':');
      const x=c.createDecipheriv('aes-256-gcm',k,Buffer.from(d[0],'base64'));
      x.setAuthTag(Buffer.from(d[1],'base64'));
      console.log(JSON.parse(x.update(Buffer.from(d[2],'base64'),null,'utf8')+x.final('utf8')).access_token);
    " 2>/dev/null) || return
  else
    tok=$(python3 -c "import json; print(json.loads(open('$HOME/.factory/auth.encrypted').read())['access_token'])" 2>/dev/null) || return
  fi
  tmp="${USAGE_CACHE}.tmp.$$"
  curl -s --max-time 5 --noproxy api.factory.ai "https://api.factory.ai/api/organization/subscription/schedule" \
    -H "Authorization: Bearer $tok" \
    -H "Content-Type: application/json" -H "X-Factory-Client: cli" \
    -o "$tmp" 2>/dev/null
  if _has_valid_usage_data "$tmp"; then
    mv -f "$tmp" "$USAGE_CACHE"
    _store_last_good_usage_cache "$USAGE_CACHE"
  else
    rm -f "$tmp"
  fi
}
if _has_valid_usage_data "$USAGE_CACHE"; then
  _store_last_good_usage_cache "$USAGE_CACHE"
elif [ -f "$USAGE_CACHE" ] && [ -s "$USAGE_CACHE" ]; then
  _restore_last_good_usage_cache
fi
if [ -f "$USAGE_CACHE" ] && [ -s "$USAGE_CACHE" ]; then
  CACHE_AGE=$(( $(date +%s) - $(_mtime_seconds "$USAGE_CACHE") ))
  [ "$CACHE_AGE" -ge 600 ] && _fetch_usage &
else
  _fetch_usage
fi
if _has_valid_usage_data "$USAGE_CACHE"; then
  USAGE_DATA=$(cat "$USAGE_CACHE")
elif _has_valid_usage_data "$LAST_GOOD_USAGE_CACHE"; then
  USAGE_DATA=$(cat "$LAST_GOOD_USAGE_CACHE")
fi
if [ -n "$USAGE_DATA" ]; then
  USED=$(echo "$USAGE_DATA" | jq -r '.usage.standard.orgTotalTokensUsed // 0' 2>/dev/null)
  TOTAL=$(echo "$USAGE_DATA" | jq -r '.usage.standard.totalAllowance // 0' 2>/dev/null)
  END_MS=$(echo "$USAGE_DATA" | jq -r '.usage.endDate // 0' 2>/dev/null)
  PLAN=$(echo "$USAGE_DATA" | jq -r '.schedule[0].plan.name // empty' 2>/dev/null)
  # extract short plan name: "Factory Pro Plan" -> "Pro"
  SHORT_PLAN=$(echo "$PLAN" | sed -E 's/Factory ([A-Za-z]+) Plan/\1/')
  if [ "$TOTAL" -gt 0 ] 2>/dev/null; then
    USED_M=$(awk "BEGIN{printf \"%.1f\", $USED/1000000}")
    TOTAL_M=$(awk "BEGIN{printf \"%.0f\", $TOTAL/1000000}")
    PCT=$(awk "BEGIN{printf \"%.0f\", $USED/$TOTAL*100}")
    if [ "$PCT" -ge 80 ]; then
      USAGE_CLR="38;5;174"
    elif [ "$PCT" -ge 60 ]; then
      USAGE_CLR="38;5;222"
    else
      USAGE_CLR="38;5;114"
    fi
    # days until renewal
    RENEW=""
    if [ "$END_MS" -gt 0 ] 2>/dev/null; then
      NOW_S=$(date +%s)
      END_S=$((END_MS / 1000))
      DAYS_LEFT=$(( (END_S - NOW_S) / 86400 ))
      RENEW=" ${DAYS_LEFT}d"
    fi
    BILLING_URL="https://app.factory.ai/settings/billing"
    USAGE_BODY="${OSC_START}${BILLING_URL}${OSC_END}\033[38;5;243m${SHORT_PLAN}\033[0m \033[${USAGE_CLR}m${USED_M}/${TOTAL_M}M\033[0m\033[38;5;243m${RENEW}\033[0m${OSC_START}${OSC_END}"
    USAGE_STR=" · ${USAGE_BODY}"
  fi
fi

if [ "$IS_CC" = "0" ]; then
  MAX_CWD_LEN=$((COLS / 3))
  [ "$MAX_CWD_LEN" -lt 24 ] && MAX_CWD_LEN=24
  if [ "${#SHORT_CWD}" -gt "$MAX_CWD_LEN" ]; then
    SHORT_CWD="…/$(basename "$CWD")"
  fi
  right_col=$((COLS - ${#SHORT_CWD}))
  DIR_LINK="\033[${right_col}G${OSC_START}vscode://file${CWD}${OSC_END}\033[1;38;5;66m${SHORT_CWD}\033[0m${OSC_START}${OSC_END}"
else
  DIR_LINK="${SEP}${OSC_START}vscode://file${CWD}${OSC_END}\033[1;38;5;66m${SHORT_CWD}\033[0m${OSC_START}${OSC_END}"
fi

if git -C "$CWD" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  BRANCH=$(git -C "$CWD" --no-optional-locks branch --show-current 2>/dev/null)

  # stale-while-revalidate PR cache
  REPO_ROOT=$(git -C "$CWD" --no-optional-locks rev-parse --show-toplevel 2>/dev/null)
  REPO_NAME=$(basename "$REPO_ROOT" 2>/dev/null)
  SAFE_BRANCH=$(echo "$BRANCH" | tr '/' '_')
  CACHE_FILE="/tmp/droid_statusline_pr_${REPO_NAME}_${SAFE_BRANCH}"
  PR_STR=""
  PR_VIS=""

  if [ -f "$CACHE_FILE" ]; then
    CACHE_AGE=$(( $(date +%s) - $(_mtime_seconds "$CACHE_FILE") ))
    if [ "$CACHE_AGE" -ge 300 ]; then
      (cd "$REPO_ROOT" && gh pr view --json number,url -q '.number,.url' > "$CACHE_FILE" 2>/dev/null || echo "none" > "$CACHE_FILE") &
    fi
  else
    (cd "$REPO_ROOT" && gtimeout 2 gh pr view --json number,url -q '.number,.url' > "$CACHE_FILE" 2>/dev/null) || echo "none" > "$CACHE_FILE"
  fi
  if [ -f "$CACHE_FILE" ]; then
    PR_NUM=$(head -1 "$CACHE_FILE")
    PR_URL=$(tail -1 "$CACHE_FILE")
    if [ -n "$PR_NUM" ] && [ "$PR_NUM" != "none" ]; then
      PR_STR=" · \033[38;5;146mPR ${OSC_START}${PR_URL}${OSC_END}#${PR_NUM}${OSC_START}${OSC_END}\033[0m"
      PR_VIS=" · PR #${PR_NUM}"
    fi
  fi

  STATS=$({ git -C "$CWD" --no-optional-locks diff --numstat 2>/dev/null; git -C "$CWD" --no-optional-locks diff --cached --numstat 2>/dev/null; } | awk '{a+=$1; d+=$2} END {print a+0, d+0}')
  ADD=${STATS% *}
  DEL=${STATS#* }

  SID_STR=""
  [ -n "$SHORT_SID" ] && SID_STR=" · \033[38;5;243m${SHORT_SID}\033[0m"

  if [ "$IS_CC" = "0" ]; then
    if [ "$ADD" -gt 0 ] || [ "$DEL" -gt 0 ]; then
      printf "%b · \033[1;38;5;146m%s\033[0m%b \033[1;38;5;114m+%s \033[1;38;5;174m-%s\033[0m%b${DIR_LINK}" "$SID_STR" "$BRANCH" "$PR_STR" "$ADD" "$DEL" "$USAGE_STR"
    else
      printf "%b · \033[1;38;5;146m%s\033[0m%b%b${DIR_LINK}" "$SID_STR" "$BRANCH" "$PR_STR" "$USAGE_STR"
    fi
  else
    printf "${OSC_START}vscode://file${CWD}${OSC_END}\033[1;38;5;66m%s\033[0m${OSC_START}${OSC_END}${SEP}\033[1;38;5;146m%s\033[0m${SEP}\033[1;38;5;214m%s\033[0m%b%b" "$SHORT_CWD" "$BRANCH" "$MODEL" "$SID_STR" "$USAGE_STR"
  fi
else
  SID_STR=""
  [ -n "$SHORT_SID" ] && SID_STR=" · \033[38;5;243m${SHORT_SID}\033[0m"
  if [ "$IS_CC" = "0" ]; then
    printf "%b%b${DIR_LINK}" "$SID_STR" "$USAGE_STR"
  else
    printf "${OSC_START}vscode://file${CWD}${OSC_END}\033[1;38;5;66m%s\033[0m${OSC_START}${OSC_END}${SEP}\033[1;38;5;214m%s\033[0m%b%b" "$SHORT_CWD" "$MODEL" "$SID_STR" "$USAGE_STR"
  fi
fi

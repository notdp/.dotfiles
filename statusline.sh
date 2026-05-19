#!/bin/bash
input=$(cat)
MODEL=$(echo "$input" | jq -r '.model.display_name')
CWD=$(echo "$input" | jq -r '.cwd')
IS_CC=$(echo "$input" | jq -e '.context_window' >/dev/null 2>&1 && echo 1 || echo 0)

if [[ "$CWD" == "$HOME"/* || "$CWD" == "$HOME" ]]; then SHORT_CWD="~${CWD#$HOME}"; else SHORT_CWD="$CWD"; fi
COLS=$(stty size </dev/tty 2>/dev/null | awk '{print $2}')
[ -z "$COLS" ] && COLS=120

SEP='\033[0m · '

OSC_START='\033]8;;'
OSC_END='\033\\'

if [ "$IS_CC" = "0" ]; then
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
    CACHE_AGE=$(( $(date +%s) - $(stat -f %m "$CACHE_FILE" 2>/dev/null || echo 0) ))
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

  if [ "$IS_CC" = "0" ]; then
    if [ "$ADD" -gt 0 ] || [ "$DEL" -gt 0 ]; then
      printf "\033[1;38;5;60m%s\033[0m · \033[1;38;5;146m%s\033[0m%b \033[1;38;5;114m+%s \033[1;38;5;174m-%s\033[0m${DIR_LINK}" "$MODEL" "$BRANCH" "$PR_STR" "$ADD" "$DEL"
    else
      printf "\033[1;38;5;60m%s\033[0m · \033[1;38;5;146m%s\033[0m%b${DIR_LINK}" "$MODEL" "$BRANCH" "$PR_STR"
    fi
  else
    printf "${OSC_START}vscode://file${CWD}${OSC_END}\033[1;38;5;66m%s\033[0m${OSC_START}${OSC_END}${SEP}\033[1;38;5;146m%s\033[0m${SEP}\033[1;38;5;60m%s\033[0m" "$SHORT_CWD" "$BRANCH" "$MODEL"
  fi
else
  printf "\033[1;38;5;60m%s\033[0m${DIR_LINK}" "$MODEL"
fi

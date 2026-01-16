#!/bin/bash
# 等待条件满足
# 用法: duo-wait.sh <PR_NUMBER> <FIELD1> <VALUE1> [<FIELD2> <VALUE2> ...]
# 例如: duo-wait.sh 85 s1:codex:status done s1:opus:status done

PR=$1
shift
KEY="duo:$PR"

while true; do
  ALL_MATCH=1
  ARGS=("$@")
  i=0
  while [ $i -lt ${#ARGS[@]} ]; do
    FIELD="${ARGS[$i]}"
    EXPECTED="${ARGS[$((i+1))]}"
    ACTUAL=$(redis-cli HGET "$KEY" "$FIELD")
    if [ "$ACTUAL" != "$EXPECTED" ]; then
      ALL_MATCH=0
      break
    fi
    i=$((i+2))
  done
  
  if [ $ALL_MATCH -eq 1 ]; then
    echo "done"
    exit 0
  fi
  
  sleep 3
done

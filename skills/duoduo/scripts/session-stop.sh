#!/bin/bash
# session-stop.sh <name> <pr_number>
# 停止 session，清理 FIFO 和进程

NAME=$1
PR=$2
KEY="duo:$PR"

PID=$(redis-cli HGET "$KEY" "${NAME}:pid")
FIFO=$(redis-cli HGET "$KEY" "${NAME}:fifo")
LOG=$(redis-cli HGET "$KEY" "${NAME}:log")

# 停止进程
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID" 2>/dev/null
  echo "Stopped process $PID"
fi

# 删除 FIFO
if [ -n "$FIFO" ] && [ -p "$FIFO" ]; then
  rm -f "$FIFO"
  echo "Removed FIFO $FIFO"
fi

# 清理 Redis 字段
redis-cli HDEL "$KEY" "${NAME}:session" "${NAME}:fifo" "${NAME}:pid" "${NAME}:log" > /dev/null

echo "Session $NAME (PR $PR) cleaned up"

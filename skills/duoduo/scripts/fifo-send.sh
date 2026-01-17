#!/bin/bash
# fifo-send.sh <name> <pr_number> <message>
# 往运行中的 session 发送消息

NAME=$1
PR=$2
MESSAGE=$3

FIFO=$(redis-cli HGET "duo:$PR" "${NAME}:fifo")

if [ -z "$FIFO" ] || [ ! -p "$FIFO" ]; then
  echo "Error: FIFO not found for $NAME (PR $PR)" >&2
  exit 1
fi

ESCAPED=$(echo "$MESSAGE" | jq -Rs '.')

echo '{"jsonrpc":"2.0","type":"request","factoryApiVersion":"1.0.0","method":"droid.add_user_message","params":{"text":'"$ESCAPED"'},"id":"msg-'"$(date +%s)"'"}' > "$FIFO"

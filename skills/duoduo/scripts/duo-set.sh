#!/bin/bash
# 设置 Redis 字段
# 用法: duo-set.sh <PR_NUMBER> <FIELD> <VALUE>

PR=$1
FIELD=$2
VALUE=$3
KEY="duo:$PR"

redis-cli HSET "$KEY" "$FIELD" "$VALUE" > /dev/null

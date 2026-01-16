#!/bin/bash
# 获取 Redis 字段
# 用法: duo-get.sh <PR_NUMBER> <FIELD>

PR=$1
FIELD=$2
KEY="duo:$PR"

redis-cli HGET "$KEY" "$FIELD"

#!/bin/bash
# 获取完整状态
# 用法: duo-status.sh <PR_NUMBER>

PR=$1
KEY="duo:$PR"

redis-cli HGETALL "$KEY"

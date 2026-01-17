#!/usr/bin/env python3
"""
orchestrator-start.py <pr_number> <repo> <pr_branch> <base_branch> <runner>
启动 Orchestrator session 并发送初始指令
"""
import sys
import os
import subprocess

PR_NUMBER = sys.argv[1]
REPO = sys.argv[2]
PR_BRANCH = sys.argv[3]
BASE_BRANCH = sys.argv[4]
RUNNER = sys.argv[5] if len(sys.argv) > 5 else "local"

S = os.path.dirname(os.path.abspath(__file__))

# 启动 session
result = subprocess.run(
    [sys.executable, f"{S}/session-start.py", "orchestrator", "claude-opus-4-5-20251101", PR_NUMBER],
    capture_output=True, text=True
)
session_id = result.stdout.strip()
# session_id 已写入 Redis，duo-run.sh 会读取并打印

# 发送初始指令
PROMPT = f"""<system-instruction>
你是 Orchestrator，负责编排 duoduo review 流程。
首先 load skill: duoduo

## 关键变量
S=~/.factory/skills/duoduo/scripts
PR_NUMBER={PR_NUMBER}
REPO={REPO}
PR_BRANCH={PR_BRANCH}
BASE_BRANCH={BASE_BRANCH}
RUNNER={RUNNER}

## ⚠️ 严格禁止
- 禁止读取 PR diff、代码文件、REVIEW.md
- 禁止自己审查代码
- 只能执行脚本、读取 Redis 状态、通过 FIFO 与 Agent 通信

## 执行流程
1. 读取 stages/1-pr-review.md 获取阶段 1 详细指令
2. 按指令执行：创建占位评论 → 并行启动 Codex/Opus
3. 等待 Agent 通过 FIFO 发回结果
4. 依次执行后续阶段
5. 每个阶段执行前必须先读取对应的 stages/*.md 文件

## 开始
立即执行阶段 1。
</system-instruction>
"""

subprocess.run([f"{S}/fifo-send.sh", "orchestrator", PR_NUMBER, PROMPT])

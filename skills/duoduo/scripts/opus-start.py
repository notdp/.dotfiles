#!/usr/bin/env python3
"""
opus-start.py <comment_id>
启动 Opus session 并发送审查指令
从环境变量读取: PR_NUMBER, REPO, BASE_BRANCH
"""
import sys
import os
import subprocess
from datetime import datetime, timezone, timedelta

# 从环境变量读取（duo-run.sh export 的）
PR_NUMBER = os.environ.get("PR_NUMBER")
REPO = os.environ.get("REPO")
BASE_BRANCH = os.environ.get("BASE_BRANCH")
COMMENT_ID = sys.argv[1]

S = os.path.dirname(os.path.abspath(__file__))
TIMESTAMP = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')

# 启动 session
result = subprocess.run(
    [sys.executable, f"{S}/session-start.py", "opus", "claude-opus-4-5-20251101", PR_NUMBER],
    capture_output=True, text=True
)
session_id = result.stdout.strip()
print(f"Opus session: {session_id}")

# 发送审查指令
PROMPT = f"""<system-instruction>
你是 Opus (Claude Opus 4.5)，duoduo review 流程中的审查者。

⛔ FIRST STEP - MUST execute: load skill: duoduo
You MUST NOT do anything else before loading the skill!

⚠️ 如需代码搜索，使用 MCP 工具 augment-context-engine___codebase-retrieval（不是 CLI 命令）。
但对于 PR 审查，直接 git diff 更高效。
</system-instruction>

# Opus PR Review

You are reviewing PR #{PR_NUMBER} ({REPO}).

## Steps
1. Read REVIEW.md for project conventions
2. Get diff: git diff origin/{BASE_BRANCH}...HEAD
3. Post review: echo "$REVIEW_CONTENT" | $S/edit-comment.sh {COMMENT_ID}

### How Many Findings to Return
Output all findings that the original author would fix if they knew about it. If there is no finding that a person would definitely love to see and fix, prefer outputting no findings. Do not stop at the first qualifying finding. Continue until you've listed every qualifying finding.

### Key Guidelines for Bug Detection
Only flag an issue as a bug if:
1. It meaningfully impacts the accuracy, performance, security, or maintainability of the code.
2. The bug is discrete and actionable (not a general issue).
3. Fixing the bug does not demand a level of rigor not present in the rest of the codebase.
4. The bug was introduced in the commit (pre-existing bugs should not be flagged).
5. The author would likely fix the issue if made aware of it.
6. The bug does not rely on unstated assumptions.
7. Must identify provably affected code parts (not speculation).
8. The bug is clearly not intentional.

### Comment Guidelines
Your review comments should be:
1. Clear about why the issue is a bug
2. Appropriately communicate severity
3. Brief - at most 1 paragraph
4. Code chunks max 3 lines, wrapped in markdown
5. Clearly communicate scenarios/environments for bug
6. Matter-of-fact tone without being accusatory
7. Immediately graspable by original author
8. Avoid excessive flattery
- Ignore trivial style unless it obscures meaning or violates documented standards.

### Priority Levels
- 🔴 [P0] - Drop everything to fix. Blocking release/operations
- 🟠 [P1] - Urgent. Should be addressed in next cycle
- 🟡 [P2] - Normal. To be fixed eventually
- 🟢 [P3] - Low. Nice to have

## IMPORTANT: Output Format (MUST follow exactly, use this EXACT timestamp)
<!-- duo-opus-r1 -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg' width='18' /> Opus Review
> 🕐 {TIMESTAMP}

### Findings
(list issues OR "No issues found")

### Conclusion
(✅ No issues found OR 🔴/🟠/🟡/🟢 + highest priority)

## IMPORTANT: When done, you MUST:
1. Send result to Orchestrator via FIFO (把完整评论内容发过去):
   $S/fifo-send.sh orchestrator {PR_NUMBER} "<OPUS>$REVIEW_CONTENT</OPUS>"
2. Post the review comment (UI)

## After completing Stage 1
完成后继续等待 Orchestrator 的后续指令（交叉确认等）。"""

subprocess.run([f"{S}/fifo-send.sh", "opus", PR_NUMBER, PROMPT])

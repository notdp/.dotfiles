# 阶段 1: 并行 PR 审查

**执行者**: Orchestrator + Codex + Opus

## ⚠️ 重要规则

1. **禁止读取脚本内容** - 直接执行，不要检查脚本里写了什么
2. **必须使用 fireAndForget: true** - Codex 和 Opus 必须并行启动，不能串行

## 流程

```plain
初始化 Redis → 创建占位评论 → 并行启动 Codex/Opus (fireAndForget) → duo-wait 等待完成
```

## 1.1 初始化

```bash
$S/duo-init.sh $PR_NUMBER $REPO $PR_BRANCH $BASE_BRANCH
```

## 1.2 创建占位评论

```bash
PROGRESS_ID=$($S/post-comment.sh $PR_NUMBER $REPO "<!-- duo-review-progress -->
## 🔄 Duo Review 进度
<img src=\"https://github.com/user-attachments/assets/5ac382c7-e004-429b-8e35-7feb3e8f9c6f\" width=\"14\" /> 审查中...
")

CODEX_COMMENT=$($S/post-comment.sh $PR_NUMBER $REPO "<!-- duo-codex-r1 -->
<img src=\"https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg\" width=\"18\" /> **Codex** 审查中...
")

OPUS_COMMENT=$($S/post-comment.sh $PR_NUMBER $REPO "<!-- duo-opus-r1 -->
<img src=\"https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg\" width=\"18\" /> **Opus** 审查中...
")

$S/duo-set.sh $PR_NUMBER progress_comment "$PROGRESS_ID"
$S/duo-set.sh $PR_NUMBER s1:codex:comment "$CODEX_COMMENT"
$S/duo-set.sh $PR_NUMBER s1:opus:comment "$OPUS_COMMENT"
```

## 1.3 启动 Codex

**⚠️ 必须使用 Execute 工具的 `fireAndForget: true` 参数！不要读脚本内容！**

脚本会自动写入 Redis（status, session, conclusion）。

```bash
$S/codex-exec.sh $PR_NUMBER "You are acting as a reviewer for a proposed code change made by another engineer.

Review PR #$PR_NUMBER ($REPO).

## Steps
1. Read REVIEW.md for project conventions
2. gh pr diff $PR_NUMBER --repo $REPO
3. Update comment: echo 'content' | \$S/edit-comment.sh $CODEX_COMMENT

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
- 🔴 **[P0]** - Drop everything to fix. Blocking release/operations
- 🟠 **[P1]** - Urgent. Should be addressed in next cycle
- 🟡 **[P2]** - Normal. To be fixed eventually
- 🟢 **[P3]** - Low. Nice to have

## Output Format
<!-- duo-codex-r1 -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg' width='18' /> Codex | PR #$PR_NUMBER
> 🕐 YYYY-MM-DD HH:MM (GMT+8)

### Findings (or 'No issues found')
- 🔴[P0]/🟠[P1]/🟡[P2]/🟢[P3] Title - reason

### Conclusion
✅ No issues OR list highest priority found"
```

## 1.4 启动 Opus

**⚠️ 必须使用 Execute 工具的 `fireAndForget: true` 参数！不要读脚本内容！**

脚本会自动写入 Redis（status, session, conclusion）。

```bash
$S/opus-exec.sh $PR_NUMBER "You are acting as a reviewer for a proposed code change made by another engineer.

Review PR #$PR_NUMBER ($REPO).

## Steps
1. Read REVIEW.md for project conventions
2. gh pr diff $PR_NUMBER --repo $REPO
3. Update comment: echo 'content' | \$S/edit-comment.sh $OPUS_COMMENT

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
- 🔴 **[P0]** - Drop everything to fix. Blocking release/operations
- 🟠 **[P1]** - Urgent. Should be addressed in next cycle
- 🟡 **[P2]** - Normal. To be fixed eventually
- 🟢 **[P3]** - Low. Nice to have

## Output Format
<!-- duo-opus-r1 -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg' width='18' /> Opus | PR #$PR_NUMBER
> 🕐 YYYY-MM-DD HH:MM (GMT+8)

### Findings (or 'No issues found')
- 🔴[P0]/🟠[P1]/🟡[P2]/🟢[P3] Title - reason

### Conclusion
✅ No issues OR list highest priority found"
```

## 1.5 等待完成

```bash
$S/duo-wait.sh $PR_NUMBER s1:codex:status done s1:opus:status done
```

## 输出

完成后 Redis 中有：
- `s1:codex:status = done`
- `s1:codex:session = <UUID>`
- `s1:codex:conclusion = ok|p0|p1|p2|p3`
- `s1:opus:*` 同上

→ 进入阶段 2

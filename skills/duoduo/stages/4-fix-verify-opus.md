# 阶段 4: 修复 - Opus

修复阶段 3 确认的问题。

```mermaid
flowchart TD
    Start([开始]) --> S1[1. 创建占位评论]
    S1 --> S2[2. 创建修复分支]
    S2 --> S3[3. 修复问题]
    S3 --> S4[4. 提交代码]
    S4 --> S5[5. 推送并更新评论]
    S5 --> S6[6. 通知 Codex 验证]
    S6 --> Done([等待验证结果])
```

---

## 1. 创建占位评论

```bash
TIMESTAMP=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M')

COMMENT_ID=$(duo-cli comment post --stdin <<EOF
<!-- duo-opus-fix -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg' width='18' /> Opus 修复中
> 🕐 $TIMESTAMP

<img src='https://github.com/user-attachments/assets/5ac382c7-e004-429b-8e35-7feb3e8f9c6f' width='18' /> {随机ing词}...
EOF
)
```

**{随机 ing 词}**: Fixing, Patching, Refactoring 等，自己想一个有趣的！

---

## 2. 创建修复分支

```bash
ROUND=$(duo-cli get s4:round)
BRANCH="duo/pr$DROID_PR_NUMBER-fix-r$ROUND"
git checkout -b "$BRANCH"
duo-cli set s4:branch "$BRANCH"
```

---

## 3. 修复问题

根据阶段 3 确认的问题进行修复。

---

## 4. 提交代码

```bash
git add -A
git commit -m 'fix(duo): ...'
```

---

## 5. 推送并更新评论

```bash
# 禁止推送到 main
[[ "$BRANCH" == "main" || "$BRANCH" == "master" ]] && echo "ERROR: Cannot push to main/master" && exit 1
git push origin "$BRANCH" --force

# 更新评论
duo-cli comment edit $COMMENT_ID "$FIX_CONTENT"
```

**评论格式：**

```markdown
<!-- duo-opus-fix -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg' width='18' /> Opus 修复完成
> 🕐 {TIMESTAMP}

### 修复内容
**Commit**: [`<short_hash>`](https://github.com/$DROID_REPO/commit/<full_hash>)

(说明修复了什么问题)

### 文件变更
(列出修改的文件及行数变更)
```

---

## 6. 切回 PR 分支并通知 Codex

```bash
git checkout $DROID_BRANCH

duo-cli send codex --stdin <<EOF
修复完成，分支: $BRANCH

请验证修复是否正确。阅读 ~/.factory/skills/duoduo/stages/4-fix-verify-codex.md 执行。
EOF
```

# 阶段 4: 修复 - Agent

修复交叉确认中确认的问题。

## 步骤

1. 创建修复分支
2. 修复问题
3. 提交代码
4. 推送
5. 写入结果文件

---

## 1. 创建修复分支

格式: `cr/pr{NUMBER}-{简要描述}`

```bash
PR_NUMBER=$(cat "$CR_WORKSPACE/state/pr-number")
BRANCH="cr/pr${PR_NUMBER}-{简要语义化描述}"
git checkout -b "$BRANCH"
echo "$BRANCH" > "$CR_WORKSPACE/state/s4-branch"
```

---

## 2. 修复问题

根据任务文件中列出的问题进行修复。

---

## 3. 提交代码

```bash
git add -A
git commit -m 'fix(cr): ...'
```

---

## 4. 推送

```bash
# 安全检查
[[ "$BRANCH" == "main" || "$BRANCH" == "master" ]] && echo "ERROR: Cannot push to main" && exit 1
git push origin "$BRANCH" --force
```

---

## 5. 切回 PR 分支并写入结果

```bash
BRANCH_PR=$(cat "$CR_WORKSPACE/state/branch")
git checkout "$BRANCH_PR"
```

将修复摘要写入 `$CR_WORKSPACE/results/claude-fix.md`，格式：

```markdown
## Fix Summary

### Changes
**Branch**: {branch}
**Commit**: {short_hash}

{修复说明}

### Files Changed
{文件列表}
```

然后创建 sentinel：`touch $CR_WORKSPACE/results/claude-fix.done`

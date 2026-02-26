# 阶段 4: 验证 - Agent

验证修复是否正确。

## 步骤

1. 查看修复 diff
2. 验证代码
3. 写入结果文件

---

## 1. 查看修复

```bash
FIX_BRANCH=$(cat "$CR_WORKSPACE/state/s4-branch")
BASE=$(cat "$CR_WORKSPACE/state/base")
git fetch origin "$FIX_BRANCH"
git diff "origin/$BASE...origin/$FIX_BRANCH"
```

---

## 2. 验证

检查：
- 问题是否真正解决
- 是否引入新问题
- 代码质量是否符合规范

---

## 3. 写入结果

将验证结果写入 `$CR_WORKSPACE/results/gpt-verify.md`。

结果第一行必须是 `PASS` 或 `FAIL`（Orchestrator 据此判断下一步）。

```markdown
PASS

### Details
{验证说明}
```

或：

```markdown
FAIL

### Details
{失败原因}
```

最后创建 sentinel：`touch $CR_WORKSPACE/results/gpt-verify.done`

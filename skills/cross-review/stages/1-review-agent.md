# 阶段 1: PR 审查 - Agent

审查 PR，写入结果文件。

## 步骤

1. 读取项目 REVIEW.md（如有）
2. 获取 diff
3. 审查代码
4. 写入结果文件 + sentinel

---

## 1. 获取 diff

```bash
BASE=$(cat "$CR_WORKSPACE/state/base")
git diff "origin/$BASE...HEAD"
```

---

## 2. 审查代码

### 发现多少问题

输出所有作者知道后会修复的问题。如果没有值得修复的发现，优先输出"无问题"。

### Bug 判定标准

仅在以下条件全部满足时才标记为 bug：

1. 对准确性、性能、安全性或可维护性有实质影响
2. 问题具体且可操作
3. 修复不要求超出代码库其余部分的严格程度
4. 是本次 commit 引入的（不标记已存在的问题）
5. 作者知道后很可能会修复
6. 不依赖未声明的假设
7. 必须能识别受影响的具体代码位置
8. 明显不是有意为之

### 评论风格

- 清楚说明为什么是问题
- 适当传达严重程度
- 简洁 — 每个发现最多 1 段
- 代码块最多 3 行
- 客观语气
- 忽略琐碎样式问题

### 优先级

- 🔴 [P0] - 立即修复，阻塞发布
- 🟠 [P1] - 紧急，下个周期处理
- 🟡 [P2] - 正常，后续修复
- 🟢 [P3] - 低优先级

---

## 3. 写入结果文件

将审查结果写入 `$CR_WORKSPACE/results/{AGENT}-r1.md`。

格式：

```markdown
## {AGENT} Review

### Findings
(列出问题 或 "No issues found")

### Conclusion
(✅ No issues found 或 🔴/🟠/🟡/🟢 + 最高优先级)
```

**最后一步**：创建 sentinel 文件

```bash
touch "$CR_WORKSPACE/results/${AGENT}-r1.done"
```

⚠️ **必须在所有工作完成后才创建 sentinel**。Orchestrator 靠此文件判断你已完成。

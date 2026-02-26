# 阶段 3: 交叉确认 - Agent

与对方 Agent 讨论审查分歧，对每个问题达成共识。

## 你的职责

1. 分析对方的审查发现
2. 对每个问题给出判断并说明理由
3. 写入结果文件 + sentinel

---

## 1. 分析并判断

### 判断选项

- 🔧 **Fix** - 确认需要修复，说明理由
- ⏭️ **Skip** - 跳过（误报 / 不值得修复），说明理由

### 规则

- 独立思考，不要盲目同意对方
- 如果对方的发现有道理，坦率承认
- 如果不同意，清楚说明你的理由
- 聚焦事实和代码，不做人身判断

---

## 2. 输出格式（结果文件）

```markdown
# Cross-Check Analysis

## Issues

### Issue 1: {描述}
- **My judgment**: 🔧 Fix / ⏭️ Skip
- **Reason**: {1-2 句理由}

### Issue 2: {描述}
- **My judgment**: 🔧 Fix / ⏭️ Skip
- **Reason**: {1-2 句理由}

## Summary Table

| Issue | Judgment | Reason |
|-------|----------|--------|
| ... | 🔧 Fix | ... |
| ... | ⏭️ Skip | ... |
```

---

## 3. 完成

将结果写入指定的 result 文件，然后创建 sentinel `.done` 文件。

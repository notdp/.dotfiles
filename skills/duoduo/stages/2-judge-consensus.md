# 阶段 2: 判断共识

**执行者**: Orchestrator

## 判断方法

直接从阶段 1 收到的 FIFO 消息判断，**不要读 Redis**。

看 `<OPUS>` 和 `<CODEX>` 消息中的 Conclusion 部分：

- `✅ No issues` → ok
- `🔴 [P0]` → p0
- `🟠 [P1]` → p1
- `🟡 [P2]` → p2
- `🟢 [P3]` → p3

## 决策矩阵

| Codex  | Opus               | 结果        | 下一阶段 |
| ------ | ------------------ | ----------- | -------- |
| ok     | ok                 | both_ok     | 5        |
| 有问题 | 有问题（相同级别） | same_issues | 4        |
| ok     | 有问题             | divergent   | 3        |
| 有问题 | ok                 | divergent   | 3        |
| 有问题 | 有问题（不同级别） | divergent   | 3        |

## 执行

```bash
$S/duo-set.sh $PR_NUMBER stage 2
```

根据判断结果进入对应阶段：

→ both_ok → 阶段 5
→ same_issues → 阶段 4  
→ divergent → 阶段 3

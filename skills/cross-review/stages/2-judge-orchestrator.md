# 阶段 2: 判断共识 - Orchestrator

## 禁止操作

- 不要直接操作 tmux

## 概述

分析 Claude 和 GPT 的审查结果，判断是否达成共识。

## 执行

```bash
echo "2" > "$CR_WORKSPACE/state/stage"

# 读取两份审查结果
CLAUDE_RESULT=$(cat "$CR_WORKSPACE/results/claude-r1.md")
GPT_RESULT=$(cat "$CR_WORKSPACE/results/gpt-r1.md")
```

## 分析维度

- 是否发现问题？
- 发现了哪些问题？
- 问题的严重程度如何？
- 两者的发现是否有交集？

## 判断结果

| 结果          | 条件                    | 下一阶段               |
| ------------- | ----------------------- | ---------------------- |
| `both_ok`     | 双方都没发现问题        | → 阶段 5（汇总）       |
| `same_issues` | 双方发现相同/相似的问题 | → 阶段 4（修复）       |
| `divergent`   | 结论有分歧              | → 阶段 3（交叉确认）   |

## 记录结果

```bash
echo "both_ok" > "$CR_WORKSPACE/state/s2-result"    # 或 same_issues / divergent
```

然后读取对应阶段的 orchestrator 文档继续执行。

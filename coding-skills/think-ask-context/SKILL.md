---
name: think-ask-context
description: 当 agent 准备回答复杂问题但未掌握所有相关文件、或怀疑上下文不足时使用；输出信息需求清单作为回答前置。
---

# Ask Context

动手或回答前，先声明"需要看什么文件"、"已经有什么"、"不确定什么"，避免盲推。

## 输入

{{question}}

## 指令

1. 基于问题，列出需要看的文件及其相关性
2. 区分"必须看"和"可能需要看"
3. 标出已经在上下文里的文件
4. 显式说明不看源码就不能确认的点

## 输出格式

```markdown
## Files I Need

### Must See（必须看，影响答案正确性）
- `path/to/file` — <为什么需要>

### Should See（可能需要，影响答案完整性）
- `path/to/file` — <为什么可能需要>

### Already Have（已经在上下文）
- `path/to/file` — <从哪一步看到>

### Uncertainties（不看代码无法确认的点）
- <具体的不确定项>
```

提供完文件后，我会重新提问或基于新信息继续。

## 与其他 skill 的边界

- `think-map` 做整个仓库/技术栈的地图，不针对具体问题
- `think-context-map` 针对具体改动画文件地图，包含 Dependencies / Tests / Patterns
- 本 skill 最轻：只声明信息需求，不铺展依赖/测试/模式分析

## Gotchas

- 不要跳过"Already Have"——重复读已读的文件浪费上下文
- "Uncertainties" 必须具体，"我不太确定" 不算
- 如果问题本身就清晰、现有上下文足够，直接回答，不要强行走本 skill

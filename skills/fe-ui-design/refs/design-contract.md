# Design Contract

UI 任务先锁定契约，再写代码。目标是减少模型自由发挥，把风格、层级和验证方式前置。

## 最小模板

```md
Surface: web / mobile / dashboard / deck / fixed canvas
Audience: <谁用，什么场景>
Direction: editorial / modern-minimal / warm-soft / tech-utility / brutalist / existing-system
Tokens:
- --bg:
- --surface:
- --fg:
- --muted:
- --border:
- --accent:
- --font-display:
- --font-body:
Type scale: 12 / 14 / 16 / 20 / 24 / 32 / 48 / 64
Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 80
Grid: <max-width / columns / gutters>
Accent budget: <= 2 visible uses per screen
Forbidden: <gradients / emoji icons / fake metrics / filler copy / etc>
Verification: <viewports + screenshot + overflow checks>
```

## Direction packages

| Direction | 适用 | 姿态 |
|---|---|---|
| editorial | 内容、报告、品牌故事 | serif display、克制色彩、强排版、少容器 |
| modern-minimal | SaaS、工具、docs | near-greyscale、hairline border、少阴影 |
| warm-soft | wellness、fintech、creator | warm neutral、soft radius、单一 editorial flourish |
| tech-utility | dashboard、developer tool、ops | 信息密度、tabular numerics、状态 pill |
| brutalist | agency、art、manifesto | 大字、强网格、低圆角、显性边框 |

## 优先级

1. 项目已有 design system / component library
2. 用户提供的品牌规范、Figma、截图
3. 本文件的 direction package
4. 临时 neutral contract

不要沉默混用多个方向。冲突时以项目已有系统为准，并指出取舍。

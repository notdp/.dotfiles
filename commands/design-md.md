---
description: 建立、使用、诊断和验证项目 DESIGN.md；降低 UI 美学工作流的认知负担。
argument-hint: <init|use|critique|verify|help> [页面/路径/目标]
---

# DESIGN.md Workflow

DESIGN.md 是 UI 视觉契约入口，不是又一份普通说明文档。它把 agent 的审美输入拆成两层：

- YAML front matter：颜色、字体、间距、圆角、组件状态等机器可读 token。
- Markdown body：品牌氛围、使用场景、取舍理由、Do / Don't。

## 最常用路径

```text
init -> use -> capture -> critique -> iterate -> verify
```

| 目标 | 使用方式 |
|---|---|
| 没有设计系统 | 触发 `/fe-ui-design-system`，生成临时 DESIGN.md contract |
| 已有 UI 但没美感 | 触发 `/fe-ui-critique`，对照截图、代码和 DESIGN.md 找问题 |
| 新做页面 | 先 `/think-plan` 锁定 DESIGN.md 来源，再 `/fe-ui-design` 实现 |
| 对照参考图 | 触发 `/fe-ui-visual-iterate`，截图后小步收敛 |
| 准备交付 | 触发 `/guard-verify`，补截图、overflow、状态覆盖、DESIGN.md adherence 证据 |

## 状态图

```text
no contract
  -> choose reference
  -> write DESIGN.md
  -> build with tokens
  -> screenshot
  -> critique against contract
  -> iterate
  -> verify
```

## 参考

- 规范：`refs/google-labs-code/design.md/docs/spec.md`
- 样本库：`refs/voltagent/awesome-design-md`
- 调研：`docs/software-engineering-research/design-md-aesthetic-workflow.md`

## 禁止

- 不直接复制某个品牌样本当自己的品牌。
- 不用 DESIGN.md 取代截图验收。
- 不把临时推断写成项目事实。
- 不在没有 token 的情况下散落新 hex、字号、圆角和阴影。

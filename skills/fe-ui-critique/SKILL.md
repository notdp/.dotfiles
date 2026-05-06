---
name: fe-ui-critique
description: 当已有页面、截图、组件实现或设计稿需要判断视觉质量时使用；输出带证据的 UI 设计诊断、CRAP 原则检查、AI slop 信号与修复计划，不默认改代码。
---

# UI Critique

用于回答“为什么丑”“哪里不对劲”“哪里像 AI 做的”。本 skill 只诊断，不默认修改代码。

## 输入

接受任一输入：

- 页面 URL 或本地 route
- 截图路径
- 组件 / 页面文件路径
- 参考图或目标风格
- 设计系统 / brand brief

信息不足时，先用现有代码、截图或浏览器取证；不要凭印象评价。

## 流程

1. **Collect evidence**
   - 有 URL：用浏览器截图和 DOM snapshot。
   - 有文件：读取组件、样式、token 来源。
   - 有参考图：记录 viewport、语言、主题和差异目标。

2. **Lock context**
   - Surface：web / mobile / dashboard / deck / fixed canvas
   - Audience：工具型 / 营销型 / 内容型 / 游戏型
   - Intended direction：现有设计系统或推断的视觉方向
   - DESIGN.md source：项目现有 / 用户提供 / 临时生成 / 未找到

3. **Critique**
   - Direction fit：是否符合产品/受众/场景
   - Hierarchy：主次是否清楚
   - CRAP：亲密性、对齐性、重复性、对比性
   - Craft：typography、color、spacing、motion
   - Usability：状态、响应式、可访问性
   - Detail reliability：文字溢出、遮挡、错位、长文本
   - AI slop：默认紫、trust gradient、emoji icon、filler copy、假指标
   - Contract adherence：颜色、字体、间距、圆角、组件状态是否偏离 DESIGN.md 或现有 token

## 输出契约

```markdown
## UI Critique

### Verdict
- Overall: A/B/C/D/F
- Main issue: <一句话>

### Findings
| Priority | Area | Evidence | Principle | Issue | Fix |
|---|---|---|---|---|---|
| P0 | ... | screenshot region / selector / file:line | Contrast | ... | ... |


当存在 `DESIGN.md` 或本轮生成的 design contract 时，Findings 表改用：

```markdown
| Priority | Area | Evidence | Contract | Principle | Issue | Fix |
|---|---|---|---|---|---|---|
| P1 | Color | file:line | `colors.accent` | Repetition | hardcoded accent drift | use token |
```
### CRAP Check
| Principle | Status | Evidence | Fix |
|---|---|---|---|
| Proximity | pass/warn/fail | ... | ... |
| Alignment | pass/warn/fail | ... | ... |
| Repetition | pass/warn/fail | ... | ... |
| Contrast | pass/warn/fail | ... | ... |

### AI Slop Signals
- ...

### Fix Plan
1. ...
```

## 严重度

| Priority | 标准 |
|---|---|
| P0 | 文字溢出、遮挡、不可读、关键操作不可见、严重 a11y 失败 |
| P1 | 层级混乱、明显不对齐、design system 违背、响应式破版 |
| P2 | AI slop、token 漂移、一致性差、状态缺失 |
| P3 | 微调：字距、阴影、节奏、文案 polish |

## 规则

- 每条问题必须有证据：截图区域、selector、file:line、token 或 DOM 观察。
- 不把个人审美当结论；落到原则、上下文和可验证细节。
- 参考图本身可能有问题；冲突时指出参考图违反的原则。
- DESIGN.md 与可访问性冲突时，优先报告冲突，不沉默照做。
- 如果用户要继续修复，再转 `/fe-ui-design` 或 `/fe-ui-visual-iterate`。

## 关联技能

- 生成/修改 UI 前 → `/fe-ui-design`
- 对照参考图迭代 → `/fe-ui-visual-iterate`
- 交付前验证 → `/guard-verify`

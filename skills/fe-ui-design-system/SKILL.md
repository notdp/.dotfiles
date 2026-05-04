---
name: fe-ui-design-system
description: 当项目缺少明确视觉约束、需要从现有 UI/品牌/截图提取规则或生成轻量设计系统时使用；输出可复用的 DESIGN.md 风格 contract，约束颜色、字体、布局、组件和禁用项。
---

# UI Design System

把“凭感觉设计”收敛成可复用设计契约。输出应短、可审查、可被 `/fe-ui-design` 读取。

## 输入

- 现有项目 UI / 组件库 / CSS token
- Figma、截图、品牌描述、产品定位
- 用户指定的风格方向
- 没有输入时，生成临时 neutral contract，并标注来源为推断

## 流程

1. **Discover source**
   - 优先读取项目已有 token、theme、组件库、CSS variables。
   - 其次读取用户提供的品牌规范或截图。
   - 都没有时，选择一个方向包：editorial / modern-minimal / warm-soft / tech-utility / brutalist。

2. **Extract contract**
   - 颜色按用途命名，不按 hue 命名。
   - 字体只保留 display/body/mono。
   - 间距、圆角、阴影、边框给出少量 token。
   - 组件规则只写最常用：button、card、input、nav/table。

3. **Add guardrails**
   - Accent budget
   - 禁用项
   - 响应式策略
   - 内容真实性规则

## 输出模板

```markdown
# <Design System Name>

## Visual Theme
<氛围、受众、适用页面>

## Color Tokens
- Background:
- Surface:
- Foreground:
- Muted:
- Border:
- Accent:
- Success / Warn / Danger:

## Typography
- Display:
- Body:
- Mono:
- Scale:
- Line height:
- Letter spacing:

## Layout
- Grid:
- Max width:
- Gutters:
- Section spacing:
- Component spacing:

## Components
- Buttons:
- Cards:
- Inputs:
- Navigation / Tables:

## Responsive
- Desktop:
- Tablet:
- Mobile:

## Do / Don't
- Do:
- Don't:

## Verification
- Viewports:
- Overflow:
- Contrast:
- State coverage:
```

## 规则

- 不直接搬大型 design-system 库；只提炼当前任务需要的最小契约。
- 不创造 20 个 token；少量稳定 token 优于庞大 palette。
- 不把品牌色到处用；每屏最多 2 个 accent。
- 不把临时推断伪装成事实；用 `[推断]` 标注来源不明的选择。

## 关联技能

- 用 contract 实现 UI → `/fe-ui-design`
- 诊断现有 UI 是否遵守 contract → `/fe-ui-critique`
- 交付前验证 → `/guard-verify`

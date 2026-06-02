---
name: fe-ui-design-system
description: 当项目缺少明确视觉约束、需要从现有 UI/品牌/截图提取规则或生成轻量设计系统时使用；输出可复用的 DESIGN.md 风格 contract，约束颜色、字体、布局、组件和禁用项。
---

# UI Design System

把“凭感觉设计”收敛成可复用设计契约。输出应短、可审查、可被 `/fe-ui-design` 读取。

优先输出 DESIGN.md 形态：YAML front matter 放机器可读 token，Markdown sections 放人类可读 rationale。格式参考：

- `refs/google-labs-code/design.md/docs/spec.md`
- `refs/google-labs-code/design.md/examples/atmospheric-glass/DESIGN.md`
- `refs/voltagent/awesome-design-md/README.md`

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
   - DESIGN.md 输出中，token 是规范值，prose 解释为什么和怎么用。

3. **Add guardrails**
   - Accent budget
   - 禁用项
   - 响应式策略
   - 内容真实性规则

## DESIGN.md 输出模板

优先使用下面的结构。没有足够信息时，用 `[推断]` 标注来源，不能把猜测写成事实。

```markdown
---
version: alpha
name: <Design System Name>
description: "<一句话定位>"
colors:
  background: "#..."
  surface: "#..."
  foreground: "#..."
  muted: "#..."
  border: "#..."
  accent: "#..."
typography:
  display:
    fontFamily: <font>
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1.1
  body:
    fontFamily: <font>
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: 4px
  md: 8px
spacing:
  sm: 8px
  md: 16px
  lg: 32px
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.background}"
    rounded: "{rounded.md}"
    padding: 8px 14px
---

## Overview
<氛围、受众、适用页面>

## Colors
<颜色角色、accent budget、禁用色>

## Typography
<display/body/mono 的用途与层级>

## Layout
<grid、max width、gutter、section spacing>

## Elevation & Depth
<阴影、边框、层级策略；不用阴影时说明替代方式>

## Shapes
<圆角、边框、图标形状>

## Components
<button、card、input、nav/table 的状态和规则>

## Do's and Don'ts
<Do / Don't，尤其是 AI slop 禁用项>

## Verification
<viewport、overflow、contrast、state coverage>
```

## 规则

- 不直接搬大型 design-system 库；只提炼当前任务需要的最小契约。
- 不创造 20 个 token；少量稳定 token 优于庞大 palette。
- 不把品牌色到处用；每屏最多 2 个 accent。
- 不把临时推断伪装成事实；用 `[推断]` 标注来源不明的选择。
- 不直接复制 `awesome-design-md` 品牌样本；只能提取可迁移的风格规则。
- 不把 DESIGN.md 当作最终验收；还必须配合截图和 critique。

## 关联技能

- 用 contract 实现 UI → `/fe-ui-design`
- 诊断现有 UI 是否遵守 contract → `/fe-ui-critique`
- 交付前验证 → `/guard-verify`

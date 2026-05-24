---
name: fe-ui-design
description: 当需要构建 web 组件、页面或应用界面时使用；提供设计原则、正向质量门和参考文档。
argument-hint: <页面/组件需求|设计目标>
---

# FE UI Design

构建符合设计原则的前端界面，用具体证据检查视觉质量。

## Design Contract（动 UI 前先锁定）

写任何 UI 代码前，先用 5-8 行锁定设计契约；已有 design system 时读取并沿用，没有时生成临时契约。

→ 契约模板见 [design-contract](refs/design-contract.md)

### DESIGN.md SSOT

UI 任务开工前先找项目级 `DESIGN.md`：

1. 如果存在，读取并遵守其中的 token 与 rationale。
2. 如果不存在但项目已有 theme / CSS variables / 组件库，先用 `/fe-ui-design-system` 提取临时 DESIGN.md contract。
3. 如果没有任何来源，先声明 `[推断]` 的临时方向，不能把临时审美当成项目事实。
4. 实现时颜色、字体、间距、圆角、组件状态优先从 DESIGN.md 或现有 token 派生。

参考规范：`refs/google-labs-code/design.md/docs/spec.md`。参考样本库：`refs/voltagent/awesome-design-md`。

DESIGN.md 不是最终验收。实现后仍需要截图、CRAP 检查、overflow 检查和状态覆盖证据。

必填：

- Surface：web / mobile / dashboard / deck / fixed canvas
- Audience：工具型 / 营销型 / 内容型 / 游戏型
- Direction：editorial / modern-minimal / warm-soft / tech-utility / brutalist，或项目既有风格
- Tokens：`--bg` / `--surface` / `--fg` / `--muted` / `--border` / `--accent` / display/body font
- Type scale：12 / 14 / 16 / 20 / 24 / 32 / 48 / 64
- Spacing scale：4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 80
- Accent budget：每屏最多 2 个可见 accent
- Avoid list：本任务明确排除的视觉套路和内容占位
- DESIGN.md source：项目现有 / 用户提供 / 临时生成 / 未找到

## 四大基础原则

每次生成或修改 UI 时，先用这四条自检：

1. **对齐** — 每个元素都有视觉锚点。文本左对齐、元素沿网格线排列、间距对称。
2. **对比** — 用 size/weight/color 的明确差异建立层次。标题和正文的大小比至少 1.5:1，差异不够 = 没有层次。
3. **一致** — 间距、颜色、字体、圆角、阴影在整个页面使用统一 token。不造新值。
4. **聚合（Proximity）** — 相关元素靠近，无关元素拉远。用距离表达分组，不依赖边框和卡片。

→ 可执行检查表见 [layout-principles](refs/layout-principles.md)

## P0 Quality Gate（交付前必须通过）

→ 完整规则见 [anti-ai-slop](refs/anti-ai-slop.md)

- Accent 来自项目 token 或任务设计契约；使用 Tailwind indigo/purple 默认色时，需要说明它和品牌/语义的关系。
- Gradient 服务信息层级或品牌方向；purple→blue、blue→cyan、indigo→pink 这类常见组合需要有明确设计理由。
- Feature / UI icon 使用项目图标库、语义图标或自定义 SVG。
- 卡片强调优先用结构、间距、字重和 token 化颜色；左侧粗彩边只在信息类型需要时使用。
- 指标必须有来源或上下文：`10x faster`、`99.9% uptime`、`3x productive` 这类文案需要可验证依据。
- 文案使用任务真实内容或明确标注的待替换内容。
- 颜色来自 token 或 token 派生值，新增颜色需要写入设计契约。
- 文本溢出通过布局、换行和尺寸约束解决；`overflow-hidden` 只能用于明确的裁切设计。

## Overflow Contract

→ 详细规则见 [overflow](refs/overflow.md)

- flex/grid 子项承载文本时默认考虑 `min-width: 0`
- 长单词、URL、数字串、混排文本必须有安全换行策略
- 按钮和卡片使用内容可伸缩的尺寸、换行和最小/最大宽度策略
- fixed canvas / deck / poster 先定义 content bounds，再放文字
- 内容超预算时拆 section/slide，不把正文缩到不可读

## Typography

→ 详细参考 [typography](refs/typography.md)

**Use**: modular type scale + fluid sizing (`clamp()`) 建立字号层次。
**Use**: 字重和大小变化创造清晰的视觉层次。
**Prefer**: display/body 字体与项目语气匹配；使用 Inter、Roboto、Arial、Open Sans 或 system defaults 时，说明它们为何适合当前产品。
**Prefer**: 等宽字体只用于代码、数据、终端或需要字符对齐的场景；技术感优先来自密度、结构、图标和颜色纪律。
**Check**: 标题装饰需要服务信息层级；图标、徽标和标题的组合要避免模板化重复。

## Color

→ 详细参考 [color](refs/color.md)

**Use**: OKLCH 色彩空间（感知均匀）。
**Use**: 给中性色加品牌色微调（tinted neutrals），哪怕 chroma 只有 0.01。
**Prefer**: 彩色背景上的文字使用背景色系的深浅变化，而不是脱离背景的通用灰。
**Prefer**: 背景和前景带少量色相倾向；纯黑 `#000` / 纯白 `#fff` 只在设计契约明确需要时使用。
**Prefer**: 调色盘来自品牌、内容语义或项目 token；cyan-on-dark、紫蓝渐变、霓虹暗底需要有产品语境。
**Check**: 渐变文字必须承担层级、状态或品牌表达功能。
**Check**: 暗色模式和发光强调色需要服务阅读、氛围或状态表达，而不是默认视觉方案。

## Layout & Space

→ 详细参考 [spatial](refs/spatial.md)

**Use**: 4pt 基础间距系统（4, 8, 12, 16, 24, 32, 48, 64px）。
**Use**: varied spacing 创造节奏：紧密分组 + 宽松分隔。
**Use**: `clamp()` 做流体间距。
**Prefer**: 容器只用于分组、状态、背景或交互边界明确的内容。
**Prefer**: 扁平层级和清晰分组；需要嵌套卡片时，用背景、边框、间距区分层级。
**Prefer**: 网格项按内容重要性、密度或交互优先级变化尺寸和节奏。
**Prefer**: 正文和复杂信息左对齐；居中布局用于短文本、hero 或明确的展示场景。
**Check**: 间距要表达亲密性和分隔关系，同一页面需要有节奏变化。

## Visual Details

**Prefer**: glassmorphism 只用于需要表达深度、半透明材质或背景关系的场景。
**Prefer**: 强调方式服务信息类型；可选手段包括结构位置、字重、背景、图标、状态色和边框。
**Prefer**: sparkline 只展示真实趋势数据，并配合标签或数值解释。
**Prefer**: 卡片形状、阴影和边框来自设计契约，并能支持页面记忆点或层级。
**Prefer**: modal 用于阻断式决策；非阻断信息优先用 inline panel、drawer、popover 或页面内状态。

## Motion

→ 详细参考 [motion](refs/motion.md)

**Use**: exponential easing（ease-out-quart/quint/expo）做自然减速。
**Use**: 对高度动画使用 `grid-template-rows` 而非直接动画 `height`。
**Prefer**: 动画优先使用 transform + opacity；layout 属性动画需要性能验证。
**Prefer**: 平滑减速表达工具型界面；bounce / elastic 只在产品语气明确需要轻快物理反馈时使用。

## Interaction

→ 详细参考 [interaction](refs/interaction.md)

**Use**: 每个交互元素设计 8 种状态（default/hover/focus/active/disabled/loading/error/success）。
**Use**: 有意义的空状态，说明发生了什么、用户能做什么。
**Prefer**: primary / secondary / ghost / text link 分层表达行动优先级。
**Prefer**: 文案补充用户看不到的原因、影响或下一步。

## Responsive

→ 详细参考 [responsive](refs/responsive.md)

**Use**: container queries 做组件级响应式。
**Prefer**: 移动端保留关键功能路径，通过布局、分组和渐进披露适配界面。

## UX Writing

→ 详细参考 [ux-writing](refs/ux-writing.md)

**Use**: 按钮文案用「动词 + 名词」— "保存更改" 而非 "确定"。
**Use**: 错误信息回答三个问题：发生了什么？为什么？怎么修？

## Codex 反模式索引

来源细则见 OpenAI codex base_instructions / Frontend guidance；本 skill 主流程只保留交付契约：

- 已有 design system 时沿用现有约定，不引入第二套 token。
- 控件优先使用熟悉模式和现有图标库；不靠圆角矩形 + 文字描述替代清晰 affordance。
- Landing / hero / game / 3D / fixed canvas 先锁定任务类型和视觉资产来源，再决定布局。
- Card、section、视觉装饰、文本容器、固定尺寸控件都必须服务信息层级和可用性。
- 命中大面积模板化调色、无意义装饰、文字遮挡、重叠或 reflow 风险时，停下重审设计契约。

## AI Slop Test

**关键质量检查**：如果你把这个界面展示给人，说"AI 做的"，他们会立刻相信吗？如果会，那就是问题。

把流行趋势作为可选素材，而不是永久规则；判断依据是任务目标、信息层级、可访问性、响应式和项目既有风格。

## Gotchas

- 设计质量优先看层次、对齐、一致和可用性；装饰风格必须服务这些目标
- 暗色、玻璃、渐变、发光需要有信息价值、品牌语境或状态表达
- 组件单看顺眼不代表页面成立；必须从整体节奏、信息层级和状态覆盖重新检查
- 设计约束不是只审美化输出，落地时要和可访问性、响应式、实现成本一起判断

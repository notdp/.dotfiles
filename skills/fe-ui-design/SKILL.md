---
name: fe-ui-design
description: 当需要构建 web 组件、页面或应用界面时使用；提供设计原则、反模式约束和参考文档。
argument-hint: <页面/组件需求|设计目标>
---

# FE UI Design

构建符合设计原则的前端界面，避免 AI 生成的典型视觉问题。

## Design Contract（动 UI 前先锁定）

写任何 UI 代码前，先用 5-8 行锁定设计契约；已有 design system 时读取并沿用，没有时生成临时契约。

→ 契约模板见 [design-contract](refs/design-contract.md)

必填：

- Surface：web / mobile / dashboard / deck / fixed canvas
- Audience：工具型 / 营销型 / 内容型 / 游戏型
- Direction：editorial / modern-minimal / warm-soft / tech-utility / brutalist，或项目既有风格
- Tokens：`--bg` / `--surface` / `--fg` / `--muted` / `--border` / `--accent` / display/body font
- Type scale：12 / 14 / 16 / 20 / 24 / 32 / 48 / 64
- Spacing scale：4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 80
- Accent budget：每屏最多 2 个可见 accent
- Forbidden：本任务明确禁用的视觉套路和内容占位

## 四大基础原则

每次生成或修改 UI 时，先用这四条自检：

1. **对齐** — 每个元素都有视觉锚点。文本左对齐、元素沿网格线排列、间距对称。不要随意放置。
2. **对比** — 用 size/weight/color 的明确差异建立层次。标题和正文的大小比至少 1.5:1，差异不够 = 没有层次。
3. **一致** — 间距、颜色、字体、圆角、阴影在整个页面使用统一 token。不造新值。
4. **聚合（Proximity）** — 相关元素靠近，无关元素拉远。用距离表达分组，不依赖边框和卡片。

→ 可执行检查表见 [layout-principles](refs/layout-principles.md)

## P0 Anti-slop Gate（交付前必须通过）

→ 完整规则见 [anti-ai-slop](refs/anti-ai-slop.md)

- 禁默认 Tailwind indigo/purple accent：`#6366f1`、`#4f46e5`、`#4338ca`、`#3730a3`、`#8b5cf6`、`#7c3aed`、`#a855f7`
- 禁两段式 trust gradient：purple→blue、blue→cyan、indigo→pink
- 禁 emoji 做 feature / UI icon
- 禁圆角卡片 + 左侧彩色粗边框
- 禁无来源指标：`10x faster`、`99.9% uptime`、`3x productive`
- 禁 filler copy：lorem ipsum、Feature One/Two/Three、placeholder text、sample content
- 禁颜色散落：颜色必须来自 token 或 token 派生值
- 禁用 `overflow-hidden` 掩盖文本溢出；真正修布局

## Overflow Contract

→ 详细规则见 [overflow](refs/overflow.md)

- flex/grid 子项承载文本时默认考虑 `min-width: 0`
- 长单词、URL、数字串、混排文本必须有安全换行策略
- 按钮和卡片不能靠固定宽高赌文案长度
- fixed canvas / deck / poster 先定义 content bounds，再放文字
- 内容超预算时拆 section/slide，不把正文缩到不可读

## Typography

→ 详细参考 [typography](refs/typography.md)

**DO**: 用 modular type scale + fluid sizing (`clamp()`) 建立字号层次
**DO**: 用字重和大小变化创造清晰的视觉层次
**DON'T**: 使用过度泛滥的字体 — Inter, Roboto, Arial, Open Sans, system defaults
**DON'T**: 用等宽字体作为"技术感"的偷懒手段
**DON'T**: 在每个标题上方放大圆角图标 — 看起来像模板

## Color

→ 详细参考 [color](refs/color.md)

**DO**: 使用 OKLCH 色彩空间（感知均匀）
**DO**: 给中性色加品牌色微调（tinted neutrals），哪怕 chroma 只有 0.01
**DON'T**: 灰色文字放在彩色背景上 — 用背景色的深色调代替
**DON'T**: 使用纯黑 #000 或纯白 #fff — 永远加一点色调
**DON'T**: 使用 AI 调色盘：cyan-on-dark、紫蓝渐变、霓虹暗底
**DON'T**: 渐变文字做"冲击力" — 装饰性而非功能性
**DON'T**: 默认暗色模式 + 发光强调色 — 不需要真正的设计决策就能"看起来酷"

## Layout & Space

→ 详细参考 [spatial](refs/spatial.md)

**DO**: 使用 4pt 基础间距系统（4, 8, 12, 16, 24, 32, 48, 64px）
**DO**: 用 varied spacing 创造节奏 — 紧密分组 + 宽松分隔
**DO**: 用 `clamp()` 做流体间距
**DON'T**: 把所有东西包在卡片里 — 不是所有内容都需要容器
**DON'T**: 卡片嵌套卡片 — 视觉噪音，扁平化层级
**DON'T**: 相同大小的卡片网格无限重复 — icon + heading + text 的模板
**DON'T**: 全部居中 — 左对齐 + 不对称布局更有设计感
**DON'T**: 到处使用相同间距 — 没有节奏的布局是单调的

## Visual Details

**DON'T**: 到处用 glassmorphism — 模糊效果、玻璃卡片、发光边框缺乏目的性
**DON'T**: 圆角元素 + 一侧粗彩色边框 — 偷懒的强调，几乎从不显得有意
**DON'T**: 用 sparkline 做装饰 — 看起来精致但不传达信息
**DON'T**: 圆角矩形 + 通用阴影 — 安全、无记忆点，典型 AI 输出
**DON'T**: 用 modal 除非真的没有更好的选择

## Motion

→ 详细参考 [motion](refs/motion.md)

**DO**: 用 exponential easing（ease-out-quart/quint/expo）做自然减速
**DO**: 对高度动画使用 `grid-template-rows` 而非直接动画 `height`
**DON'T**: 动画 layout 属性（width, height, padding, margin）— 只用 transform + opacity
**DON'T**: 使用 bounce 或 elastic easing — 过时且俗气，真实物体平滑减速

## Interaction

→ 详细参考 [interaction](refs/interaction.md)

**DO**: 每个交互元素设计 8 种状态（default/hover/focus/active/disabled/loading/error/success）
**DO**: 设计有意义的空状态 — 不只是"暂无内容"
**DON'T**: 不要把每个按钮都做成 primary — 用 ghost、text link、secondary 建立层级
**DON'T**: 重复用户已能看到的信息

## Responsive

→ 详细参考 [responsive](refs/responsive.md)

**DO**: 用 container queries 做组件级响应式
**DON'T**: 在移动端隐藏关键功能 — 适配界面，不要截肢

## UX Writing

→ 详细参考 [ux-writing](refs/ux-writing.md)

**DO**: 按钮文案用「动词 + 名词」— "保存更改" 而非 "确定"
**DO**: 错误信息回答三个问题：发生了什么？为什么？怎么修？

## Codex 反模式硬约束（信息密度优先，逐条照抄）

> 来源：OpenAI codex base_instructions / Frontend guidance。完整保留以避免漏项。

### Build with empathy

- 已有 design system 时严格沿用现有约定
- 设计需匹配应用受众与领域：SaaS / CRM / 运营工具应安静、实用、信息密集；游戏可表现化
- 通用工作流必须便捷高效、可在视图间无缝穿梭

### Controls & Icons

- 工具按钮带图标；颜色用 swatch；模式用 segmented control；二元设置用 toggle / checkbox；数值用 slider / stepper / input；选项集用 menu；视图用 tab；命令才用文字按钮
- 卡片圆角 ≤ 8px（除非现有 design system 要求）
- 能用熟悉符号 / 图标的不用圆角矩形 + 文字（撤销重做、加粗斜体、保存下载缩放）；不熟悉的图标 hover 显示 tooltip
- 优先 lucide 图标，其次现有库；不手画 SVG
- 不用页内可见文字描述功能、快捷键、视觉元素或如何使用应用

### Hero / Landing

- 不做 landing page，除非明确要求；要 site / app / game / tool 直接给可用体验
- Hero 用相关图片 / 生成位图 / 沉浸式全幅交互场景做背景，文字叠加（不在卡片里）
- 禁用 split text/media hero 卡片布局
- 禁用 hero 文字或主体放卡片
- 禁用 gradient / SVG hero 页
- 真实图片可用时不要 SVG hero illustration
- 品牌 / 产品 / 场所 / 作品集 / 对象页：品牌或主体必须出现在首屏首要位置，不能只在导航小字
- 任意 mobile / desktop 视口下，hero 必须留出下一节可见的提示
- landing hero 的 H1 = 品牌 / 产品 / 地点 / 人名 或 直白的 offer / 品类；价值主张放副文，不挤进 H1

### 视觉资源

- 网站和游戏必须使用视觉资产
- 可用图片搜索、相关图、生成位图，避免 SVG（除非游戏）
- 主图必须呈现真实产品 / 地点 / 物体 / 状态 / 玩法 / 人物
- 拒绝暗、模糊、裁切过度、stock-style、纯氛围照
- 高度具体的游戏资产用 SVG / Three.js 自定义

### Game / 引擎

- 有成熟规则 / 物理 / 解析 / AI 引擎库时直接用，不手写核心域逻辑（除非用户明示）

### 3D

- 用 Three.js
- 主 3D 场景 full-bleed 或无框，不放装饰卡 / 预览容器
- 完成前用 Playwright 跨视口截图 + canvas 像素检查：非空、构图正确、可交互 / 有动效、引用资产正确无重叠

### Card / Section 边界

- 不在卡片里嵌卡片
- 不把页面 section 做成浮动卡
- 卡片仅用于：可重复条目、modal、有真实边界的工具表面
- 页面 section 必须 full-width band 或无框布局，内容内收

### 装饰禁忌

- 不放离散 orb / 渐变 orb / bokeh blob 作装饰或背景

### 文本容器适配

- 文本必须在所有 mobile / desktop 视口适配父容器；不行就换行；仍不行用动态字号让最长词放下
- 文本不能遮挡前后内容
- 卡片 / 按钮内文本仍需看起来专业精致

### 显示文字与容器匹配

- hero 字号留给真 hero
- 紧凑面板 / 卡片 / 侧栏 / dashboard / 工具面用更小、更紧的标题

### 固定布局尺寸

- 棋盘 / 网格 / 工具栏 / 图标按钮 / 计数器 / 瓦片这类固定格式 UI，必须用 `aspect-ratio` / grid tracks / min-max / container-relative sizing 定稳
- 防 hover / label / icon / loading / 动态内容触发 reflow

### 字号 / 字距

- 不让字号随 viewport width 缩放
- letter-spacing = 0，不用负值

### 调色禁忌

- 避免单一色相主导整个 UI
- 避免主紫 / 紫蓝渐变占主导
- 避免米色 / 奶油 / 沙色 / 棕褐色主导
- 避免深蓝 / 石板蓝主导
- 避免棕橙 / 咖啡色主导
- 收稿前扫一遍 CSS 颜色，命中以上主调要改

### 重叠

- UI 元素与文字不能不连贯地重叠（极差体验）

## AI Slop Test

**关键质量检查**：如果你把这个界面展示给人，说"AI 做的"，他们会立刻相信吗？如果会，那就是问题。

回顾上面所有 DON'T — 它们是 2024-2025 年 AI 生成作品的指纹。

## Gotchas

- 不要把 dribbble 风格装饰当成设计质量；先保证层次、对齐、一致和可用性
- 不要为了“高级感”默认上暗色、玻璃、渐变、发光；没有信息价值的视觉效果只会显得廉价
- 组件单看顺眼不代表页面成立；必须从整体节奏、信息层级和状态覆盖重新检查
- 设计约束不是只审美化输出，落地时要和可访问性、响应式、实现成本一起判断

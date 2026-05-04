# Open Design UI Quality Integration Research

## 0. 结论

[事实] 当前仓库已有 `fe-ui-design`、`fe-ui-visual-iterate`、`guard-verify`、`guard-review`、`think-plan`、`commands/fe-audit.md` 等前端质量相关入口。

[事实] `open-design` 的高价值部分不是它的 daemon/Web/Electron runtime，而是这套设计质量机制：

```text
DESIGN.md
+ craft rules
+ direction package
+ seed/layout skeleton
+ P0/P1/P2 checklist
+ artifact linter
+ screenshot/preview feedback
```

[推断] 对当前 `.dotfiles` 体系，ROI 最高的路线是：**增强现有 FE skill 的设计契约、视觉验证和可执行检查；新增少量专职 skill；不要搬 open-design runtime 和全量 design-systems。**

推荐优先级：

| 优先级 | 动作 | 判断 |
|---|---|---|
| P0 | 增强 `fe-ui-design`、`fe-ui-visual-iterate`、`guard-verify` | 直接对应用户痛点，成本低 |
| P0 | 新增 `fe-ui-critique` | 补“生成后审美诊断”入口 |
| P1 | 新增 `fe-ui-design-system`、`fe-ui-lint-artifact` | 把设计从自由发挥变成 contract + lint |
| P1 | 增强 `think-plan`、`guard-review`、`commands/fe-audit.md` | 把 UI 约束前置到计划和 review |
| P2 | 增加 responsive/overflow 专项脚本或 skill | 适合后续工具化 |
| 不建议 | 集成 open-design daemon、SSE、SQLite、Electron | 体量过重，与当前 skill 体系边界不匹配 |

## 1. 调研范围与依据

### 当前仓库依据

- `skills/fe-ui-design/SKILL.md`
- `skills/fe-ui-design/refs/typography.md`
- `skills/fe-ui-design/refs/color.md`
- `skills/fe-ui-visual-iterate/SKILL.md`
- `skills/guard-verify/SKILL.md`
- `skills/guard-review/SKILL.md`
- `skills/think-plan/SKILL.md`
- `commands/fe-audit.md`
- `skills/catalog.json`
- `docs/software-engineering-research/codex-base-instructions.md`

### Open Design 依据

- `refs/nexu-io/open-design/docs/skills-protocol.md`
- `refs/nexu-io/open-design/design-systems/default/DESIGN.md`
- `refs/nexu-io/open-design/craft/anti-ai-slop.md`
- `refs/nexu-io/open-design/craft/typography.md`
- `refs/nexu-io/open-design/craft/color.md`
- `refs/nexu-io/open-design/apps/daemon/src/prompts/system.ts`
- `refs/nexu-io/open-design/apps/daemon/src/prompts/directions.ts`
- `refs/nexu-io/open-design/apps/daemon/src/lint-artifact.ts`
- `refs/nexu-io/open-design/skills/web-prototype/SKILL.md`
- `refs/nexu-io/open-design/skills/web-prototype/references/checklist.md`
- `refs/nexu-io/open-design/skills/mobile-app/references/checklist.md`
- `refs/nexu-io/open-design/skills/simple-deck/references/checklist.md`
- `refs/nexu-io/open-design/skills/pptx-html-fidelity-audit/SKILL.md`

## 2. 当前体系缺口

### 已经做得好的部分

[事实] `fe-ui-design` 已覆盖四大基础原则、typography、color、layout、motion、interaction、responsive、UX writing，并吸收了 Codex frontend guidance。

[事实] `fe-ui-visual-iterate` 已有真实浏览器截图、固定差异表、小步迭代、re-capture 门禁。

[事实] `commands/fe-audit.md` 已覆盖设计原则、AI 反模式、可访问性、响应式和 React 代码健康。

### 主要缺口

| 缺口 | 当前表现 | 影响 |
|---|---|---|
| 设计系统不是明确输入 | `fe-ui-design` 提到沿用 design system，但没有 `DESIGN.md` 风格 contract | LLM 仍会自由造颜色、间距、字体 |
| 缺少生成后 critique skill | 设计原则多，审美诊断入口弱 | “丑”无法被稳定转成可修复项 |
| 视觉验证未进入 `guard-verify` | `guard-verify` 偏 test/build/lint 与 L1/L2/L3 | UI 任务可能功能通过但视觉未验 |
| AI slop 缺自动化检查 | 主要靠自然语言提醒 | 默认紫色、emoji icon、filler copy 容易漏 |
| overflow/detail 没有专项 contract | `fe-ui-design` 有文本适配规则，但没有 viewport 证据表 | 文字溢出、按钮撑破、表格横滚常被漏掉 |
| `/fe-audit` 和 FE skills 规则分散 | command 与 skill 存在重叠 | 规则维护成本上升，agent 路由不稳定 |

## 3. 哪些 skill 需要增强

### P0: `fe-ui-design`

路径：`skills/fe-ui-design/SKILL.md`

#### 当前定位

[事实] 它是构建 web 组件、页面或应用界面时的主要设计规则入口。

#### 需要增强的原因

[推断] 它现在更像“原则汇总”，但 open-design 的强点是“设计契约 + craft + checklist + lint”。如果只继续堆原则，LLM 仍容易在实现时漂移。

#### 建议增强内容

1. **Design Contract 前置**

   每次 UI 任务先锁定：

   - surface：web / mobile / dashboard / deck / fixed canvas
   - audience：工具型 / 营销型 / 内容型 / 游戏型
   - direction：editorial / modern minimal / warm soft / tech utility / brutalist
   - tokens：bg、surface、fg、muted、border、accent、font-display、font-body
   - type scale：12 / 14 / 16 / 20 / 24 / 32 / 48 / 64
   - spacing scale：4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 80
   - accent budget：每屏最多 2 个可见 accent

2. **把反 AI slop 从提醒升级为 P0 checklist**

   来自 open-design 的高价值 P0：

   - 禁默认 Tailwind indigo：`#6366f1`、`#4f46e5`、`#4338ca`、`#3730a3`、`#8b5cf6`、`#7c3aed`、`#a855f7`
   - 禁两段式 trust gradient：purple to blue、blue to cyan、indigo to pink
   - 禁 emoji feature icons
   - 禁圆角卡片 + 左侧彩色边框
   - 禁 invented metrics
   - 禁 filler copy
   - 禁 raw hex 散落在 token block 之外

3. **增加 CRAP 原则的可执行表**

   当前有四原则，但需要变成检查项：

   | 原则 | 必查问题 |
   |---|---|
   | Proximity 亲密性 | 相关项是否比无关项更近；是否用距离表达分组 |
   | Alignment 对齐性 | 左边缘、基线、图标中心线、网格列是否一致 |
   | Repetition 重复性 | 同类组件是否复用 token、radius、border、state |
   | Contrast 对比性 | 主次层级是否靠 size/weight/color 明确区分 |

4. **把 refs 模块化**

   建议新增或拆出：

   - `skills/fe-ui-design/refs/design-contract.md`
   - `skills/fe-ui-design/refs/anti-ai-slop.md`
   - `skills/fe-ui-design/refs/layout-principles.md`
   - `skills/fe-ui-design/refs/overflow.md`

### P0: `fe-ui-visual-iterate`

路径：`skills/fe-ui-visual-iterate/SKILL.md`

#### 当前定位

[事实] 它用于对照参考图反复迭代 UI，并强制截图和差异表。

#### 需要增强的原因

[推断] 它已经解决“必须看真实页面”的问题，但差异表还偏视觉表层。用户明确提到的文字溢出、细节不对齐、亲密性、对齐性、重复性、对比性，应该成为固定行。

#### 建议增强内容

在 Diff 表中新增必填维度：

| 维度 | 检查 |
|---|---|
| 文本溢出 | 是否换行、截断、遮挡、按钮文案撑破、长单词撑破 |
| 横向滚动 | `document.documentElement.scrollWidth > innerWidth` 是否为 false |
| 对齐 | 左边缘、右边缘、图标文字中心线、表格列、按钮组是否一致 |
| 亲密性 | label/value、标题/正文、卡片内部元素是否成组 |
| 重复性 | 同类卡片、按钮、tag、状态、表单控件是否一致 |
| 对比性 | 标题/正文/辅助文本/CTA 是否有层级差 |
| 状态覆盖 | hover/focus/active/disabled/loading/error 是否覆盖关键控件 |
| 响应式 | 至少 mobile + desktop 两个 viewport 复拍 |

#### 新的停止条件

UI 任务不能只因为“截图看起来接近”停止。至少要满足：

- 当前目标 viewport 无横向滚动
- 聚焦区域无文本溢出
- 关键交互控件有 focus-visible
- 差异表中 CRAP 四项均为 `接近` 或有明确取舍理由

### P0: `guard-verify`

路径：`skills/guard-verify/SKILL.md`

#### 当前定位

[事实] 它要求交付前提供验证证据，强调 test/build/lint 与 L1/L2/L3。

#### 需要增强的原因

[推断] UI 改动的“可交付”不等于测试通过。视觉、响应式、overflow 需要证据，否则“完成”会过早。

#### 建议增强内容

增加 UI 任务分支：

```md
当 diff 涉及 UI/CSS/组件/页面时，验证证据必须包含：

- URL 或本地页面入口
- viewport 列表
- screenshot 路径
- DOM snapshot 路径或关键元素查询结果
- 无横向滚动检查结果
- 文本溢出检查结果
- 如果有参考图，附 `fe-ui-visual-iterate` 差异表
```

建议输出表：

| Check | Evidence |
|---|---|
| Screenshot | `/tmp/.../page.png` |
| Viewport | `390x844`, `1280x900` |
| Horizontal overflow | `scrollWidth <= innerWidth` |
| Text overflow | inspected focused selectors |
| Focus state | selector + screenshot/snapshot |

### P1: `think-plan`

路径：`skills/think-plan/SKILL.md`

#### 建议增强内容

UI 任务 plan 增加字段：

- 页面类型：app / dashboard / landing / docs / mobile / deck
- 受众与使用情境
- 设计系统来源：现有项目 / 用户提供 / 临时生成
- 视觉方向：5 选 1 或沿用项目
- 禁用项：渐变、glass、emoji icon、虚构指标、filler copy
- 验收方式：截图、viewport、overflow、状态覆盖

[推断] 这能从计划阶段减少“LLM 自由发挥”。

### P1: `guard-review`

路径：`skills/guard-review/SKILL.md`

#### 建议增强内容

当前 review 偏 correctness/architecture/security/test。建议在 diff 涉及 UI 时增加专项：

- 新增颜色是否来自 token
- 是否新增硬编码 magic spacing/radius/shadow
- 是否使用固定宽高导致 overflow
- 是否隐藏关键 mobile 功能
- 是否缺 focus-visible / reduced-motion
- 是否出现卡片嵌套、glass、紫色渐变、emoji icon
- 是否改动状态样式却没有覆盖 loading/error/disabled

### P1: `commands/fe-audit.md`

#### 当前定位

[事实] 它已经有前端审计维度和输出契约。

#### 建议增强内容

- 吸收 open-design `lint-artifact.ts` 的 greppy 检查清单。
- 明确 `/fe-audit` 与 `fe-ui-critique` 的边界：
  - `/fe-audit`：代码级 file:line 审计
  - `fe-ui-critique`：截图/页面级设计诊断
- 把 P0/P1/P2 严重度与 `fe-ui-design` 的 P0 checklist 对齐。

### P2: `think-quality`

路径：`skills/think-quality/SKILL.md`

#### 建议增强内容

增加 UI 可修改性检查：

- token 是否集中
- className 是否过长且不可复用
- 同类组件是否有多套样式
- 状态样式是否分散
- 响应式规则是否局部可推理
- 布局是否依赖脆弱 absolute positioning

### P2: `guard-check`

路径：`skills/guard-check/SKILL.md`

#### 建议增强内容

交付前编排时，如果 diff 命中 UI/CSS/React 页面：

```text
guard-check
→ guard-review UI 分支
→ fe-ui-visual-iterate 或 fe-ui-critique
→ guard-verify UI 分支
```

## 4. 哪些 skill 需要新增

### P0: 新增 `fe-ui-critique`

#### 定位

当已有页面、截图或实现需要设计诊断时使用；输出带证据的设计问题分级表，不默认改代码。

#### 为什么需要它

[事实] 当前 `fe-ui-design` 是生成前/实现中规则，`fe-ui-visual-iterate` 是对照参考图迭代。

[推断] 当用户说“这个设计很丑”“哪里不对劲”时，需要一个独立的 critique 入口，不应强行走参考图迭代。

#### 输入

- URL
- 截图路径
- 组件/文件路径
- 可选目标风格或设计系统

#### 输出契约

```md
## UI Critique

### Verdict
整体等级：A/B/C/D/F

### Findings
| Priority | Area | Evidence | Principle | Issue | Fix |
|---|---|---|---|---|---|
| P0 | Hero | screenshot region / selector | Contrast | 主 CTA 与次按钮层级不明显 | 降低次按钮视觉重量 |

### AI Slop Signals
...

### Fix Plan
1. ...
```

#### 检查维度

- 方向一致性
- 信息层级
- CRAP 四原则
- typography craft
- color/accent discipline
- AI slop
- responsive/overflow
- 状态与交互
- 内容真实性

### P1: 新增 `fe-ui-design-system`

#### 定位

当项目缺少明确视觉约束，或需要从现有 UI/品牌/截图中提取规则时使用；输出轻量 `DESIGN.md` 风格 contract。

#### 为什么需要它

[推断] LLM 设计丑的根因之一是没有风格 SSOT。没有设计系统时，它会回到训练集默认模板。

#### 输出最小 schema

```md
# <Design System Name>

## Visual Theme
...

## Tokens
- bg:
- surface:
- fg:
- muted:
- border:
- accent:

## Typography
- display:
- body:
- mono:
- scale:

## Layout
- max width:
- grid:
- spacing:

## Components
- buttons:
- cards:
- inputs:

## Do / Don't
...
```

#### 注意

不要直接搬 open-design 的 137 个 design system。当前高 ROI 是 schema 和默认模板，不是资产数量。

### P1: 新增 `fe-ui-lint-artifact`

#### 定位

当需要用确定性扫描发现 AI slop、硬编码 token、filler copy、overflow 风险时使用；输出 file:line 或 snippet 级报告。

#### 形式选择

有两种可选实现：

| 方案 | 成本 | 收益 | 推荐 |
|---|---:|---:|---|
| 先做 skill/checklist | 低 | 立即可用 | 推荐先做 |
| 再做脚本 `scripts/ui-lint-artifact.*` | 中 | 可自动化 | 第二阶段 |

#### 可检查项

- `#6366f1|#4f46e5|#8b5cf6|#7c3aed|#a855f7`
- `linear-gradient` 中的 purple/blue/cyan trust gradient
- emoji icons
- `lorem ipsum|placeholder text|feature one|sample content`
- invented metrics：`10x faster`、`99.9% uptime`、`3x productive`
- raw hex outside token block
- `overflow-hidden` 掩盖文字问题
- fixed width/height on text-heavy containers
- missing `focus-visible`
- missing `prefers-reduced-motion`

### P1: 新增 `fe-ui-responsive-overflow`

#### 定位

当页面出现或可能出现响应式、长文本、i18n、表格、按钮撑破问题时使用；通过多 viewport 截图和 DOM 检查输出 overflow 报告。

#### 检查 viewport

- mobile：`390x844`
- tablet：`768x1024`
- desktop：`1280x900`
- wide：`1440x1000`

#### 检查项

- `document.documentElement.scrollWidth > window.innerWidth`
- 可见文本是否被截断
- 关键按钮是否换行或撑破
- 表格/卡片是否破版
- sticky header/footer 是否遮挡内容
- long word、中文、英文、数字混排是否安全

### P2: 新增 `fe-ui-layout-principles`

#### 定位

当需要专项审查亲密性、对齐性、重复性、对比性时使用；输出 CRAP 原则表。

#### 是否必须新增

[推断] 不一定。这个能力也可以并入 `fe-ui-critique`。如果希望 skill 数量克制，先不新增独立 skill。

### P2: 新增 `fe-ui-artifact-contract`

#### 定位

当产物是 deck、poster、fixed canvas、HTML artifact 时使用；定义尺寸、rail、bounds、cursor layout、禁止 overflow 的契约。

#### 来源

`open-design/skills/pptx-html-fidelity-audit/SKILL.md` 中的 rail/cursor 思想：

- 先定义 `CONTENT_MAX_Y`
- 保留 header/footer rail
- 每个块通过 cursor 分配空间
- 超出即拆页，不缩到不可读

## 5. 如何解决 LLM 设计很丑

### 根因分析

| 根因 | 表现 | 解法 |
|---|---|---|
| 缺少设计系统 | 随机颜色、随机圆角、随机阴影 | `DESIGN.md` 风格 contract |
| 缺少方向选择 | 默认紫蓝渐变、玻璃、卡片网格 | 5 个 direction package |
| 从空白 CSS 开始 | 每个 section 临场发明 | seed/layout skeleton |
| 内容不真实 | filler copy、虚构指标 | content/data provenance gate |
| 装饰替代信息 | blob、orb、emoji、sparkline | anti-slop P0 lint |
| 无生成后 critique | 第一版直接交付 | `fe-ui-critique` + visual iterate |

### 推荐方案

#### 1. 先锁定 Design Contract

LLM 不应该先写 JSX/CSS。先写一个短 contract：

```md
Surface: dashboard
Audience: operations team
Direction: tech-utility
Tokens: ...
Grid: 12 columns, 1200px max
Accent budget: max 2 visible uses per screen
Forbidden: purple gradient, emoji icons, invented metrics
```

[推断] 这会显著减少“随便现代一点”的默认输出。

#### 2. 使用 5 个有限方向包

来自 open-design 的方向思想可以轻量化：

| Direction | 适用 |
|---|---|
| editorial | 内容、报告、品牌故事 |
| modern minimal | SaaS、工具、docs |
| warm soft | wellness、fintech、creator |
| tech utility | dashboard、developer tool、ops |
| brutalist experimental | agency、art、manifesto |

每个方向只需要：mood、font stack、palette、layout posture、禁用项。

#### 3. 强制“一个 decisive flourish”

open-design checklist 里有一个高信号规则：**只做一个决定性亮点**。

例子：

- 一个强排版标题
- 一个真实截图
- 一个产品特定微交互
- 一个具体数据视图
- 一个不像模板的 section

[推断] 这比堆 10 个视觉效果更能避免 AI 味。

#### 4. 内容真实性门禁

设计丑常常不是 CSS 丑，而是内容假：

- “Feature One / Two / Three”
- “10x faster”
- “99.9% uptime”
- “Get Started”
- “Lorem ipsum”

建议把这些升为 P0：没有来源就删除、标 `[placeholder]`，或向用户询问。

#### 5. 视觉资源策略

[推断] 对 landing、portfolio、game、product page，缺少真实视觉资产会让模型用抽象 SVG/blob 填空，从而显得廉价。

建议规则：

- 产品页优先真实产品截图
- 人物/地点/作品页优先真实图
- 图标优先现有 icon 库，禁 emoji
- 没有资产时，用结构和 typography 承担设计，不用 orb/blob 补洞

## 6. 如何解决 LLM 细节总是有问题

### 总原则

[推断] 细节错误不是靠“更认真”解决，而是靠 **layout contract + viewport evidence + deterministic lint** 解决。

### 6.1 文字溢出

#### 常见原因

- 按钮固定宽度
- card 固定高度
- flex 子项缺 `min-width: 0`
- 长英文/数字/URL 无换行策略
- absolute positioning 手填 `top`
- fixed canvas 没有 content bounds
- 中文/英文/i18n 文案长度未测

#### 规则

```md
Overflow Contract:
- text containers use min-width: 0 in flex/grid children
- long text has overflow-wrap: anywhere or safe wrapping policy
- buttons allow wrapping or have max-width strategy
- cards do not rely on fixed height for text content
- fixed canvas defines content bounds before placing text
- if content exceeds budget, split section/slide, do not shrink below readable size
```

#### 验证

- mobile + desktop 截图
- `scrollWidth <= innerWidth`
- 重点 selector 检查 `scrollWidth <= clientWidth` 或人工确认 wrap

### 6.2 对齐性

#### 常见原因

- 组件各自定义 padding
- 同类卡片没有共享 template
- `gap` 和 margin 混用
- 图标与文字 baseline 未对齐
- 表格列没有固定策略

#### 规则

- 页面先声明 grid：max-width、columns、gutter
- 同类组件共享 padding/radius/border token
- 禁 almost-aligned：要么严格对齐，要么明确 intentional offset
- icon + text 用 flex align center，并检查视觉中心

### 6.3 亲密性

#### 常见原因

- 所有间距都一样
- label 和 value 离得过远
- section 之间不够分离
- 用边框/卡片代替分组距离

#### 规则

- 相关项 gap < 无关项 gap
- group 内部 padding 固定
- section 间距至少是 group 间距的 2 倍
- 优先用 whitespace 表达分组，少加容器

### 6.4 重复性

#### 常见原因

- 每个 card 都有一套 className
- 状态样式散落
- 同一页面出现多个 radius/shadow/border 体系

#### 规则

- 同类组件只允许一套 visual grammar
- radius/shadow/border 从 token 出
- 重复 section 使用 rhythm，而不是复制模板到无聊

### 6.5 对比性

#### 常见原因

- 标题/正文大小差异太小
- 所有按钮都像 primary
- muted 文字过浅或过多
- accent 到处用，反而没有重点

#### 规则

- 标题和正文大小比至少 1.5:1
- primary/secondary/tertiary action 视觉层级分明
- 每屏一个主焦点
- accent 每屏最多 2 次
- body contrast 不能低于基本可读标准

## 7. 更多值得研究或落地的主题

### 7.1 Design system memory

[推断] 可以为常见项目沉淀轻量 `DESIGN.md`，让后续 UI 任务复用，而不是每次重建风格。

### 7.2 UI artifact lint

从 open-design `lint-artifact.ts` 抽规则，先做 grep checklist，再考虑脚本化。

### 7.3 Screenshot evidence standard

把 `fe-ui-visual-iterate` 的截图证据标准提升为所有 UI 交付的默认门槛。

### 7.4 Component skeleton library

不要让 LLM 每次发明布局。沉淀：

- dashboard shell
- settings page
- data table
- pricing page
- mobile onboarding
- deck slide
- empty/error/loading state

### 7.5 Content and data realism

建立规则：

- 没有来源的指标不写
- 示例数据必须标注 placeholder
- CTA 文案用“动词 + 名词”
- UI 文案不能重复用户已经能看到的信息

### 7.6 Accessibility as visual quality

A11y 不只是合规：

- 对比度影响层级
- focus-visible 影响可用性
- touch target 影响移动端视觉密度
- reduced-motion 影响动效策略

### 7.7 Responsive and i18n stress testing

专门测试：

- 长中文
- 长英文单词
- 数字/货币/日期
- RTL [未验证：当前体系是否需要 RTL，需按项目判断]
- mobile narrow viewport

### 7.8 Fixed-canvas/deck fidelity

对 PPT、海报、卡片、poster、固定比例 artifact，普通 responsive 规则不够。需要 rail、bounds、cursor、overflow error。

### 7.9 Visual regression integration

[推断] 如果未来要进入 CI，可接 Playwright screenshot、Storybook、Chromatic 或 Percy。但当前 `.dotfiles` 层更适合先做 inner-loop skill，不急着引入外部服务。

### 7.10 Design review rubric

建立统一评分：

- Direction fit
- Hierarchy
- Craft
- Usability
- Originality
- Detail reliability

## 8. 建议实施路线

### Phase 1: 低成本立即做

1. 更新 `fe-ui-design`
   - 增加 Design Contract
   - 增加 anti-slop P0 checklist
   - 增加 CRAP 检查表
2. 更新 `fe-ui-visual-iterate`
   - 差异表新增 overflow、CRAP、状态、响应式
3. 更新 `guard-verify`
   - UI 任务必须提供截图和 overflow 证据
4. 更新 `commands/fe-audit.md`
   - 加入 open-design lint-artifact 的 greppy 扫描项

### Phase 2: 新增少量 skill

1. 新增 `fe-ui-critique`
2. 新增 `fe-ui-design-system`
3. 新增 `fe-ui-lint-artifact`
4. 更新 `skills/catalog.json`
5. 跑 `python3 scripts/verify_skills.py`

### Phase 3: 工具化

1. 增加 overflow 检查脚本
2. 增加 grep 级 artifact lint 脚本
3. 与 `agent-browser` 截图链路联动
4. 将 UI 证据表接入 `guard-verify`

## 9. 不建议做的事

| 不建议 | 原因 |
|---|---|
| 搬 open-design daemon | 太重，涉及 Express/SSE/SQLite/agent spawn |
| 搬全量 design-systems | 137 个资产会增加噪音，维护成本高 |
| 搬 question-form UI runtime | 当前体系没有对应 UI 渲染面 |
| 搬完整 artifact save/lint endpoint | 当前不是 open-design 风格应用 runtime |
| 新增过多细粒度 skill | 路由复杂度上升，反而降低可用性 |

## 10. 最小可执行方案

如果只做一轮，我建议：

```text
1. fe-ui-design: 加 Design Contract + P0 anti-slop + CRAP gate
2. fe-ui-visual-iterate: 加 overflow/CRAP/状态/响应式差异行
3. guard-verify: UI 任务必须提供截图 + viewport + overflow 证据
4. 新增 fe-ui-critique: 负责无参考图时的设计诊断
```

[推断] 这四项覆盖用户提出的两个核心问题：

- LLM 设计丑：通过 design contract、direction、anti-slop、critique 解决。
- 细节总错：通过 visual iterate、overflow contract、CRAP gate、guard-verify 证据解决。

## 11. 后续验收标准

实施后，至少用 3 类 UI 任务验证：

| 任务 | 验证重点 |
|---|---|
| Dashboard | 信息密度、对齐、表格/数字、状态 |
| Landing page | 视觉方向、反 AI slop、真实内容 |
| Mobile UI | overflow、tap target、响应式、CTA 首屏 |

每类任务都应产出：

- 设计 contract
- 截图证据
- overflow 检查
- CRAP 检查结果
- P0 anti-slop 检查结果

---
description: 上线前、重构后、设计走查时使用的前端质量审计命令；输出带 file:line 的修复清单。
argument-hint: <文件/目录/留空=当前项目>
---

# Frontend Audit

## 0. 适用场景

适用于以下场景：

- 页面准备上线或提 PR 前，做一次前端质量走查
- 用户反馈“界面像 AI 拼出来的”“层次乱”“可访问性差”
- 设计/实现重构后，需要快速找出优先修复项

不适用于以下场景：

- 纯后端/CLI/非 UI 任务
- 明确是功能 bug 定位，应该先 `/dev-debug`
- 明确是 React 运行时问题，应该优先结合 `react-doctor`

## 1. 确定范围

解析 `$ARGUMENTS`：

- 文件或目录路径 → 审查指定范围
- 留空 → 审查当前项目中的前端代码（自动检测 src/、app/、pages/、components/ 等）

识别项目类型（React/Vue/Svelte/纯 HTML 等）和使用的 CSS 方案（Tailwind/CSS Modules/styled-components 等）。

## 2. 审查维度

### 设计原则（逐条检查）

| 原则 | 检查方式 |
|------|---------|
| 对齐 | 元素是否沿网格线排列？文本对齐是否一致？ |
| 对比 | 标题/正文大小比是否 >= 1.5:1？是否用了多维度对比（size+weight+color）？ |
| 一致 | 间距/颜色/圆角/阴影是否使用统一 token？有没有散落的 magic number？ |
| 聚合 | 相关元素间距是否小于无关元素间距？分组是否靠距离而非多余边框？ |
| 层次 | 做模糊测试（Squint Test）：模糊后能否识别最重要/次重要元素和分组？ |

### AI 反模式扫描

Grep 代码库检查以下 AI 典型指纹：

- 字体：Inter, Roboto, Open Sans 作为主字体
- 颜色：`purple`/`violet`/`indigo` 渐变、cyan-on-dark、纯黑 `#000`/`#000000`
- 布局：卡片嵌套卡片、相同卡片网格无限重复
- 动画：`bounce`/`elastic` easing
- 视觉：glassmorphism（`backdrop-filter: blur`）、渐变文字、一侧粗彩色边框
- 交互：过度使用 modal

### Open Design 风格 P0 扫描

把以下命中作为 P0/P1 候选，必须结合上下文确认后报告 `file:line`：

```bash
rg '#6366f1|#4f46e5|#4338ca|#3730a3|#8b5cf6|#7c3aed|#a855f7' <scope>
rg 'linear-gradient|purple|violet|indigo|cyan' -i <scope>
rg '✨|🚀|🎯|⚡|🔥|💡|✅|⭐' <scope>
rg 'lorem ipsum|placeholder text|sample content|feature one|feature two|feature three' -i <scope>
rg '10x faster|10× faster|99\\.9% uptime|3x productive|3× productive' -i <scope>
rg 'overflow-hidden|backdrop-filter|scrollIntoView' <scope>
```

严重度建议：

| 发现 | 严重度 |
|---|---|
| 默认 indigo/purple accent、trust gradient、emoji icon、filler copy、无来源指标 | P0/P1 |
| raw hex 大量散落、accent 过度使用、placeholder 图片 CDN | P1/P2 |
| decorative blob/orb、卡片嵌套、玻璃拟态泛滥 | P2 |

### 可访问性

- 文本对比度是否达到 WCAG AA（正文 4.5:1，大文本 3:1）
- 交互元素是否有 `:focus-visible` 样式
- 图片是否有 `alt` 属性
- 表单是否有 `<label>`（不只是 placeholder）
- 触控目标是否 >= 44px
- 是否有 `prefers-reduced-motion` 处理

### 响应式

- 是否有移动端适配（media query 或 container query）
- 触控目标尺寸
- `viewport-fit=cover` 和 safe area 处理
- 图片是否用了 `srcset` / `<picture>`

### 代码健康

检测项目类型后执行：

- **React 项目**：调用 `npx react-doctor@latest . --verbose` 获取健康评分
- **React 项目**：调用 `npx -y react-doctor@latest . --verbose --diff` 获取健康评分
- **所有项目**：检查 CSS 中的 magic number、!important 泛滥、过深嵌套（> 4 层）

## 2.1 输出契约

最终报告必须满足：

- 给出总评（A/B/C/D/F）
- 每条发现都有 `file:line`
- 每条发现都有明确修复建议
- 修复计划按优先级排序，优先处理 P0/P1
- React 项目若运行了 `react-doctor`，要显式引用结果而不是重复造轮子

## 3. 输出报告

```
## 审计结果

### 总分
[基于发现的问题数量和严重度给出 A/B/C/D/F 评级]

### P0 — 必须修复
- [维度] file:line — 问题 — 修复建议

### P1 — 应该修复
- ...

### P2 — 建议修复
- ...

### P3 — 可改进
- ...

### 亮点
[做得好的地方，具体到 file:line]

### 修复计划
按优先级排列的修复步骤，每步包含具体代码修改建议
```

## 严重度定义

| 级别 | 标准 |
|------|------|
| P0 | 可访问性违规、功能性问题 |
| P1 | 设计原则严重违反（无层次、无对齐） |
| P2 | AI 反模式、一致性问题 |
| P3 | 微调建议（字体优化、间距细化） |

## 规则

- 每条发现必须有 file:line 和具体修复建议
- 不报告"可以更好"的泛泛意见 — 要指出具体问题
- 先 Grep 确认后报告，不凭印象
- React 项目的代码健康检查优先使用 react-doctor，不重复造轮子

## Gotchas

- 不要把个人审美偏好当成审计结论；优先报告可验证的问题
- 没有证据的“像 AI 味道”不算发现，必须落到具体代码或界面结构
- 发现很多问题时，先排序，不要把所有建议都堆成同一优先级

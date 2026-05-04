# Layout Principles

把亲密性、对齐性、重复性、对比性转成可审查证据。

## 检查表

| 原则 | Pass 标准 | 常见失败 |
|---|---|---|
| 亲密性 | 相关项距离小于无关项，group 内部 padding 稳定 | label/value 分离、section 间距和组内间距相同 |
| 对齐性 | 文本、按钮、卡片、媒体沿清晰网格或边缘排列 | almost-aligned、图标文字中心线漂移、列宽随机 |
| 重复性 | 同类组件复用 token、radius、border、state | 每张卡片一套 class、状态样式散落 |
| 对比性 | 主焦点明确，标题/正文/辅助信息有 size/weight/color 差异 | 所有按钮都像 primary，accent 泛滥 |

## 规则

- 相关项 gap 应小于无关项 gap；section gap 至少是 group gap 的 2 倍。
- 页面先声明 grid：max-width、columns、gutters，再摆内容。
- 同类组件只允许一套 visual grammar；变化来自内容和状态，不来自随机样式。
- 每屏一个主焦点；primary/secondary/tertiary action 视觉层级必须不同。
- 用 whitespace 表达分组，少用边框和卡片堆叠。

## 输出格式

```md
| Principle | Status | Evidence | Fix |
|---|---|---|---|
| Proximity | pass/warn/fail | selector / screenshot region / file:line | ... |
| Alignment | ... | ... | ... |
| Repetition | ... | ... | ... |
| Contrast | ... | ... | ... |
```

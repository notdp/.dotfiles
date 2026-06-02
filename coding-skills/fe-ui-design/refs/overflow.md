# Overflow Contract

文字溢出、按钮撑破、表格横滚和 fixed-canvas 裁切必须作为布局问题处理，不能靠遮罩掩盖。

## Web / app UI

- flex/grid 子项包含文本时，默认需要 `min-width: 0`。
- 长英文、URL、数字串、代码片段使用安全换行：`overflow-wrap: anywhere`、`word-break` 或组件级 truncation 策略。
- 按钮允许文案换行或有明确 max-width；不要固定宽度赌文案长度。
- 卡片不要用固定高度承载可变文本；用 min-height、内容流或 clamp。
- 表格在窄屏要有明确策略：横向滚动容器、列折叠、卡片化或隐藏低优先级列。
- sticky header/footer 不得遮挡可交互内容。

## Fixed canvas / deck / poster

- 先定义 canvas、header rail、footer rail、content bounds。
- 每个块必须在 content bounds 内；超出就拆页/拆屏。
- 不把正文缩到不可读尺寸来塞内容。
- 避免手填 absolute `top`；能用 flow/cursor layout 就不用随机坐标。

## 验证

至少检查：

- mobile viewport：约 `390x844`
- desktop viewport：约 `1280x900`
- `document.documentElement.scrollWidth <= window.innerWidth`
- 聚焦区域中关键文本未被截断、遮挡或撑破容器

## 失败报告

```md
| Viewport | Selector/Area | Problem | Evidence | Fix |
|---|---|---|---|---|
| 390x844 | .cta | button text wraps badly | screenshot path | allow wrap + wider container |
```

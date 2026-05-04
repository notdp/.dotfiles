# Anti AI Slop

这些是可检查的 P0/P1 规则，不是个人审美偏好。命中 P0 时先修再交付。

## P0 must fix

- **Default indigo/purple accent**：禁止硬编码 `#6366f1`、`#4f46e5`、`#4338ca`、`#3730a3`、`#8b5cf6`、`#7c3aed`、`#a855f7`。使用 `var(--accent)`。
- **Trust gradient**：禁止 purple→blue、blue→cyan、indigo→pink 的两段式 hero gradient。用 flat surface + 排版层级。
- **Emoji feature icons**：禁止 `✨`、`🚀`、`🎯`、`⚡`、`🔥`、`💡` 等出现在 heading、button、list item、icon 容器中。用现有 icon 库或 `currentColor` SVG。
- **AI dashboard tile**：禁止圆角卡片 + 左侧彩色粗边框。去掉 radius 或改成正常状态条。
- **Invented metrics**：禁止无来源的 `10x faster`、`99.9% uptime`、`3x productive`。来自用户/数据源，或标注 placeholder。
- **Filler copy**：禁止 lorem ipsum、Feature One/Two/Three、placeholder text、sample content。空内容应该删掉或向用户询问。
- **Scattered colors**：颜色来自 token 或 token 派生值，不在组件内随手造 hex。
- **Overflow masking**：禁止用 `overflow-hidden` 掩盖文字溢出，除非是明确的视觉裁切且提供 tooltip/展开路径。

## P1 should fix

- Hero→Features→Pricing→FAQ→CTA 全套模板无变化。
- 外部 placeholder 图片 CDN：`placehold.co`、`picsum.photos`、`unsplash.com` 等。
- `var(--accent)` 每屏使用 3 次以上。
- 同屏超过 3 个主要字号。
- 装饰性 blob、orb、wave SVG 背景。
- 卡片嵌套卡片、全页玻璃拟态、无意义发光边框。

## Grep hints

```bash
rg '#6366f1|#4f46e5|#4338ca|#3730a3|#8b5cf6|#7c3aed|#a855f7'
rg 'linear-gradient|purple|violet|cyan|indigo' -i
rg '✨|🚀|🎯|⚡|🔥|💡|✅|⭐'
rg 'lorem ipsum|placeholder text|sample content|feature one|feature two|feature three' -i
rg '10x faster|10× faster|99\\.9% uptime|3x productive|3× productive' -i
```

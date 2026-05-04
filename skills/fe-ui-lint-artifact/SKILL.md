---
name: fe-ui-lint-artifact
description: 当需要确定性扫描 UI artifact、HTML/CSS/组件代码中的 AI slop、硬编码 token、filler copy 或溢出风险时使用；输出分级 finding 表和可执行修复建议。
---

# UI Artifact Lint

用 grep / DOM / 代码扫描找确定性视觉质量问题。它不替代设计审查，只负责低成本、可复现的信号。

## 范围

适用于：

- HTML artifact
- React/Vue/Svelte 组件
- CSS / Tailwind class
- landing、dashboard、mobile screen、deck HTML

不适用于：

- 纯后端代码
- 需要主观判断的整体审美评价，转 `/fe-ui-critique`
- 对照参考图迭代，转 `/fe-ui-visual-iterate`

## 扫描项

### P0 candidates

```bash
rg '#6366f1|#4f46e5|#4338ca|#3730a3|#8b5cf6|#7c3aed|#a855f7' <scope>
rg 'linear-gradient|purple|violet|indigo|cyan' -i <scope>
rg '✨|🚀|🎯|⚡|🔥|💡|✅|⭐' <scope>
rg 'lorem ipsum|placeholder text|sample content|feature one|feature two|feature three' -i <scope>
rg '10x faster|10× faster|99\\.9% uptime|3x productive|3× productive' -i <scope>
```

### P1 candidates

```bash
rg 'overflow-hidden|truncate|line-clamp|white-space:\\s*nowrap' <scope>
rg 'backdrop-filter|blur\\(|drop-shadow|shadow-2xl|shadow-xl' <scope>
rg 'placehold\\.co|picsum\\.photos|placekitten|unsplash\\.com' -i <scope>
rg 'scrollIntoView' <scope>
rg '#[0-9a-fA-F]{3,8}' <scope>
```

### P2 candidates

```bash
rg '!important|z-\\[|w-\\[|h-\\[|text-\\[|rounded-\\[' <scope>
rg 'modal|dialog|drawer' -i <scope>
```

## 输出契约

```markdown
## UI Artifact Lint

### Scope
- <path / url / artifact>

### Findings
| Priority | ID | Evidence | Issue | Fix |
|---|---|---|---|---|
| P0 | ai-default-indigo | path:line/snippet | ... | ... |

### False positives checked
- ...

### Next
1. ...
```

## 规则

- Grep 命中只是候选；报告前必须看上下文。
- 每条 finding 必须有 `file:line` 或 snippet。
- 如果颜色在 `:root` / theme token 中定义且由 design system 明确要求，不报默认色问题；下游应使用 token。
- `overflow-hidden` 只有在装饰性裁切、可访问替代明确时才允许。
- 不用“像 AI”作为 issue；必须指出具体模式。

## 关联技能

- 设计诊断 → `/fe-ui-critique`
- 生成/修改 UI → `/fe-ui-design`
- 前端代码审计 → `/fe-audit`

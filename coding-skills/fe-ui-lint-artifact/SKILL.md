---
name: fe-ui-lint-artifact
description: 当需要确定性扫描 UI artifact、HTML/CSS/组件代码中的 AI slop、硬编码 token、filler copy 或溢出风险时使用；输出分级 finding 表和可执行修复建议。
---

# UI Artifact Lint

用脚本 / grep / DOM / 代码扫描找确定性视觉质量问题。它不替代设计审查，只负责低成本、可复现的信号。

优先运行仓库 scanner：

```bash
python3 ${HOME}/.dotfiles/scripts/scan_ui_artifact.py <scope>
python3 ${HOME}/.dotfiles/scripts/scan_ui_artifact.py --format json <scope>
```

没有脚本或目标不在仓库内时，再降级使用下面的 grep 候选清单。

> 本 scanner 扫的是 **HTML/CSS/组件文本层** 的 slop。若目标是 **DESIGN.md 视觉契约本身**（token 图语义：断引用 / section 顺序 / 孤儿 token / WCAG 对比），用正交的另一层校验器：
> ```bash
> python3 ${HOME}/.dotfiles/scripts/lint_design_md.py <DESIGN.md> [--json]
> ```
> 两者互补不重叠：本脚本看渲染产物，`lint_design_md.py` 看契约的 token-graph。

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
rg 'text-decoration:\\s*underline|<u>|\\bunderline\\b' <scope>   # 标题加下划线（h1-h6 命中需人工确认）
rg 'text-align:\\s*center|\\btext-center\\b' <scope>             # 长正文/段落容器居中（标题/按钮居中是合理的，需人工判断范围）
```

> [!NOTE]
> 上面两条（标题下划线、正文居中）是手动 rg 项，命中需人工判断；**不**进 `${HOME}/.dotfiles/scripts/scan_ui_artifact.py` 的 gating 规则（居中/下划线正则误报率高）。来源吸收：`docs/refs-absorption-plan-2026-06-02.md` A9。

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

脚本 JSON 输出契约：

```json
{
  "findings": [
    {
      "priority": "P0|P1|P2",
      "id": "finding-id",
      "file": "path",
      "line": 1,
      "snippet": "source line",
      "issue": "why this matters",
      "fix": "actionable fix"
    }
  ]
}
```

## 规则

- Grep 命中只是候选；报告前必须看上下文。
- 每条 finding 必须有 `file:line` 或 snippet。
- 如果颜色在 `:root` / theme token 中定义且由 design system 明确要求，不报默认色问题；下游应使用 token。
- `overflow-hidden` 只有在装饰性裁切、可访问替代明确时才允许。
- 不用“像 AI”作为 issue；必须指出具体模式。

## Verification

- Scanner 变更后运行 `python3 -m unittest scripts.tests.test_scan_ui_artifact -v`。
- Skill 文档变更后运行 `python3 ${HOME}/.dotfiles/scripts/verify_skills.py`。
- 交付前至少保留一个 JSON 或 Markdown scanner 输出作为 deterministic evidence。

## 关联技能

- 设计诊断 → `/fe-ui-critique`
- 生成/修改 UI → `/fe-ui-design`
- 前端代码审计 → `/fe-audit`
- DESIGN.md token 图语义校验 → `${HOME}/.dotfiles/scripts/lint_design_md.py`（与本 scanner 正交）

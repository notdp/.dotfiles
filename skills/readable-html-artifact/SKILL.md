---
name: readable-html-artifact
description: 当需要从 Markdown SSOT 生成或刷新 HTML companion artifact 且不让完整 HTML 进入主上下文时使用；通过脚本或隔离 worker 产出路径、摘要和验证证据。
argument-hint: <source.md> <output.html> [profile]
---

# Readable HTML Artifact

## Goal

从 Markdown SSOT 生成本地 HTML companion，让浏览器承担展示负载，主 agent 只保留路径、摘要和验证证据。

不算完成：

- 只在聊天里贴 HTML。
- HTML 成为唯一事实源。
- 生成后没有验证 source / output / 转义行为。

## Input

| 字段 | 要求 |
|---|---|
| `source_md` | 已存在的 Markdown SSOT 文件 |
| `output_html` | 要写入的 HTML artifact 路径 |
| `profile` | `generic` / `plan` / `research` |
| `title` | 可选；不传则由 source 第一个 H1 推断 |

## Flow

1. 确认 `source_md` 是文件，且 Markdown 是结论 SSOT。
2. 优先运行仓库根脚本：

   ```bash
   python3 scripts/render_html_artifact.py --source <source.md> --output <output.html> --profile <generic|plan|research>
   ```

3. 若平台支持隔离子任务，可派发“隔离生成任务”，但必须使用 `references/worker-contract.md` 的输入输出契约。
4. 不支持子任务的平台直接运行脚本；不要为了兼容性引入 Droid-only 或 Codex-only 入口。
5. 最终只返回 source path、HTML path、验证结果、已知风险；不要返回完整 HTML。

## Cross-agent rules

- 子任务派发使用“派发隔离生成任务”这种通用描述，不写 Droid `Task`、missions 或平台专属语法。
- 工具名使用 Read / Edit / Execute 等通用概念；实现细节由当前 agent 映射。
- 路径默认相对 repo root；不要依赖 `.factory`、`~/.factory` 或某个 agent 的私有目录。
- 并行子任务不可用时，降级为主流程顺序执行脚本。

## Risk / Evidence

风险：

- HTML 全文进入主上下文会抵消本 skill 的价值。
- raw HTML / JS 如果未转义，可能在本地预览中执行。
- HTML 与 Markdown 分叉会制造双 SSOT。

必须给出证据：

- renderer stdout 中的 `wrote <output>`。
- source path 与 output path。
- 若输入包含 `<script>`、尖括号或代码块，确认输出中被转义。
- 若跳过浏览器预览，说明原因。

## Output Format

```markdown
## HTML Artifact

| Field | Value |
|---|---|
| Source | `<source.md>` |
| Output | `<output.html>` |
| Profile | `<profile>` |
| Validation | `<command/result>` |

Known gaps:
- <none or concise list>
```

## References

- `references/worker-contract.md` — 隔离 worker 的跨 agent 契约。
- `scripts/render_html_artifact.py` — Markdown SSOT 到静态 HTML 的确定性 renderer。

## Gotchas

- 不要把 Markdown 原文整段再复制进最终回复；给路径即可。
- 不要在调用方 skill 里重新手写 HTML 模板。
- 不要让 HTML 反向修改 Markdown，除非用户明确要求。

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
2. 先把路径拆成两个概念，不要把目标项目 root 当成 renderer 所在位置：

   - `target_repo_root`：`source_md` / `output_html` 所在项目，用于相对路径、报告和 SSOT 归属。
   - `renderer_path`：实际执行的 renderer 脚本路径，独立于目标项目。
   - 相对 `source_md` / `output_html` 默认按当前工作目录解析；解析后再用 `git -C <source_or_output_parent> rev-parse --show-toplevel` 找目标项目。
   - 若无法定位 `target_repo_root`，仍可用绝对 `source_md` / `output_html` 生成，但最终报告要写明“无法定位 target repo root”。

3. 按顺序解析 `renderer_path`，只要找到第一个存在的绝对路径就使用：

   1. `<target_repo_root>/scripts/render_html_artifact.py`，允许目标项目覆盖 renderer。
   2. `<skill_dir>/render_html_artifact.py`，即随本 skill 一起安装的 wrapper。
   3. `<skill_dir>/../../scripts/render_html_artifact.py`，即在 dotfiles 源仓库内开发本 skill 时的 renderer。

   只有这些绝对路径都检查过仍不存在时，才能报告 renderer 缺失；不要因为目标项目没有 `${HOME}/.dotfiles/scripts/render_html_artifact.py` 就向用户询问是否临时生成 HTML。

4. 运行已解析的 renderer：

   ```bash
   python3 "<renderer_path>" --source <source.md> --output <output.html> --profile <generic|plan|research>
   ```

5. 若平台支持隔离子任务，可派发“隔离生成任务”，但必须使用 `references/worker-contract.md` 的输入输出契约。
6. 不支持子任务的平台直接运行脚本；不要为了兼容性引入 Droid-only 或 Codex-only 入口。
7. 最终只返回 source path、HTML path、target repo root、renderer path、验证结果、已知风险；不要返回完整 HTML。

## Cross-agent rules

- 子任务派发使用“派发隔离生成任务”这种通用描述，不写 Droid `Task`、missions 或平台专属语法。
- 工具名使用 Read / Edit / Execute 等通用概念；实现细节由当前 agent 映射。
- `source_md` / `output_html` 可以相对当前工作目录，但 renderer 调用必须使用已解析的 `renderer_path`；不要把目标项目的 repo root 当成 renderer root。
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
| Target repo root | `<target_repo_root or unresolved>` |
| Renderer | `<renderer_path>` |
| Validation | `<command/result>` |

Known gaps:
- <none or concise list>
```

## References

- `references/worker-contract.md` — 隔离 worker 的跨 agent 契约。
- `${HOME}/.dotfiles/scripts/render_html_artifact.py` — Markdown SSOT 到静态 HTML 的确定性 renderer。

## Gotchas

- 不要把 Markdown 原文整段再复制进最终回复；给路径即可。
- 不要在调用方 skill 里重新手写 HTML 模板。
- 不要让 HTML 反向修改 Markdown，除非用户明确要求。

# Learnings Store

本目录是本仓库的 learning note 统一落点（canonical store）。`/assist-learn` 产出的可复用经验写在这里，`skills/assist-learn/scripts/learnings_search.py` 从这里按 frontmatter + 关键词检索。

吸收来源：`docs/refs-details/EveryInc/compound-engineering-plugin.md`（compound 的 `docs/solutions/` + grep-first 检索）。保守版：opt-in 检索，不 always-on 自动注入。

## 约定

- 一条经验一个文件：`docs/learnings/<category>/<slug>.md`，category 自取（如 `hooks`、`refactor`、`tooling`）。
- 顶部 frontmatter 用于检索，字段见 `skills/assist-learn/templates/learning-note.md`：
  - `title`、`date`（scaffold 自动填）
  - `problem_type`：`bug | knowledge | pattern | decision`（可选）
  - `module` / `component` / `tags`（可选，便于检索）
- 正文沿用 learning-note 模板（Context / Outcome / Reusable Pattern / Evidence / Follow-ups）。

## 用法

- 写入：`/assist-learn` → 产出 note → 落到本目录对应 category。
- 检索（opt-in，开工前可选）：`python3 skills/assist-learn/scripts/learnings_search.py <关键词...>`，默认搜 `./docs/learnings`，返回 top 命中的路径 + frontmatter 摘要，不展开全文。

## 边界

- 检索是 opt-in 工具，不是 always-on 注入到每个流程（保守，稳定优先）。
- store 是 per-project：在其它项目运行 `/assist-learn` 时落点是那个项目的 `docs/learnings/`。

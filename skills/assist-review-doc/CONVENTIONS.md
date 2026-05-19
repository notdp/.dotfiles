# assist-review-doc Conventions

机器约束。`SKILL.md` 引用本文件，agent 在生成、编辑、消费 review-managed 文档时必须遵守。

## 数据模型（comments.json schema v1）

```json
{
  "schema_version": 1,
  "spec_file": "docs/.../doc.md",
  "review_version": 3,
  "anchors": {
    "<anchor-id>": {
      "heading": "原始 heading 文本",
      "comments": [
        {
          "id": "c-<timestamp>-<anchor>-<n>",
          "role": "user" | "agent",
          "status": "open" | "resolved" | "answered" | "moved",
          "classification": "blocker" | "question" | "nit" | "idea" | null,
          "text": "评论正文",
          "response": "agent 回应（user-role 评论被消费后填写）",
          "created_in_version": 2,
          "resolved_in_version": 3
        }
      ]
    }
  }
}
```

- `comments.json` **必须进 git**，与 `<doc>.md` 并列，文件名 `<doc>.comments.json`
- 渲染产物 `<doc>.review.html` **不进 git**（从 MD + comments 派生），加入 `.gitignore` 或仓库级 ignore 模式
- schema 演进必须经过 `scripts/review_doc_migrate.py`，不允许 ad-hoc 字段加减

## 编辑 review-managed 文档时的硬约束

1. **不裸用 blockquote**。所有引用、注意、警告一律走 GFM alert（`> [!NOTE]` / `> [!WARNING]` / `> [!TIP]` / `> [!IMPORTANT]`）。裸 `>` 在协议里语义保留给"已解决评论的痕迹"和（未来扩展的）内联评论。
2. **不改 heading 文本**，一旦该文件出现过 `[review:anchor` commit。heading 是 anchor ID 的源；改 heading = 改 ID = 评论孤立。要改必须显式 rename 流程：先把旧评论 resolve 或迁移到新 ID，再改。
3. **不删 `## Backlog` 区**。即使为空也保留，让 idea 类评论有归属。

## anchor ID 生成

- 来自 heading 文本：`slugify_heading()` 在 `scripts/review_doc_ids.py`
- 同名 heading 自动加数字后缀（`foo`、`foo-2`、`foo-3`）
- 中文、ASCII、混合都接受；标点和空白统一压成 `-`

## commit 协议

baseline 与每轮处理后 commit，message 必须含 `[review:anchor v{N}]` 或 `[review:v{N}]`：

```
[review:anchor v0] <doc>: initial baseline
[review:v3] <doc>: 5blocker 2question 1nit 3idea→backlog
```

- review 期间用户不要手 commit 该 doc；如果检测到 baseline 之后有非 anchor commit，agent 必须停下让用户先确认
- 消费完毕的 commit 同时含 `<doc>.md` + `<doc>.comments.json`

## Role 字段语义

| role | 谁写 | 谁应答 | UI 渲染 |
|---|---|---|---|
| `user` | 用户在浏览器里 | agent 在下一轮消费时填 `response` | 蓝色背景 |
| `agent` | agent 在 use case B 提问时 | 用户在浏览器里写新评论作为回答 | 黄色背景 |

Use case B 的 agent 评论也走同一个 `comments.json` schema，区别只在 `role` 字段。Agent 在 spec.md 同 anchor 下方插入 `> [!QUESTION]` 形式的提问标记是可选的视觉提示，不是协议要求。

## 边界

- 段落级评论归属不支持，只到 heading 级
- 跨文件评论不支持，每个文件独立一个 comments.json
- 多人协作不支持（升级走 GitHub PR review）

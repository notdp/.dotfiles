---
name: pr-polish
description: 去掉当前 PR 或分支中文字的机器味。当用户说 polish PR、改 PR 文案、砍废话，或要求重写 PR、commit、注释、文档、测试名、behavior anchor 时使用。读懂 diff，保留事实，不改行为。
---

# PR polish

先读完整 diff，再像一个靠谱的维护者那样重写本次改动里的文字：

- 说代码现在做什么，不复盘修改过程，不展示推理。
- 代码已经说清楚的注释直接删。
- 保留事实、约束和不确定性；删套话、重复、夸张和硬凑的用户价值。
- 注释写为什么，测试名写行为，PR 和 commit 写实际变化。
- 用仓库里的说法，说人话。只给一个终稿，不给选项。

只动当前 PR 的文字。保留 PR 要求的固定 section；不要改业务逻辑，也不要擅自重写已发布的 commit。

直接落地修改。涉及 live PR、commit 或 push 时使用 `ce-commit-push-pr`。改完重读 diff，运行 `git diff --check`；只有测试名或 anchor 变动时才补对应校验。

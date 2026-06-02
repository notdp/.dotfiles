# Phase 2 改造提案（待裁决）

> 6 个 skill 正文/模板改动的提案。每条标了**现有覆盖**(事实) / **真正增量** / **拟改措辞** / **风险** / **我的建议**。
> 关键背景：经现状采集，多项的核心机制本仓库**已存在**，真正净增量比计划预想小。请逐条裁决：`approve` / `trim`(只取增量) / `reject`(已覆盖不做)。
> 来源：`docs/refs-absorption-plan-2026-06-02.md` A6/A7/A8/A9/A15/A16。

---

## 决策点 1 — A6 六段式 mistake 模板

- **落点**：新增 `skills/assist-retrospect/templates/mistake-note.md`
- **现有覆盖**（事实）：`assist-retrospect/SKILL.md:119-155` 已有 8 段固定复盘产物结构（事件还原→…→行动项表），比六段更全。无 templates/ 目录。
- **真正增量**：现有 8 段是**深度复盘**产物；缺一个**轻量快记**模板——小失误不值得走完整苏格拉底式复盘时，用 6 字段快速落盘。
- **拟改措辞**（新文件，轻量、明确区别于完整复盘）：
  ```markdown
  # Mistake Note（轻量快记，非完整复盘）
  > 小失误快速落盘用；够深的事故走 SKILL.md 的 8 段完整复盘，不要两套都填。
  - What happened：<事实，1-2 句>
  - Root cause：<根因，附证据>
  - Why missed：<当时为什么没发现>
  - Fix applied：<怎么修的，file:line>
  - Prevention：<下次怎么防，可勾选>
  - Lesson：<一句可迁移结论；可 [[link]] 到 learnings>
  ```
- **风险**：与现有 8 段结构重叠，可能造成"两套模板"困惑。已用文件头部硬声明边界缓解。
- **我的建议**：`trim` —— 只做这个轻量模板且头部写清与完整复盘的分工；若你觉得 8 段已够，直接 `reject`。

---

## 决策点 2 — A7 TRIGGER / DO NOT TRIGGER 正反短语簇

- **落点**：`docs/software-engineering-research/skill-authoring.md` §1.3 末尾新增子节
- **现有覆盖**（事实）：§1.3 已有"用户行为化❌ vs 场景化✅"对比表——但那是**措辞轴**(怎么写 description)。
- **真正增量**：A7 是**另一根轴**——给高误触发 skill 补一组"哪些用户原话**会**触发 / **不会**触发"的具体样例，帮 agent 划路由边界。与现有触发前缀硬约束**共存**(前缀仍必填)。
- **拟改措辞**（§1.3 末尾追加）：
  ```markdown
  ### 1.3.1 TRIGGER / DO NOT TRIGGER 正反簇（可选增强）

  对通用对话里容易误触发/漏触发的 skill，可在 SKILL.md **正文**(不是 frontmatter)补一组用户原话样例：

  - TRIGGER：列 3-5 条会命中的用户原话
  - DO NOT TRIGGER：列 3-5 条貌似相关但不该命中的原话

  约束：放正文不放 description(避免 description 超长)；触发前缀仍必填；样例写"客观场景"不写"用户是否明示"(沿用 §1.3 硬约束)。
  ```
- **风险**：description 膨胀(已用"放正文不放 frontmatter"约束规避)。
- **我的建议**：`approve` —— 净增量清晰，是文档约定不改 runtime，风险低。

---

## 决策点 3 — A8 对抗式 QA 体裁

- **落点**：`skills/guard-verify/SKILL.md` 的 `## Anti-Rationalization Guard`(216-226) 之后
- **现有覆盖**（事实）：guard-verify 已有借口→反驳表(本地手测/测试改了/编译≠验证/同类改过)；**大部分已覆盖**。
- **真正增量**：现有是"被动反驳借口"；A8 加一句**主动对抗姿态**——默认"产物有缺陷"，先去找反证再声称完成。不塞领域特定 grep 探针(那是 MiniMax PPT 专用)。
- **拟改措辞**（在 Anti-Rationalization Guard 表后追加一段）：
  ```markdown
  对抗式姿态：声称"已验证/已完成"前，先假设产物**仍有缺陷**，主动找一条能**反驳**完成声明的证据(边界输入、回归、未覆盖路径)。找不到反证才算通过；找到就如实降级为 partial。
  ```
- **风险**：与现有 guard 高度重叠，净增量仅一段姿态描述。
- **我的建议**：`trim`(只加这一段姿态) 或 `reject`(认为现有借口表已够)。

---

## 决策点 4 — A9 AI slop 负向门

- **落点**：`skills/fe-ui-lint-artifact/SKILL.md` 扫描项末（+ 可选 `scripts/scan_ui_artifact.py` RULES）
- **现有覆盖**（事实）：已有 9 条规则 P0-P2，**默认蓝/emoji/filler/虚构指标/溢出/重效果/占位图/硬色值/硬编码 token 全覆盖**。计划提的"默认蓝"已是 `ai-default-indigo`。
- **真正增量**：MiniMax slop 清单里**未覆盖**的两项——**标题下划线**(underline headings)、**正文居中**(centered body text)。
- **拟改措辞**（SKILL.md 扫描项表末补 2 行，P2）：
  ```markdown
  | P2 | underline-heading | 标题加下划线 | text-decoration:underline 用在 h1-h6 |
  | P2 | centered-body-text | 长正文居中 | text-align:center 用在段落/列表容器 |
  ```
  - **子决策**：是否同步给 `scan_ui_artifact.py` 加这 2 条正则规则？居中/下划线正则**易误报**(居中也用于标题/按钮)，建议**只加文档 NEVER 项不加扫描器规则**，或加扫描器但标 P2 仅提示。
- **风险**：扫描器规则误报；文档 NEVER 项无风险。
- **我的建议**：`trim` —— 只加文档 2 项 NEVER，不动扫描器正则。

---

## 决策点 5 — A15 主动性等级标注

- **落点**：`agents/AGENTS.md` 能动性表（190-198）+ guard-* description
- **现有覆盖**（事实）：AGENTS.md 已有"被动 vs 主动"二元表；guard-secure description 已含"先取得授权"门禁。
- **真正增量**：缺"授权必需 / 自动 / 仅显式"的**三元主动性**显式标注。
- **拟改措辞**（两种范围，二选一）：
  - **范围 A（保守，推荐）**：只在 AGENTS.md 能动性表下补一句约定，不动各 skill description：
    ```markdown
    主动性三档：高风险/不可逆能力(线上、删除、offensive)默认"需授权"——先取范围/允许动作/停止条件；只读诊断默认"AUTO"；其余"仅显式"。
    ```
  - **范围 B（激进）**：再给每个 guard-* description 末尾加 `[AUTO|需授权|仅显式]` 标签。
- **风险**：**本组最高**。AGENTS.md 进每次 session 上下文(context surface)；改 description 要过 `verify_skills.py` 触发前缀/风险校验,标签可能干扰。范围 B 风险显著高于 A。
- **我的建议**：`trim` 到**范围 A**（只加 AGENTS.md 一句约定）；范围 B 暂缓。

---

## 决策点 6 — A16 置信度硬停门语义

- **落点**：`skills/think-scope/SKILL.md` + `skills/think-refine/SKILL.md` 停止条件节
- **现有覆盖**（事实）：**两者都已有 Ambiguity Score 硬停门**(总分>0.20 必须继续追问)；think-scope 还已写"3-5 轮无法收敛→给 2-3 候选 scope 让用户选"。**核心语义已存在**。
- **真正增量**：缺一个**统一的"低置信→上报决策缺口"输出格式**(两个 skill 各自表述，无固定模板)。
- **拟改措辞**（两个 skill 的停止条件节各补一小段，共用同一格式）：
  ```markdown
  ## Escalate（低置信收尾）

  3-5 轮仍无法把 Ambiguity Score 压到 <=0.20 时，不要硬猜，按固定格式上报：
  - 剩余歧义：<哪几维没收敛>
  - 候选解释：<2-3 个，附各自代价>
  - 需要你定的：<具体决策点>
  ```
- **风险**：与现有机制**高度重叠**，净增量只是统一输出格式。
- **我的建议**：`trim`(只统一这个 Escalate 输出格式) 或 `reject`(认为现有"给候选让用户选"已够)。

---

## 汇总（我的整体建议）

| # | 项 | 现有覆盖 | 净增量 | 建议 |
|---|---|---|---|---|
| 1 | A6 mistake 模板 | 高(8段复盘) | 轻量快记 | trim/reject |
| 2 | A7 正反簇 | 部分(另一轴) | 清晰 | **approve** |
| 3 | A8 对抗 QA | 高 | 一段姿态 | trim/reject |
| 4 | A9 slop 负向门 | 高(9规则) | 下划线/居中 2 项 | trim |
| 5 | A15 主动性标注 | 部分 | 三元约定 | trim(范围A) |
| 6 | A16 置信硬停 | 高 | 统一上报格式 | trim/reject |

净增量最实的是 **A7**；其余多为已有机制的小补强。请逐条裁决。

---
name: assist-review-doc
description: 当需要对长 MD 文档做多轮 inline 评论，或 agent 累积 ≥5 个决策点需要用户批量裁决时使用；生成可交互 HTML 评审产物，用户浏览器写评论 / 答复，subagent 隔离消费、按 blocker/question/nit/idea 四类处理、commit 锚定（与 /readable-rewrite 的区别是不重写文体，与 /guard-review 的区别是不评 code diff，与 /think-plan 的区别是不出新 spec）。
---

# Assist Review Doc

把"长 MD 文档评审"和"agent 累积大量决策点"这两个一直在 chat 里硬扛的场景，外化成可视、可标注、可多轮迭代的 HTML 评审产物。机制核心是三件套：MD 是内容 SSOT、`comments.json` 是评审状态 SSOT、`review.html` 是派生交互层；评论分类与消费由 subagent 隔离处理，主 agent 上下文不被全文污染。

## 何时使用

| 触发场景 | 路由 |
|---|---|
| 用户主动要求"review / 评审 / 看一下 / 评一下"指向长 MD 文档 | 进入 Use Case A（用户评 doc） |
| agent 当前回应需要用户回答 ≥ 5 个决策点 / 分歧 / 二选一 | 先 propose 进入本 skill；用户同意 → Use Case B（agent 收集决策） |
| 用户刚让 agent 生成 ≥ 500 行或 ≥ 30 heading 的 MD doc 且追问"看一下/怎么样" | 主动 propose 进入 Use Case A |

**不要**做的事：

- 评 code diff（→ `/guard-review`）
- 改文体可读性（→ `/readable-rewrite`）
- 出新 spec（→ `/think-plan`）
- PDF / 图像 / 数据标注（独立 skill，未来再做）

## 两个 Use Case，一个协议

Use Case A 和 B 共用同一个 `comments.json` schema，区别仅在 `role` 字段（`user` vs `agent`）。流程对称：

| | A：用户评 doc | B：agent 收决策 |
|---|---|---|
| 谁先写评论 | 用户在浏览器里 | agent 在 spec.md 同步生成 + 在 comments.json 注入 role=agent 的 open 评论 |
| 渲染后用户看到 | 自己的 open 评论等 agent 答复 | agent 的 open 提问等自己回答 |
| 用户写"新评论"作用 | 新提问 | 对 agent 提问的答复 |
| 终止 | 所有 user 评论 status ∈ {resolved, answered, moved} | 所有 agent 评论得到 user 答复 |

Use Case B 进入前 agent 必须先在 chat propose 一次：

```
我有 N 个决策点需要拍：<列表前 3 个示例>。
chat 串行回答容易丢上下文。建议进入 /assist-review-doc 批量评审，
我把决策点注入到 docs/.../<topic>.md 的对应 heading 下方，你浏览器一次性回。
进入？(y/n)
```

用户拒绝 → 退回 chat 列。

## 协议三件套

```
<doc>.md                  ← 内容 SSOT（进 git）
<doc>.comments.json       ← 评审状态 SSOT（进 git，schema v1）
<doc>.review.html         ← 派生交互层（不进 git，从前两者重渲）
```

详细 schema、commit message 格式、heading 改名规则、role 字段语义 → `skills/assist-review-doc/CONVENTIONS.md`

## 默认流程

### 1. Baseline init（首次评审某 doc）

```bash
python3 scripts/review_doc_render.py --doc <doc.md> --output <doc>.review.html
# 写空 comments.json
git add <doc>.md <doc>.comments.json
git commit -m "[review:anchor v0] <doc-stem>: initial baseline"
open <doc>.review.html      # macOS；其它平台用等价命令
```

### 2. 用户评审

用户在浏览器里读、按 anchor 写评论、点"导出未提交评论"，浏览器下载 `<doc-stem>.comments.json` 到 `~/Downloads/`。用户侧自动化把路径回传给 agent（或用户手贴）。

### 3. Subagent 消费

派发只读 + 编辑权限的 subagent，输入：下载文件路径、git 里的 baseline comments.json 路径、doc.md 路径、CONVENTIONS.md。指令模板：

```
1. 跑 scripts/review_doc_consume.py diff --baseline <git.json> --incoming <download.json>
   拿到 new_comments 列表（含 anchor_id / heading / text / role）
2. 对每条 new comment：
   - 读 doc.md 中对应 anchor 的上下文（heading 起到下一个同级或更高级 heading 之间）
   - 分类 (blocker/question/nit/idea)，给出 confidence
   - 不确定的（confidence < 0.7）收集到 ambiguous 列表，处理结束一并回问用户
3. 对确信的分类按下表动作：

   | 类型 | spec.md 动作 | comments.json 动作 |
   |---|---|---|
   | blocker | Edit 对应章节 | status=resolved, classification=blocker, response=<一句话说改了什么> |
   | question | 不改 | status=answered, classification=question, response=<答复> |
   | nit | Edit 对应章节 | status=resolved, classification=nit, response=<一句话> |
   | idea | spec.md 末尾 ## Backlog 追加 `- [from §<heading>] <text>` | status=moved, classification=idea, response="moved to Backlog v{N}" |

4. 跑 scripts/review_doc_ids.py verify <doc.md> <comments.json>  # 校验无 orphan anchor
5. git commit -am "[review:v{N+1}] <doc-stem>: {M}blocker {K}question {J}nit {I}idea→backlog"
6. 返回主 agent 紧凑摘要（不带 spec 全文）
```

### 4. 主 agent 摘要 + 用户下一轮

主 agent 拿到 subagent 摘要后呈现给用户，用户选择继续评审（重开 HTML，旧评论显示成历史线程，新评论草稿仍在 sessionStorage）或结束循环。

## 脚本

| 脚本 | 作用 |
|---|---|
| `scripts/review_doc_ids.py` | anchor ID 生成 (`extract`) + 稳定性校验 (`verify`)；orphan 评论时 exit 1 |
| `scripts/review_doc_render.py` | MD → 评审 HTML，载入 comments.json 预填、textarea + sessionStorage、导出按钮 |
| `scripts/review_doc_consume.py` | `diff` 提取新评论 + apply_resolution 库函数；版本必须单调递增 |
| `scripts/review_doc_migrate.py` | schema v1 验证 + 未来 vN→vN+1 迁移入口 |

测试：`python3 -m unittest scripts.tests.test_review_doc_ids scripts.tests.test_review_doc_render scripts.tests.test_review_doc_consume scripts.tests.test_review_doc_migrate`

## Evidence / Acceptance

任何"评审已完成"的声明必须给出：

- `comments.json` 中所有 open 评论已变成 resolved / answered / moved
- 最新 `[review:v{N}]` commit 已落地，含 doc.md + comments.json 两个文件
- 主 agent 摘要包含分类计数（blocker / question / nit / idea）和 spec.md 改动行号

inner-loop 验证（pytest 全绿）只证明脚本正确，**不能**单独替代用户对评审收敛的判断。

## Stop / Escalate

| 信号 | 动作 |
|---|---|
| `review_doc_consume.py diff` 报 version 不单调 | 停下，让用户确认是否拿错文件（可能下了旧版） |
| `review_doc_ids.py verify` 报 orphan anchor | 停下，提示用户：要么恢复 heading 文本，要么走 rename 流程迁移评论 |
| `git log <anchor>..HEAD -- <doc.md>` 有非 anchor commit | 停下，让用户确认 baseline 是否要前移 |
| 单轮 ambiguous（低置信度）分类 ≥ 5 条 | 怀疑评论本身太宽泛，问用户是否要更细粒度 anchor |
| 连续 2 轮 review 收敛慢（resolved/total < 30%） | 升级 `/think-unstuck`，可能该用 chat 直接谈而不是 review 产物 |

## Risk / Gotchas

- **不要在评审期间手 commit doc.md**。git diff baseline 跑偏，评论检测会漏或误识别
- **不要改 heading 文本**（详见 CONVENTIONS.md）。改 = anchor ID 漂移 = 评论孤立
- **不要把 `<doc>.review.html` 进 git**。它是派生产物，每次从 MD + comments 重渲
- **不要让 LLM 跳过 ambiguous 回问**。强行选边会把矛盾埋进 spec，下一轮爆出来代价更高
- **subagent 必须隔离上下文**。让主 agent 直接读 spec 全文 + 处理评论会爆 token；本 skill 的核心收益之一就是 context isolation
- **Use Case B 不允许自决进入**。≥ 5 阈值只是触发 propose，必须用户同意才注入 agent 评论到 spec.md

## 关联技能

- 还没出 spec → `/think-plan` 先写
- 评 code diff → `/guard-review`
- 改文体可读性 → `/readable-rewrite`
- 评审收敛慢 / 卡壳 → `/think-unstuck`
- 评审完毕要 ship → `/guard-ship`

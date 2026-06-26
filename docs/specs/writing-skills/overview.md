# writing-skills 体系设计 spec（overview）

> **现行架构（最新，覆盖下方所有「物理隔离 / 不暴露给编程 agent」表述）**：写作 skill 已**并入编程池** `coding-skills/`（软链 12 个 `write-*` / `guard-write-*` / `assist-write-corpus` + `_shared/`），供编程项目里的临时写作诉求，**靠 `write-*` 域前缀做路由隔离，而非物理隐藏**。因此下方 TL;DR 的「物理隔离」、`spec-contract` 的 `checks` S4「编程 agent 看不到 write-* skill」与 `non_goals`「不把写作 skill/hook 暴露给任何编程 agent 全局」**均为历史决策、已不成立**——以 `README.md` 与 `coding-skills/` 现状为准。本文档全文（含内部旧路径 `writing-skills/hooks/`、`scripts/verify_writing.py` 等）留作演进记录，不再逐处订正。

> **最终架构（2026-06-03 二次重构，覆盖下方 B 缩减）**：两层写作能力体系。
> 用户指出「去 AI 味等是**通用能力**应沉淀 dotfiles，敏感+定制留项目」，故把 B 的误删纠正回来：
> - **Layer 1 — dotfiles `writing-skills`（通用、account-agnostic、零敏感）**：12 个 skill
>   = 8 个恢复的通用管道（write-scope/source/outline/draft/revise/hook/voice + guard-write-check）
>   + write-dissolve / guard-write-facts / assist-write-corpus + 脱敏后的 article-growth-diagnosis。
>   `_shared/` = writing-constraints（质量下限）+ **narrative-methodology（从项目风格指南抽出的通用方法论）**
>   + style-contract.schema（**接缝**：账号 voice/定位/对标 由项目 `account-style.md` 提供）。
>   视觉 4 个不纳入（平台/渲染耦合）；writing-hooks 通用工具，默认休眠。
> - **Layer 2 — 创作项目（定制+平台+敏感）**：`account-style.md`（账号声音/定位/对标/AI 味反例）+
>   微信排版（瘦身后的 `写作风格指南.md`）+ 发布管线（AGENTS.md/scripts/VPS）+ 敏感文件（不动）。
> - **接缝**：dotfiles skill 通用 + 运行时读项目 `account-style.md` 注入账号特性；skill 正文零账号名/零微信特定。
>   新账号 = 软连接 writing-skills + 自带 account-style.md + 自带平台层。
> 计划见 `~/.claude/plans/1-2-lovely-breeze.md`。下方 B 段与原始全量设计留作演进记录。

> **实现结果（2026-06-03 修订，覆盖原 TL;DR 的全量计划）**：
> 全量实现后发现创作项目已有一套成熟、按数据反馈更新的写作方法论（`写作风格指南.md` +
> `AGENTS.md` 的素材→草稿→review→发布脚本工作流 + `gen_image.py` 出图 + `find_material.py` 取材）。
> 通用 writing-skills 与之高度重叠且多处更弱/冲突，故**缩减为「补充」**（用户决策 B）：
> - **保留 3 个不重叠 skill**：`write-dissolve`（动笔前消解/证伪）、`guard-write-facts`（事实/引用核验）、
>   `assist-write-corpus`（语料库）+ 用户既有 `article-growth-diagnosis`。
> - **删除 12 个与风格指南重叠的 skill**（write-scope/source/outline/draft/revise/hook/voice +
>   视觉 card/deck/illustration/poster + guard-write-check）——保留在 git 历史（commit c8ac5e2），可恢复。
> - **不挂 hooks**：移除创作项目 `.claude/settings.json`；`writing-hooks/` 代码保留为**休眠工具**（未注册），
>   原因见 §「与项目既有方法论的冲突」。风格/结构/取材/发布以项目 `写作风格指南.md` / `AGENTS.md` 为权威。
> 下文为原始全量设计，留作记录与未来其他写作项目的参考。

> 原状态：设计稿（已批准全量实现，后按 B 缩减）。SSOT = 本文档。
> 输入证据：`docs/writing-refs-synthesis.md`、`docs/writing-refs-details/*`（10 份逐仓库 why+how）。

## TL;DR

为创作项目建一套**与 coding-skills 平行、物理隔离**的中文写作能力体系：`writing-skills/<name>/SKILL.md` + `writing-skills/catalog.json` + 共享「中文写作硬约束」前缀 + 独立写作 lint 脚本 + **独立写作 hook 目录**。新增 `write-` 域，复用 `readable-/think-/guard-/assist-/web-read`。voice 用可替换语料库 + 用户配置承载。**全程只软连接到创作项目 `.claude/skills`，hook 只在该项目 `.claude/settings.json` 注册——不挂任何编程 agent**。规模较大（文字+视觉全做），分 5 个阶段（P0 骨架 → P1 文字核心 → P2 取材/事实 → P3 hooks → P4 视觉资产），文字先扎实、视觉最后做。

## 已锁定（用户已拍板）

1. **scope = 文字 + 视觉全做**：含 social-card/ppt/baoyu/xiaohei 的渲染管线（HTML→PNG、插画、PPT）。
2. **新建 `write-` 域 + 复用现有域**（`readable-/think-/guard-/assist-/web-read`），不把写作生成硬塞进 `readable-`。
3. **hooks 姿态 = 确定性硬拦 + 主观先告警**：排版/slop/篇幅/provenance → exit-code 脚本 + PostToolUse 硬 block；去 AI 味评分门 / 事实引用门 → 先 warn。
4. **voice = 可替换语料库（`assist-write-corpus`）+ 用户 EXTEND.md 配置**，人格不硬编进 skill。
5. **隔离 hook 目录 = 顶层 `writing-hooks/`**（本轮拍板，选项 1）：写作 hook 脚本 + `verify_writing.py` 放顶层 `writing-hooks/`，与编程 `scripts/hooks/` 分开；**只在创作项目 `.claude/settings.json`（项目级）注册**，不进任何 agent 的全局 settings。
   - 写作硬约束 SSOT `_shared/writing-constraints.md` 等**留在 `writing-skills/_shared/`**：创作项目只软连接 `.claude/skills → writing-skills`，skill 运行时只能相对引用 writing-skills 树内的文件；hook 则用绝对路径读同一份。`_shared/` 不是 skill，由 `verify_writing.py` 像 `.system/` 一样豁免。
   - **接受的不对称（明确取舍）**：编程 hook 维持在 `scripts/hooks/`，不改名为 `coding-hooks/`——改动影响面大（install_hooks、5 个 agent 注册、多个测试均引用），收益不抵成本。故 `writing-hooks/` 与 `scripts/hooks/` 命名不完全对称，属已知接受项。
6. **物理隔离**：沿用已完成的 `writing-skills/`（系统级编程技能在 `coding-skills/`）；创作项目 `.claude/skills → ~/.dotfiles/writing-skills`（已软连接）。

## 待决策（需你拍板，影响实现形态）

已解决（不再待决）：
- **D1 写作 hook 目录** → 顶层 `writing-hooks/`（见已锁定 #5）。
- **D2 写作 catalog 强制校验** → 做 `writing-hooks/verify_writing.py`（孤儿/漂移/触发前缀校验，类比 verify_skills.py）；隔离性验收依赖它。

仍待决（影响实现形态，可按推荐默认）：

| # | 决策点 | 候选 | 推荐 |
| :- | :- | :- | :- |
| D3 | `write-scope`/`write-dissolve` 是否独立成 skill | (a) 独立写作特化 skill / (b) 直接复用 `think-scope`/`think-refine` | **(a) 轻量版**：写作前置语义差异大（受众/体裁/voice），但内部引用 think-scope 方法，避免重造 |
| D4 | 去 AI 味落点 | (a) 新 `readable-dehumanize` / (b) 扩展现有 `readable-rewrite` 增加「去 AI 味 + section 反馈」模式 | **(b)**：readable-rewrite 已是 writer+critic 循环，扩展模式比新 skill 维护面小、触发更清晰 |
| D5 | 视觉资产阶段（P4）现在做还是另立 scope | (a) 纳入本 spec 的 P4（依赖 Playwright/node 渲染，重） / (b) 本 spec 只到文字+hooks，视觉另开 spec | 倾向 **(b)**：视觉管线成本高、依赖环境，建议文字体系跑顺后单独立项；但你已选「全做」，故 P4 保留在本 spec，仅标注可拆分 |

## 边界

### Goals
- 一套可被创作项目 Claude Code 触发的中文写作 skill 体系，覆盖：前置对齐 → 取材 → 提纲 → 成稿 → 改稿 → 去 AI 味/注魂 → 事实校验 → 视觉资产产出。
- 把 10 个项目验证过的「硬约束 / 填空式生成 / 分层自检 / 人在环契约 / 状态外置」工程模式落成可复用结构。
- 确定性规则用脚本 + hook 强制；主观质量先告警。
- voice/语料/风格偏好与 skill 解耦，可替换、可配置。

### Non-goals
- 不改动 `coding-skills/` 及编程 agent 的任何 wiring。
- 不把写作 hook/skill 暴露给 cc/codex/droid/opencode/kilo 全局。
- 不照搬任一项目的具体商业主张 / 作者人格（只取工程骨架）。
- 不追求「保证去干净 AI 味」或「保证过检测」——LLM 行为不保证，评分门为自评 inner-loop。
- 不在本 spec 内写实现代码。

### Constraints
- 遵循仓库 skill 规范：`description` 触发前缀、hyphen-case 命名、SKILL.md 体例（见 `docs/software-engineering-research/skill-authoring.md`）。
- 文风/事实纪律对齐 AGENTS.md：默认 ASCII、`[推断]/[未验证]` 标注、禁用 Guarantee/Will never。
- 写作 hook 注册范围 = 仅创作项目；实现时不得改全局 `~/.claude/settings.json` 等。
- 视觉 skill 的共享资产必须随 skill vendored 或用相对路径（吸取 ppt 本机绝对路径失效的反面教训）。

## 场景化推演

| Scenario | Actor / Context | Step-by-step path | System touchpoints | Exposed issue | Requirement / Contract |
| :- | :- | :- | :- | :- | :- |
| S1 写公众号长文 | 你在创作项目里让 Claude「把这堆素材写成一篇讲 X 的公众号长文」 | write-scope 对齐受众/体裁/voice → write-source 取材+行内引用 → write-outline 提纲(内嵌 Research To-Do) → write-draft 填槽成稿 → readable-rewrite(去AI味+注魂) → guard-write-facts 校验引用 → 定稿 | writing-skills/* + 共享硬约束前缀 + 项目 EXTEND.md(voice) + slop-lint hook | 多 skill 串联需要状态外置(改某段不重跑)；voice 必须可注入 | R: 状态用 draft-vN 文件 + 固定 schema；voice 从 corpus/EXTEND.md 读 |
| S2 定稿前触发 slop hook | Claude 写完 draft 落盘 | PostToolUse 触发 writing-slop-lint：扫到 3 个 em dash + 缺盘古之白 + 1 句 AI 套话 | 项目 .claude/settings.json + writing-skills/hooks/slop_lint.py | 硬 block 必须只作用于写作产物、且只在本项目 | R: hook matcher 限定写作产物路径；exit 2 阻断并打印逐处定位 |
| S3 文章转小红书卡片 | 你让 Claude「把这篇拆成小红书图文」 | write-card 读成稿 → 填种子模板 → 渲染 HTML → Playwright 截图 → 规则 lint(exit 1) → 产出 PNG | writing-skills/write-card/* + 渲染依赖(node/Playwright) + golden sample | 渲染管线依赖环境；分发后绝对路径/缺脚本会失效 | R: 资产相对路径或随 skill vendored；环境缺失要 fail fast 给安装指引 |
| S4 编程 agent 不受影响 | 你在别的代码仓库用 cc 改代码 | cc 加载 ~/.claude/skills(→coding-skills) 与全局 settings | 全局 settings.json 不含写作 hook；coding-skills 不含 write-* | 隔离失败会让写作 hook 误拦代码、或写作 skill 干扰编程路由 | R: 写作 hook/skill 零进入全局；验收须证明 cc 看不到 write-* 也不触发写作 hook |

## 方案

### 目录与组成（方案 A，推荐）

```
~/.dotfiles/
  writing-skills/                      # 已存在（已软连接到创作项目）；只装 skill + catalog + _shared
    catalog.json                       # 写作 skill 注册表（类比 coding-skills/catalog.json）
    _shared/                           # 共享 SSOT（html-anything「共享前缀」模式）；留在 skill 树内，便于 skill 经软连接引用
      writing-constraints.md           # 中文写作硬约束：盘古之白/禁em dash/禁emoji/真实数据/不堆形容词/[推断][未验证]标注
      style-contract.schema.md         # 风格契约文件 schema（Tone/称谓/禁用词/Avoid/署名/Best-For）
    write-*/  ... (各 skill 目录)
    assist-write-corpus/               # voice 语料库 skill + 可替换原子库/正反例
  writing-hooks/                       # 顶层隔离 hook 目录（与 scripts/hooks/ 分开，不挂全局）
    slop_lint.py  length_budget.py  provenance_guard.py  dehumanize_score.py  facts_gate.py  publish_confirm.py
    verify_writing.py                  # 写作 catalog/孤儿/前缀/_shared 漂移校验；用绝对路径读 writing-skills/_shared
  docs/writing-refs*                   # 已存在：分析与综合
  docs/specs/writing-skills/           # 本 spec
创作项目/.claude/
  skills -> ~/.dotfiles/writing-skills # 已软连接
  settings.json                        # 新增：仅此项目注册写作 hooks（项目级，绝对路径指向 ~/.dotfiles/writing-hooks/*）
```
（编程侧维持 `coding-skills/` + `scripts/hooks/` + `scripts/verify_skills.py` 不变；`writing-hooks/` 与 `scripts/hooks/` 命名不对称为已接受取舍。）

### Skill 清单（write- 域 + 复用）

R（需求）× S（skill）fit 见下；标 ✅ 为该 skill 满足该需求。

文字（write- 新域）：
- `write-scope`：动笔前对齐受众/体裁/voice/不可牺牲约束（借 think-scope，写作特化）
- `write-dissolve`：消解优先——审计模糊词/隐含假设/相关性当因果，先证伪问题（借 dbskill）
- `write-source`：取材/查证，建在 `web-read` 之上 + 行内引用 + 反问钩子（借 notebooklm/content-research）
- `write-outline`：提纲 + 内嵌 Research To-Do + 每段功能/证据来源对齐表（借 content-research/ppt）
- `write-draft`：填槽成稿——固定体裁骨架 + 暴露内容槽位 + 正交旋钮（体裁×语气×结构×受众）（借 baoyu/ppt）
- `write-revise`：改稿 diff-edit——保留结构语气只动差异（借 baoyu/html-anything）
- `write-hook`：标题/开头/CTA/过渡句多策略候选 + Why + 判定问句（借 content-research）
- `write-voice`：注魂/活人感层——观点/节奏/第一人称/口语化白名单，读 corpus + EXTEND.md（借 Humanizer/khazix）

视觉（write- 域，P4）：
- `write-card`：社交卡片/小红书图文（借 social-card/baoyu）
- `write-deck`：文章→PPT/演讲图，美学硬约束 + exit-code lint（借 ppt）
- `write-illustration`：正文认知锚点插画（借 xiaohei）
- `write-poster`：Markdown→海报/多格式 HTML→PNG（借 html-anything）

复用/扩展现有域：
- `readable-rewrite`（扩展，D4(b)）：新增「去 AI 味 + 注魂 + section-by-section 反馈」模式
- `guard-write-check`：写作交付总检查，编排 去AI味/事实引用/篇幅/术语一致（借 khazix L1-L4，区分 inner/acceptance）
- `guard-write-facts`：事实/引用核验门（标注齐全性 + 结论有无来源支撑）
- `assist-write-corpus`：voice 语料 → 带 confidence 标签的可替换原子库 / 正反例对照库

### Hooks（隔离目录 + 项目级注册）

| Hook | 类型 | 触发 | 行为 |
| :- | :- | :- | :- |
| writing-slop-lint | 硬 block | PostToolUse（写作产物 write/edit） | 盘古之白/em dash/emoji/全角半角/AI套话扫描，exit 2 阻断 + 逐处定位 |
| writing-length-budget | 硬 block | 成稿后 lint | 段字数/每段一论点/标注上限/内容驱动篇幅 |
| writing-provenance-leak | 硬 block | 产物 write 后 | 来源/赞助/本机路径误入产物 |
| writing-dehumanize-score | warn | 声明定稿前 | 编号模式扫描 + N 维评分，低于阈值告警（自评，不替代人工） |
| writing-facts-citation | warn | 含引用产物定稿前 | [推断]/[未验证] 齐全性 + 引用列表完整性 |
| writing-publish-confirm | 硬 block | 覆盖原文/发布动作前 | 默认拦截，仅显式放行（对齐边界审批） |

实现倾向：静态门做 `*.py` + PostToolUse；评分/事实门先 skill 内 checklist + 可选脚本，避免误杀。全部注册在创作项目 `.claude/settings.json`，matcher 限定写作产物路径。

### 阶段计划（垂直切片，文字优先）

- **P0 骨架**：`writing-skills/catalog.json` + `_shared/writing-constraints.md`、`style-contract.schema.md` + `scripts/verify_writing.py` + 目录结构。验收：verify_writing 通过、创作项目能看到空体系不报错。
- **P1 文字核心**：write-scope/dissolve/outline/draft/revise/hook + readable-rewrite 去AI味模式 + write-voice + assist-write-corpus（含一份初始 corpus + EXTEND.md 模板）。验收：S1 端到端跑通一篇真实长文。
- **P2 取材/事实**：write-source（建在 web-read）+ guard-write-facts。验收：取材带行内引用、事实门能标出无支撑结论。
- **P3 hooks（隔离）**：建 `writing-skills/hooks/` + 创作项目 settings.json 注册；先上 slop-lint 硬 block，再 length/provenance/publish，最后 dehumanize/facts(warn) + guard-write-check 编排。验收：S2/S4——写作产物触发拦截、编程 agent 完全不受影响。
- **P4 视觉资产**（可拆分为独立 spec）：write-card/deck/illustration/poster + 渲染管线。验收：S3——渲染出 PNG + lint 通过 + 无绝对路径失效。

## 领域语言

**写作硬约束前缀（writing-constraints）**：所有 writing skill 复用的单一 SSOT 约束块（排版/禁用项/标注纪律）。_Avoid_：在每个 skill 各写一份（会漂移）。
**风格契约（style-contract）**：承载某账号/作者 voice 的配置文件（语气/称谓/禁用词/Avoid/署名）。_Avoid_：把 voice 硬编进 SKILL.md。
**corpus 原子库**：从真实写作语料提炼、带 confidence 标签的可检索/可替换正反例集合。_Avoid_：把语料当 skill 正文。

## 风险与验证

### Premise collapse（最脆弱假设）
- **方案 A（隔离 + 项目级 hook）**：`If 写作 hook 只在创作项目 settings.json 注册且 matcher 正确限定写作产物路径，则编程 agent 不受影响。If does not hold（误注册进全局或 matcher 太宽），写作 hook 会拦截/干扰代码改动，破坏 coding 工作流，必须紧急回滚 settings。`
- **视觉 P4**：`If 创作项目本机有 node + Playwright + 中文字体，则 write-card/deck/poster 能渲染出图。If does not hold，渲染管线静默失败或出空白图，必须 fail fast 给安装指引而非假装成功。`
- **voice 解耦**：`If voice 经 corpus + EXTEND.md 注入而非硬编，则可多账号切换。If does not hold（人格混进 SKILL.md），换账号要改 skill，丧失复用。`

### 验证
- **inner-loop verifier**：`verify_writing.py`（catalog/孤儿/前缀/共享前缀漂移）；hook 脚本各自 unit test（用 golden 正反样本）；slop-lint 对 golden sample 跑 0 误报/0 漏报。这些只证明结构与规则脚本正确，**不证明写作质量**。
- **acceptance verifier**：在创作项目里跑 S1（真实长文）与 S3（真实出图），由你人工验收去 AI 味/结构/出图效果；S2/S4 用真实操作证明 hook 只拦写作、编程 agent 看不到 write-* 也不触发写作 hook。LLM 写作质量类断言标 `[未验证]`，不保证。

### 回滚
- skill/hook 全部未 commit 前：删 `writing-skills/<新增>`、`docs/specs/writing-skills/` 即回到当前态。
- hook 已注册：移除创作项目 `.claude/settings.json` 的写作 hook 段即停用，零影响其他仓库。
- 视觉 P4 独立：可整段不做或单独回退，不影响 P0-P3 文字体系。

## 实施顺序（批准后才进入，逐阶段过验收）
P0 → P1 →（验收 S1）→ P2 → P3 →（验收 S2/S4）→ P4（验收 S3）。每阶段走 `/dev-tdd`（脚本/hook 有测试条件）→ `/guard-verify`。视觉 P4 建议批准时确认是否拆为独立 spec。

```yaml
# spec-contract
checks:
  - "writing-skills/ 与 coding-skills/ 物理隔离；创作项目 .claude/skills 软连接到 writing-skills"
  - "写作 hook 位于顶层 writing-hooks/，仅在创作项目 .claude/settings.json 注册，全局 settings 零写作 hook"
  - "S4：编程 agent（cc/codex/droid/opencode/kilo）看不到 write-* skill，也不触发任何写作 hook"
  - "verify_writing.py 通过：catalog 无孤儿、触发前缀合规、_shared 前缀无漂移"
  - "writing-slop-lint 对 golden 正反样本 0 误报 0 漏报，命中时 exit 2 并逐处定位"
  - "S1 真实长文端到端跑通；S3 真实出图且无本机绝对路径失效"
non_goals:
  - "不改动 coding-skills 及编程 agent wiring"
  - "不把写作 skill/hook 暴露给任何编程 agent 全局"
  - "不保证去干净 AI 味或过检测（评分门为自评 inner-loop）"
  - "本 spec 不含实现代码"
validation_commands:
  - "python3 writing-hooks/verify_writing.py"
locked_decisions:
  - "scope=文字+视觉全做"
  - "新建 write- 域 + 复用现有域"
  - "hooks=确定性硬拦+主观先告警"
  - "voice=可替换语料库+用户配置"
  - "隔离写作 hook 目录=顶层 writing-hooks/ + verify_writing.py，仅项目级注册"
  - "_shared 写作硬约束留在 writing-skills/_shared/（skill 经软连接引用）"
  - "编程 hook 维持 scripts/hooks/ 不动；writing-hooks 与 scripts/hooks 命名不对称为已接受取舍"
```

# rjs/shaping-skills

- 上游仓库：`https://github.com/rjs/shaping-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/rjs/shaping-skills`
- 纳入 commit：`d8b65d7733c71e9bf436f0c2e4da60e5214a96d9`（2026-05-29 加入，本地 remote-tracking）
- 主分类：**研发流程 / 产品塑形（Shape Up）方法论 skill**
- 能力标签：`Shape Up`, `framing`, `shaping`, `breadboarding`, `slicing`, `kickoff`, `Claude Code Skills`, `hook 强制`
- 一句话总结：Ryan Singer（Shape Up 作者）把 shaping 全链路（framing → shaping/fit-check → breadboarding → slicing → kickoff）编码成一组 agent skills，核心设计是"表格为唯一事实源、文档分层一致性靠 hook 强制"，让 LLM 在写代码前先把"为什么做 / 做什么 / 怎么连"显式化为可验证的结构化产物。

## 能力概览

- 4 个主 skill + `breadboard-reflection`（README 未列）+ 1 个 hook：`framing-doc`、`shaping`、`breadboarding`、`breadboard-reflection`、`kickoff-doc`、`hooks/shaping-ripple.sh`。
- 编码的 Shape Up 概念：Framing（问题选择 + "why this not that"）、Shaping（R 需求 / S 解法分离 + fit check）、Breadboarding（Places/affordances/wiring）、Slicing（垂直可演示切片）、Kickoff（交接）。
- [事实] 原书的 appetite（时间盒）/ betting table / cooldown 几乎未编码——用结构上限替代时间盒（见特别技巧）。
- 注意：`breadboarding/skill.md`、`breadboard-reflection/skill.md` 用小写 `skill.md`，另两个用大写 `SKILL.md`，命名不统一。

## 设计理由（WHY）— 每个 skill 对应的失败模式

| skill | 针对的失败模式 | 设计回应 |
|---|---|---|
| `framing-doc` | agent/人直接跳进解法，从不论证"为什么是这个问题不是那个" | 强制 Source（逐字引用）→ Pre-work（选项景观 + signal strength）→ Problem/Outcome；用 "Less about / More about" 挡住"技术对、方向错"的解法 |
| `shaping` | "需要什么"和"怎么造"混在一起；用 estimate 假装确定性 | R(need) 与 S(mechanism) 强制分离，禁止 R/S 同义反复；fit check 二元化（只能 ✅/❌） |
| `breadboarding` | LLM 把设计画成扁平 pipeline（user types → LLM → app），掩盖真实接缝 | 先抽象成 Places/affordances/wiring 表再渲染图；名字必须指向代码里真实存在的东西；navigation flow ⊥ data flow 双流分解 |
| `breadboard-reflection` | breadboard 与代码漂移；orchestrator 被命名成它没做的下游效果 | SEE（对齐代码）→ REFLECT（挑设计 smell）强制双相，顺序不可逆 |
| `kickoff-doc` | 把 kickoff 录音按时间线复述，builder 查不到"某区域怎么工作" | "Territory, not Timeline"——按系统区域组织；决策就地内联 |

为什么先 breadboard 再写代码：从概念 shape 直接出的设计是扁平 pipeline，而代码已通过模块切分/函数提取决定了接缝在哪；breadboard 用来在写代码前逼出这些接缝。为什么不用 estimate 而用结构上限：[推断] 用 "R ≤ 9 / slices ≤ 9 / slice 太大要拆" 这类结构上限代替时间盒，达成 appetite 约束 scope 的作用。

## 特别技巧（非显然）

1. **表格是唯一事实源，图是给人看的渲染**：反复出现 "The tables are the truth. Mermaid diagrams are optional visualizations."；改动顺序钉死为先改表再渲染图，禁止只在图里加未命名子节点。single-source-of-truth + 单向数据流。
2. **hook 强制 ripple，而非自然语言提醒**（`hooks/shaping-ripple.sh`，15 行）：PostToolUse 匹配 Write|Edit → 读文件前 5 行 → `grep '^shaping: true'` 命中则 `exit 2` 阻断并把 checklist 注入 stderr；非 shaping 文件静默通过。用 frontmatter 开关做选择性激活。
3. **fit check 二元强制 + flagged-unknown 三段论**：fit 只能 ✅/❌ 不准 ⚠️；`⚠️`（知道 what 不知道 how）只能进 Parts 表，且逻辑推出"flag = 不知道 how → 必须 ❌"。结构化遏制 LLM 把猜测标成"能做到"。
4. **命名测试作为设计 smell 探测器**（`breadboard-reflection`）：每个 affordance 用一个地道动词命名；"需要 or 连两个动词" = 两个职能塞进一个函数；区分 step-level vs chain-level effect 的方法是"列出所有下游调用 → 全删 → 命名剩下的"。
5. **Place 的"阻塞测试"把 UI 状态形式化**："能不能跟背后交互？不能 = 不同 Place"，把"什么算独立交互上下文"变成可机械判定。
6. **多层双向 ripple**：shaping doc → slices → slice plans 三层，高层改往下 trickle、低层发现新机制往上 trickle，同一次操作全部更新，每个改动行标 `🟡`。
7. **反例驱动 + GIGO 诚实声明**：几乎每条规则配 ✅/❌ 成对反例；README 直接声明 doc skill 只 format & distill、不评判输入对错（垃圾进垃圾出），诚实划定 skill 职责边界。

## 与本仓库 agent skill 生态的关系

对照 `think-plan` / `think-refine` / `dev-large-delivery` / `think-context-map`：

- **互补**：R/S 分离 + fit 矩阵（本仓库 think-plan 用散文 spec，缺这种可扫描、能逼出"哪条需求没被任何机制满足"的结构）；breadboarding 填补"代码地图"与"实现"之间那一层（affordance/wiring/Place 面向交互与数据流）；breadboard-reflection 把"设计 vs 代码对齐"做成一等流程，与本仓库"事实优先、闭环验证"同源；结构上限（≤9）比时间盒更操作化。
- **本仓库缺失视角**：Framing 层（选项景观 + signal strength + 为什么 now 的战略选择产物）；fit check 把"知道 what 不知道 how"强制降级 ❌；doc skill 的 GIGO 诚实声明。
- **冲突点**：[推断] framing-doc/kickoff-doc 的 ground truth 是会话录音，与本仓库代码/仓库事实源取向不匹配；真正可迁移的是 shaping + breadboarding + reflection 三件。

## 可吸收候选（L0-L5，均建议先走 /think-plan，不直接改 skill）

| # | affected asset | 吸收形式 | level | 风险 |
|---|---|---|---|---|
| C1 | `docs/software-engineering-research/`（新 ref 笔记） | 把 breadboarding 的"Place/affordance/wiring + navigation⊥data + 表为事实源"沉淀为参考，供 think-context-map/think-architecture 可选引用 | L1 | 低 |
| C2 | `think-plan` / `think-refine` | R(need)/S(mechanism) 分离 + R×S fit 二元矩阵作为复杂需求的可选输出格式，附"禁止 R/S 同义反复"反例 | L2（opt-in） | 中 |
| C3 | `dev-*` 或新 `guard-*` | 借鉴 Naming Test（一个动词 / step vs chain / 列下游全删剩什么）作为函数职责切分 review 启发式 | L2 | 中（普适性待验证） |
| C5 | `think-plan` / `guard-close` | flagged-unknown 三段论：决策矩阵里"知道 what 不知道 how"强制 ❌ + 挂 spike | L2 | 低-中（与 Truth Directive 同源） |
| — | framing-doc / kickoff-doc 整体搬运 | 不建议（ground truth 取向不匹配） | — | — |

## 关键文件

- `README.md`
- `hooks/shaping-ripple.sh`（hook 全部逻辑）
- `shaping/SKILL.md`
- `breadboarding/skill.md`（小写）
- `breadboard-reflection/skill.md`（小写，README 未提及）
- `framing-doc/SKILL.md`
- `kickoff-doc/SKILL.md`
- `test-gfm.sh`（用 GitHub markdown API 校验表格渲染）

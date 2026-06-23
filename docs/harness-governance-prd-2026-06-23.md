# PRD: Harness 可治理化 —— 程序级需求文档与路线图(2026-06-23)

> 性质:**需求文档(requirements / roadmap),不是 spec。** 只描述 problem / outcome / 行为契约 / 验收 / 依赖,不写 API、skill 骨架、DSPy 代码等实现。
> 证据基础:本轮 workflow(19 agents)技能图缺口审计 + 假设证伪 + 跨 agent 机制 + 方法论调研;agentsview 探查;`docs/storm-methodology-2026-06-22.md`。
> 后续:本文批准后,每个工作流再各自走 `/think-plan` 出 spec、`/to-issues` 拆任务。

## 北极星

让我的跨 agent skill / harness 体系**可治理**:知道有什么、用得怎样、质量够不够、capsule 准不准 —— 决策由数据驱动,而非凭记忆和感觉。

## 背景与核心判断(已由 workflow 证据确立)

- **"技能多 → 不好选择 → 需要渐进式暴露" 这个假设 misframed。** 51 条 description 在 session 启动一次性注入(实测 ~1400-2000 tokens,<1% 窗口),模型一次看全;选错不是因为数量,而是**域内近邻 description 区分度不足**(think/guard 域语义糊)。常驻 token 成本是伪命题。
- 因此**真问题有两类,都不是"技能太多"**:(A) 近邻边界区分度;(B) 真能力缺口(发散/创新)。
- **capsule 选不准(B 工作流)与 skill 描述区分度差(A 工作流)是同一个病:类别边界模糊。** 同一份真实 prompt 数据可同时治两者。
- **所有砍/改决策都缺数据**,而 agentsview(C 工作流)是产数据的层。**先建数据层,再用数据驱动 A、B**;不依赖数据的快赢(ideation、agentsview MVP)可立即并行。

## 全局 Goals / Non-Goals

**Goals**
- 补齐技能图真缺口(发散/创新),且**净新增能力维度**,不加剧选择负担。
- 让近邻技能/capsule 的边界对模型和用户都清晰可辨。
- 用真实使用数据识别死技能、误调用、context 成本,驱动治理。
- capsule 路由质量可度量、可迭代。

**Non-Goals(本程序明确不做)**
- 不做"检测活动 → 隐藏无关技能组"的 gating 渐进暴露(workflow 明确反对:解决不了近邻歧义、引入 F1 54% 漏召回、省 token<1%)。
- 不为追求"覆盖完整"而堆砌近邻细分技能。
- 不把重基础设施(向量库、概念树、多进程 agent 社会)塞进 markdown-prompt 技能。
- 不在本文阶段做任何实现/spec。

## 全局约束

- markdown-prompt 形态:技能=纪律,采纳方法论思想而非机器实现。
- 跨 agent 兼容:任何注入类改动须复用现有 `context_capsule.py` substrate(CC/Codex/Droid 原生 hook;kilo/opencode 经 .mjs plugin,有 part-schema 坑),soft/advisory + fail-open,永不阻塞。
- 真实性纪律:不削弱现有 `_shared/writing-constraints.md` 与 AGENTS.md 红线。

---

## 工作流 A:技能能力缺口治理

### Problem
think 域 11 个技能全是收敛型(理解/对齐/调研/取舍/成文/救火),**没有任何以"刻意扩大解空间"为目标的发散/创新入口**。同时,新增技能若是近邻细分,会加剧选择负担。

### Desired Outcome
- 存在一个发散/创新能力入口,能在"主动想要更宽解空间"(非卡壳、非 bug、非选型)时产出多条本质不同的候选,再交给现有收敛技能裁决。
- 近邻技能边界清晰,模型与用户都能快速判断"该用谁/不该用谁"。

### 需求(行为契约)
- **A1 发散生成能力**:给定问题/约束,强制产出 N 条本质不同的候选(含反惯性/反直觉项),显式禁止过早收敛与自我审查,产出多样性自检(候选是否同源),并移交收敛技能(think-compare/think-research)。**只产候选,不做裁决。**
- **A2 净新增校验**:任何新增技能在落地前,必须用 2-3 个真实近期任务回放,证明现有技能组合无法覆盖该场景;不能覆盖才建,否则降级为给现有技能加 opt-in 子节。
- **A3 近邻边界可辨(已扩范围)**:现有 routing 基础设施已覆盖约 80%——前缀做域级粗路由(免费,但域内近邻无效、且 ~6 个 brand-exception 无前缀)、AGENTS.md 已有前缀图例 + 9 条场景→序列配方。缺的精确一块是**近邻判别"用 X 不用 Y"未进常驻层**(只在 README + 零散括注里)。A3 = 三件事:① 收紧近邻 description 互斥判别式;② 把精简"近邻怎么选"判别矩阵提进 AGENTS.md(常驻);③ 给 ~6 个无前缀 brand-exception 技能归类。**不引入任何加载/gating/加亮机制。**
  - **✅ 编程域已完成(2026-06-23,a3 workflow + 自落编辑):** ①重写 19 条近邻 description(info-gather-decide / understand-scope / reason-recover-diverge / guard-gates / dev-workflows 五簇),每条含"何时不用→改用谁"互斥判别,verify_skills 通过(52 skills,无新增 VAGUE);②判别矩阵已提进 AGENTS.md(软链至 CLAUDE.md 常驻)。
  - **✅ 跨线已补(2026-06-23,R2 平铺后):** AGENTS.md 前缀图例加 `write-*`/`guard-write-*`/`assist-write-corpus` 行 + 矩阵加"写作 vs 编程(同前缀防混)"行(guard-write-* 非代码→guard-review/verify;assist-write-corpus 非 assist-learn)。同前缀写作 skill 描述已自识别写作域,无需逐条改。③ brand-exception 归类已被 AGENTS.md 专项行覆盖(足够)。改动均**未 commit**,待用户 review。
- **A4 横切纪律收口**:对"目标驱动是否广收信息"的判据(VOI:即使拿到完美信息结论会变吗?不变就别收)以横切纪律形式落地(capsule 或并入现有技能),**不单独成 think-deep 技能**。

### Acceptance Criteria
- [ ] 存在发散/创新技能,对测试问题能产出现有 think-plan/compare 不会产出的"本质不同、刻意反惯性"候选,且不越界做最终裁决。
- [ ] think/guard 域近邻技能的 description 含可被模型和用户使用的互斥判别式。
- [ ] "是否广收信息"的 VOI 判据在体系中可被触发,且未新增独立技能。
- [ ] 新增技能数量受控,每个都通过 A2 净新增校验。

### 已决裁决(workflow 对抗式验证)
- ✅ **建 → 已交付(2026-06-23)**:`think-ideate` 已建+注册+verify 通过(catalog 52 skills);A2 冒烟测试通过(拿 capsule 路由问题实跑,产出 8 个 think-plan/compare 不会产出的发散候选,确认是真发散维度非换皮)。合并了候选中的 think-ideate 与 think-brainstorm 为一个。
- ❌ **不建独立 think-deep**:confidence=low、~70% 与 dev-debug/think-unstuck/think-research 重叠;唯一新点 VOI 门 → 走 A4 横切纪律。
- ❌ **驳回**:think-redteam(已被 think-plan Premise Collapse 覆盖)、think-estimate(并入 think-compare)、think-confidence-check(已被 think-scope Ambiguity Score 覆盖)、think-introspect(已被 think-unstuck 覆盖)、think-explain(已被 think-architecture + readable 覆盖)。
- 🤔 **待定**:think-council(多视角对抗决策)—— 仅当"多条可信路径无明显赢家的 go/no-go"高频时才值得;暂列 backlog。

### 依赖
- A1/A4 不依赖数据,可立即做。
- A3(描述重写)**理想上等 C 的误调用数据**定哪些近邻最该修,但近邻对可由人读描述识别,不必硬等。

---

## 工作流 B:context_capsule 质量与数据迭代

### Problem
`context_capsule.py` 的 prompt→capsule 路由准确率有限(deepseek-v4-flash F1 ~54%,正则 fallback ~27%),用户已感到不准,但**缺少用真实数据度量和迭代的手段**;且尚未确认"不准"是否造成真实工作偏差。

### Desired Outcome
- capsule 路由质量可用真实历史 prompt 度量(不是凭感觉说"不准")。
- 能基于度量结果迭代分类器(prompt/few-shot/类别定义),并验证迭代是否真的改善。
- 类别边界定义清晰(与工作流 A 的近邻区分度同源)。

### 需求(行为契约)
- **B1 先验证危害(XY 门)**:capsule 是 soft/advisory + fail-open;在投入调优前,先确认误注入/漏注入是否造成实际工作偏差(尤其 FP 诱导过度流程),而非只是"难看"。数据来源:capsule 注入内容进 transcript,故 `(prompt, fired capsules)` 对可从 C 的 transcript 解析还原,采样人工判害。危害不足则降优先级。
- **B2 可度量**:能从真实历史 prompt 构建带标注的评测集(prompt → 应注入的 capsule),量化当前路由质量,并定位**在哪些类别对上出错**。
- **B3 可迭代(先定目标、先归因)**:先定目标 F1(达标即停,避免无限优化);错误归因区分"边界模糊"(→改/合 capsule 定义,同 A3)与"prompt/示例差"(→手调)。能基于评测集改进分类器并验证前后变化;迭代手段为**离线**,不进运行时 hook(hook 保持快、fail-open)。DSPy 为延后可选优化器,非起点。
- **B4 边界清晰**:capsule 类别定义的互斥性与工作流 A3 的技能边界用同一套"模糊边界"治理思路。

### B1 已执行(2026-06-23,kilo 480 条真实注入)
裁决:**capsule 不准是轻度、有界、可廉价修,不值 DSPy。**
- 过度触发轻:每条触发数 1 个=75% / 2 个=22% / **≥3 个仅 2.5%**(deepseek 自评 ≥3 几乎一定过度,实际很少落)。Debug(194)/Security(135) 主力且抽样判得准。
- FP 集中在三类可识别模式:① 只读分析/bug 被打 Scope/Planning(该 Debug/无);② 小 UI 改动被打 Planning/Scope(该 UI);③ **dev-long-run 的 `phase_planner/phase_coder` 角色派发 prompt 被打 Planning(该不打,系统性,最该修)**。
- harm 有界(advisory 可忽略)但有过度流程噪声 → **修法=改 capsule 定义/加负模式(尤其 hook 跳过 role-dispatch 提示),廉价;不上 DSPy(与 R4 一致)**。
- 副产:这 480 条 `(prompt, fired)` 对是现成 **eval 集种子**(B2 直接用)。
- **✅ B1→修复已落地(2026-06-23):** FP 模式 #3(role-dispatch 提示误触发 Planning)已修——context_capsule.py 加 `ROLE_DISPATCH_RE`,在 `resolve_capsule_names` 命中即返回 `[]`(deepseek 前短路,省调用),fail-open 不变;加 2 个测试,30/30 通过。模式 #1/#2(只读分析/小 UI 被误判)属分类器判断,留作 B2/B3 改定义/负例时一并处理,不上 DSPy。

### Acceptance Criteria
- [x] 有一份来自真实 prompt 的 capsule 评测集种子(kilo 480 条)和过度触发基线(≥3 仅 2.5%)。
- [ ] 能指出当前错误集中在哪些类别对(供 B4 修边界)。
- [ ] 任一次分类器改动都能用评测集给出"改善/未改善/退化"的判定。
- [ ] 运行时 hook 不新增重依赖、不破坏 fail-open。

### 依赖
- B2 的评测集**依赖工作流 C 的真实 prompt 数据**(agentsview 历史 session)。
- B1 可立即做(最小 XY 检查)。

### 待决策项(Open)
- **DSPy 的定位**:[推断] 用户提到的 "pydsy" 即 DSPy(STORM 即建于其上)。它是合适类别的**离线优化器**,但**真正瓶颈是标注数据不是优化器**;eval 集是 90% 价值。决策:先建 eval 集 + 手调,DSPy 留作后续可选优化器,**不作为起点**。

---

## 工作流 C:agentsview 观测度量层

### Problem
治理 A、B 所需的事实(哪些是死技能、调用分布、context 成本、capsule 真实表现)目前都**不可见**,只能靠推断。已有本地项目 agentsview(多 agent 观测平台:已解析 25+ agent 的 session/messages/tool_calls,有 token 成本与工具使用分析、全文搜索),是天然的数据层底座。

### Desired Outcome
agentsview 成为 skill/harness 体系的**治理观测层**:可看清单、可看用量、可看 context 成本、可体检,并能导出供 A/B 使用的数据。

### 需求(行为契约,按视图)
- **C1 技能清单(可用 skills)**:展示当前体系有哪些技能(名称/域/角色/启用状态),比静态 catalog 更新更活。
- **C2 健康体检**:检查软链完整性、wiring、hooks、重复/冲突、指向不存在技能的引用等(agent-health 能力产品化)。
- **C3 静态 context 成本**:展示各技能 description 的常驻 token 成本与总量 —— 用数据**终结"常驻成本"争论**。
- **C4 使用统计**:展示技能真实调用频率/分布,**识别死技能 vs 稀有但关键 vs 因路由差而未被用**。前提见 R5(各 agent 调用可还原性需先 spike)。**测量有效性约束:调用统计只数走 skill 机制的调用,模型 inline 完成的能力不计入;UI/解读须标明此口径,修剪前排除 inline 可能,不靠调用数单杀。**
- **C5 数据导出**:能把真实 prompt / 调用记录导出,供工作流 B 建 capsule 评测集、供工作流 A3 识别误调用近邻。

### Acceptance Criteria
- [ ] 浏览器中可查看技能清单 + 健康体检结果 + 各技能静态 description 成本。
- [ ] 可看到一段时间内的技能调用分布,并据此标注死技能候选。
- [ ] 能导出 capsule 评测集所需的真实 prompt 数据。

### 数据建模决策 ✅ 已决(2026-06-23,kilo dual-review 裁决)
**B 为主的 hybrid;明确否决"skill 伪装成 session 复用 sessions/messages"(方案 A)。** kilo 读真代码裁决污染风险=高:`stats` trigger(schema.sql:88-112)对所有 session 做无 agent 过滤的全局计数;analytics 侧无 `ExcludeAgent`(仅 usage 侧有),GetStats/GetProjects/GetAgents/ListSessions/trends 全会被假 session 污染;且 SQLite+PG 双后端过滤要成对维护——"到处加 `agent!='skills'`"是长期陷阱,远贵于独立建模。落地模型:
- **C1/C2/C3 → 独立 `skills` 维度表 + `skill_health`(或字段)+ 静态成本作维度/派生指标**,不进 sessions/messages。
- **C4 → 直接复用现有 `tool_calls.skill_name`**(join sessions 取 agent/project/time、left join skills 取 domain/role);仅当性能/历史归档需要时再物化 `skill_invocations` fact 表。来源是真实 transcript/tool_calls,不是 catalog。

### 关键技术前提(部分已由 kilo 核实)
- **✅ R5 全部已核实:C4 数据源 4/5 agent 结构化可还原。** CC=`tool_calls.skill_name`(agentsview parser 已抽,`internal/parser/content.go:51-70`,索引 idx_tool_calls_skill,PG 同);Kilo/OpenCode=各自 `~/.local/share/*/{kilo,opencode}.db` 的 `part.data` JSON(`type=tool, tool="skill", state.input.name`,kilo 1958 / opencode 51 样本实测);Droid=`tool_use` name="Skill"。**仅 Codex 需文本启发式。** agentsview 若要统计 kilo/opencode,需确认其 OpenCode/Kilo parser 是否已把 skill part 抽进 `tool_calls.skill_name`(spec 阶段核);CC 路径已就绪。
- **⚠️ tool-category 坑(kilo 发现):`NormalizeToolCategory("Skill")` 返回 `Tool`**,通用 `/analytics/tools` 只把 Skill 计入 Tool 类、不按 skill_name 细分。C4 须新增 skill-specific 聚合,**不要改通用 tool category 含义**(会破坏现有工具分析)。
- C3 拆两半:**静态描述成本=低难度(扫 catalog 直接 tokenize)**;动态 per-session capsule 注入追踪=高难度(需 hook 落日志),后者后置。

### C4 预览发现(kilo 真实数据,2026-06-23)
直接读 kilo part 表 1958 条 skill 调用得到的提前信号(仅 kilo 一家,inline 用不计数,非定论):
- **无确认死技能**:15 个 catalog 技能 kilo 0 调用,但多有合理解释(think-ideate 新建/think-refine legacy/read-droid-session 跨 agent/guard-threat-model 等稀有但关键)。
- **信号**:`assist-*`(learn/retrospect/review-doc)与 `readable-*`(rewrite/metrics/html)整组 kilo ~0 调用——大概率被 inline 干了未走 skill(印证 R6 测量坑)。值得查"该用没被发现 vs inline 本就够",不据此单杀。
- **catalog ≠ 实际全集**:kilo 调过 14 个不在 dotfiles catalog 的技能,部分高频(`behavior-anchor` x172、`dev-long-run-v2` x67、`db-query` x61、`deploy` x57 等,项目特定 + kilo 自有 harness)。**C1/C4 必须覆盖各 agent 实际拥有的技能全集,不能只读 dotfiles 52。**

### 依赖
- C1/C2/C3-静态 无前置依赖,构成 MVP。
- C4 依赖上面的 skill-invocation 识别前提验证。
- C5 是 B、A3 的上游。

---

## 路线图(依赖排序,需求级)

| 阶段 | 工作流项 | 解决 | 是否依赖数据 |
|---|---|---|---|
| **P0 并行快赢** | A1 ideation 技能 / C MVP(C1+C2+C3静态) | 真缺口 + 看得见/体检/终结成本争论 | 否 |
| **P1 数据层** | C4 使用统计 + C5 导出 | 死技能识别、为 A3/B 供数据 | 自身即产数据 |
| **P2 数据驱动治理** | A3 近邻描述重写 / B2 capsule 评测集(+B1 危害验证可提前) | 近邻区分度、capsule 可度量 | 是(用 P1 数据) |
| **P3 优化与按需** | B3 分类器迭代(DSPy 可选)/ A4 VOI 横切纪律 / think-council 评估 | capsule 提质、补 VOI、按需补能力 | 部分 |
| **Parked** | 见下 | — | — |

注:P0 两条线(ideation=dotfiles、agentsview MVP=Go)互不依赖,真并行。

## 执行方法论(每个工作流配不同 skill,不强套 /dev-long-run)

本程序**跨两个 repo(dotfiles + agentsview)+ 三个异质工作流**,不适合用单一 /dev-long-run 罩全程(后者假设单 repo、单 worktree 分支、逐 phase)。程序级编排 = 本 PRD(需求,已完成)→ 各工作流各自 /think-plan 出 spec → 各自用最贴合的方法论:

| 工作流 | 体量/性质 | 建议方法论 | 为什么不用 /dev-long-run |
|---|---|---|---|
| A1 ideation 技能 | 单 markdown 技能,叶子 | 直接 skill 起草 + A2 真实任务回放 + `verify_skills.py` | 太小、非多 phase 代码 |
| A3 描述/AGENTS.md 判别矩阵/brand-exception 归类 | ~10-15 处描述编辑 + 文档 | 聚焦编辑 pass + `verify_skills.py` | 机械careful 编辑,非多 phase |
| B1/B2/B3 capsule | 数据审计 + 评测集 + 离线调优 | 偏 `/dev-operational-task`(数据)+ 迭代调优 | 非代码多 phase |
| **C agentsview(MVP→C4→C5)** | **跨 parser/db/api/ui 多 phase 代码,异 repo(Go+Svelte)** | **先 `/think-map` 摸清架构 → `/think-plan` 出集成 spec → `/dev-long-run` 逐 phase 实现/review/commit** | **这才是 /dev-long-run 的正例** |

要点:
- **/dev-long-run 仅用于 C(agentsview)的完整建设弧**,且必须在该 repo 的 /think-map + /think-plan 之后;若只想先做 MVP,也可先 `/dev-complete` 出 MVP 再评估是否升级到 long-run。
- agentsview 是 **dotfiles 之外的 repo**,任何改动/提交走 `/guard-gitops` 意识;/dev-long-run 在该 repo 起独立 worktree。
- 程序整体不是一个 long-run,而是 **PRD → 多个独立 spec → 各自交付**,我在工作流之间停下来对齐,不一口气跑完。

## Out of Scope / Parked(显式记录,避免重复评估)

- **常驻后台 service(mac launchd)+ 状态栏菜单**:这属于"实时活动/成本监控"(产品 B),与本程序的"技能治理观测"(产品 A)是两个产品。产品 A 反思型、偶尔看,浏览器足够,**不需要**常驻/状态栏。重启条件:用户能明确说出一个"想在状态栏一眼看到的实时指标"(如当日 agent 花费、跑飞的 session、告警)。
- **gating 渐进暴露**(分类器检测活动→隐藏技能组):workflow 明确反对,见 Non-Goals。区分:**分类器门控**(F1 54%,否)≠ **用户显式加载**(用户即分类器、接近 100% 准,逻辑成立)。后者在 R2 被评估后**仍未采纳**——因为用户编程时 (a)(b) 写作需求都有、无法预测,平铺更简单,且前缀已做域路由使平铺低风险。若未来描述重写无效,fallback 优先级:additive 加亮 > 用户显式加载 > 分类器 gating。均非本程序目标。
- **独立 think-deep 技能**:见工作流 A 裁决,改为 A4 横切纪律。
- **驳回的技能**:think-redteam / think-estimate / think-confidence-check / think-introspect / think-explain。

## Risks / Open Questions

- **R1 ✅ 已决(2026-06-23):双线并行**,agentsview MVP 作为主线长杆优先启动(P1/P2 依赖它,我可largely 自主推进),ideation 作为并行叶子(没人依赖它,占 review 带宽小)。不"只先做 ideation"(那是晾着长杆)。
- **R2 ✅ 已决(2026-06-23):全平铺(单向合并)。** 用户确认编程项目里 (a) 工程文字与 (b) 内容稿都有,无法预测,故不做"用户显式加载",直接把 writing-skills 接进编程池(单向:编程池=编程+写作;写作项目池保持干净)。依赖 `write-` 前缀做域路由(模型不会拿 write-* 干编程活),仅 write-source↔think-research、write-outline↔think-plan 等 ~5 对真重叠交给 A3 消歧。**架构后果:README"writing 不暴露给编程 agent"原则反转**,需在 README/catalog 同步。account 特定技能(write-voice/hook/article-growth-diagnosis)随平铺优雅降级(无 account-style.md 时退化,且无写作意图不会被选中)。
  - **✅ 已实现(2026-06-23):** coding-skills/ 下建 12 个写作 skill 子软链 + `_shared` 子软链(关键:解决写作 skill 内 `../_shared/` 引用断裂),12 条加入 coding-skills/catalog.json(verify_skills 加 `write` 域 + `article-growth-diagnosis` brand-exception),verify 通过(64 skills)。CC 实测重扫后已看到 12 个写作 skill(scanner 跟随子软链成立)。修了 write-source 一处示例性 `scripts/find_material.py` 引用(改非路径表述,免 broken-reference)。全测试 530 通过。**[推断] 其它 4 agent 同为目录级软链同结构,应同样生效,未逐一运行端到端验证。**
- **R3 ✅ 已决(2026-06-23):先做 B1 廉价危害分流,再决定是否投入 capsule 调优。** "准确率难看 ≠ 有害":capsule 是 advisory+fail-open,FP=过度流程诱导+token 噪声(有界但真实,本对话讨论轮被反复打 scope/planning capsule 即活证据),FN=丢强化但 AGENTS.md 全局纪律兜底。B1 搭 C 的 transcript 解析(capsule 注入内容进 transcript,故 `(prompt, fired capsules)` 对可还原),采样 ~30-50 条人工判"无害噪声 vs 改变行为"。多数无害→B 降级(顶多手调几条);有实质过度流程→B 值得上 eval 集。**依赖:B 整体 gate 在 B1;B1 轻度依赖 C5 导出。**
- **R4 ✅ 已决(2026-06-23):DSPy 记为延后可选优化器,不作起点。** 先定目标 F1(advisory+fail-open,多数 prompt 0-1 标签,~70-75% 大概率够,达标即停)→ 错误归因:错在边界模糊→改/合 capsule 定义(同 A3 上游);错在 prompt/示例→手调 DEEPSEEK_SYSTEM+few-shot。仅当手调触顶仍不达标 + 预期频繁重调,才上 DSPy。最大杠杆可能是 capsule 定义边界而非分类器本身。警惕从 STORM 联想来的"工具迷恋"。
- **R5 ✅ 已核实(全部,2026-06-23):C4 跨 agent 数据可得性已查实(直接读各 agent 真实 session 库)。** 4/5 结构化可还原:CC=`Skill` tool_call(kilo review 证);Kilo/OpenCode=`part.data` JSON 里 `type=tool, tool="skill", state.input.name=<skill>`(kilo 1958 样本、opencode 51 样本,直接查 `~/.local/share/{kilo,opencode}/*.db` 证);Droid=`tool_use` name="Skill"(spike 证)。**仅 Codex 只在文本提 slash、需启发式。** 故 C4 对用户主用的 kilo/opencode **完全可做且数据丰富**。⚠️ 教训:首个 spike 误判 kilo/opencode "不可还原"(只看 `message` 元数据表、漏了 `part` 内容表),负面结论交叉核对后被证伪——子 agent 负面结论尤需验证。**测量坑仍成立(记入 C4):调用统计只数走 skill 机制的调用;模型 inline 干活不计入,"低调用数 ≠ 能力没用",不据此单杀技能。** tool-category 坑见 C 工作流。
- **R7(2026-06-23,C4 预览暴露 → 已调查,警报降级):dotfiles catalog ≠ 各 agent 实际技能全集,但多为合法项目本地技能,非 SSOT 失控。** 调查结论:`behavior-anchor`(x172)等是**项目级 skill**(各 ordo 项目 `.claude/skills/` + `scripts/lint/`),合法不在 dotfiles;`db-query/deploy/aliyun/rbac-integrate/user-cookie/kilo-config` 同属项目/kilo 特定。`dev-long-run-v2 / dev-long-loop / dev-long-task-scaffold` **当前文件系统找不到对应目录**(疑历史会话用过、已合并或改名),非现存漂移。**真正待办(非紧急,用户裁决):** ① C 工作流清单/治理须覆盖项目本地技能,不止 dotfiles 52(确认 C1/C4 scope);② 如在意,扫一眼是否还有 dev-long-run 旧变体残留需清理。**不自动 reconcile(项目 skill 是用户的)。**
- **R6 ✅ 已决(2026-06-23):有意识接受"数量↑、难度↓"取舍,不再以减少技能总数为目标。** 诚实账:本程序使编程池 ~+13(ideation +1、写作平铺 +12),被驳回 5 缺口为并入现有(+0)。workflow 已证"数量非病、清晰度才是",故目标是选择难度↓(A3 互斥描述 + 前缀域路由 + AGENTS.md 判别矩阵),非数量↓。两条硬规:(1) A2——ideation 之后任何新技能(如 council)落地前用 2-3 真实任务回放证明现有组合覆盖不了;(2) C4 修剪带证据——砍 skill 前排除"能力被 inline 干了",不靠调用数单杀。

## 验证(程序级)
- 各工作流出 spec 前,本文的对应 Acceptance Criteria 必须可映射为可验证条件。
- 涉及 agentsview 跨仓库改动、或任何远程/部署动作时,走 `/guard-gitops`。

# content-research-writer (ComposioHQ/awesome-claude-skills 子目录)
- 仓库 / owner: ComposioHQ/awesome-claude-skills（合集仓库，本条目为其子目录 `content-research-writer/`）/ 实测★ 12.6k(来源存疑，star 属于整个合集仓库而非本子目录) / vendored commit 未vendored（仅通过 GitHub WebFetch 在线读取，未落本地）/ 分类 资料驱动写作 / 核实日期 2026-06-02
- 元信息标注：**未 vendored / 合集子目录 / star 12.6k(来源存疑)**
- 资产规模事实：本子目录仅 1 个文件 `SKILL.md`（14,244 bytes），无 scripts / README / 子目录（来源：GitHub Contents API 列目录，已核）

## 思路哲学（Why）

核心定位（来自 frontmatter `description` 原文）：把写作从「solo effort」变成「collaborative partnership」——它要解决的真实痛点不是「让 AI 替你写」，而是**让 AI 做你的写作搭档（writing partner）**，在研究、提纲、起草、打磨各环节介入，同时**保留作者本人的 voice 与 style**。

几个可辨认的设计取舍（部分为 [推断]）：

1. **Voice Preservation 是第一性约束，而非附加项。** SKILL.md 专门有第 6 节 "Preserve Writer's Voice"，明确写「Suggest, don't replace」「Enhance, don't override」「If they prefer their version, support it」。这与「AI 一把梭重写全文」的同类工具形成关键差异：它把 AI 定位为 reviewer/coach，而非 ghostwriter。[推断] 这是为了对抗「AI 味」和作者失去文章所有权的痛点。

2. **流程拆成可中断的小步，而非一次出全文。** 全文围绕「section-by-section」「one section at a time」「get feedback incrementally」组织（"Pro Tips" 第 2 条、"Section Feedback" 第 5 节）。它假设长文写作的真实瓶颈是反馈回路太长，所以把反馈粒度切到「每写完一节就评一节」。

3. **资料/引用是写作的一等公民。** 它把 research 与 citation 管理做成独立环节（第 3、7 节），并强制「Verify sources before citing」「Link to original sources」（Best Practices）。[推断] 针对「资料驱动写作」这一品类的核心焦虑：claim 无出处。

4. **文件系统即状态载体。** 它不依赖任何隐藏记忆，而是要求用户用真实文件夹结构（`outline.md` / `research.md` / `draft-v1.md` / `final.md` / `feedback.md` / `sources/`）承载写作状态，并显式版本化草稿（`article-v1.md`, `article-v2.md`）。这是一个「无外部依赖、纯约定」的轻量设计。

## 特殊技巧（How）

逐条列出，均带 SKILL.md 文件证据：

1. **「Clarifying questions」开场契约。** "Instructions" 第 1 步要求先问 6 个固定问题（topic/main argument、target audience、length/format、goal=educate/persuade/entertain/explain、existing sources、writing style）。把写作意图显式化为一组槽位，避免直接动笔。证据：SKILL.md "1. Understand the Writing Project"。

2. **提纲模板自带「Research To-Do」复选框区。** 提纲 markdown 模板末尾固定有 `## Research To-Do` + `- [ ] Find data on [topic]`，把「研究缺口」嵌进提纲本身，让 outline 同时是 task list。证据：第 2 节 outline 模板。

3. **Hook 改写走「Analysis → 3 Options → Why it works」三段式。** 不是直接给一个改写，而是先做 Current Hook Analysis（what works / what could be stronger / emotional impact），再给 3 个不同策略的备选（Bold statement / Personal story / Surprising data），每个都附 `*Why it works*` 解释，最后用 4 个判定问题收尾（curiosity / value / specific / audience）。证据：第 4 节 + Example 3。这是一个非常可复用的「多策略候选 + 归因」prompt 模式。

4. **Section Feedback 结构化输出契约。** 固定 7 个区块：What Works Well / Suggestions(Clarity, Flow, Evidence, Style) / Specific Line Edits(Original→Suggested→Why) / Questions to Consider，并以 "Ready to move to next section!" 收尾形成节奏信号。证据：第 5 节模板。其中 **Original / Suggested / Why 三行式 line edit** 是高密度、可直接落地的反馈格式。

5. **引用支持三种风格并维护「running citations list」。** 显式给出 Inline、Numbered `[1]`、Footnote `^1` 三种格式样例，并要求维护一个持续累积的 `## References`。证据：第 7 节。把「引用格式」做成可选契约而非硬编码。

6. **Final Review 带 Pre-Publish Checklist。** 终审输出固定包含 Overall Assessment / Structure & Flow / Content Quality / Technical Quality / Readability / Final Polish + 一个 `Pre-Publish Checklist`（all claims sourced / citations formatted / examples clear / transitions smooth / CTA present / proofread）。证据：第 8 节。把「能否发布」收敛成可勾选门禁。

7. **按体裁分流的 Workflow 表。** 提供 4 套差异化流程：Blog Post（逐节反馈）/ Newsletter（一次成稿+快打磨）/ Technical Tutorial（含 test instructions、troubleshooting）/ Thought Leadership（先找独特角度+强 POV）。证据："Writing Workflows" 节。同一 skill 内按内容类型切换流程强度，是轻量的体裁路由。

8. **状态用真实文件 + 版本号文件名管理。** 推荐目录结构把 research 与 draft 物理分离，并显式版本化草稿。证据："File Organization" + Pro Tips 第 3、4 条。

9. **Voice 校准用周期性自检问句。** 内置 "Does this sound like you?" / "Is this the right tone?" / "Should I be more/less [formal/casual/technical]?" 作为 voice drift 的探针。证据：第 6 节。

## 可借鉴点（for writing-skills）

站在「博采众长做一套中文写作 skills 体系」的角度：

1. **把「voice preservation」做成显式约束节，而不是隐含期望。** 我们的写作 skill 可借鉴它的「Suggest, don't replace / Enhance, don't override / 用户偏好优先」三原则，并配套周期性自检问句（"这听起来像你吗"），用来对抗中文 AI 写作最大的痛点——千篇一律的 AI 腔。

2. **section-by-section 增量反馈作为默认交互节奏。** 与我们体系里 `readable-rewrite`（writer 出稿 + critic 审稿 3 轮）思路同源，可把「逐节评审 + Ready to move to next section 节奏信号」吸收进中文长文写作 skill 的循环契约。

3. **结构化反馈输出契约（What Works / Clarity-Flow-Evidence-Style / Original→Suggested→Why / Pre-Publish Checklist）。** 这套 7 区块反馈模板可直接中文化，作为我们写作 skill 的输出 schema；尤其 **Original/Suggested/Why 三行式 line edit** 与 `readable-*` 体裁规范契合，信息密度高。

4. **「Research To-Do 嵌入提纲」的数据驱动手法。** 与我们 CLAUDE.md「复杂逻辑写成表」「资料驱动写作」一致：把研究缺口做成提纲内的复选项，让 outline 即 task list，便于 agent 对照执行（呼应执行纪律里的 TodoWrite 思路）。

5. **Hook 的「多策略候选 + Why it works + 判定问句」模式可泛化。** 不止用于开头，可推广到标题、CTA、过渡句等「需要从多个角度给候选并解释取舍」的场景，是高复用的 prompt 模式。

6. **引用三风格可选 + running citations list。** 我们做资料驱动写作 skill 时，可把引用格式做成可配置契约（脚注 / 编号 / 行内），并强制「verify before cite + 链原始来源」作为 Fail Fast 门禁，契合事实纪律。

7. **反面教训也要借鉴：它没有任何脚本化/确定性强制。** 全文是自然语言约定，引用核验、checklist 全靠模型自觉。按我们 CLAUDE.md「能靠配置/脚本/hook/测试强制的规则不要只写成自然语言提醒」，我们的版本应把「引用必须可核验」「checklist 必须逐项打证据」做成可被 hook/脚本校验的门禁，而非仅口头清单。

## 资产盘点（事实）

- 实际读到的文件：`content-research-writer/SKILL.md`（14,244 bytes，已读全文）。
- 子目录文件清单（GitHub Contents API 核实）：**仅 1 个文件 SKILL.md**，无 README、无 `scripts/`、无 `references/`、无子目录。
- frontmatter：`name: content-research-writer`；`description:` 强调 research / citations / hooks / outline iteration / real-time section feedback，并自述「Transforms your writing process from solo effort to collaborative partnership」。
- SKILL.md 章节结构（实读）：When to Use / What This Skill Does（7 项）/ How to Use（Setup + Basic Workflow）/ Instructions（8 步：理解项目→协作提纲→研究→改 Hook→分节反馈→保留 voice→引用管理→终审）/ Examples（4 例，含 Teresa Torres、AI×PM 研究、Hook 改写、Section 反馈）/ Writing Workflows（4 体裁）/ Pro Tips（7 条）/ File Organization / Best Practices / Related Use Cases。

## 备注 / 风险

- **star 12.6k 来源存疑**：该 star 数 [推断] 属于整个 `awesome-claude-skills` 合集仓库，**不代表本子目录单独的受欢迎程度**。本条目为合集中的一个子目录，未单独 vendored。
- **未 vendored**：分析全部基于 2026-06-02 的在线 WebFetch（master 分支），未固定 commit，后续上游可能变动；本地无副本可回溯。
- **无确定性机制**：本 skill 纯靠自然语言约定驱动，无脚本、无 schema 校验、无 hook，引用核验与 checklist 执行全依赖模型行为，[未验证] 实际可靠性。
- 设置说明里假设用户用 Claude Code + VS Code 在专用目录写作（"Work in VS Code: Better than web Claude for long-form writing"），是面向 CLI/编辑器场景的写作工作流，而非纯对话场景。

# nexu-io/html-anything
- 仓库 / owner / 实测★ 5851 / vendored commit b54a0fba / 分类 多格式产出 / 核实日期 2026-06-02

> 说明：本项目是一个 Next.js 应用（"agentic HTML editor"），核心资产是 **75 个 `SKILL.md` 模板** + 一层 **共享设计指令（shared prompt）** + 一层 **agent 适配层**。从「中文写作 skills 体系」的角度看，真正可借鉴的是它把"内容 → 成品视觉产物"的写作意图编码进 prompt 的方式，而非 Next.js 框架代码。下面只评我实际读到的文件。

## 思路哲学（Why）

- **核心命题：Markdown 是草稿（writer-facing），HTML 才是成品（reader-facing）。** README 反复强调 "HTML is the final form for humans. Markdown is just an intermediate state during writing."（README.md L96-98）。写作的终点不是"一段排好的文字"，而是"读者实际看到的、已经排好版的视觉产物"——一张小红书卡、一个 deck、一份数据报告。这是它和"纯文字写作助手"最大的取舍差异：它把"成品形态"当成写作约束的一部分，而不是事后排版。
- **"Ship-ready" 是验收门槛，不是"我待会再修"。** README L98 明确："when generation finishes, the artifact is what your audience actually sees. No 'I'll touch it up later' pass." —— 一次产出即定稿，倒逼 prompt 把所有质量约束前置写死。
- **不自带模型，复用用户已登录的 CLI。** "We don't ship an agent. Yours is good enough."（README L325）。8 个 coding-agent CLI 自动探测 + 每个一个薄适配器，零 API key（README L196-208）。这是工程取舍，但对写作体系的启发是：**把 skill 设计成与具体模型/agent 解耦的纯 prompt 资产**。
- **反 AI-slop 是显式纪律，不是默认祈祷。** 设计纪律明确 lift 自 `alchaincyf/huashu-design` 的 Junior-Designer mode + anti-AI-slop checklist（README L105, L343, L475），并把它们硬编码进每个 `SKILL.md` 和共享指令里：CJK-first 字体栈、8px 基线网格、对比度 ≥ 4.5、禁止纯黑纯白、必须用真实数据。哲学是：**约束属于 prompt，模型不会自己自律。**
- **skill = 文件夹，不是插件。** "Skills are folders, not plugins."（README L329）。一个 skill 就是一个目录：`SKILL.md`（frontmatter + prompt body）+ 可选 `example.md` / `example.html` / `assets/`。加 skill = 加文件夹，无需改 TS 代码，picker 自动 rescan（loader.ts L5-20, L242-270）。降低贡献门槛是显式设计目标（CONTRIBUTING.md："one folder, ~3 files"）。

## 特殊技巧（How）

- **两层 prompt 组装：共享设计指令 + 模板专属 body + 用户内容尾。** `assemblePrompt({body, content, format})`（shared.ts L46-58）固定拼成 `SHARED_DESIGN_DIRECTIVES + body + 【输入格式】 + 【用户内容】`。所有 skill 共用同一份全局设计纪律（字体/网格/配色/真实性），单个 skill 只写差异化的版式与意图。这是教科书式的 DRY + Single Source of Truth：全局约束改一处，75 个 skill 全部生效（shared.ts L6-38）。

- **"内容驱动数量"作为最高优先级约束，专门对抗模型偷懒。** 共享指令开篇就写（shared.ts L9-14）："模板只定义可用版面/风格/配色/字体/组件库，**不定义** slide/帧/卡片/section 的数量……输出数量完全由【用户内容】的实际长度和信息结构决定……用户给了 12k 字符的内容，输出 4-6 张是**严重错误**。" 还显式拆解了模板里写的"6-10 张"应被理解为"短示例下的参考下限，不是上限"，"22 个锁死版面"是"可复用版式池"而非页数上限。这是对 LLM 一个真实失败模式（把内容压缩进固定模板格子）的针对性 prompt 防御。[推断] 这条是从大量实际产出回归出来的经验，因为它写得极具体、带反例。

- **frontmatter 是结构化的 skill 元数据 schema，picker 直接消费。** `SkillFrontmatter`（loader.ts L24-44）字段含 `mode/scenario/category/aspect_hint/featured/recommended/tags` + 一组 `example_*`（来源 URL/label 用于署名）。`recommended:` 是数字排序键（越小越靠前，进 Featured 组）；`scenario` 是固定词表（scenarios.ts L15-28：marketing/engineering/product/design/finance/hr/sales/personal/education/creator/video）。**写作启发：用 frontmatter 把"什么时候用这个 skill / 给谁 / 产物长什么样"做成机器可读字段，而不是埋在散文里。**

- **依赖极简、零依赖的 frontmatter parser。** loader.ts L94-150 手写了一个 tiny parser（只处理字符串/整数/单行数组字面量），不引 YAML 库。配 `isValidBundledId`（kebab-case）/`isValidSkillId`（marketplace namespaced id 用 `pkg-owner__repo--id`）做 id 白名单校验（L208-220），fail-fast 拒绝非法 id。

- **每个 SKILL.md 把"硬性铁律"写成可违反即判错的断言。** 例：`deck-swiss-international/SKILL.md` L55-63 —— "**只用直角**：全程 `border-radius: 0`。圆角 = 立刻违反。""**不许编造**：数字必须来自用户输入，图表柱高 = 真实数据按比例。" `deck-guizang-editorial` L25-30 把 5 套调色板的 hex 全部写死并加 "**严禁改 hex、严禁混用**"。约束写成"X = 立刻违反"这种可判定句式，而不是"尽量""建议"。

- **把已知技术坑直接写进 prompt 当护栏。** `data-report/SKILL.md` L23 —— "图表容器必须有固定高度……Chart.js 用 `responsive:true,maintainAspectRatio:false` 时若父容器没有显式高度，会陷入 ResizeObserver 死循环，图表无限增高直至卡死浏览器。**绝对不要**直接给 canvas 写 `height=`。" 把一个具体 bug 的成因 + 正确写法写进 skill body，让模型避坑。

- **"diff-edit / 最小化差异编辑"模式：第二次生成不重画。** convert/route.ts L30-62 `buildEditPrompt`：当 task 已有 HTML，客户端把旧 HTML + 旧内容 + 新内容一起发回，prompt 命令模型"仅根据新旧内容差异替换对应文字/数据节点……字体配色布局栅格组件结构动画都不许改……新旧只差几个字也只改那几个字，不要顺手优化或重排。" 显式目的（L21-27 注释）："Saves output tokens AND prevents creative drift between runs." —— **把"改稿"和"重写"区分成两种 prompt，防止模型每次重排导致风格漂移。**

- **禁止落盘工具 + 强制流式输出正文。** 共享指令 L17-23 硬禁 Write/Edit/Bash 等文件工具，要求"直接把完整 HTML 作为助手回复正文流式输出……第一个字符必须是 `<`……不要先说'我来生成'。" 配合 SSE 把 agent stdout 的 text delta 实时打进 iframe srcdoc（README L116, L345-347）。**输出契约写死成"裸正文、首字符受控、无寒暄"，便于程序解析。**

- **示例即产物：每个 skill 附 `example.html` 可直接打开。** loader.ts L227-229 读 `example.html`/`example.md`；README L38 说 Featured 8 个 skill "ships a real example.html you can open straight from the repo"。frontmatter 的 `example_source_url/label` 还保留 upstream 署名（如 guizang/kami）。**写作启发：skill 自带"金样本输出"，既是文档也是回归基准。**

- **marketplace 安装：从公开 GitHub repo 拉 skill 包，带安全上限。** skills/install.ts 支持 `owner/repo` / URL / `#ref`，两种布局（根 `SKILL.md` 单 skill / `skills/<id>/SKILL.md` 多 skill 包）；带 SKILL_MD/EXAMPLE/TARBALL 大小上限 + 解压上限防 gzip bomb（L26-36），id 命名空间化避免冲突。[推断] 这是为"社区贡献 prompt 资产"准备的分发机制。

## 可借鉴点（for writing-skills）

1. **共享 directive + skill 专属 body 的两层结构，直接对应我们的全局 CLAUDE.md / AGENTS.md + 单 skill 关系。** 它把"全局写作纪律"（语气、留白、真实性、盘古之白）抽到一份 `SHARED_DESIGN_DIRECTIVES` 单点维护，单 skill 只写差异。我们的中文写作体系可以同样抽出一份"中文写作硬约束"（如：中英文之间半角空格、不用 em dash、不堆砌形容词、引用必须真实）作为所有 writing skill 的共享前缀。

2. **"内容驱动数量/篇幅"这条反偷懒约束值得直接搬。** 中文写作里对应的失败模式是"模型把长材料压缩成固定几段/几条"。可以写一条等价约束："产出的小节/要点数量由源材料信息结构决定，不许为凑模板而压缩或丢弃信息；模板里的'3-5 条'是短材料下限不是上限。"

3. **把质量约束写成"可违反即判错"的断言句式，而不是软建议。** "圆角 = 立刻违反""输出 4-6 张是严重错误"这种写法比"建议保持简洁"对模型更有效。我们的 readable-* / 写作 skill 可以把禁用项写成同样硬的判定句。

4. **frontmatter 做成机器可读的触发/适用元数据。** `scenario`（固定词表）+ `aspect_hint`（产物形态）+ `recommended`（排序）+ `example_*`（金样本与署名）。我们的 skill 已有 description 触发前缀约束，可借鉴它把"适用场景/产物形态/推荐度/示例来源"也结构化进 frontmatter，便于路由与展示。

5. **"diff-edit vs 从零生成"分成两套 prompt 防风格漂移。** 中文长文改稿同理：改稿 prompt 应明确"保留原结构与语气，只动差异部分，不要顺手重排/润色全文"。这能省 token 也能稳住风格——可落进一个独立的"writing-revise"模式。

6. **把已知坑写进 skill body 当护栏（data-report 的 Chart.js 死循环）。** 对应到写作：把高频踩坑（如"标题党""结论先行后无支撑""把推断写成事实"）连同正确写法写进 skill，而不是只说"注意质量"。这与本仓库 Truth Directive（[推断]/[猜测]/[未验证] 标注）精神一致。

7. **每个 skill 自带金样本（example.html / example.md）作为文档 + 回归基准。** 我们的写作 skill 可附"标准输入 → 标准输出"样例对，既降低使用者理解成本，也可做产出质量回归。

8. **skill = 文件夹、加 skill 零代码改动、picker 自动发现。** 与我们 `skills/` 目录 + `verify_skills.py` 校验的方向一致；它的"id 白名单 + frontmatter schema + 自动 rescan"可作为 skill 注册健壮性的参考。

## 资产盘点（事实）

实际读到的关键文件：

- `README.md`（全量读）/ `AGENTS.md` / `CLAUDE.md`（`@AGENTS.md` 引用）/ `CONTRIBUTING.md`（头部）。
- prompt 组装核心：`next/src/lib/templates/shared.ts`（`SHARED_DESIGN_DIRECTIVES` + `assemblePrompt`）。
- skill 注册/加载：`next/src/lib/templates/loader.ts`（frontmatter schema + parser + listSkills/loadSkill）、`next/src/lib/templates/scenarios.ts`（场景词表）、`next/src/lib/templates/index.ts`（未逐行读，[未验证] 细节）。
- 流式 + 改稿契约：`next/src/app/api/convert/route.ts`（`assemblePrompt` 调用、`buildEditPrompt`、SSE）。
- marketplace 安装：`next/src/lib/skills/install.ts`（GitHub 拉包 + 大小/解压上限）；`registry.ts` / `paths.ts`（未逐行读）。
- 逐字读过的 SKILL.md（5 个）：`deck-guizang-editorial`、`deck-swiss-international`、`card-xiaohongshu`、`video-hyperframes`、`data-report`、`pm-spec`。
- skill 目录共 75 个（README 声明，与 `next/src/lib/templates/skills/` 下文件夹数量一致，已 Glob 列出全部），分 mode：prototype / deck(20) / frame·vfx·mockup(12) / social / office·doc。每个 skill 多含 `SKILL.md` + 可选 `example.html`/`example.md`/`assets/`（如 `competitive-teardown/assets/` 含 3 个 html 片段）。
- agent 适配层：`next/src/lib/agents/`（README/CONTRIBUTING 多次引用 `argv.ts`/`detect.ts`/`invoke.ts`，本次未逐行读，[未验证] 内部实现）。

## 备注 / 风险

- **本项目主体是产品代码（Next.js app），不是纯 prompt skill 库。** 对"中文写作 skills 体系"可借鉴的是 prompt 设计哲学与结构，框架/导出/SSE/sandbox 层与我们的目标关系不大。
- **README 营销色彩较重**（大量 ★ 数字、上游项目背书、badge）。"实测★ 5851" 与 README 中 open-design "40k★" 等数字未在本地源码内交叉验证，仅为 README 自述，[未验证]。
- **大量设计纪律自述 lift 自上游**（huashu-design / guizang / kami / mdnice / hyperframes）。本分析只核实了它们如何落进 `SKILL.md` 与 `shared.ts`，未核实 upstream 原始内容，[未验证] upstream 一致性。
- 本次未逐行读 `index.ts`、`agents/*`、`export/*`、`registry.ts`，相关结论以 README/CONTRIBUTING 自述 + 已读文件交叉为准，已标注 [未验证] 之处不应当作事实引用。
- 反 AI-slop 约束（对比度/网格/真实数据）的实际效果属于 LLM 行为，[推断]，不保证模型每次遵守。

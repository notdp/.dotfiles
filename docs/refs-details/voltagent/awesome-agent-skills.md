# voltagent/awesome-agent-skills

- 上游仓库: `https://github.com/voltagent/awesome-agent-skills`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/voltagent/awesome-agent-skills`
- Source SHA: `f4a2d027b25b5526f85ab3567215d926f332a4ae`（heads/main），分析日期: 2026-06-02
- 一句话总结: 一个人工策展(非 AI 批量生成)的 Agent Skills "awesome list" 索引仓库，只收录开发团队官方与社区已验证的 skill 链接，并附带一套跨工具安装路径表与最小质量门禁，自身不托管任何 skill 实现。

## 仓库性质澄清(先验事实)

这是一个**纯目录/索引型仓库**，不是 skill 实现库。整个仓库只有 4 个有效文件:

- `README.md`(1787 行，223KB)—— 唯一的内容载体，1114 条 skill 链接条目
- `CONTRIBUTING.md` —— 收录规则
- `LICENSE`(MIT)
- `.gitignore`

`.gitignore` 明确排除了 `skills/`、`skills/downloads/`、`scripts/download-skills.py`(证据: `.gitignore` 全文)。也就是说**存在一个本地下载脚本与下载目录，但被刻意排除出版本库**——仓库只维护"指针"，不维护"内容"。本地 clone 中这些文件不存在，所以下面对下载脚本的判断标注为 [推断]。

因此本文的"思路哲学/技巧"分析对象是**策展方法论与索引结构设计**，而不是某个 SKILL.md 的 prompt 写法。原始任务模板中"抽样读关键 SKILL.md/hooks/安装脚本"在本仓库**不适用**——这些都不在仓库内，全部是外链到各 author 自己的 repo 或 `officialskills.sh` 平台。

## 思路哲学 (Why)

### 它在解决什么真问题

Skill 生态正在经历"AI 批量生成 skill 灌水"的稀释。README 开篇第一句就把自己定位为反例: "Unlike many bulk-generated skill repositories, this collection focuses on real-world Agent Skills created and used by actual engineering teams, not mass AI-generated stuff"(README:37)。徽章直接写 "Hand-picked, not AI-slop generated"(README:11)。它解决的真问题是**信噪比**:当 skill 数量爆炸时，发现"值得用的 skill"比"写新 skill"更难。

### 设计原则(逐条带证据)

- **策展而非生产 / 指针而非内容**: "This repository curates links only. Each skill lives in its own repo"(CONTRIBUTING.md)。仓库只存链接，每个 skill 留在原 author 的 repo,保证单一事实源在上游、避免 fork 腐烂。这是 awesome-list 范式的核心,也是它跟"把几百个 skill 塞进一个 mono-repo"型集合的根本区别。
- **社会证明优先于新颖性**: 收录硬门槛是"必须有真实社区使用",并显式拒绝新鲜 skill: "Skill must have real community usage... Brand new skills that were just created are not accepted. Give your skill time to mature"(CONTRIBUTING.md);README 尾部再次强调 "Please don't submit skills you created 3 hours ago"(README:1774)。用**采纳度**而非作者自评作为质量代理指标。
- **官方团队署名作为信任锚**: 目录把"Official Skills by"放在最前,列出 Anthropic、Google、Vercel、Stripe、Cloudflare、Trail of Bits 等(README:39-41、52-70)。署名(author/org prefix 强制要求,CONTRIBUTING.md)既是信任信号,也是命名空间防撞。
- **跨工具可移植是一等公民**: 提供一张"Skills Paths for Other AI Coding Assistants"表(README:1740-1749),把同一份 skill 在 8 个 agent(Antigravity / Claude Code / Codex / Cursor / Gemini CLI / Copilot / OpenCode / Windsurf)的 project 路径与 global 路径并列。世界观是: **skill 是可跨 harness 移植的资产**,不绑定单一工具——这跟本仓库 AGENTS.md "跨 agent 兼容"约定同源。
- **策展 ≠ 背书安全**: 显式声明 "Skills in this list are curated, not audited"(README:1722),并把安全责任明确推回使用者: "Agent skills can include prompt injections, tool poisoning, hidden malware payloads... Always review the code and use skills at your own discretion"(README:1734)。还推荐了第三方扫描器(Snyk agent-scan、Agent Trust Hub,README:1729-1732)。这是**诚实的边界声明**:把"我帮你筛过"与"我替你担保"两件事切开。
- **最小质量门禁而非全量规范**: 只定义 4 条可机器/人工核验的硬标准(见下),不追求"完整 skill 编写指南"。

### 与"堆功能"型 skill 集的根本区别

堆功能型(如某些 mono-repo)追求"我这里 skill 最多最全",倾向 AI 批量生成填充。本仓库反过来: **用准入门槛和社会证明做减法**,价值主张是"我替你过滤掉了 slop"。它的资产不是 skill 代码,而是**一份被维护的信任白名单 + 一张跨工具落地映射表**。

## 特殊技巧 (How)

### 1. 双层链接策略: 平台中转 + 源仓库直链

1114 条条目里,588 条指向 `officialskills.sh/<org>/skills/<name>`,544 条直接指向 `github.com/.../tree/main/skills/<name>`(证据: grep 计数)。官方团队 skill 多走 `officialskills.sh` 中转页(README:105-130),社区 skill 多走 GitHub 直链(如 README:1700-1710 的 n8n 条目)。`officialskills.sh` 是 VoltAgent 自己的分发平台(README:92 "appear across the officialskills.sh platform")。这等于**用 awesome-list 给自家平台导流,同时平台页又能提供统一的安装/预览体验**——这是它独有的商业-技术耦合手法,非纯社区 list。[推断] 中转页比裸 GitHub 路径更利于一键安装。

### 2. 条目格式即微契约

CONTRIBUTING.md 把条目格式锁死为:
`- **[author/skill-name](url)** - Short description`
并约束 "Description must be short, 10 words or fewer. No lengthy paragraphs"。这条 10 词上限不是排版洁癖——**短描述本身就是 skill 触发语义的浓缩**,迫使每条用可被 agent 匹配的关键词。实际条目高度遵守(例: "Prioritize feature requests by theme, impact, effort, and risk",README:1060)。

### 3. 用 `<details>/<summary>` 折叠对抗 223KB 巨型 README

44 个 `### ` 分区,几乎每个团队分区都包到 `<details><summary><h3>...</h3></summary>` 里(README:103、225、252...)。这是用 GitHub 原生折叠把一个 1787 行的目录变成可扫描的索引——**README 自身就是一次"渐进式披露"的实践**(默认折叠,点开才加载注意力),与它写进质量标准的 progressive disclosure 原则自洽。

### 4. 质量门禁压缩成 4 条可核验标准

`Skill Quality Standards > Quality Criteria` 表(README:1750-1765)只列 4 条,且每条都是可核验的硬规则,而非空泛倡导:

| 标准 | 机制化要点 |
|------|-----------|
| Description | 第三人称,同时写 *what* 和 *when*,用 agent 能匹配的具体关键词("PostgreSQL migration" 而非 "database stuff") |
| Progressive disclosure | 顶层 metadata < ~100 tokens;skill body < 500 行;大文档/schema 按需加载,不内联 |
| No absolute paths | 禁止 `/Users/alice/` 这类机器特定路径,用相对路径或 `$HOME`/`$PROJECT_ROOT` |
| Scoped tools | 只申请真正需要的工具,禁止 `"tools": ["*"]`,显式声明工具依赖 |

这 4 条全部是**可被 lint/hook 静态扫描的**(token 数、行数、绝对路径正则、`tools: ["*"]` 匹配)。这是它最可被本仓库吸收的部分。

### 5. 跨工具路径表作为"移植速查表"

README:1740-1749 的表把 8 个 agent 的 project/global 路径硬编码并列,等于一份 **skill 落地的 cheat sheet**。新颖点在于把"同一资产在不同 harness 的安放位置"做成结构化表,而非散文描述。

### 6. 安全免责与扫描器推荐分离

把"curated"与"audited"在两处反复切开(README:1722、1781),并主动给出外部扫描工具链接(README:1729-1732)。这是**诚实标注不确定性**的范例:不假装策展等于安全审计。

### 哪些是真正新颖/反直觉的

- **反直觉**: 一个 skill 仓库**故意不放任何 skill**,只放指针——价值在筛选,不在持有。
- **反直觉**: 准入门槛要求 skill "成熟一段时间再来"(拒绝 3 小时前创建的),用时间和采纳度做质量过滤,这与开源社区"鼓励早提交"的常规相反。
- **新颖**: 把 README 本身用 `<details>` 折叠 + 10 词描述上限,做成一个"对 agent/人都可扫描"的索引产物。
- **新颖但需警惕**: awesome-list 与自家分发平台(officialskills.sh)耦合导流。

## 资产盘点

- **skill 链接条目**: 1114 条(`grep -c "^- \*\*\["`);徽章自称 "1424+"(README:21,含未折叠/平台侧)。
- **分区**: 44 个 `### ` 团队/主题分区。官方团队约 50+ 个署名分区(Anthropic / Google / Vercel / Stripe / Cloudflare / Netlify / Trail of Bits / Sentry / Microsoft / OpenAI / Figma / MongoDB / Redis / NVIDIA 等)。
- **社区分区(自定义 taxonomy)**: Productivity and Collaboration(README:1529)、Development and Testing(README:1568)、Context Engineering(README:1649)等 ——把社区 skill 按**能力域**而非作者归类,其中 "Context Engineering" 作为独立一类是该领域成熟度的信号。
- **链接分布**: officialskills.sh 588 条 / github.com 544 条。
- **质量标准**: 4 条(Description / Progressive disclosure / No absolute paths / Scoped tools)。
- **跨工具路径表**: 8 个 agent × (project path, global path, docs)。
- **实际可执行资产**: **0**。无 SKILL.md、无 commands、无 hooks、无安装脚本入库(`download-skills.py` 被 .gitignore 排除,本地不存在)。[推断] 该脚本用于按 README 链接批量下载 skill 到本地 `skills/` 目录。

## 与本仓库的关联点

(详细裁决留给后续 plan,这里只列借鉴价值)

1. **4 条质量门禁可直接做成 `scripts/verify_skills.py` 的增量校验**: 本仓库已有 verify_skills.py 强制 description 触发前缀。可补充: (a) skill body 行数上限(它建议 < 500 行);(b) 顶层 metadata token 预算 < ~100;(c) 绝对路径(`/Users/...`)扫描;(d) `tools: ["*"]` 黑名单。其中 (c) 与本仓库 AGENTS.md "默认 ASCII / 不硬编码机器路径"取向一致,且是确定性可扫描的。

2. **"description = what + when + 可匹配关键词"** 与本仓库 skill-authoring 的触发语义约束同向,可作为外部佐证补进 `docs/software-engineering-research/skill-authoring.md`。

3. **跨工具路径表**: 本仓库 AGENTS.md 已声明"跨 agent 兼容"。这张 8-agent 路径表可作为参考资料沉淀进 docs,帮助验证我们的 skill 是否真能落到 Codex/Cursor/Gemini 等路径。

4. **"curated ≠ audited" 的诚实边界声明**: 与本仓库"事实纪律 / 标注 [未验证]"哲学高度一致,可作为 refs 引用案例,但无需吸收为规则(我们已有更严格的事实纪律)。

5. **社区 taxonomy(Context Engineering 作为独立能力域)**: 可作为审视本仓库 skill 路由分类(think-/dev-/guard-/readable-/assist-)是否覆盖"上下文工程"这一维度的外部对照。

6. **反面警示(不建议吸收)**: officialskills.sh 平台导流耦合、用"成熟度门槛"拒绝新 skill——这些是该仓库的运营选择,不适合本仓库的私有 skill 体系。

# dontbesilent2025/dbskill
- 仓库 / owner dontbesilent2025 / 实测★ ~5.98k / vendored commit 70031d59 / 分类 选题/商业表达诊断 / 核实日期 2026-06-02 / VERSION 2.14.1

## 思路哲学（Why）

核心洞察是把「一个人长期产出的真实内容」当作可以工程化提炼的原料，再把提炼物固化成一组诊断型 skill。作者宣称从 12,307 条推文里筛出 4,201 条实质内容、提炼成 4,176 个「知识原子」（`知识库/原子库/README.md`），再据此手写 21 个 skill。这不是「让 AI 帮你写作」的工具，而是「用作者本人的判断框架替你做诊断」的工具。

它要解决的真实痛点不是「不会写」，而是「问题问错了」。`dbs-diagnosis` 开篇直接写：「你的核心工作不是回答问题，是消解问题。8000+ 人付费问过商业问题，其中只有 0.9% 真正被解答了，99.1% 是被消解掉的——因为问题本身是错的」（`skills/dbs-diagnosis/SKILL.md:14`）。整个体系的设计哲学是「先证伪问题，再回答问题」：标题、开头、商业模式都不是孤立技巧，而是被一套「公理 + 消解漏斗 + 检验清单」统一约束。

关键取舍：
- 强观点、强人格，而不是中立助手。每个 skill 都有「说话风格」「绝对不要做的事」段落，明确禁止说「每个人情况不同」「需要更多信息才能判断」「去做市场调研」（`skills/dbs-diagnosis/SKILL.md:442-448`）。它故意牺牲「政治正确的全面性」换取「能下判断的锋利度」。
- 反「去 AI 味」。`dbs-ai-check` 反对把 AI 特征删掉伪装成人，主张「AI 味的本质是太完美」，改写必须回到用户自己的真实意图（`skills/dbs-ai-check/SKILL.md:14-32`）。这是一个少见的、把检测工具的目的从「规避检测」翻转成「找回作者声音」的立场。
- 诊断是可累积资产，不是一次性问答。`dbs-save/restore/report` 三件套把「单次问诊」升级成「私人医生」，状态落在 `~/.dbs/sessions/{项目}/`（`skills/dbs-save/SKILL.md:31-37`）。

## 特殊技巧（How）

1. 路由器 skill 做纯分发、零诊断。`dbs` 入口 skill 只有 92 行，开宗明义「你不做诊断，不做分析，不给建议。你只做路由」，用一张「用户意图信号 → 路由到 → 一句话说明」表 + 一个兜底澄清问题（编号选项 1-15）把流量分到 20 个专项 skill（`skills/dbs/SKILL.md:14,18-40`）。这是把「主入口」和「能力实现」彻底解耦的范式。

2. 公理化 prompt：把判断标准提成「非谈判项」。`dbs-diagnosis` 把方法论压成 6 条编号公理（商业模式是客观存在、定价即产品、99% 创业问题是心理问题……），并要求「每个判断都能追溯到 6 条公理」（`skills/dbs-diagnosis/SKILL.md:18-42,435`）。公理是显式数据，不是散落在正文的 tacit knowledge。

3. 概率标注的「消解漏斗」。诊断不是一次跑完，而是分 5 层逐层过滤（语言陷阱 25% → 假设错误 25% → 逻辑错误 20% → 事实前提 1.5% → 信息充分性 2.5%），每层都给出占比、检测方法、固定话术模板，并强制「每消解一层就停下来等用户回应，不要一次性跑完」（`skills/dbs-diagnosis/SKILL.md:97-189`）。概率数字本身是表达技巧——它让用户相信「你的问题大概率会被证伪」。

4. 公式库 + 编号溯源的输出契约。`dbs-xhs-title` 把自己定义为「公式匹配器，不是标题生成器」，75 个公式按 12 类心理触发器编号内联，硬规则是「你生成的每一个标题都必须能追溯到公式库中的具体公式编号，不准自由发挥」，输出里强制带 `公式 #编号` + 原始爆款举例 + 一句话理由（`skills/dbs-xhs-title/SKILL.md:12-15,95-150`）。这把「可信度」绑定到「可溯源」上。

5. 逐处引用 + 严重度分级的检测报告体裁。`dbs-ai-check` 按文本顺序逐处引用原文、标 `特征 #N + 🔴/⚠️/💡 严重度`，并配一张「追问映射表」——每个 AI 特征对应一个「背后意图 + 一个追问」，改写阶段一次只问一个问题（`skills/dbs-ai-check/SKILL.md:42-71,104-119`）。这是「诊断默认只读、改写要显式授权」的输出契约。

6. 「术语对用户隐身」的措辞约定。`dbs-save` 专门有一段把内部术语映射成用户语言：snapshot→存档、session→对话、slug→项目，并规定 frontmatter 字段名「不出现在用户对话里」（`skills/dbs-save/SKILL.md:18-26`）。skill 同时维护「机器可读的状态文件 schema」和「人类可读的对话表层」，两层不互相污染。

7. 状态文件的固定 schema。存档是 YAML frontmatter（slug/timestamp/title/source_skill/status/next_skill）+ 6 段固定 body（主诉/已得出结论/已否决方向/待验证假设/推荐下一步/备注），路径 `~/.dbs/sessions/{slug}/{YYYYMMDD-HHMMSS}-{title-slug}.md`，并要求用 `python3 ... isoformat` 生成合规时间戳（`skills/dbs-save/SKILL.md:99-142`）。`next_skill` 字段是给 `dbs-restore` 自动接续用的桥。

8. 条件触发的「下一步建议」做 skill 间编排。`dbs-diagnosis` 末尾有一张「触发条件 → 推荐话术」表，把诊断结果路由到 `dbs-action`/`dbs-benchmark`/`dbs-content`/`dbs-decision` 等（`skills/dbs-diagnosis/SKILL.md:454-466`）。skill 之间不是孤岛，而是用「条件触发 + 一句话话术」串成工作流，且强调「不是每次都推荐」。

9. 双层资产：手写 SKILL.md + 自动生成知识包/原子库。`知识库/Skill知识包/*.md` 是从原子库按 skill 聚合生成的「深度参考」（如 `diagnosis_公理与诊断框架.md` 标注「共 500 个知识原子 | 自动生成」），SKILL.md 末尾用 `> 📚 深度参考：...` 软引用（`skills/dbs-diagnosis/SKILL.md:470`）。原子库是带 `confidence`/`type`/`topics`/`skills` 标签的 JSONL，可按季度切分、可单独复用。

10. 重型 skill 的自包含 + 构建期裁剪。`dbs-content-system` 是单目录重型 skill（SKILL.md + scaffold + templates + tools + docs），明确「本 skill 必须自包含，不要假设安装后还能读仓库里的知识包」（`skills/dbs-content-system/SKILL.md:16-18`）。`tools/build-skills.sh` 在打包时用 `grep -Eo '知识库/[^...]*\.md'` 扫描 SKILL.md 引用的知识包并随 zip 一起带上，再按使用场景分组打成「一个 zip 一个 skill」供 Trae Solo 安装。

11. 内容工程的「先审计再建工程」门槛。`dbs-content-system` 设硬门槛（≥50 个文本文件或 ≥80000 字、≥2 类来源、必须先说清纳入/排除边界），不达标就只出审计结论 + 降级路径，不空转建工程；并把内容拆成 5 类「内容单元」（QST/CON/OPI/CAS/SOL）作为最小语义对象而非按文件夹整理（`skills/dbs-content-system/SKILL.md:52-104,122-163`）。

## 可借鉴点（for writing-skills）

1. 「消解优先于回答」可直接移植成一个中文写作前置 skill：在动笔前先审计选题/标题/命题里的模糊词、隐含假设、相关性当因果，多数「不会写」其实是「没想清楚」。我们的 `think-scope`/`think-refine` 已有类似精神，但 dbskill 的「分层 + 概率标注 + 固定话术 + 每层停下对话」的颗粒度更适合做成写作领域的诊断 skill。

2. 公理化 + 编号溯源是对抗「AI 泛泛而谈」的强手段。我们的写作 skill 可以把判断标准提成显式编号规则表（类似 `dbs-xhs-title` 的 5 条铁律 + 75 公式编号），并要求每个产出能追溯到具体规则号，天然兼容我们「数据驱动、规则表优先于一堆判断」的硬约束。

3. 「检测默认只读、改写需显式授权 + 一次只问一个问题」是一个干净的输出契约，值得做成我们写作类 skill 的通用交互模板（对应 `dbs-ai-check`）。它避免了 AI 一上来就大段重写、夺走作者控制权。

4. 状态三件套（save/restore/report）的 schema + 措辞分层值得借鉴：固定 frontmatter schema 做机器接续、`next_skill` 字段做自动路由、术语对用户隐身。我们若要做「跨会话的写作项目记忆」，这是现成范式，且落地成本低（纯本地 markdown，无依赖）。

5. 路由器 skill 的「纯分发、零实现 + 意图信号表 + 兜底编号选项」是 skill 体系入口的好范式，比我们当前 CLAUDE.md 里那张长路由表更适合做成可触发的交互式入口（我们的 `workflow-helper` 可吸收这种「信号→路由→一句话确认→立即执行」的结构）。

6. 「下一步建议」用条件触发表做 skill 编排，比硬编码 pipeline 灵活：每个 skill 末尾挂一张「触发条件→推荐 skill→一句话话术」，且强调「不是每次都推荐」。可借鉴到我们 `dev-*`/`guard-*` 链路的收尾推荐。

7. 双层资产架构（手写 prompt 层 + 自动生成的证据/知识库层 + 构建期按引用裁剪打包）是把「大量原始素材」沉淀成可复用 skill 的工程化路径。对我们「做一套中文写作 skills 体系」尤其相关：可以把作者/团队的真实写作语料提炼成带 confidence 标签的原子库，再喂给各写作 skill 作深度参考。

8. 反「去 AI 味」的立场对我们写作体系是一个明确的价值锚：检测工具的目的应是「帮作者找回自己的声音」而非「骗过检测器」，这与我们「可读性优先、保留事实和声音」一致，可写进写作 skill 的哲学层。

## 资产盘点（事实）

实际读到的关键文件：
- `README.md`（364 行）、`VERSION`（2.14.1）、`.claude-plugin/marketplace.json`（声明 20 个 plugin 条目，README/营销文案称「21 个 skill」）
- `tools/build-skills.sh`：分组 + 自包含打包 + 按 SKILL.md 引用裁剪知识包的构建脚本
- 路由器：`skills/dbs/SKILL.md`（92 行，纯路由）
- 完整读：`skills/dbs-diagnosis/SKILL.md`（516 行，6 公理 + 问诊/体检双模式 + 消解漏斗 + 七项检验 + 内联案例库 + 条件触发下一步）、`skills/dbs-save/SKILL.md`（231 行，状态 schema）
- 重点读：`skills/dbs-xhs-title/SKILL.md`（736 行，75 公式 + 12 类触发器 + 编号溯源契约）、`skills/dbs-ai-check/SKILL.md`（272 行，22 特征 + 追问映射表）、`skills/dbs-content-system/SKILL.md`（549 行，审计门槛 + 5 类内容单元 + 自包含约束）
- skill 清单（共 21 个目录）：`dbs`（路由）、`dbs-diagnosis`、`dbs-benchmark`、`dbs-content`、`dbs-content-system`、`dbs-hook`、`dbs-xhs-title`、`dbs-ai-check`、`dbs-slowisfast`、`dbs-action`、`dbs-deconstruct`、`dbs-goal`、`dbs-good-question`、`dbs-decision`、`dbs-learning`、`dbs-save`、`dbs-restore`、`dbs-report`、`dbs-chatroom`、`dbs-chatroom-austrian`、`dbs-agent-migration`
- 知识库：`知识库/原子库/atoms.jsonl`（4,176 条全量 + 6 个按季度切分文件，带 id/knowledge/original/url/date/topics/skills/type/confidence 字段）、`知识库/Skill知识包/*.md`（14 份按 skill 聚合的自动生成深度参考）、`知识库/高频概念词典.md`（46 个高频术语词频表）
- `skills/dbs-content-system/` 子资产：10 个 `tools/*.js`（init/抽取/装配/去重/link-map 等）、7 个 `templates/*.md`（观点/案例/概念/方案/问题单元 + 选题装配 + 主题地图模板）、`scaffold/`（root 的 AGENTS.md/CLAUDE.md/SOURCE_OF_TRUTH.md + rules/*.md）、`docs/quickstart.md`、`docs/acceptance.md`

## 备注 / 风险

- 数量口径不一致：`marketplace.json` 的 `plugins` 数组只列了 20 个条目（含路由 `dbs`），但 README、build 脚本分组与营销文案均称「21 个 skill」。`skills/` 下确为 21 个目录。[推断] marketplace.json 漏列了 1 个（疑似 `dbs-chatroom` 与 `dbs-chatroom-austrian` 之一未登记为独立 plugin），但我未逐条比对全部条目，标 [推断]。
- 营销数字（12,307 推文、8000+ 付费、0.9%/99.1% 消解率、4,176 原子）来自项目自述（README、原子库 README、SKILL 正文）；我只独立核实了原子库 JSONL 行数（atoms.jsonl 共 4,176 行，与自述一致）。推文总量、付费人数、消解率等无法独立验证，标 [未验证]。
- 这是一套强人格、强观点的诊断体系，其「公理」是作者个人商业立场（如「反需求调研」「不要找擅长的事赚钱」），直接移植会把作者的价值判断带进我们的体系；借鉴时应取「公理化 + 编号溯源 + 消解漏斗」的形式骨架，而非其具体商业主张。
- 我未逐行读完全部 21 个 SKILL.md（完整读 2 个、重点读 3 个、其余读 frontmatter + marketplace 描述 + README 表格）；`dbs-decision`/`dbs-goal`/`dbs-good-question`/`dbs-chatroom*`/`dbs-agent-migration` 等的内部机制细节标 [未验证]，未在本文展开。
- `dbs-content-system/tools/*.js` 我只确认了文件名与用途归类，未逐个读实现，其行为细节标 [未验证]。

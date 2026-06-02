# 中文内容创作 Skills 横向综合（10 个开源项目）

本文综合分析 10 个中文内容创作相关开源项目，目的是为后续设计「面向中文写作的 skills 体系」提供输入。
所有结论基于各项目分析摘要（见 `docs/writing-refs-details/`）与对 `writing-refs/` 下 vendored 源码的抽样复核（Humanizer-zh SKILL.md、dbskill README、guizang-ppt validate-swiss-deck.mjs、guizang-social-card references 目录结构）。

涉及的项目（缩写）：

| 缩写 | 项目 | 定位 |
| :--- | :--- | :--- |
| Humanizer | op7418/Humanizer-zh | 去 AI 味 + 注魂 |
| dbskill | dontbesilent2025/dbskill | 商业诊断/写作公理库 + 路由器 |
| notebooklm | PleasePrompto/notebooklm-skill | source-grounded 取材/查证 |
| khazix | KKKKhazix/khazix-skills | 活人感写作人格 + 分层自检 |
| xiaohei | helloianneo/ian-xiaohei-illustrations | 文章配图（认知锚点插画） |
| social-card | op7418/guizang-social-card-skill | 文章→社交图编排 |
| baoyu | JimLiu/baoyu-skills | 内容→视觉资产流水线 |
| ppt | op7418/guizang-ppt-skill | 文章→PPT，美学硬约束 |
| html-anything | nexu-io/html-anything | Markdown→HTML 成品 + 反 slop |
| content-research | ComposioHQ/content-research-writer | voice-preserving 写作搭档 |

> 真实性声明：本文为对既有摘要与源码的归纳与设计建议。第 4-5 节的 taxonomy 与 hook 为 [推断]/设计草案，非最终决定，需经 `/think-scope` 与用户拍板。LLM 行为类断言均不保证效果。

---

## 1. 共同思路哲学（跨项目主题）

### 主题 A：质量靠「可枚举 + 可校验的硬约束」而非「请写优雅」
模型不会自律，所以审美/文风下限必须写死成可枚举、可 grep、可脚本校验的规则，而不是软建议。
- 体现：ppt（locked mode + validate-swiss-deck.mjs，FAIL exit 1）、social-card（Playwright 7 条规则 lint）、Humanizer（24 条编号模式 + 50 分量化表）、khazix（黑名单工程化为可全文扫描串）、html-anything（"圆角=立刻违反"断言句式）。

### 主题 B：去 AI 味只是底线，「保留/注入作者 voice」才是目标
反对把 AI 当 ghostwriter；价值锚是帮作者找回声音，而不是骗过检测器。
- 体现：Humanizer（去痕 + 注魂双层）、dbskill（消解优先于回答，反"去 AI 味"立场）、khazix（活人感人格层 + AI 能力边界声明）、content-research（voice preservation，Suggest not replace）。

### 主题 C：生成降级为「填空」——固定骨架 + 暴露槽位
禁止从零自由生成，把易错的全局机制锁死在模板，只让模型碰内容层，对抗风格漂移。
- 体现：ppt（种子模板 + 占位符 + 类名唯一来源契约）、social-card（种子模板替换）、baoyu（prompt 文件即 SSOT + 正交旋钮 preset）、xiaohei（填槽式英文骨架 + 中文内容变量）、html-anything（共享设计前缀 + skill body + 用户内容尾）、content-research（6 个 clarifying questions 把意图变槽位）。

### 主题 D：分层自检 + 交付门禁（inner-loop 与 acceptance 分离）
质量检查分层（硬规则→风格→内容→体验/活人感），并以可勾选 checklist 或 exit-code 脚本作为放行门。
- 体现：khazix（L1-L4 四层自检 + 固定质检报告）、Humanizer（快速检查清单 + 5 维评分阈值）、content-research（Pre-Publish Checklist）、social-card（双清单 QA + 体验级验收）、xiaohei（必过项/失败信号双清单 + 1 秒看懂验收）。

### 主题 E：人在环交互契约（检测只读、改写需授权、一次一问）
把作者控制权显式保留：默认只检测不改写，改写需显式授权，一次只问一个问题，先给结果再按需跑昂贵校验。
- 体现：dbskill（检测默认只读 + 改写需授权 + 一次一问 + 消解漏斗每层停下等回应）、notebooklm（确认硬门禁）、baoyu（确认为硬门禁，仅显式措辞放行）、social-card（one-shot 提问 + 先给用户看再校验）、content-research（section-by-section 增量反馈）。

### 主题 F：状态与资产外置（文件即 SSOT，支持中断续跑）
写作过程产物落盘为可复现文件，状态用固定 schema 承载，支持跨会话接续，不依赖隐藏记忆。
- 体现：dbskill（save/restore/report 三件套 + YAML frontmatter schema + next_skill 路由）、baoyu（prompt 文件即 SSOT + EXTEND.md 三级配置）、content-research（draft-v1/v2 版本号文件名，无隐藏记忆）、notebooklm（source-grounded 知识库外置事实，从来源层治理幻觉）。

---

## 2. 技巧目录（可复用技巧清单）

| 技巧 | 出现于 | 一句话怎么用 |
| :--- | :--- | :--- |
| 编号模式条目模板（警示词+问题+改写前+改写后） | Humanizer | 每条 AI 味模式做成四段式高密度条目，便于定位/勾选/反向归因 |
| 对称编号分类（N 类×各 M 条） | Humanizer、dbskill | 把检查项编号，结论可追溯到编号，对抗"泛泛而谈" |
| 总纲+细则双层（速查规则叠在细则上） | Humanizer | 5 条核心规则作认知压缩层，降低长 skill 执行负担 |
| 量化评分表 + 阈值放行 | Humanizer | N 维×10 分，达阈值才放行，把"去干净没"结构化（仅自评，不替代 acceptance） |
| 公理化 prompt + 编号溯源 | dbskill | 判断标准提成编号公理（非谈判项），每个产出带规则编号 |
| 路由器 skill（信号表→一句话确认→执行） | dbskill | 入口 skill 零实现纯分发，意图信号表 + 兜底编号选项 |
| 消解漏斗（分层过滤+概率标注+每层停下） | dbskill | 动笔前先证伪问题，分层过滤，不一次跑完 |
| save/restore/report 状态三件套 | dbskill | 固定 schema + next_skill 字段做跨会话项目记忆，纯本地无依赖 |
| 反问钩子（输出尾部拼自检 prompt） | notebooklm | 工具输出末尾拼 follow-up reminder，把持续取材变成工具驱动循环 |
| 元数据必填 + 先读真实内容再登记 | notebooklm | 素材入库强制 required 字段，禁止凭空编通用描述，防检索失效 |
| 两级验证（mtime 软过期快检 + 实测） | notebooklm | 对应 inner-loop verifier 与 acceptance verifier |
| 易变选择器集中成表 + 多语言 fallback | notebooklm、ppt | 依赖外部页面/接口的工具把选择器/路径/超时单点维护 |
| 分层自检 L1-L4 + 固定质检报告 | khazix | 硬规则→风格→内容→活人感，每层有通过标准+修复指引 |
| 黑名单工程化为可扫描串 + 替换映射 | khazix、html-anything | 每个禁用词/标点配好替换，落成扫描器而非提醒 |
| 白名单口语化词组库 + 定量约束 | khazix | 至少 8-10 个口语词、断裂句≥3 次，正向约束防机器稿 |
| 文章原型/体裁分类表驱动差异化 | khazix、content-research、baoyu | 先选原型再走对应流程强度与专项校验 |
| 正例反例三栏对照（AI 初稿 vs 人改 vs 差异） | khazix、xiaohei | 作为 style reference 标准格式 |
| AI 能力边界显式声明（哪些交 AI/哪些必须人） | khazix、social-card | skill 开头声明边界，防越界编造第一手经历 |
| 可证伪判据替代形容词 | xiaohei | "删句信息是否丢失/1 秒能否抓结论"代替"要清晰简洁" |
| 量化写作预算（段字数/每段一论点/标注上限） | xiaohei、social-card | 落成 readable-* 门槛，防过载与平均用力 |
| 受限词表（过渡词池/比喻池）"只选 1-2 个" | xiaohei | 防 AI 堆砌套话 |
| exit-code lint 作 acceptance gate | ppt、social-card | 渲染后正则/规则校验，FAIL exit 1，区分 inner/acceptance |
| 强制前置规划/对齐表 | ppt、content-research | 提纲→每段功能→证据来源先对齐再落笔，降结构性返工 |
| 错例❌/对例✅并排 + 配 grep 自检命令 | ppt | checklist 体裁比纯条文更适合 LLM 自检 |
| 少量精选预设 + 委婉拒绝自定义 | ppt、baoyu、xiaohei | 对审美敏感维度"不给自由给保护"（语气维度需谨慎勿过锁） |
| provenance 隔离注释（来源/赞助不写入产物） | ppt | 含元信息显式标注不进产物，防泄漏 |
| 正交维度旋钮 + 命名 preset + 自动推荐 | baoyu | 体裁×语气×结构×受众自由组合 + 兼容矩阵，兼顾低门槛与高级控制 |
| prompt 文件即 SSOT | baoyu | 先写 prompts/NN-*.md 再调后端，换后端/改某段/对比候选都靠它 |
| style 文件标准 schema（含 Avoid 负向段） | baoyu | Palette/Elements/Typography/Enforcement/Avoid/Best-For 六段，用 Avoid 压漂移 |
| diff-edit vs 从零生成分两套 prompt | baoyu、html-anything | 改稿只动差异、保留结构语气，省 token 稳风格 |
| 三级配置（项目→XDG→home）+ 显式 YAML schema | baoyu | 持久化长期写作偏好（语气/称谓/禁用词/署名），胜过一次性 prompt |
| 共享前缀 + skill 专属 body + 用户内容尾拼装 | html-anything | 共享硬约束单点 SSOT，单 skill 只写差异 |
| 内容驱动篇幅（模板数字是下限非上限） | html-anything | 反 LLM 把长材料压进固定格子，"输出 4-6 是严重错误" |
| 禁用项写成"X=判错"硬句式 | html-anything | 比"尽量简洁"对模型更有效 |
| frontmatter 机器可读触发/适用元数据 | html-anything | scenario 词表 + recommended 排序 + 金样本署名，辅助路由 |
| 已知坑连正确写法写进 skill body 当护栏 | html-anything | 把标题党/结论无支撑/推断当事实连正解写进 skill |
| 金样本 example（既当文档又当回归基准） | html-anything、social-card | 每 skill 附标准输入→标准输出金样本 |
| 6 个固定 clarifying questions | content-research | 开场把写作意图显式化为槽位再动笔 |
| 提纲内嵌 Research To-Do 复选框 | content-research | 让 outline 同时是 task list，呼应表驱动 |
| Hook 多策略候选 + Why + 判定问句 | content-research | 标题/CTA/过渡句生成模式，可泛化 |
| N 区块结构化反馈 schema（Original→Suggested→Why） | content-research | section 反馈固定契约，三行式 line edit |
| 引用三风格可选 + running citations list | content-research | 行内/编号/脚注 + 维护引用列表 |

---

## 3. 博采众长可借鉴清单（按优先级）

### P0：体系骨架级（决定整套 writing-skills 的形态）
1. **html-anything：抽一份「中文写作硬约束」共享前缀**（盘古之白、禁 em dash/emoji、真实数据、不堆形容词、[推断]/[未验证] 标注），所有 writing skill 复用、单 skill 只写差异。与现有 `readable-*` / `fe-ui` slop 检测统一。
2. **Humanizer + khazix：去 AI 味做成「去痕 + 注魂」双层 + L1-L4 分层自检**，强制输出质检报告，天然对应 inner-loop 与 acceptance verifier 分离。
3. **ppt + social-card + khazix：把文风下限编译成 exit-code lint**（句长、术语一致、禁用词、标题层级、引用齐全、盘古之白），而非自然语言提醒——对齐 AGENTS.md「能脚本强制的不要只写提醒」。
4. **dbskill：消解优先于回答的前置诊断 skill** + 公理化编号溯源，动笔前审计模糊词/隐含假设/相关性当因果，兼容「规则表优先于一堆判断」硬约束。

### P1：交互与流程级
5. **dbskill + content-research：写作类 skill 通用交互契约**——检测只读 + 改写需授权 + 一次一问 + section-by-section 增量反馈（与 `readable-rewrite` 的 writer+critic 循环同源可融合）。
6. **content-research + ppt：强制前置对齐**——6 个 clarifying questions / 提纲内嵌 Research To-Do / 提纲→每段功能→证据来源对齐表，接入 `think-scope` / `think-plan`。
7. **baoyu：正交维度旋钮 + 命名 preset + 三级配置持久化偏好**——体裁×语气×结构×受众；用 EXTEND.md 式配置存语气/称谓/禁用词/署名。
8. **dbskill + content-research：状态外置**——save/restore/report 三件套（固定 schema + next_skill）/ draft-vN 文件，支持中断续跑、改某段不重跑全文。

### P2：内容质量与素材级
9. **notebooklm：取材/查证 source-grounded 化** + 反问钩子 + 元数据必填先读后登记，从来源层治理幻觉，对应 `web-read` / 取材 skill。
10. **xiaohei + html-anything：反空洞/反堆砌约束**——可证伪判据替代形容词、量化写作预算、受限词表"只选 1-2 个"、内容驱动篇幅。
11. **khazix + xiaohei：正例反例三栏对照库**（AI 初稿 vs 人改 vs 差异）作为 style reference 标准格式与金样本。
12. **baoyu + html-anything：改稿独立模式**——diff-edit prompt 保留结构语气只动差异，省 token 稳风格。

### 反面教训（要避免的坑）
- **ppt**：golden source 用了作者本机绝对路径、引用了仓库内不存在的 compare 脚本，分发后失效——共享资产必须随 skill vendored 或用相对路径。
- **content-research**：纯自然语言约定无脚本强制——引用核验/checklist 必须做成 hook/脚本门禁而非口头清单。
- **dbskill / khazix**：人格层与工程层耦合——借鉴工程骨架，人格/语料做成可替换资产而非硬编进 skill。

---

## 4. 候选 writing-skills taxonomy（设计 spec 输入，非最终决定）

> 沿用现有域前缀风格（`think-` / `dev-` / `guard-` / `readable-` / `assist-`）。下表中 `write-` 为新增写作专属域；其余尽量复用既有域以避免体系膨胀。这是给后续 `/think-scope` + spec 的输入，最终命名与拆分待用户拍板。

| 域 / 前缀 | 候选 skill | 一句话职责 |
| :--- | :--- | :--- |
| `think-` | think-write-scope | 动笔前对齐写作意图：受众/体裁/voice/不可牺牲约束（复用 think-scope 思路，写作特化） |
| `think-` | think-write-dissolve | 消解优先：审计模糊词/隐含假设/相关性当因果，先证伪问题再决定要不要写（借 dbskill） |
| `write-` | write-outline | 提纲生成，内嵌 Research To-Do + 每段功能/证据来源对齐表（借 content-research/ppt） |
| `write-` | write-draft | 填槽式成稿：固定体裁骨架 + 暴露内容槽位，正交旋钮（体裁×语气×结构×受众）（借 baoyu/ppt） |
| `write-` | write-revise | 改稿专用模式：保留结构语气只动差异（diff-edit），省 token 稳风格（借 baoyu/html-anything） |
| `write-` | write-hook | 标题/开头/CTA/过渡句多策略候选 + Why + 判定问句（借 content-research） |
| `write-` | write-source | 取材/查证：source-grounded 素材库 + 元数据必填 + 反问钩子（借 notebooklm） |
| `write-` | write-voice | 注魂/活人感层：注入观点、节奏、第一人称、口语化白名单（借 Humanizer/khazix，人格做可替换语料） |
| `readable-` | readable-dehumanize（去 AI 味） | 去痕 + 注魂双层重写，编号模式归因（借 Humanizer，可并入/扩展 readable-rewrite） |
| `readable-` | readable-style-contract | 生成/校验写作风格契约文件（语气/称谓/禁用词/Avoid 段/署名），三级配置持久化（借 baoyu/html-anything） |
| `guard-` | guard-write-check（写作交付总检查） | 交付前总入口：编排去 AI 味/事实引用/篇幅/术语一致校验，区分 inner/acceptance（借 khazix L1-L4） |
| `guard-` | guard-write-facts | 事实/引用核验门：标注 [推断]/[未验证]、检查结论是否有支撑（借 content-research/Truth Directive） |
| `assist-` | assist-write-corpus | 把真实写作语料提炼成带 confidence 标签的可替换原子库/正反例对照库（借 dbskill/khazix） |

潜在与现有 skill 的重叠/复用点：
- `readable-rewrite` 已是 writer+critic 循环，去 AI 味与 section 反馈可作为它的扩展模式而非全新 skill。
- `web-read` 已覆盖外链抓取，`write-source` 应建在其之上而非重造。
- `think-scope` / `think-plan` / `think-survey` 可直接服务写作前置，`think-write-*` 是否独立成 skill 需评估边际收益。

---

## 5. hooks 候选

> 原则（AGENTS.md）：能靠 hook/脚本/测试强制的规则，不要只写成自然语言提醒；故障导向安全（校验失败应阻止而非放行）。

| Hook 候选 | 用途 | 触发时机 |
| :--- | :--- | :--- |
| 中文排版/slop 静态门 | 检测盘古之白缺失、em dash、emoji、全角半角混用、AI 高频套话/连接词、否定式排比 | 写作产物文件 write/edit 后（PostToolUse），或定稿前 |
| 去 AI 味评分门 | 对成稿跑编号模式扫描 + N 维评分，低于阈值阻止"已定稿"声明（自评，不替代人工 acceptance） | 声明定稿/发布前 |
| 事实/引用校验门 | 检查 [推断]/[未验证] 标注是否齐全、引用列表是否完整、结论是否有来源支撑 | 含引用/事实断言的产物定稿前 |
| 篇幅/结构预算门 | 段字数、每段一论点、标注上限、内容驱动篇幅（防压缩/堆砌） | 成稿后 lint |
| provenance 泄漏门 | 检查来源/赞助/作者本机路径等元信息是否误写入产物 | 产物 write 后 |
| 覆盖/发布确认门 | 覆盖原文或发布前默认拦截，仅显式措辞放行（对齐边界审批 + guard-gitops） | 覆盖原文 / 发布动作前 |
| 风格契约同步漂移门 | 校验各 writing skill 的共享硬约束前缀与 style 契约文件未漂移（呼应 verify_skills.py） | skill 变更 / CI |

实现倾向：静态门（排版/slop/篇幅/provenance）适合做成 `verify_*.py` 式脚本 + PostToolUse hook；评分门与事实门可先以 skill 内 checklist + 可选脚本起步，避免误杀正常写作。

---

## 6. 开放问题 / 需用户拍板

1. **新建 `write-` 域 vs 全部塞进 `readable-`**：写作创作（生成）与可读性重写（已有内容改写）边界在哪？是否值得新增一个域前缀，还是扩展 `readable-*` + `think-*` 即可？（关系到体系是否膨胀）
2. **去 AI 味评分门是否硬阻止**：自评分数不能替代 acceptance，硬阻止"定稿"声明可能误杀。要 block 还是只 warn？阈值由谁定？
3. **voice/人格层如何承载**：khazix/dbskill 都把作者人格硬编进 skill。我们的 voice 语料应放 `assist-write-corpus` 原子库、还是用户 EXTEND.md 配置、还是 docs/？是否需要支持多 voice 切换？
4. **取材/查证是否做 source-grounded 知识库**：notebooklm 模式重（需外部库 + 浏览器）。写作取材多为一次性，是否 stateless（直接 `web-read` + 行内引用）就够，还是值得建持久素材库？
5. **scope 边界**：本轮只做「中文长文/公众号/博客」写作，还是要覆盖社交图/PPT/插画（social-card/ppt/baoyu/xiaohei 这类内容→视觉资产）？后者依赖渲染管线，成本高，建议另立 scope。
6. **禁用词/套话词表的来源与维护**：黑名单（AI 套话）+ 白名单（口语词）需要中文语料 SSOT。是手工维护一张表，还是从 Humanizer/khazix 现成词表迁移并标注中文适配项？
7. **与现有 readable-rewrite 的融合**：去 AI 味、section 反馈是扩展 readable-rewrite 的模式，还是独立 skill？影响维护面与触发清晰度。

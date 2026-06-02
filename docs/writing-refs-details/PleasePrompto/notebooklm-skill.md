# PleasePrompto/notebooklm-skill
- 仓库 / owner PleasePrompto（第三方，非 Google 官方）/ 实测★ 6812 / vendored commit eea5cb28 / 分类 资料驱动写作 / 核实日期 2026-06-02

## 思路哲学（Why）

核心洞察：把「写作/编码所依赖的事实来源」从模型权重里挪出来，交给一个外部的、source-grounded 的知识库（Google NotebookLM / Gemini），让 Claude Code 只负责"提问 + 综合 + 落地"，不负责"记住事实"。它要解决的真实痛点写得很直白（README "The Problem"）：让 Claude "搜本地文档"会带来 token 暴涨、检索不准、找不到就编 API（幻觉）、以及在 NotebookLM 浏览器和编辑器之间反复 copy-paste 的"copy-paste dance"。

设计哲学：
- **幻觉治理靠"答案只来自上传文档"**：不在 prompt 层反复叮嘱"不要编"，而是换一个本身就 source-grounded 的回答引擎，从源头压缩编造空间（SKILL.md 第 8 行、README 第 184-185 行；作者用 "drastically reduced / minimal" 这种限定词，没有打包票）。[推断] 这是把"约束模型行为"转成"约束信息来源"的取舍。
- **明确拒绝本地 RAG**：README 用一张对比表（第 50-55 行）论证为什么不自己做 embedding/chunking/vector DB——本地 RAG 要数小时搭建且仍有检索缺口；NotebookLM 5 分钟接入、预处理由 Gemini 完成、天然带 citation。关键取舍是"不自建检索基础设施，借现成的托管知识库"。
- **无状态优于有状态**：和它自己的 MCP server 版本（持久会话）相对照，skill 版本刻意选"每个问题开一个全新浏览器、问完即关"的 stateless 模型（README 第 277-291 行）。代价是没有会话上下文，无法引用"上一条回答"；收益是简单、契合 skill 架构、不用维护会话生命周期。
- **把"上下文丢失"用一句固定 prompt 补偿**：既然每次都是新会话，就在每个答案尾部强行追加 follow-up 提醒，把"持续追问直到信息完整"的责任压回 Claude 身上（见下）。

## 特殊技巧（How）

1. **输出契约里植入"反问钩子"（最值得抄的一招）**：`ask_question.py` 第 31-37 行定义 `FOLLOW_UP_REMINDER`，把固定文本拼到每个返回答案末尾——`"EXTREMELY IMPORTANT: Is that ALL you need to know? ... before you reply to the user, review their original request and this answer. If anything is still unclear or missing, ask me another comprehensive question that includes all necessary context (since each question opens a new browser session)."`。SKILL.md "Follow-Up Mechanism (CRITICAL)" 段（第 128-141 行）把它升级成对 Claude 的强制行为协议：STOP → ANALYZE → IDENTIFY GAPS → ASK FOLLOW-UP → REPEAT → SYNTHESIZE。用"工具输出的一段文本"来驱动 agent 的下一步决策，而不是靠系统 prompt。

2. **Smart Add：先查再存，禁止凭空编元数据**：SKILL.md "CRITICAL: Add Command - Smart Discovery"（第 19-38 行）规定，用户给 URL 但没给描述时，先用一条 query 问 notebook "你的内容是什么/覆盖哪些主题"，拿真实回答再去 `notebook_manager.py add`。反复强调 `NEVER guess or use generic descriptions`。这是"元数据必须来自事实而非臆测"的纪律，用 skill 文案 + 必填参数双重强制。

3. **必填参数当硬门禁**：`notebook_manager.py` 的 add 子命令把 `--description`、`--topics` 设为 `required=True`（第 318-319 行），缺失直接 argparse 报错。把"不许偷懒"从自然语言提醒落成了 CLI 层强制（呼应我们体系"能靠脚本强制就别只写提醒"的原则）。

4. **run.py 统一入口 + 自举环境**：SKILL.md 反复强调 `NEVER call scripts directly. ALWAYS use python scripts/run.py [script]`（第 40-52 行）。`run.py` 在首次调用时自动建 `.venv`、装依赖、装 Chrome，再用 venv 的 python 执行目标脚本（run.py 第 26-45、84-91 行）。对 agent 来说这是"单一调用契约"——只要记一个命令模式，环境问题被吞进 wrapper，降低 agent 出错面。

5. **状态/记忆三件套分层**：`config.py` 把所有路径集中（第 8-15 行）；持久状态分成 `library.json`（notebook 元数据库 + active_notebook_id）、`auth_info.json`（认证时间戳）、`browser_state/`（cookie/profile）。`NotebookLibrary` 维护 use_count / last_used / active 指针（notebook_manager.py），相当于一个轻量"知识库目录 + 使用画像"，让 Claude 能按 topic 搜索并自动选对 notebook。

6. **认证状态用文件 mtime 做软过期**：`auth_manager.py` `is_authenticated()`（第 52-62 行）只检查 state 文件是否存在，再用 mtime 算"7 天提醒"，不阻断；另设 `validate_auth()` 真正起浏览器访问 NotebookLM 看是否被重定向到登录页。区分"廉价快检"与"昂贵实测"两级验证。

7. **回答完成判定：轮询文本稳定 + thinking 检测**：`ask_question.py` 第 117-160 行不靠固定 sleep，而是轮询响应元素文本，连续 3 次不变才认定答案稳定（`stable_count >= 3`），并优先检测 `div.thinking-message` 是否还在转（commit 标题 "Thinking Detection"）。2 分钟 deadline 兜底。这是对抗流式输出"何时算说完"的实用招法。

8. **选择器多语言 fallback + 集中表驱动**：`config.py` 的 `QUERY_INPUT_SELECTORS` / `RESPONSE_SELECTORS` 是有序列表，含德语/英语 aria-label fallback（第 18-28 行），逐个 try。UI 选择器集中成数据表而非散落代码里，便于 NotebookLM 改版时单点维护。

9. **反检测当成显式能力而非默认**：用真实 Chrome 而非 Chromium（setup_environment.py 第 70-85 行注释解释是为指纹一致性/反检测），`BROWSER_ARGS` 关掉 automation 标志（config.py 第 31-37 行），`StealthUtils.human_type` 模拟人类打字速度和随机停顿（browser_utils.py 第 67-89 行）。README/Disclaimer 诚实声明"无法保证 Google 不检测，建议用专用账号"（第 357-360 行），没把"反检测"说成"保证不被封"。

## 可借鉴点（for writing-skills）

1. **"反问钩子"模式可直接移植到中文写作 skill**：在任何"取材/查证"类工具的输出末尾拼一段固定的中文自检 prompt（如"这些素材足够支撑你要写的段落吗？还缺哪些事实/数据/案例？缺就再查一次"），把"持续取材直到信息完整"变成工具驱动的循环，而不是指望写作 agent 自觉。比纯 SKILL.md 提醒更可靠。

2. **"先查再存元数据 + 必填参数"适合素材库管理**：做"资料驱动写作"时若有素材库/笔记库，把"描述/标签/主题"设为必填，并强制先读真实内容再登记，避免素材库被一堆"通用描述"污染、后续检索失效。这是写作体系做"可检索素材资产"的基础纪律。

3. **两级验证（快检 mtime / 实测起浏览器）值得抄进我们的 verify 纪律**：对应我们 AGENTS.md 的 inner-loop verifier vs acceptance verifier——廉价检查只判"看起来有没有"，真验收要"真跑一次看结果"。

4. **stateless + 外部 SSOT 的取舍框架**：当我们的写作 skill 需要接外部知识源（NotebookLM / 检索 API / 本地语料）时，这个项目给了一个清晰对照：要不要持久会话？答案取决于"上下文连续性收益 vs 生命周期维护成本"。资料驱动写作多数场景一次性取材即可，stateless 更省心。

5. **表驱动选择器 / 集中 config**：任何依赖外部网页或不稳定接口的写作工具（如抓素材、读外链），把易变的选择器/路径/超时集中成表，符合我们"数据集中管理、复杂逻辑写成表"的原则。

6. **诚实的限定词文风**：README 全程用 "minimal / drastically reduced / probably fine" 而非 "guarantee / never"，且在 Disclaimer 主动认怂——和我们的"真实性纪律 + 禁用 Guarantee/Will never"高度一致，是对外文案可借鉴的口径。

## 资产盘点（事实）

实际读到的文件：
- `SKILL.md`（269 行）：唯一的 skill 入口；含触发条件、Smart Add、run.py 强制、四步 workflow、Follow-Up 机制、脚本参考、decision flow、限制。
- `README.md`（412 行）：面向人类的项目说明；Problem/Solution、为什么不用本地 RAG 的对比表、与自家 MCP server 的差异表、stateless session model、Disclaimer。
- `scripts/run.py`（101 行）：统一 wrapper，自举 venv。
- `scripts/setup_environment.py`（203 行）：建 venv、装依赖、装真实 Chrome。
- `scripts/ask_question.py`（256 行）：核心提问脚本；FOLLOW_UP_REMINDER、文本稳定轮询、thinking 检测、notebook URL/id/active 解析。
- `scripts/notebook_manager.py`（409 行）：素材库 CRUD + search + activate + stats + use_count。
- `scripts/auth_manager.py`（357 行）：Google 登录、状态持久化、两级验证、reauth/clear。
- `scripts/browser_utils.py`（107 行）：BrowserFactory（持久 context + cookie 注入 workaround）+ StealthUtils（人类打字/点击）。
- `scripts/config.py`（44 行）：路径、选择器表、浏览器参数、超时常量集中。
- `scripts/cleanup_manager.py`（301 行，未逐行读，标题与 SKILL.md 一致：预览/执行清理、--preserve-library）。[未验证] 内部细节未逐行核对。
- `references/usage_patterns.md`（337 行）：10 个使用 pattern + Claude 工作流伪代码。
- `references/troubleshooting.md`（375 行，读了前 60 行）：错误速查表、认证问题处置。
- `references/api_reference.md`（308 行，未读）。[未验证]
- 其它：`AUTHENTICATION.md`、`CHANGELOG.md`、`requirements.txt`（patchright==1.55.2 / python-dotenv==1.0.0）、`LICENSE`、`images/example_notebookchat.png`、`scripts/__init__.py`（80 行，未读）、`scripts/browser_session.py`（254 行，未逐行读）。

技术栈事实：Python + Patchright（Playwright 衍生的反检测分支）+ 真实 Chrome；数据全本地存于 `~/.claude/skills/notebooklm/data/`，靠 `.gitignore` 排除。单一 skill（非多 skill 体系），无 prompts/ 目录，所有 prompt 文本内嵌在脚本常量和 SKILL.md/references 里。

## 备注 / 风险

- **它本质是"工具型/检索型 skill"，不是"写作体裁型 skill"**：分类为"资料驱动写作"是因为它解决"写作/编码所依赖的事实来源"问题，但它本身不产出文章、不管文体；对我们写作体系的价值在"取材层"和"工程模式"，不在"写作方法论"。
- **强外部依赖**：依赖 Google NotebookLM 网页结构、登录态、Gemini 行为，全是不可控外部面；选择器、follow-up 触发文本随时可能因对方改版失效（troubleshooting 已为此准备速查表）。[推断]
- **合规/账号风险作者已自陈**：浏览器自动化可能被 Google 判为 scraping，建议专用账号；免费额度 50 次/天。引入类似机制时需评估 ToS 与封号风险。
- **第三方项目**：非 Google 官方 NotebookLM 产品；依赖浏览器自动化 + 持久登录会话，使用前应审脚本与授权范围。
- `api_reference.md` / `cleanup_manager.py` / `browser_session.py` / `__init__.py` 未逐行核对，相关结论仅基于文件名与 SKILL.md 描述，标注为 [未验证]，未编造其内部实现。
- 真实性说明：本文档所有机制均来自上述实际读到的文件与行号；带 [推断]/[未验证] 标记处为未直接证据支撑的判断。

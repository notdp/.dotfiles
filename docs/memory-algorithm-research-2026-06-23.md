# Agent Memory 算法 SOTA 调研(2026-06-23)

> workflow wd3x0dz8s(7 维 + benchmark,web 取证)。think-research 体例,每条带置信度。状态:调研产物,喂 memory-vault plan 算法选型。

## 每维推荐

### 召回 (Retrieval)  `[confirmed]`

**推荐**:dense(brute-force numpy cosine)+ BM25/grep lexical 的 hybrid,RRF 融合,叠加 recency×importance 重排。hook 那次带 fallback 的 API 调用专用于 query 扩展(LLM 改写 + 抽时间范围),失败回退原 query。不引向量 DB/不引图谱/不引常驻进程。

**依据**:本机实测 N=3000→0.33ms/N=50000→4.88ms;LongMemEval recall@5=0.644;Zep Graphiti 三路 φ_cos+φ_bm25+φ_bfs 证 hybrid 互补;mem0 LoCoMo J=66.88%。

### 编码 / salience (写入抽取)  `[confirmed]`

**推荐**:抄 mem0 FACT_RETRIEVAL_PROMPT 骨架但裁剪到领域类目(decision/preference/correction/failure-mode/fact),强制 few-shot 含'返回空数组'负例;salience 用二值(抽/不抽)+ 类目标签,不用 LLM 1-10 打分。每条事实强制自带一句 context/来源。

**依据**:mem0 issue #4573(一手, 作者原话);Generative Agents importance 局限(frontiersin psychology 2025);LangMem 官方文档 triple+context。

### 巩固 / 更新 (ADD/UPDATE/DELETE/NOOP)  `[confirmed]`

**推荐**:以 mem0 的'检索 top-K → 单次 LLM tool-call 逐条裁决'为主干,但三处硬改造:(1) 禁裸物理 DELETE,矛盾降级为 UPDATE(旧值标 superseded)+ soft-delete(移 .archive/ 或 status:archived);(2) prompt 给'同类多实例≠矛盾'few-shot;(3) 返回 JSON 的 id 必须命中现有文件名否则 fallback 成 ADD/丢弃。放显式 /assist-learn 触发而非每条对话 hook。

**依据**:mem0 issue #4536/#4573/#1499;Zep edge invalidation 语义。

### 表示 / 分型与结构  `[confirmed]`

**推荐**:flat 原子 note + markdown frontmatter;三型 episodic/semantic/procedural 用 type 字段;关联降级为 frontmatter related/正文 [[wikilink]];embedding 外置为旁路 .npy/JSONL 做 brute-force;时序用标量字段 valid_from/valid_to/status 做 superseded 软失效。procedural 直接复用现有 assist-learn 产物体裁。

**依据**:CoALA arxiv 2309.02427;A-MEM 多跳 F1 45.85 vs MemGPT 25.52, token 2520 vs 16910;mem0g +1.5pt/慢3x/贵2x。

### 遗忘 / 衰减 / 失效 / 防陈旧  `[confirmed]`

**推荐**:三层:bi-temporal 软失效(Zep 语义落 frontmatter invalid_at/superseded_by,文件不删)+ 检索期 recency(基于 last_accessed,衰减常数 holdout 重标定)×importance 衰减(Generative Agents)+ 可执行作废钩子(memory 带指向文件/grep/命令 exit code 的 verify 断言,定期校验失败即写 invalid_at='code-conflict')。trust score 复用 recency 同套衰减防投毒。

**依据**:Zep arxiv 2501.13956 四时间戳 + edge invalidation;Generative Agents decay 0.995 over last-retrieved;MINJA 98.2% 注入。

### 反思 / 抽象 (reflection / consolidation)  `[confirmed]`

**推荐**:以 Generative Agents reflection 为骨架,按需触发(累计 importance > 阈值 + 冷却窗口, debounce 思想), 一次 API 调用三段(召回本地 numpy + 生成洞见强制 '(because of <id>)' 引用 + mem0 式去重/矛盾校验), fallback=跳过反思不丢原始记忆。双轨存(原始情景永不被反思删除),支撑 <2 条不升为规则,被推翻标 stale 不静默改写。不引 Letta sleep-time/LangMem daemon(违无常驻进程),只移植'延迟+去重的单次调用'思想做成 on-demand skill。

**依据**:Generative Agents arxiv 2304.03442(阈值150/3问题→5洞见/because-of引用);SSGM arxiv 2603.11768(语义漂移);Experience-Following arxiv 2505.16067。

## 整体推荐算法

端到端推荐:一个纯文件、无向量 DB、无图引擎、无常驻进程的 file-native 记忆层,只借 mem0 / A-MEM / Generative Agents / Zep 的【算法内核与 prompt/schema】,不借任何 runtime。这与用户进行中的 memory-vault Plan v3 高度收敛——本调研的作用是用 SOTA 证据校验并锐化该 plan 的算法选择,不另起平行体系。\n\n六维端到端串接:\n\n[表示] 每条 memory = 一个 md(frontmatter)或 JSONL 行,沿用现有 assist-learn problem_type schema 扩可选字段:type(semantic|episodic|procedural)、created/last_accessed、importance(可选, backlog)、keywords/tags、related([[wikilink]])、valid_from/valid_to/status(active|superseded|archived)、origin_session(hash 前N位, 禁绝对路径)、verify(可选可执行断言)、trust(0-1, 按来源初始化)。embedding 外置旁路 .npy/.gitignore + 幂等 rebuild 命令。粒度:round/atomic-note 单文件单事实(A-MEM 思路, 别整段塞, 别过度压成干瘪 fact 卡)。\n\n[编码/salience] 写入走 mem0 FACT_RETRIEVAL_PROMPT 裁剪版(类目白名单 decision/preference/correction/failure-mode/fact + 强制'返回空数组'负例 few-shot),salience 二值化 + 类目优先级(decision>correction>preference>fact),不用 LLM 1-10 分。每条事实强制带一句 context/来源。\n\n[巩固] 新候选先 brute-force numpy cosine 取 top-K(5~8)→ 一次带 fallback 的 LLM 调用(复用 deepseek capsule 路由骨架, fail-open=只 ADD 不破坏)裁决 ADD/UPDATE/SKIP;禁裸 DELETE(矛盾→UPDATE 标 superseded + soft-delete);prompt 含'同类多实例≠矛盾'few-shot;校验返回 id 命中现有文件名。放显式 /assist-learn 触发, 非每轮对话 hook。\n\n[召回] hybrid:dense brute-force numpy cosine + BM25/grep lexical, RRF 融合, 叠加 recency(last_accessed 指数衰减, 常数 holdout 标定)×importance 重排;硬过滤 status=superseded/低 trust。hook 内那一次带 fallback 的 API 调用专用于 query 扩展(LLM 改写 + 抽时间范围, fallback=原 query)——不要花在 LLM rerank/triple 过滤(一次调用 cover 不全且无优雅 fallback)。0 命中/低分则不注入(空优于噪声)。\n\n[遗忘/防陈旧] bi-temporal 软失效(Zep 语义, 文件不删, git 保留历史)+ 检索期 recency×importance 衰减 + 可执行作废钩子(verify 断言失败 → invalid_at='code-conflict', 这是代码场景独有优势)+ trust score 随时间衰减防 stale-poisoning。\n\n[反思] on-demand /compact-memory 或 /reflect-memory skill, 累计 importance 阈值 + 冷却窗口触发, 一次调用三段(本地召回 + 强制 (because of <id>) 引用生成洞见 + mem0 式去重/矛盾校验), 双轨存原始情景, 支撑<2不升规则, 被推翻标 stale 不静默改写。\n\n分发:把检索/裁决封装成单个可执行脚本(stdin query → stdout 召回 / stdin 候选 → stdout 裁决 JSON),5 agent hook 共同调起 + memory 目录软链, 绝不在每个 agent 重写逻辑(否则 5 套平行体系)。落地分层 ROI 排序:第1层 dense+BM25+RRF(零外部依赖)和第2层 query 扩展(复用 deepseek)就拿到大部分召回质量, 第3层 recency×importance 是低成本'类 graph'关联信号。验证用自建 holdout 不用 LoCoMo。

## 方案矩阵

| 方案 | 适用 | 优点 | 代价 | 脆弱假设 | 裁决 |
|---|---|---|---|---|---|
| 推荐方案: file-native hybrid(dense brute-force + BM25 + RRF + recency/importance + 一次 query 扩展调用 + mem0 式软裁决 + Zep 软失效 + Generative Agents 反思) | 单用户、几百~几千条、文件型 git-tracked、不要向量/图 DB、不要常驻进程、跨 5 agent 软链、复用既有 deepseek/assist-learn | 全部纯文件+纯计算+单次 LLM 调用; 与用户既有 memory-vault Plan v3 / capsule 路由 / assist-learn 完全收敛; git 可审计; 算法选择全有 SOTA 证据支撑; 实测延迟亚毫秒 | 需自实现轻量 numpy 检索层 + BM25 + RRF + 衰减; 多跳推理要自己在内存建邻接表做 BFS(几千条毫秒级可接受); 衰减常数/trust 阈值需 holdout 校准 | 假设记忆永远是单用户几千条(若未来多用户/多项目汇池逼近几十万条需重评); embedding 缓存与 md 正文一致性需 content hash + 惰性重嵌兜底 | 采用。最贴合全部约束,且不是另起体系而是校验/落地用户进行中的 plan |
| 整包引入 mem0 / Letta(MemGPT) / LangMem SDK | 多用户 SaaS、有服务端、可跑向量 DB(Qdrant/Chroma)和/或 LangGraph 运行时、不在意跨异构 agent | 开箱即用、社区成熟、prompt/算子经实战 | 带服务端/SDK/向量 DB/常驻进程,破坏纯文件+软链+跨 5 agent+无常驻进程约束; mem0 有裸 DELETE 丢信息/过度抽取 97.8% junk 已知坑; Letta archival 去重至今未内建 | 假设可接受常驻 runtime 与单框架绑定 | 拒绝整包。只复用其开源 prompt 文本 + 数据 schema + 算子语义,不引 runtime |
| graph 路线: HippoRAG 2 / Zep-Graphiti(KG + PPR / bi-temporal 图) | 跨多文档深多跳推理、大规模实体消歧、企业多用户长时演化、可跑 Neo4j/图引擎 | 多跳/时间推理 Recall 最高(HippoRAG Recall@5 78.2; Zep 时序子集 83%) | 需常驻图引擎或每次重建图、每条 memory LLM 抽三元组、检索时 LLM 逐 triple 过滤; mem0g 证图在小体量总分只多 1.5pt 却慢 3x 贵 2x | 假设收益在多跳——但单用户对话记忆很少触发跨多文档深多跳 | 拒绝。只降级借两个语义: 关联→frontmatter wikilink, 时序失效→frontmatter valid_from/valid_to/status |
| 纯 full-context(不做抽取, 每次塞全部历史) | 会话总量 <150(ConvoMem 拐点)、单用户、不在意 token | 零工程; ConvoMem 证小规模下 ≥ RAG; LoCoMo full-context J≈73 反超多数记忆系统 | 几千条已超拐点, token/延迟不可控; 不可 git diff/人审/跨 agent 复用; 无遗忘/防陈旧 | 假设永远在 context 窗口内 | 拒绝作主方案, 但作为 fallback 心智: LLM 调用失败时宁可漏记/退化为原始召回也不乱写 |
| 纯 dense(只向量 cosine, 无 BM25, 无重排) | 查询全是语义改述、几乎无专有名词/ID/精确字符串 | 最简单; mem0 纯向量已拿 LoCoMo J≈67 | 系统性漏专有名词/ID/罕见词(文件名/命令/配置 key)——恰是 agent memory 高价值条目 | 假设 agent memory 里精确字符串不重要(错) | 拒绝。加 BM25/grep 这一路几乎零成本却补盲区 |

## 不要自造轮子

- 复用用户既有 deepseek capsule 路由骨架(scripts/hooks/context_capsule.py 的 classify_with_deepseek + 正则 fail-open + ~/.config/deepseek/apikey + thinking disabled + 6s 超时)做 query 扩展和巩固裁决的'一次带 fallback API 调用',不另写 LLM 客户端
- 复用用户既有 assist-learn 的 problem_type frontmatter schema + learnings_search.py 的 score_note(已吃任意 frontmatter, 加字段不废检索器), 只新增可选字段, 不造新 schema
- 复用用户进行中的 memory-vault Plan v3 的全部架构决策(memory/ 落 ~/.dotfiles、grep-first 单流注入扩 context_capsule、单写入口扩 assist-learn、INDEX.md 机械生成过 redact、跨 5 agent 软链), 本调研只校验其算法内核
- 抄 mem0 开源 FACT_RETRIEVAL_PROMPT + DEFAULT_UPDATE_MEMORY_PROMPT 的文本与 JSON schema(github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py), 不 pip install mem0
- 抄 A-MEM 的 note 七属性 schema 可读子集(keywords/tags/context/timestamp/links)与 top-k 链接思想, 不引 ChromaDB
- 抄 Generative Agents 的 importance prompt + recency×importance×relevance 评分公式 + reflection 三段式(3问题→5洞见→because-of引用), 全本地计算
- BM25 用 rank-bm25 或自写纯 Python(几千条够用), 检索用 numpy 矩阵乘 + argpartition, 不引 faiss/qdrant/chroma
- 复用既有 redact.py / stop_check.py transcript 读取栈做捕获(plan E1 已核实: 不是 context_state.py 死代码)

## 证据地图

| 结论 | 来源类型 | 强度 | 冲突 |
|---|---|---|---|
| 在单用户/几千条体量下,brute-force numpy cosine 检索是亚毫秒级,向量 DB 是过度工程(N=3000→0.33ms, N=10000→0.72ms, N=50000→4.88ms, 含 top-10; 内存 N=5000 仅 20MB)。真正瓶颈是 embedding API 调用本身。 | 本机实测 + mem0 论文 arxiv 2504.19413 | strong | 无冲突。直接证伪'要不要向量 DB'这个问题本身。 |
| benchmark(尤其 LoCoMo)不可作为选型铁证:厂商互撕(Zep 自报 84%→mem0 复现 58.44%→Zep 反驳 75.14%),full-context 裸跑 J≈73% 反超多数记忆系统,Letta filesystem-only 74.0% 超 mem0-graph 68.5%,简单 filesystem 操作就能拿 74%。 | Zep 官博 + mem0 论文 + getzep issue #5 + emergentmind LoCoMo 批评 | strong | 各厂商数字互相矛盾本身就是结论;采用 LongMemEval(有独立 indexing/reading 消融、非自评)作主要参考,LoCoMo 仅当 sanity check。 |
| graph+PPR(HippoRAG 2)在多跳/关联检索上确实最强(Recall@5 78.2 vs dense 73.4),但 mem0g(图)比 mem0(flat)总分只多 ~1.5pt,且 single/multi-hop 反而更差、检索慢 ~3x、token ~2x。图的边际收益主要在跨多文档深多跳,不在单用户对话记忆。 | HippoRAG 2 (ICML 2025, arxiv 2502.14802) + mem0 论文 mem0 vs mem0g | strong | 质量证据(HippoRAG 强)与成本/约束证据(mem0g 负收益 + 需常驻图引擎)冲突;落地约束下采用后者,graph 出局,只降级借'关联=wikilink''时序失效=frontmatter 字段'两个语义。 |
| 召回质量的提升顺序是'索引粒度 + key 扩展 + 时间感知 > 检索算法本身':round 粒度优于整 session,key=value+LLM抽取的 user facts 带来 recall@k +9.4%,time-aware query expansion 带来时间类 recall +6.8~11.3%。best 配置 recall@5=0.644/recall@10=0.784。 | LongMemEval 论文 arxiv 2410.10813 (独立消融, 非厂商自评) | strong | 无。这是最干净的中立证据,直接指导'hook 那次 API 调用花在哪'。 |
| 写入侧真瓶颈在提取(extraction)不在巩固(consolidation):mem0 生产 32 天累积 10134 条审计后仅 224 条存活(97.8% junk),作者明确根因是提取 prompt 太 permissive,'更强模型反而更忠实照烂 prompt 乱抽'。 | mem0 维护者 issue #4573(一手) | strong | 无。修正了'优化巩固就能防膨胀'的直觉;salience gate(类目白名单+返回空数组负例 few-shot)才是高 ROI。 |
| 裸 DELETE 会丢信息:mem0 把矛盾直接判 DELETE 导致删旧不加新留下空状态(issue #4536);把'又养了一只狗 Scout'误判为与'养了狗 Buddy'矛盾而覆盖(官方自曝)。Zep/Graphiti 的做法是 invalidate(标 invalid_at)不物理删,保留时间线。 | mem0 issue #4536 + mem0 官博 + Zep 论文 arxiv 2501.13956 | strong | 无。一致指向'矛盾降级为 UPDATE/soft-delete,禁裸物理删',与 git-as-SSOT 天然契合。 |
| 小体量下'全量保留'可能等于甚至优于复杂抽取:ConvoMem 实测约 150 会话以内 full-context ≥ RAG/抽取式记忆,作者建议小规模单用户'retain full conversation context'。 | ConvoMem benchmark arxiv 2511.10523 | medium | 与'做 LLM 抽取有价值'部分张力;调和:几千条已略超 150 会话拐点,做最小 LLM 抽取仍值(省检索 token + 人可读 + git diff),但不上重型协调/reflection/向量库。 |
| 反思必须带证据引用(reflection grounding):Generative Agents 强制洞见格式 '(because of 1,5,3)' 指回底层记忆 id,是抗过度泛化/语义漂移的第一道防线;无引用的反思=幻觉温床。 | Generative Agents 论文 arxiv 2304.03442 + SSGM arxiv 2603.11768 | strong | 无。直接给出反思层的安全设计约束。 |
| recency 衰减应基于 last_accessed 而非 created;衰减常数 0.995 是 sandbox game-hour 尺度,真实日历(天/周)必须重标定否则老记忆被永久埋没。 | Generative Agents 论文(decay 0.995 over game-hours since last retrieved) | strong | 无。常数移植是已知坑,需 holdout 校准。 |
| stale-memory-poisoning 是真实威胁:MINJA 证明 query-only 交互即可投毒,注入成功率 98.2%/攻击成功率 76.8%;防御=每条记忆带随时间衰减的 trust score + trust-aware retrieval,但阈值校准是安全-可用性根本权衡(无一键安全)。 | MINJA arxiv 2503.03704 + Memory Poisoning Defense arxiv 2601.05504 | strong | 无。与用户既有 redact gate/secret 模型互补,trust 可复用 recency 衰减同一套。 |
| 用户已有 capsule 路由用 deepseek-v4-flash 做'一次带 fallback 的分类调用'(F1 54% vs 正则 27%, ~0.2s, thinking 必须 disabled, fail-open 退正则),并有进行中的 memory-vault Plan v3(schema 沿用 assist-learn problem_type、grep-first 检索、扩 context_capsule 单流注入、扩 assist-learn 单写入口、mem0 ADD/UPDATE/DELETE/NOOP、跨 5 agent 软链)。 | 本机文件: memory/capsule-routing-deepseek.md + docs/memory-vault-plan-2026-06-23.md | strong | 无。研究推荐与用户既有方案高度收敛;本调研作用是用 SOTA 证据校验/锐化该 plan 的算法选择,不另起体系。 |

## Plan Handoff

- **requirements**:R1 文件型 git-tracked 记忆层(md+frontmatter / JSONL),沿用 assist-learn problem_type schema 扩可选字段(type/last_accessed/importance/related/valid_from/valid_to/status/trust/verify/origin_session-hash),embedding 外置旁路 .npy 走 brute-force, 禁向量/图 DB、禁常驻进程。R2 召回 = dense brute-force numpy cosine + BM25/grep, RRF 融合, recency(last_accessed)×importance 重排, 硬过滤 superseded/低trust; 0命中不注入。R3 hook 内一次带 fallback API 调用专用 query 扩展(改写+抽时间, fallback=原 query), 复用 deepseek capsule 骨架。R4 写入 salience gate(类目白名单+空数组负例)+ 巩固单次 LLM 裁决 ADD/UPDATE/SKIP(禁裸DELETE, 矛盾→UPDATE+superseded+soft-delete, id 校验, 多实例≠矛盾 few-shot), 显式 /assist-learn 触发, fail-open=只ADD。R5 遗忘 = bi-temporal 软失效(invalid_at/superseded_by 不删)+ 可执行作废钩子(verify 断言失败→invalid_at='code-conflict')+ trust 衰减。R6 反思 on-demand skill, 阈值+冷却触发, 强制 (because of <id>) 引用, 双轨存原文, 支撑<2不升规则。R7 检索/裁决封装单可执行脚本(stdin→stdout), 5 agent 软链共用。
- **approach**:按 ROI 分层增量(对齐 Plan v3 的 Phase 1-6): 先做纯本地零 API 的存储+schema+brute-force hybrid 召回(R1+R2, 立即可用可回归); 再加复用 deepseek 的 query 扩展(R3)和巩固裁决(R4); 再加软失效+可执行作废(R5); 最后 on-demand 反思(R6)。只借 mem0/A-MEM/Generative Agents/Zep 的 prompt+schema+算法内核, 不引任何 runtime。与用户进行中的 memory-vault Plan v3 合并实施(本调研是其算法侧证据校验, 不另起 plan)。
- **risks**:提取膨胀(salience gate + 显式触发); 裸DELETE丢信息(soft-delete); LoCoMo 不可信(自建 holdout 验证); 衰减常数/trust 阈值需校准(holdout); embedding 漂移(content hash + 惰性重嵌); stale-poisoning(trust 衰减 + 复用 redact gate); 跨 5 agent schema 一致性(枚举定死 + 校验脚本)。
- **verification**:自建 holdout 而非 LoCoMo: (1) 时序问答 holdout——事实被 supersede 后必须返回新值且能查到旧值 invalid_at; (2) 注入与代码冲突的 memory, 断言 verify 钩子自动写 invalid_at='code-conflict'; (3) 注入 MINJA 式投毒记忆, 验证 trust 衰减+阈值把它挡在召回外; (4) 多跳召回测试(内存邻接表 BFS 顺链 2-3 跳); (5) 回归: 高 importance 但久未访问的记忆不被衰减错杀; (6) salience gate 对寒暄/通用知识返回空数组; (7) 巩固对'又养一只狗 Scout'不误删'Buddy'; (8) 召回 hybrid vs 纯 dense 在含专有名词/ID 的 query 上 recall 提升; (9) BM25/numpy/embedding key 在 5 agent hook 环境可用 + 单脚本 stdin/stdout 烟测。
- **deriskSpikes**:S1 embedding 一致性 spike: content hash 校验 + 手改 md 后惰性重嵌是否正确触发(纯文件方案最易踩的工程坑)。S2 衰减常数标定 spike: 用几条已知 last_accessed 的真实 memory 校准日历尺度半衰期, 确认老但重要的记忆不被埋没。S3 query 扩展 spike: 复用 deepseek 骨架做改写+时间抽取, 验证弱模型时间抽取是否因幻觉净负收益(若是则对时间结果加校验或不做)。S4 多跳 BFS spike: 几千条内存邻接表顺 wikilink 跳 2-3 跳的延迟与召回, 确认 flat+link 够用、无需 PageRank。S5 跨 agent 单脚本 spike: stdin query→stdout 召回 在 cc/kilo/opencode/codex/droid 五个 hook 环境跑通(numpy/BM25/key 可达性)。

## 风险

- [confirmed] LoCoMo 数字全是厂商互撕不可作选型铁证(Zep 84%→58.44%→75.14%, full-context 73 反超, 简单 filesystem 74%); 用 LongMemEval(独立消融)作主参考, LoCoMo 仅 sanity check, 验证一律用自建 holdout
- [confirmed] 写入膨胀真瓶颈在提取不在巩固(mem0 97.8% junk, '更强模型更忠实照烂 prompt 乱抽'); 若 5 agent 把每条对话都灌进 staging 会爆炸, 必须 salience gate(类目白名单+空数组负例)+ 显式触发, 不每轮 hook 裁决
- [confirmed] 裸物理 DELETE 丢信息(mem0 #4536 删旧不加新留空状态; Buddy/Scout 同类多实例误判为矛盾); 必须矛盾→UPDATE 标 superseded + soft-delete, git 留历史, prompt 给'多实例≠矛盾'few-shot
- [confirmed] LLM importance 1-10 分 noisy/系统偏高/缺理论锚, 不可做 salience 排序; 用二值+类目优先级
- [confirmed] recency 衰减常数 0.995 是 game-hour 尺度, 真实日历直接用会让老记忆衰减过快被永久埋没; 必须基于 last_accessed + holdout 重标定
- [confirmed] stale-memory-poisoning 真实(MINJA query-only 98.2% 注入); trust 阈值校准是安全-可用性根本权衡(过严全拒/过松 54/82 恶意被采信), 无一键安全, 先保守降权 + 人工抽检
- [confirmed] mem0/A-MEM/Letta/LangMem 官方实现都带向量 DB/服务端/常驻进程, 直接 pip 装违约束; 只采纳 schema+算法+prompt, 不引 runtime
- [inferred] embedding 缓存(.npy/JSONL)与 md 正文会漂移(git merge/手改 md 后召回静默错乱); 需 content hash 校验 + 缺失惰性重嵌, .npy 用 .gitignore + 幂等 rebuild 命令避免二进制 diff 噪声
- [inferred] frontmatter related/wikilink 无图的传递闭包; 多跳要检索时自建内存邻接表 BFS(几千条毫秒级可接受但需在 Verification 测多跳召回, 别默认 flat 永远够)
- [confirmed] A-MEM memory evolution 静默改写邻居 context/tags 无版本, 与 git SSOT 冲突; 只取 note schema + 链接, 不取 evolution 重写
- [confirmed] 反思过度泛化/语义漂移('微辣'漂成'爱吃很辣'); 强制 (because of <id>) 引用 + 双轨存原文不删 + 支撑<2不升规则 + 被推翻标 stale 不静默改写
- [inferred] 跨 5 agent 一致性: frontmatter schema(type/status 枚举)一旦软链分发要一次定死并加校验脚本, 否则某 agent 写入不规范污染共享库; BM25/numpy/embedding key 三者需在每个 agent hook 环境可用, 封装成单可执行脚本靠软链分发

## 各维原始发现(节选)

### 召回 (Retrieval): LLM agent 长期记忆的检索算法选型 — lexical vs dense vs hybrid vs graph、rera

**最佳实践**:2024-2026 的实证共识(以 LongMemEval 消融为最干净证据,因其同时控制了 indexing 与 reading,且非厂商自评):召回质量的提升顺序不是「换更花哨的检索算法」,而是 **索引粒度 + key 扩展 + 时间感知 > 检索算法本身**。LongMemEval 实测:(1) 把 session 拆成 round 粒度做 value 显著优于整 session;再过度压成 summary/fact 反而掉点(信息损失),除多跳推理类外;(2) 给每条 memory 的 key 加 LLM 抽取的 user facts(key = value + fact)带来 recall@k +9.4%、终答 +5.4%;(3) time-aware query expansion 让时间类问题 recall +6.8~11.3%(但用弱模型抽时间会因幻觉反伤)。其 best 配置 recall@5=0.644 / recall@10=0.784。\n\n检索算法层面的实证排序:graph+PPR(HippoRAG 2)在多跳/关联记忆上确实最强(Recall@5 78.2 vs dense 73.4),但代价是每条 memory LLM 抽三元组 + 检索时 LLM 过滤 + 维护图。hybrid(dense+BM25+RRF)在绝大多数对话记忆任务上接近 graph 且成本低一个数量级。纯 dense 已能拿到大部分分数(mem0 纯向量在 LoCoMo 与 graph 版几乎持平,multi-hop 甚至略胜其自家 graph 版),graph 的边际收益主要在多跳/时间推理。rerank 普遍有用但收益小于上面三项;RRF 几乎零成本、cross-encoder rerank 要额外模型不划算。评分上,在 dense 相似度之上叠加 Generative Agents 式 recency×importance 的结构化排序,是低成本高杠杆的「类 graph」替代。

**对约束**:约束高度有利于「轻量派」,且我已实测验证核心假设。\n\n- **不要向量 DB / brute-force 行不行**:行,且远未到边界。实测 1024 维 float32:3000 条 = 0.33ms,1万条 = 0.72ms,5万条 = 4.88ms(均含 top-10)。即用户「几百~几千条」下 brute-force numpy cosine 是亚毫秒,向量 DB 在 ~5万条前都纯属过度工程。开始「不行」的拐点 [推断]:单 query 延迟到几十毫秒(N≈30万~50万)、或内存吃紧(N=5万仅 20MB,故内存不是瓶颈)、或需要持续高 QPS 并发。用户场景永远到不了。真正瓶颈是 embedding 调用,不是搜索。\n- **文件型存储(md+frontmatter / JSONL, git-tracked)**:与 dense+lexical hybrid 完美契合。向量可存 JSONL 旁路文件或 frontmatter base64,启动时 numpy 一次性 load 进内存(几十 MB);BM25/grep 直接在 md 正文上跑,零额外存储;Generative Agents 评分的 importance/timestamp 天然就是 frontmatter 字段,recency 可复用文件 mtime。\n- **hook 内一次带 fallback 的 API 调用**:恰好匹配。强烈建议这一次调用用于 **query 改写/扩展**(LongMemEval 的 key-expansion 与 time-aware expansion 是收益最高的两个旋钮),fallback = 直接用原始 query。**不要**把这次调用花在 LLM rerank/过滤(HippoRAG 2 的 recognition step)——那需要对 top-k 候选逐条判定,一次调用 cover 不了且失败面大。\n- **跨 5 agent 纯文件 + 软链**:dense brute-force + BM25 是纯计算 + 纯文件,无常驻进程、无服务依赖,可被任意 agent 的 hook 以子进程方式调起,最易分发。graph 方案(HippoRAG/Zep)依赖 Neo4j/图引擎或重建图,违反「不要常驻进程」与「纯文件分发」,直接出局。\n- **优先复用而非造平行体系**:用户已有 capsule 路由用 deepseek 做「一次带 fallback 的分类调用」的成熟模式,query 扩展可直接复用同一调用骨架与 key 管理。

**推荐**:**推荐:dense(brute-force numpy cosine)+ BM25 lexical 的 hybrid 召回,RRF 融合,叠加 Generative Agents 式 recency×importance 重排;hook 内那一次带 fallback 的 API 调用专用于 query 扩展(LLM 改写 + 抽时间范围),失败则回退原 query。不引入向量 DB、不引入图谱、不引入常驻进程。**\n\n落地分层(按 ROI 排序,前两层就能拿到大部分召回质量):\n1. **必做(零外部依赖)**:dense brute-force + BM25 双路 + RRF 融合。向量存 JSONL/frontmatter,启动 numpy load;BM25 纯 Python 实现(rank-bm25 或自写)对几千条够用。这一层即对标 mem0 纯向量(LoCoMo J≈67),加 BM25 补专有名词/ID 召回。\n2. **强烈建议(复用现有 deepseek 调用模式)**:hook 内一次 query 扩展——LLM 把用户当前 prompt 改写成检索 query + 抽取时间范围,fallback 用原 prompt。对标 LongMemEval 的 key-expansion(+9.4% recall)与 time-aware(+6.8~11.3% 时间类 recall),是单次调用能买到的最高杠杆。\n3. **建议(纯本地计算)**:在融合分上叠加 recency(文件 mtime 指数衰减)× importance(写入时 LLM 打分存 frontmatter)的 Generative Agents 加权,作为「类 graph」的低成本关联/优先级信号。\n4. **索引粒度**:memory 写成 round/atomic-note 粒度(A-MEM 的 Zettelkasten 原子化思路),一条一事,别整段塞——LongMemEval 实测细粒度 value 优于整 session。\n\n**显式不推荐**:HippoRAG 2 / Zep-Graphiti 的图谱+PPR 路线。理由非质量(其多跳/时间 Recall@5 确实最高),而是与约束硬冲突:需常驻图引擎(Neo4j)或每次重建图、每条 memory 要 LLM 抽三元组、检索时要 LLM 逐 triple 过滤——违反「不要常驻进程 / hook 内仅一次调用 / 纯文件分发」。用户几千条单用户场景,graph 的边际收益(主要在跨多文档深多跳)远不抵其工程与跨 agent 分发成本;用第 3 层的 recency×importance 重排即可拿到「关联记忆」的大部分实用价值。

**坑**:LoCoMo 分数是厂商营销级证据,不是中立基准。mem0 称 Zep 75 实为 58.44%;Zep 反指 mem0 配置错误并自更正为 75.14%,还指出 LoCoMo 本身缺陷(类别5无 ground truth、多模态/说话人标注错误、平均仅 16k-26k token 现代 LLM 一个 context 就装下、full-context 裸跑 J≈73% 反超 mem0 graph 68%)。结论:不要拿任一厂商的 LoCoMo 数字做选型依据;LongMemEval 因有独立 indexing/reading 消融、非自评,可信度更高,应作为主要参考。; '纯 dense 就够'是危险简化。dense 会系统性漏专有名词、ID、罕见词、精确字符串——这些恰是 agent memory 里高价值条目(文件名、命令、配置 key)。BM25/grep 这一路几乎零成本却补上这个盲区,省掉它是用召回质量换微小代码量,不划算。; 把 hook 的那次 API 调用花在 LLM rerank/triple 过滤(HippoRAG recognition step)是错配:rerank 要对 top-k 候选逐条判定,一次调用 cover 不全,且失败时无优雅 fallback。那次调用应花在 query 扩展(单次、有天然 fallback=原 query)。; 过度压缩记忆会掉点。LongMemEval 实测:把 round 进一步压成 summary/fact 会因信息损失伤害大多数问题(仅多跳推理类受益)。别为省 token 把 memory 抽象成干瘪 fact 卡,保留原始 round/note 文本。
**来源**:https://arxiv.org/abs/2504.19413 (mem0 论文, LoCoMo Table 1/2 — dense 检索 + 延迟数字, confirmed); https://arxiv.org/html/2501.13956v1 (Zep/Graphiti 论文 — 三路 hybrid 检索 φ_cos+φ_bm25+φ_bfs + reranker, confirmed); https://arxiv.org/html/2502.14802 (HippoRAG 2, ICML 2025 — query-to-triple + PPR + recognition memory, Recall@5/多跳 F1 表, confirmed); https://arxiv.org/html/2410.10813v2 (LongMemEval — 检索消融:粒度/key-expansion/time-aware, recall@k 数字, confirmed); https://ar5iv.labs.arxiv.org/html/2304.03442 (Generative Agents — recency×importance×relevance 评分公式, confirmed); https://arxiv.org/abs/2310.08560 (MemGPT/Letta — self-paging 检索触发范式, confirmed); https://arxiv.org/pdf/2502.12110 (A-MEM — Zettelkasten 原子化 + embedding 初筛 + LLM 链接, confirmed); https://github.com/getzep/zep-papers/issues/5 (Zep 自更正 LoCoMo 至 58.44%/75.14% — 基准争议一手, confirmed)

### 编码 / salience：从一段对话抽出哪些「值得记」的原子事实（写入侧的事实抽取与重要性判定）

**最佳实践**:2024-2026 的写入侧 SOTA 收敛到一个共识结构：LLM 抽取原子事实 + 强制带 context + 写入时增量协调（ADD/UPDATE/DELETE/NOOP），而不是『全量追加』也不是『纯启发式正则』。三条经验证的设计要点：(1) 抽取要给明确类目清单 + few-shot 教模型对寒暄/通用知识/已知冗余返回空（mem0 FACT_RETRIEVAL_PROMPT 的做法），否则 LLM 会过度抽取产生噪声。(2) 每条事实必须自带 context/来源（A-MEM 的 X_i、LangMem 的 triple+context、mem0 的去歧义），否则检索时歧义、无法 dedup。(3) 写入不是 append 而是 reconcile：新候选要先拉相似旧记忆再让 LLM 决定 add/update/delete，这是 mem0 相对 Generative Agents 全量流的关键升级，也是省 token、保持一致性的来源。

关于『LLM 抽取 vs 启发式 vs 全量后筛』的质量证据取舍：LLM 抽取在多跳/时序类问题上明确胜出（A-MEM 多跳翻倍 MemGPT、mem0 全面领先 baseline）；但 Generative Agents 式的 LLM importance 1-10 打分被后续研究判定 noisy/偏高/缺理论锚——所以『用 LLM 抽事实』可信，『用单一 LLM 数字分做 salience 排序』不可信，salience 更应体现在『抽不抽（二值 + 类目）』而非『打几分』。全量保留只在极小规模（<150 会话，ConvoMem confirmed）才划算。

**对约束**:用户约束高度有利于『轻量 LLM 抽取』而非『复杂记忆系统』：

1. 体量几百~几千条 + 单用户：正好踩在 ConvoMem 的 150 会话拐点附近偏上。结论是——不需要向量 DB、不需要图谱、不需要 reflection 那套；但比纯 full-context 略大，做一层 LLM 抽取仍有价值（省后续每次检索的 token、让事实可被人读/git diff）。这把 mem0/A-MEM 那套重型协调砍到最小可用即可。

2. 写入可调 LLM（异步/skill 步，慢一点可接受）：完美契合 mem0/LangMem 的设计——它们本来就把抽取放后台/异步（LangMem ReflectionExecutor、mem0 异步摘要）。所以 salience 抽取走『一次带 fallback 的 LLM 调用』完全成立，且不必担心延迟。

3. 文件型 markdown+frontmatter / JSONL + git-tracked：A-MEM 的 7 属性 note 几乎就是 frontmatter 的天然映射（keywords/tags/context/timestamp/links 全是 frontmatter 字段，content 是正文）；mem0 的 facts 数组适合 JSONL。两者都能纯文件落地，无需常驻进程。

4. 跨 5 agent 纯文件 + 软链 + 优先复用：不要引入 mem0/Letta 这类带服务端/SDK 的体系（会破坏纯文件 + 跨 agent）。复用的是它们的 prompt 设计与数据 schema（开源、可直接抄 prompt），而不是它们的 runtime。

不适配的部分：mem0 的向量检索 top-s 协调、A-MEM 的嵌入建链/记忆进化（每次写入要重算近邻并改旧文件）、Generative Agents 的 reflection——这些在几千条 + 单用户下是过度工程，且记忆进化会让 git diff 变脏、难以人审。

**推荐**:采用『mem0 风格的 LLM 抽取 prompt + A-MEM 风格的 frontmatter note schema』组合，砍掉所有重型协调，落地为单次异步 LLM 调用。具体：

A. 抽取（salience 判定）——抄 mem0 FACT_RETRIEVAL_PROMPT 的骨架，但裁剪到你的领域类目。明确告诉 LLM 该记什么：决策/选型结论、用户偏好与约束、纠错（『不要这样做』）、失败模式与根因、不可逆操作的边界——这正好对应你 CLAUDE.md 里已有的『决策/偏好/纠错/失败模式』价值观。明确告诉它忽略：寒暄、可重新推导的通用知识、与已有记忆重复且无新增信息的内容、一次性 unactionable 陈述。强制 few-shot 含『返回空数组』的负例（这是 mem0 控噪的关键，confirmed）。输出 JSON facts 数组。

B. 不要用 Generative Agents 的 1-10 importance 打分做排序（已被证 noisy）。salience 用二值判定（抽 or 不抽）+ 类目标签代替分数。如果确实要排序，用类目优先级（decision > correction > preference > fact）这种确定性规则，比 LLM 数字分稳。

C. note schema 抄 A-MEM 的可读子集，落成 markdown frontmatter：每条记忆 = {content（原子事实，自带 context 一句话来源/场景）, type（decision/preference/correction/failure-mode/fact）, keywords, tags, created, source（会话/commit 锚点）}。这天然 git-friendly、人可读、可 diff。

D. 写入协调降级为『轻量 reconcile』：抽完后用 brute-force numpy cosine 对几千条已存记忆找 top-k（毫秒级，符合你约束），把候选 + top-k 一起再喂 LLM 做一次 ADD/UPDATE/SKIP（去掉 DELETE 的自动化，删除走人审/标记 deprecated，避免自动删错且保持 git 可追溯）。这保留了 mem0 去重的核心收益，又不引入向量 DB。

E. 整条链就是『一次带 fallback 的 LLM 调用』：抽取 + reconcile 可合并成一次调用（喂入新交换 + top-k 相似旧记忆，让它直接输出『要新增/更新哪些 note』）；LLM 不可用时 fallback 到不写入（fail-open，宁可漏记不可乱记），与你 capsule 路由的 fail-open 同构。

这套是『复用 prompt 与 schema、不复用 runtime』，最贴合 SSOT + 跨 5 agent + 纯文件约束。

**坑**:LLM 过度抽取（over-extraction）：mem0 社区实测 infer=True 下 LLM 过滤过激/抽太多噪声（digitalrain.studio 复盘）。对策：few-shot 必须含返回空数组的负例；类目白名单收紧；宁缺毋滥。; 用 LLM 1-10 importance 分做 salience 排序不可靠：后续研究证其 stochastic、系统性偏高、缺理论锚。别照抄 Generative Agents 的打分排序，改用二值+类目优先级。; LoCoMo 数字不能尽信：简单 filesystem 操作就能拿 74%，benchmark 区分度被批评不足；跨论文的 A-MEM 时序分（45.85 自报 vs 49.91 被 mem0 复现反超）说明实现/配置差异巨大，别拿单一榜单数字当选型铁证。; 在你的体量上过度工程：几百~几千条 + 单用户处于 ConvoMem 150 会话拐点附近，盲目上向量 DB/图谱/reflection 是负收益。先做最小 LLM 抽取，验证有效再加。
**来源**:https://arxiv.org/html/2504.19413v1 (Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory, 2025 — 两阶段抽取/更新、LoCoMo 数字、延迟与 token); https://github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py (mem0 FACT_RETRIEVAL_PROMPT 与 UPDATE_MEMORY_PROMPT 源码); https://docs.mem0.ai/open-source/features/custom-fact-extraction-prompt (mem0 自定义抽取 prompt 文档); https://arxiv.org/html/2502.12110v1 (A-MEM: Agentic Memory for LLM Agents, NeurIPS 2025 — note 七属性构造、Ps1/Ps2/Ps3、LoCoMo 多跳 45.85); https://github.com/agiresearch/a-mem (A-MEM 官方实现); https://arxiv.org/pdf/2304.03442 (Park et al. 2023, Generative Agents — importance 1-10 poignancy prompt、recency/importance/relevance 检索、reflection 触发); https://note.com/mega_gorilla/n/n63b77b6ef6a3?hl=en (Generative Agents 论文英译，逐字引用 importance prompt 与公式，用于交叉验证); https://langchain-ai.github.io/langmem/guides/extract_semantic_memories/ (LangMem 语义记忆抽取：profile vs collection、triple+context、并行 INSERT/UPDATE/DELETE)

### 巩固/更新：新候选 memory 对既有 memory 的 ADD/UPDATE/DELETE/NOOP 裁决（防膨胀、防矛盾）

**最佳实践**:当前业界对‘巩固/更新’收敛出的最佳实践范式高度一致，可拆成 5 个可独立采纳的零件（confidence 标注分散在各条）：

1) 写入前必检索（confirmed，mem0/LangMem/A-MEM/RMM 全部这么做）：新候选不能盲目 append，必须先用 embedding 检索 top-K（mem0 k=10、A-MEM k=5、LangMem top-K 可配）相关既有项，把‘旧项+新项’一起交给 LLM 裁决。这是防膨胀的第一道闸。

2) 一次 LLM tool-call 做结构化裁决（confirmed）：让 LLM 对每条既有项返回结构化 event(ADD/UPDATE/DELETE/NOOP) + 保留原 id + 对 UPDATE 带 old_memory 字段做审计。mem0 的 prompt+JSON schema 是可直接抄的最成熟模板。

3) 提取(extraction)才是真瓶颈，不是裁决(consolidation)（confirmed，Issue #4573 作者原话）：97.8% junk 的根因是提取 prompt 太 permissive 导致把心跳/系统噪声/重复 boot facts/幻觉都抽进来——‘更强的模型反而更忠实地照烂 prompt 乱抽’。所以防膨胀的投入产出，提取阶段的 ‘salience gate / 只抽稳定个人事实、拒绝 transient’ 远高于事后裁决。

4) UPDATE/合并优先于 DELETE（inferred + confirmed 反例）：mem0 Issue #4536 证明把矛盾直接判 DELETE 会丢信息（删旧不加新→空状态）。更稳的策略是矛盾→UPDATE 成‘当前值’或追加带时间戳的新值并标记旧值 invalid（Zep/Graphiti 的做法：标 invalid 不物理删，保留时序）。

5) 巩固放后台、可审计、不可静默丢（confirmed）：Letta sleeptime / LangMem ReflectionExecutor 都把巩固/去重移到对话间隙后台跑并 debounce。配合‘evolution 改写历史项必须留版本/diff’（A-MEM 被社区点名的风险正是无版本历史不可调试）。

**对约束**:落地约束高度契合，且用户【已经在跑】这套 store 的雏形（实测：~/.claude/projects/.../memory/ 下是 markdown+frontmatter(name/description/metadata.node_type=memory) + MEMORY.md 索引 + [[wikilink]] 关联 + originSessionId 溯源；且有进行中的 memory-vault 改造程序 docs/memory-vault-plan-2026-06-23.md）。逐条映射：

- 文件型 store：完全成立。几百~几千条 memory，每条一个 md 文件，frontmatter 存结构化字段，MEMORY.md 当索引——这正是 A-MEM 的 atomic-note + 索引模型的文件版，零向量 DB。

- 写入带一次检索+LLM 裁决：完全在约束内。‘brute-force numpy cosine over 几千向量=毫秒级’足够做 top-K 检索；‘hook 里一次带 fallback 的 API 调用’（用户 capsule 路由已验证可行）足够做 mem0 式的单次裁决 tool-call。即：写新 memory 时 → numpy cosine 取 top-5~10 相关 md → 一次 LLM call 返回 ADD/UPDATE/DELETE/NOOP+目标文件 → 落盘改对应 md。

- 不要向量 DB / 不要常驻进程：成立。embedding 可预算成每文件一个 .npy 或 frontmatter 里的 base64/sidecar JSONL；检索期 numpy 全量点积。Letta sleeptime / LangMem ReflectionExecutor 的‘常驻后台 agent’这条【不采纳】，改成‘git pre-commit 或显式 /memory-consolidate 命令触发的批量巩固’（无常驻进程版）。

- 跨 5 agent 纯文件+软链：成立。裁决逻辑写成一个 python 脚本(脚本被 5 agent 的 hook 共同调用)，memory 目录软链分发，5 agent 读同一份 md。

- 优先复用而非造平行体系：强约束下不应整包引入 mem0/Letta（带 SDK/向量 DB/server）。应【只借算法不借实现】：抄 mem0 的 UPDATE prompt+JSON schema、借 A-MEM 的 note schema 与 link 字段（用户已有 [[wikilink]]）、借 LangMem 的‘后台 debounce’改成‘离线批处理’。

**推荐**:推荐：以 mem0 的‘检索 top-K → 单次 LLM tool-call 逐条裁决 ADD/UPDATE/DELETE/NOOP’为主干，叠加三处针对用户场景的硬性改造，落成一个纯文件、无常驻、git-tracked 的 consolidation loop。不直接装 mem0/Letta（重依赖、向量 DB、与现有 md+frontmatter 体系平行）。

具体写入 loop（每次有新候选 memory 时触发，建议放在显式 /memory-save 命令而非每条对话 hook，避免 #4573 式膨胀）：

step 0  提取闸门（最高 ROI，对应 #4573 根因）：候选必须先过 salience gate——只接受‘稳定的用户事实/决策/约束/纠偏’，显式拒绝 transient(心跳、cron、boot facts、单次操作)。这一步用一个保守 prompt，宁可漏不可滥。

step 1  检索：对候选文本算 embedding，numpy 全量 cosine 对 memory/*.md 的 sidecar 向量取 top-K(K=5~8，几千条毫秒级)。

step 2  裁决（抄 mem0 prompt+schema）：把 [候选 + top-K 既有项(带文件名当 id, frontmatter description + 正文摘要)] 一次性交给一次带 fallback 的 LLM call（复用 capsule 路由那套 fail-open），返回 JSON：[{id(文件名), event:ADD|UPDATE|DELETE|NOOP, new_text?, old_memory?, reason}]。

step 3  执行 + 防矛盾改造（对应 #4536）：
  - ADD → 新建 md（frontmatter 写 name/description/originSessionId/created_at + sidecar embedding），并在 MEMORY.md 加一行索引。
  - UPDATE → 改对应 md 正文，frontmatter 加 updated_at，正文保留‘旧值(invalid since DATE)’一行而非直接覆盖（审计+可回溯）。
  - DELETE → 【禁止裸 DELETE】。矛盾一律降级为 UPDATE‘当前值=新，旧值标 superseded’。真正要删只允许 soft-delete(移到 memory/archive/ 或 frontmatter status: archived)，绝不物理删，因为 git 是 SSOT。
  - NOOP → 不动。

step 4  关联（借 A-MEM/复用现有 [[wikilink]]）：ADD/UPDATE 时让同一次 call 顺带产出 2-3 个 suggested [[wikilink]] 指向 top-K 里语义最近的项，写进正文末尾。【不采纳 A-MEM 的 evolution-改写邻居】——它会静默改写历史 context/tags 且无版本，与 git SSOT + 可审计冲突，ROI 也低。

step 5  离线巩固（替代 Letta sleeptime / LangMem ReflectionExecutor 的常驻版）：提供一个显式 /memory-consolidate 批处理命令（或 git pre-commit hook），对全库做：重复检测(cosine>阈值的合并)、矛盾扫描、孤儿索引修复。绝不常驻、绝不自动静默改写——产出 diff 给人确认后再 commit。

一句话：主干用 mem0 的裁决算法 + prompt（最成熟、有源码可抄），但把它的两个已知坑（裸 DELETE 丢信息 #4536、提取太滥 #4573）用‘提取闸门 + 禁裸删/改 soft-delete + UPDATE 保旧值’堵死；用户已有的 md+frontmatter+[[wikilink]]+MEMORY.md 索引直接当 store，零向量 DB、零常驻、git 可审计。

**坑**:裸 DELETE 丢信息（confirmed, mem0 #4536）：把矛盾直接判 DELETE，会删旧项却不补新项，留下空状态。务必把矛盾降级为 UPDATE(标 superseded)+soft-delete，禁止物理删——尤其 git 是 SSOT 时物理删=丢历史。; 真瓶颈在提取不在裁决（confirmed, mem0 #4573，作者原话）：97.8% junk 的根因是提取 prompt 太 permissive，把心跳/boot facts/系统噪声/幻觉全抽进来；‘更强模型反而更忠实照烂 prompt 乱抽’。若只优化 consolidation 不加 salience gate，膨胀照样发生。这是用户场景最大的坑，因为 5 agent 的 hook 很容易把每条对话都灌进来。; 幻觉自我放大反馈环（confirmed, #4573）：一条幻觉‘User prefers Vim’被后续 session 反复召回再抽取，滚成 808 条重复。对策：UPDATE/检索去重必须在写入前生效，且巩固时跑 cosine 去重。; A-MEM 式 evolution 静默改写历史且无版本（confirmed 源码 + 社区点名风险）：update_neighbor 会原地覆盖邻居的 context/tags，无 diff 无版本，难调试且不可审计。与 git SSOT 直接冲突，不要照搬。
**来源**:https://arxiv.org/html/2504.19413v1 (Mem0 论文：top-s=10 检索、四操作、function-call、LoCoMo 自报数字、Mem0^g graph 变体); https://github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py (DEFAULT_UPDATE_MEMORY_PROMPT 源码：ADD/UPDATE/DELETE/NONE 规则 + JSON schema + few-shot); https://docs.mem0.ai/open-source/features/custom-update-memory-prompt (官方更新 prompt 文档); https://github.com/mem0ai/mem0/issues/4536 (确认 bug：矛盾→裸 DELETE 丢信息); https://github.com/mem0ai/mem0/issues/4573 (审计 10134 条 97.8% junk，根因在提取 prompt); https://github.com/mem0ai/mem0/issues/1499 (LLM 返回 UPDATE 却缺 id); https://arxiv.org/abs/2502.12110 (A-MEM 论文：note construction / link generation / memory evolution / LoCoMo F1); https://github.com/agiresearch/A-mem (A-MEM 官方源码 agentic_memory/memory_system.py：_evolution_system_prompt 全文、process_memory k=5、should_evolve/update_neighbor JSON schema)

### 表示 / memory 分型与结构 (typology & structure of a memory record)

**最佳实践**:2024-2026 的共识最佳实践,落到「一条 memory 的表示」上有四点收敛证据:

(1) 分型用 episodic / semantic / procedural 三分(CoALA 母本,Letta/LangMem/2026 survey 一致采纳),working/short-term 不入库(就是当前上下文)。三类的载体不同:semantic=可累积的原子 fact;episodic=带时间的事件/会话摘要;procedural=规则/操作卡/技能。confirmed。

(2) 表示粒度:主流从「整文档」转向「LLM 抽取的原子 fact / 原子 note」(mem0 的 fact、A-MEM 的 note)。原子化是 LoCoMo 上 token 效率与多跳性能的关键(A-MEM 省 85% token、多跳 F1 翻倍)。confirmed。

(3) 字段 schema 的共识最小集:原始内容 + 创建时间戳 + LLM 生成的 keywords/tags + 一句 contextual 描述 + importance(可选)+ embedding(可选,外置)+ links。A-MEM 七字段是最完整的公开 schema;Generative Agents 贡献 importance + last-accessed;Zep 贡献 valid-time/invalidation。confirmed。

(4) graph vs flat:对单用户、几百~几千条体量,证据明确不支持上图数据库。mem0g(图)比 mem0(flat)只多 ~1.5pt 总分,且 single/multi-hop 反而更差、慢 ~3x、贵 ~2x;A-MEM 证明 flat note + LLM 判定的双向 link 已能拿到 SOTA 多跳。graph 的真正价值(Zep)在「时序事实失效 + 大规模实体消歧」,这是企业多用户/长时演化场景,不是本约束场景。confirmed。关键洞察:graph 的收益可解耦为两个可降级机制 —— 关联(降级为 frontmatter wikilink/related 字段)+ 时序失效(降级为 status + valid_from/valid_to 字段),无需真图引擎。

**对约束**:落地约束(单用户、几百~几千条、文件型 markdown+frontmatter/JSONL、git-tracked、可用 embedding 但不要向量 DB/不要常驻进程、hook 里一次带 fallback 的 API 调用、跨 5 agent 纯文件软链)对 SOTA 算法的裁剪结论:

- 不要图数据库:mem0g vs mem0 数据(+1.5pt / 慢 3x / 贵 2x)证明小体量上图负收益。A-MEM 证明 flat + link 就够。→ 采纳 flat note + frontmatter 内 links。
- 链接能降级为 frontmatter wikilink:A-MEM 的 L_i 链接集合本质是双向引用,完全可写成 frontmatter 里 `related: [id1, id2]` 或正文 `[[wikilink]]`。不需要图引擎,brute-force numpy 余弦取 top-k 候选 + hook 里一次 LLM 调用判定哪些建链(正是用户 capsule 路由的同款模式)。
- embedding 可用但外置:embedding 存为旁路 .npy / JSONL 一列(git-track 或 .gitignore 按需),query 时 numpy cosine over 几千向量 = 毫秒级,不需要 ChromaDB/向量 DB/常驻进程。A-MEM 默认依赖 ChromaDB 但七字段 schema 与之解耦,可移植。
- timestamp + 时序失效:借 Zep 的 bi-temporal 思想但降级为 frontmatter 标量字段(created / valid_from / valid_to / status: active|superseded),矛盾时标 superseded 而非删除(保 git 历史)。无需图。
- 三型分目录或 type 字段:episodic/semantic/procedural 用 frontmatter `type:` 区分,或分目录,跨 5 agent 软链同一份 markdown 即可,无平行体系。
- importance 字段可选:Generative Agents 的 importance 对'几千条内全召回'场景边际收益低,可先不引入,backlog 化。

**推荐**:推荐:采用「flat 原子 note + markdown frontmatter schema」,三型(episodic/semantic/procedural)用 type 字段区分,关联降级为 frontmatter 内 wikilink/related,embedding 外置为旁路文件做 brute-force numpy 检索,时序用标量字段做 superseded 软失效。明确不上图数据库、不上向量 DB、不上常驻进程。

理由链:CoALA 给分型(confirmed),A-MEM 给「flat note + LLM 判定链接」已达 SOTA 多跳且省 85% token(confirmed),mem0g vs mem0 数据证明图在小体量负收益(confirmed),Zep 的时序价值可降级为标量字段(inferred from Zep 机制)。

推荐字段 schema(每条 memory 一个 md 文件,或 JSONL 一行;frontmatter):
```yaml
---
id: mem-2026-0623-001        # 稳定 ID,用于 links
type: semantic               # semantic | episodic | procedural
created: 2026-06-23T10:00:00Z
valid_from: 2026-06-23       # episodic/可变事实用;不变事实可省
valid_to: null               # 被取代时填日期
status: active               # active | superseded
keywords: [capsule, deepseek] # LLM 生成,检索召回用
tags: [routing, infra]       # LLM 生成,分类用
related: [mem-2026-0610-003] # = A-MEM 的 links,降级为 wikilink
embedding_ref: emb/mem-...001.npy  # 旁路,可选;不入 frontmatter 正文
importance: null             # 可选,backlog;先不启用
---
原始内容一句话原子 fact / 事件摘要 / 操作卡正文。
正文里也可用 [[mem-2026-0610-003]] 双向引用。
```
写入流程(对齐用户 capsule 路由模式):新内容 → numpy cosine 取 top-k 近邻候选 → hook 里一次带 fallback 的 LLM 调用,判定 (a) 抽成几条原子 fact (b) 与哪些旧记忆建 related 链 (c) 是否使某旧记忆 superseded。fallback:LLM 失败则只 append 原始内容、不建链、不失效(fail-open,等同正则降级)。

procedural 记忆直接复用现有 learning note / 操作卡体裁(assist-learn 产物),不另起体系。

**坑**:LoCoMo 数字不可尽信:官方 critique(arxiv 2602.10715 / mem0 自己的 2026 benchmark blog)指出 LoCoMo 有标注模糊、重复项、可被'激进检索/大上下文'刷分等构造缺陷,且 16K-26K token 的对话其实在上下文窗口内。所有 LoCoMo 排名都应看作相对参考而非绝对真理 —— 给用户选型时别把'某系统 LoCoMo 高 2 分'当决定性证据。[confirmed]; 不要把 importance 当必备字段:Generative Agents 的 importance 是为'记忆爆炸到无法全召回'设计的;几千条内可全量 numpy 扫,importance 边际收益低还引入每条一次 LLM 打分的成本。先不上,backlog 化。[inferred]; wikilink 降级的真实代价:frontmatter related 字段没有图的传递闭包/多跳遍历能力。若未来要做 HippoRAG 式多跳推理(顺着链走 2-3 跳),纯 frontmatter 需要在检索时自己做 BFS。几千条规模这点可接受(内存里建邻接表即毫秒),但要在 Verification 里测多跳召回,别默认 flat 永远够。[inferred]; embedding 漂移与 git 噪音:embedding .npy 若 git-track 会产生大量二进制 diff;若 .gitignore 则换机/换 agent 时要重算。建议 embedding 旁路文件 .gitignore + 提供一条幂等 rebuild 命令(从 markdown 重算),不进 SSOT。[inferred]
**来源**:https://arxiv.org/abs/2309.02427 (CoALA: Cognitive Architectures for Language Agents — 分型理论母本, confirmed); https://ar5iv.labs.arxiv.org/html/2309.02427 (CoALA 全文 HTML); https://arxiv.org/abs/2304.03442 (Generative Agents — memory stream / importance+recency+relevance / reflection, confirmed); https://arxiv.org/html/2502.12110v1 (A-MEM — 七字段 note schema / Zettelkasten 链接 / memory evolution / LoCoMo 数字, confirmed); https://github.com/agiresearch/a-mem (A-MEM 官方实现 — 底层 ChromaDB+all-MiniLM-L6-v2, confirmed); https://arxiv.org/abs/2310.08560 (MemGPT — core/recall/archival 虚拟内存隐喻); https://www.letta.com/blog/agent-memory/ (Letta — memory blocks 自管理, confirmed); https://arxiv.org/abs/2501.13956 (Zep — bi-temporal 时序知识图 / 边失效 / DMR 94.8%, confirmed)

### 遗忘 / 衰减 / 失效 / 防陈旧 (Forgetting / Decay / Invalidation / Staleness-prevention)

**最佳实践**:这一维度的 SOTA 已分化成两条互补主线,且 2024-2026 的明确趋势是『软遗忘(降权检索)』在长期记忆里逐渐让位/叠加给『结构化失效(invalidate 但保留历史)』,因为后者能正确回答时序问题(what was true when),而前者只能让旧记忆更难被检索到。

(1) 软遗忘 / 衰减(降低检索概率,不改真值):Generative Agents 的 recency 指数衰减(decay 0.995,基于『上次检索时间』而非创建时间)是被复制最多的 baseline;MemoryBank/FadeMem 用 Ebbinghaus 曲线把『访问即强化、冷落即衰退』做成可剪枝的遗忘,解决无界增长。confirmed 共识:衰减应基于 last-access 而非 created,并结合 importance(防止重要但久未访问的记忆被错杀)。

(2) 结构化失效 / 防陈旧(改记忆的有效性,保留历史):Zep/Graphiti 的 bi-temporal(valid_at/invalid_at + created/expired 四时间戳)是当前最被认可的『正确做法』——矛盾时关闭旧事实的有效窗口、开新窗口,而非删除,从而既防陈旧又可查询历史,这也是它在时序 benchmark(LoCoMo temporal 83.33% vs mem0 66.47%、LongMemEval 71.2%)领先的直接原因。mem0 的 LLM 仲裁 ADD/UPDATE/DELETE 是更轻量的对照组,但 DELETE 即覆盖、无历史,且有把『新增』误判为『矛盾』的已知失败模式。LangMem 的 trustcall consolidation 是介于两者之间的工程化折中。

(3) 横切的安全维度:stale-memory-poisoning 是真实威胁(query-only 投毒成功率 >95%),其最佳防线恰好与衰减同源——给每条记忆 trust score 并随时间衰减 + 检索时按 trust 过滤/降权。但论文证明阈值校准是安全-可用性的根本权衡,不存在『一键安全』。

结论性最佳实践:对单用户长期记忆,推荐『frontmatter 显式失效字段(valid_until/superseded_by)+ 检索期 recency×importance 软衰减 + 与代码冲突时的可执行作废钩子』三件套——即用 Zep 的语义(失效不删除、保留历史)落在文件型存储上,用 Generative Agents 的检索期衰减做排序,避免引入图数据库/常驻进程。

**对约束**:落地约束(单用户、几百~几千条、markdown+frontmatter/JSONL git-tracked、可 embedding 但禁向量DB/禁常驻进程、hook 内可一次带 fallback 的 API 调用、跨 5 agent 纯文件+软链、复用优先)对各 SOTA 的取舍:

直接可移植(强匹配):
- Zep bi-temporal 的『语义』而非『实现』:把 valid_at/invalid_at/superseded_by 落成 frontmatter 字段。失效=写 invalid_at + superseded_by 指向新记忆 ID,文件不删除(git 天然保留历史,完美对应 bi-temporal 的『不删除保留可查询历史』)。无需 Neo4j/图库——单用户几千条用 frontmatter + brute-force 过滤足够。[推断] 这是 Zep 思想在文件型存储的等价落地。
- Generative Agents recency×importance×relevance:relevance=numpy brute-force cosine over 几千向量(毫秒级,符合『不要向量DB』);recency 用文件 mtime 或 frontmatter last_accessed 算指数衰减(decay 0.995 是 game-hour 尺度,真实日历需重标定衰减常数);importance 用创建时一次性 LLM 打分写进 frontmatter。三项加权在检索期纯本地算,零常驻进程。强匹配。
- MINJA 防御的 temporal-decay trust score:与上面的 recency 衰减天然同源,可复用同一套衰减;trust 初值可由来源(用户直接说 vs agent 推断 vs 外部抓取)决定,写 frontmatter。

需改造或谨慎:
- mem0 的 LLM 仲裁 ADD/UPDATE/DELETE:可在 hook 里做『一次带 fallback 的 API 调用』(正好对应用户 capsule 路由的现成模式),但必须避开它『新增误判为矛盾』的坑,且 DELETE 要改成『写 invalid_at 软删除』而非物理删,以契合 git-tracked + 可审计。
- A-MEM 的 memory evolution(重写旧 note):风险高(无版本化重写难调试),但在 git-tracked 下版本化天然解决——可保留『建链』但对『重写旧记忆属性』要走 git diff 可审计。
- LangMem/trustcall:依赖 LangGraph 运行时,与『禁常驻进程、纯文件、跨5 agent』冲突,不宜整体引入;只借鉴 consolidation 防 hoarding 的思路。

不适配(明确排除):图数据库(Graphiti 的 Neo4j 后端)、向量 DB、需要常驻 server 的 consolidation agent、强绑定单一框架运行时的方案。

特别契合点:用户的核心约束『与代码冲突时作废的可执行机制』在文件型有干净落地——把记忆的 frontmatter 加 verifiable claim(如指向某文件/某行/某命令输出),在 hook 或定期 job 里跑可执行校验(文件存在性、grep 命中、命令 exit code),失败即写 invalid_at 自动作废。这比所有 SOTA 都更强,因为通用 memory 系统无法假设记忆可被代码验证,而代码协作场景可以。

**推荐**:推荐采用『bi-temporal 软失效(Zep 语义)+ 检索期 recency/importance 衰减(Generative Agents)+ 可执行作废钩子』三层,全部落在 frontmatter,禁图库/向量库/常驻进程。理由:单用户几千条体量下,Zep 的图实现是过度工程,但它的『失效不删除、保留历史、矛盾时关有效窗口』语义是时序正确性的唯一可靠来源(benchmark 实证:时序子集 83% vs 软衰减系 66%),而这套语义恰好能 1:1 映射到 git-tracked frontmatter,零额外基础设施。

具体落地(可直接喂 /think-plan):

Requirements:
- R1 每条记忆 frontmatter 含:created_at、last_accessed、importance(1-10,LLM 创建时打一次)、valid_until(可空,TTL/显式过期)、invalid_at + superseded_by(矛盾失效时写,指向新记忆 ID)、trust(0-1,按来源初始化)、verify(可空,可执行校验断言)。
- R2 检索排序 = α_recency·exp_decay(now-last_accessed) + α_importance·importance + α_relevance·cosine,brute-force numpy,trust 与 invalid_at 作为硬过滤/降权前置。α 初值全取 1(对齐 Generative Agents),后续按 holdout 调。
- R3 写入新记忆时,hook 内做一次带 fallback 的 LLM 调用,在『同主题 top-k 旧记忆 + 新记忆』上判矛盾;判定矛盾→给旧记忆写 invalid_at + superseded_by(软失效,不删文件);判定为新增/补充→ADD(显式规避 mem0 的 Buddy/Scout 误判:prompt 里给出『同类多实例≠矛盾』的 few-shot)。API 失败→fail-open 仅 ADD,不做破坏性操作。
- R4 代码冲突可执行作废:对带 verify 断言的记忆,定期/hook 触发跑校验(文件存在、grep、命令 exit code),失败→写 invalid_at='code-conflict',git 提交可审计。

Approach 排序:
1. 先实现 R1+R2(纯本地、无 API、低风险),立刻能用且可回归。
2. 再加 R3 的 LLM 软失效(对齐用户 capsule 路由的『一次带 fallback API』成熟模式)。
3. 最后加 R4 可执行作废(这是相对通用 memory 系统的差异化优势,代码场景独有)。

Risks:
- 衰减常数:0.995 是 game-hour 尺度,真实日历必须重标定,否则记忆衰减过快/过慢。先用 holdout 几条已知答案校准。
- LLM 矛盾误判(mem0 已证有此坑):务必软失效(写 invalid_at)而非删除,保留 git 历史可回滚;并在 prompt 给『多实例≠矛盾』示例。
- trust 阈值校准(防御论文实证的根本权衡):过严丢有用记忆、过松放陈旧/投毒进来。先保守降权而非硬删,人工抽检。
- memory evolution 重写旧记忆:除非 git diff 可审计,否则不引入 A-MEM 式属性重写。

Verification:
- 构造时序问答 holdout(模仿 LoCoMo temporal):『X 现在用哪个方案』当事实被 supersede 后必须返回新值且能查到旧值的 invalid_at——验证 bi-temporal 正确性。
- 注入一条与现有代码冲突的记忆,跑 R4 校验,断言其 invalid_at 被自动写入。
- 注入 MINJA 式投毒记忆,验证 trust 衰减 + 阈值过滤把它挡在检索结果外。
- 回归:确认软衰减不会把高 importance 但久未访问的记忆错误剔除。

**坑**:把『遗忘』做成物理删除:Zep/LangMem/A-MEM 的 SOTA 共识是 invalidate/supersede 而非 delete——删除丢失时序历史(无法回答 what was true when)且不可审计。git-tracked 场景尤其应软失效(写 invalid_at)。; 衰减基于 created_at 而非 last_accessed:Generative Agents 明确用『自上次被检索以来』的时间,基于创建时间会让常用旧记忆被错误衰减。; 照搬 0.995 衰减常数:它是 sandbox game-hour 尺度,直接用在真实日历(天/周)会让记忆衰减得离谱,必须按真实时间尺度重标定。; LLM 矛盾仲裁的『新增误判为矛盾』:mem0 官方已自曝把『又养了一只狗 Scout』当成与『养了狗 Buddy』矛盾而 DELETE+ADD 覆盖原记忆——prompt 必须显式区分『同类多实例 vs 真矛盾』。
**来源**:https://ar5iv.labs.arxiv.org/html/2304.03442 — Generative Agents (Park et al. UIST 2023): recency 指数衰减 decay 0.995、importance 1-10、score 公式、无显式 forgetting; https://arxiv.org/html/2501.13956v1 — Zep: A Temporal Knowledge Graph Architecture for Agent Memory: 四时间戳 bi-temporal、LLM 矛盾检测、edge invalidation 机制、DMR 94.8% / LongMemEval 71.2%; https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/ — Graphiti 官方/Neo4j 博客:valid_at/invalid_at 有效窗口、superseded not deleted、订阅升级示例; https://mem0.ai/blog/state-of-ai-agent-memory-2026 — mem0 官方:ADD/UPDATE/DELETE/NOOP、Buddy/Scout 误判案例、benchmark 争议(58.44% vs 75.14%); https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm — mem0 新算法单 pass ADD-only、LoCoMo temporal +29.6 / multi-hop +23.1 / <7000 tokens; https://arxiv.org/html/2502.12110v11 — A-MEM (Xu et al.): Zettelkasten note、LLM 建链、memory evolution 重写旧 note、versioning/audit 风险; https://langchain-ai.github.io/langmem/concepts/conceptual_guide/ — LangMem 官方:enable_updates 矛盾修改、trustcall consolidation & invalidation、防 memory hoarding、background consolidation; https://www.langchain.com/blog/langmem-sdk-launch — LangMem SDK 发布:语义/情景/程序记忆、对话中 vs 后台更新

### 反思 / 抽象：把多条情景压成更高层语义规则（reflection / abstraction / consolidation）

**最佳实践**:当前最佳实践(2024-2026)对『反思/抽象』收敛出一套共识机制，拆成五个可独立落地的设计决策：

1) 抽象分两层，不要混。事实级合并去重(mem0 的 ADD/UPDATE/DELETE/NOOP) 和 情景→规则的高层反思(Generative Agents reflection) 是两件事。前者保证记忆不冗余、不矛盾；后者才产『更高层语义规则』。本维度的核心需求是后者，但落地时两层都要有：先去冗，再在干净的事实上做高层抽象。[confirmed]

2) 反思必须带证据引用(reflection grounding)。Generative Agents 的洞见强制 '(because of 1,5,3)' 指回底层记忆 id——这是公认的抗过度泛化第一道防线: 让 LLM 无法凭空生成 baseless generalization, 且每条规则可回溯、可在原始 trace 失效时撤销。SSGM 的『可逆和解(append-only episodic log 可回放纠错)』是同一思想的工程化。[confirmed]

3) 触发用阈值而非纯周期。Generative Agents 用『最近事件 importance 之和 > 阈值(150)』触发, 自然适配活动密度(忙时多反思、闲时不反思), 实测每天 2-3 次, 既不过度也不缺失。纯定时(每 N 条/每天) 是更简单的退化方案但易在低活动期空转或高活动期滞后。importance 用 1-10 自评打分驱动阈值累加。[confirmed]

4) 抗过度泛化是头号风险, 必须主动设计。三条已验证的反作用力: error propagation(错误经验线性复合放大)、semantic drift(反复摘要把『微辣』漂成『爱吃很辣』)、misaligned replay(看似对的经验其实误导)。对应缓解: (a) reflection grounding 强制引用; (b) 保留原始情景, 抽象与原文双轨存(SSGM Active Graph + Immutable Episodic Log), 规则可被原文证伪; (c) 预合并矛盾校验(新抽象与 core 事实冲突就拒); (d) 用『后续是否被推翻』当免费质量标签反向修剪坏规则(2505.16067)。[confirmed for mechanisms; 具体降错百分比 未验证]

5) 计算放后台/空闲, 但触发可以是按需。LangMem(background ReflectionExecutor + after_seconds debounce) 和 Letta(sleep-time dream subagent) 代表主流方向: 反思异步、不阻塞主回路、并把碎片合并成一次完整 context 的反思以省 token。其中 LangMem 的 debounce 思想(窗口内新事件取消旧反思任务、合并后再跑) 对无 daemon 场景最可移植——它的本质不是『常驻进程』而是『延迟+去重的单次调用』。[confirmed]

**对约束**:把上述机制映射到落地约束(单用户、几百~几千条、文件型 markdown+frontmatter/JSONL git-tracked、可 embedding 但无向量 DB/无常驻进程、hook 内可一次带 fallback 的 API 调用、跨 5 agent 纯文件+软链)：

直接可用：
- Generative Agents 三段式反思 [完全适配]: importance 1-10 写进 frontmatter; 触发用『自上次反思以来累计 importance > 阈值』, 阈值在文件里是一次 numpy 求和即得, 无需进程; 反思的 retrieve 用 brute-force numpy cosine over 几千向量(毫秒级); 生成洞见的 1 次 LLM 调用正好落在『hook 内一次带 fallback 的 API 调用』预算内。洞见的 (because of …) 引用 = frontmatter 里存被引 memory 的 id 列表, git-tracked 可审计。
- mem0 去冗算子 [适配, 需降级]: 不用它的向量 DB, 但 ADD/UPDATE/DELETE/NOOP 的判定 prompt 可在同一次反思调用里复用——抽象前先对候选事实做一次去重/矛盾检查。
- A-MEM 的『新记忆触发近邻改写』[部分适配]: 局部增量演化天然契合文件型(只改被链接的几条 md), 但每条新记忆都触发 LLM 改写邻居=调用次数不可控, 与『一次调用』预算冲突。建议只取它的 note 结构(keywords/tags/contextual description 写 frontmatter) 和 top-k 链接思想, 演化合并进周期性反思批处理, 别逐条触发。

需要改造：
- Letta sleep-time / LangMem background daemon [需移植思想而非实现]: 二者依赖常驻后台进程/心跳, 直接冲突。移植路径=把『反思』做成 on-demand skill(用户/工作流显式调 /reflect-memory 或在 session 结束 hook 里跑), 用 LangMem 的 debounce 思想做触发逻辑: 不是后台轮询, 而是『本次累计 importance 过阈值 且 距上次反思 > 冷却窗口』才在 hook 末尾发一次反思调用, 否则 NOOP——单次、有 fallback、无进程。
- LangMem procedural memory(prompt 规则反思) [可选, 高价值]: 把成功/失败经验反思成『更高层操作规则』写进 markdown(本质就是把情景压成规则), 与本维度目标完全一致, 且产物天然是文件、可软链跨 5 agent 共享。

**推荐**:推荐：以 Generative Agents 的 reflection 为骨架，按需触发，强制证据引用，三层抽象与原始情景双轨存——这是对本约束集合最优的组合。

具体方案(可直接喂 /think-plan)：

【Requirements】
- 把『几百~千条情景记忆』周期性压成『更高层语义规则/洞见』, 写成 git-tracked markdown(frontmatter 存元数据)。
- 每条洞见必须引用其底层情景 id(reflection grounding), 可回溯、可证伪。
- 触发无 daemon: 在 session 结束 hook 或显式 skill 内做一次带 fallback 的反思调用。
- 抗过度泛化: 抽象不删原文; 新洞见与既有 core 规则矛盾时拒绝或标冲突待人裁。

【Approach】
- 存储: 每条记忆一条 JSONL 行或一个 md, frontmatter 含 importance(1-10, 入库时一次 LLM 调用打分或规则估)、embedding、tags/keywords(借 A-MEM note 结构)。洞见单独存到 reflections.md/jsonl, frontmatter 含 cited_ids 列表与 created_at。
- 触发(借 Generative Agents 阈值 + LangMem debounce): 维护 last_reflect_importance_sum; 当『自上次反思以来 importance 累计 > 阈值(初始仿 150, 单用户体量建议先调到 30-50 再校准)』且距上次反思超冷却窗口, 才在 hook 末尾跑反思; 否则 NOOP。
- 反思一次调用三段(全在 1 次 API call, 带 fallback): (1) 取最近 N 条 + brute-force cosine 召回相关条; (2) LLM 生成 3-5 个高层问题→对每个产出洞见, 强制 '(because of <id列表>)' 格式; (3) 同一调用里对候选洞见跑 mem0 式 ADD/UPDATE/NOOP 去重 + 与既有规则矛盾校验。fallback: 调用失败则跳过反思、保留原始记忆不丢。
- 抗过度泛化: 双轨(原始情景永不被反思删除, 借 SSGM immutable episodic log 思想); 洞见带 confidence/支撑条数, 支撑 <2 条的不升为规则; 后续若某洞见被新情景推翻, 标 stale 而非静默改写(留 git 历史)。

【Risks】
- 过度泛化/semantic drift: 反复反思把弱偏好漂成强断言 → 双轨存 + 引用 + 矛盾校验 + 不静默改写缓解, 但不能消除, 需 git diff 人工抽检。
- 触发阈值不好定: 150 是模拟世界的值, 单用户真实场景需实测校准, 建议先 log 累计 importance 分布再定。
- 单次调用预算紧: 三段塞一次 call 可能超 context/降质 → 体量小(千条内)时可接受; 必要时拆成『召回(本地无 LLM)+ 一次生成调用』。
- importance 自评不稳: LLM 1-10 打分有噪声 → 可用规则+LLM 混合, 或只在反思时批量打分省调用。

【Verification】
- 给定一组合成情景(含可推断的高层规则), 跑反思, 验证: 生成的洞见命中预期规则 且 每条都带有效 cited_ids; 注入一条矛盾情景, 验证系统拒绝/标冲突而非静默覆盖; 注入一条错误情景, 验证不会单条就升为规则(支撑数门槛); git diff 可读、可审计。

不推荐：直接搬 Letta sleep-time / LangMem 完整 SDK(都要常驻进程, 违约束); 不推荐逐条新记忆触发 A-MEM 演化(调用次数不可控)。这两者只取思想。

**坑**:过度泛化/语义漂移是头号坑: SSGM 实证『微辣』经反复摘要漂成『爱吃很辣』。若抽象时删掉原始情景或静默改写既有规则, 错误会累积且不可逆。必须双轨存(原文不删)+ git 留痕 + 矛盾校验。; 无证据引用的反思=幻觉温床: 不强制 '(because of <id>)' 引用, LLM 会生成 baseless generalization。reflection grounding 是已验证的第一道防线, 不可省。; 错误线性传播: experience-following 研究确认输入越相似输出越相似, 一条错误经验/洞见会复合放大到后续所有相似任务。需用『后续是否被推翻』当质量标签反向修剪 + 支撑条数门槛(<2 条不升规则)。; 纯定时触发会空转或滞后: 低活动期定时反思浪费调用, 高活动期定时滞后。用 importance 累计阈值 + 冷却窗口(借 debounce 思想)替代纯周期。
**来源**:https://ar5iv.labs.arxiv.org/html/2304.03442 — Generative Agents (Park et al., UIST 2023): reflection 触发阈值 150、importance 1-10 prompt、100 最近记忆→3 问题→5 洞见、(because of …) 引用、反思树。confirmed; https://arxiv.org/abs/2504.19413 — Mem0 (2025): Extraction+Update 两阶段、ADD/UPDATE/DELETE/NOOP consolidation、LoCoMo LLM-Judge +26%。confirmed; https://github.com/mem0ai/mem0 — mem0 官方 repo: 算子语义与 docs。confirmed; https://arxiv.org/html/2502.12110v1 — A-MEM (NeurIPS 2025): memory evolution 公式 m_j*←LLM(...)、note 结构(keywords/tags/context)、top-k 链接、LoCoMo Multi-Hop F1 45.85% vs 18.41%。confirmed; https://github.com/agiresearch/A-mem — A-MEM 官方实现。confirmed; https://langchain-ai.github.io/langmem/guides/delayed_processing/ — LangMem: ReflectionExecutor after_seconds debounce(窗口内新消息取消旧更新、合并 context)。confirmed; https://www.langchain.com/blog/langmem-sdk-launch — LangMem SDK: hot-path vs background、semantic/episodic/procedural memory、metaprompt/gradient prompt 优化。confirmed; https://langchain-ai.github.io/langmem/concepts/conceptual_guide/ — LangMem 概念: hot-path 加延迟 vs background 召回更高、procedural memory 反思成 prompt 规则(max_reflection_steps 3)。confirmed

### memory selection

**最佳实践**:Benchmarks unreliable; full-context ~73 beats all. Letta filesystem-only 74.0 beats mem0-graph 68.5. Value is the algorithm, not the DB.

**对约束**:Reject Zep, Cognee, Letta-product, HippoRAG, LangMem (graph DB or daemon). mem0, A-MEM, Generative Agents algorithms fit markdown plus numpy.

**推荐**:Build a file-native layer borrowing mem0, A-MEM, Generative Agents kernels; no library wholesale. One fallback LLM call extracts and decides ADD/UPDATE/DELETE/NOOP; retrieve by recency plus relevance plus importance, link-hop not PageRank; reflection on threshold. Verify with a holdout, not LoCoMo.

**坑**:Self-reported LoCoMo is a sanity check only.; Performance is the algorithm, not the DB.; Port only the algorithm, not the runtime.
**来源**:https://arxiv.org/abs/2504.19413; https://www.letta.com/blog/benchmarking-ai-agent-memory/

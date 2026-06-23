# STORM / Co-STORM 方法论提炼(2026-06-22)

> 来源:STORM 论文(arXiv 2402.14207)、Co-STORM 论文(arXiv 2408.15232)、`stanford-oval/storm` 仓库 `knowledge_storm` 源码。
> 收录决策:**只做方法论 docs 笔记,不收代码 submodule**。STORM 是几 MB 的 Python 应用,不属于 `refs/` 的「skill/workflow 包」分类;为抄方法论拉整个 app 维护成本高且越界。
> 用途:为 `writing-skills`(write-source / write-outline / write-draft)+ `think-survey` + `think-research` 提供改造灵感。落地裁决见同目录 `storm-absorption-plan-2026-06-22.md`。

## STORM 是什么

斯坦福 OVAL 的 LLM 长文写作系统:给一个主题 → 自动联网调研 → 生成大纲 → 产出带引用的维基风格长文。基于 DSPy,多 agent。Co-STORM 把单向「自问自答」升级为「人可旁观、可插话的多 agent 圆桌」。

它解决的核心痛点是**「写之前的调研和搭结构」没人做好**:直接 LLM 生成无接地、易过时;outline-driven RAG 有「来源偏见原样传染」和「把无关事实强行关联」的毛病,在「识别/评估/组织外部信息」上弱。论文称对 oRAG 组织性 +25%、广度 +10%(摘要数值,[未验证] 未复现)。

## 整体流水线(事实)

**STORM 两阶段,源码为 4 个串行模块:**

1. **Pre-writing(预写作)**
   - 发现主题的多元视角(perspective discovery)
   - 每个视角各开一场「维基写手 ↔ 主题专家」多轮对话,专家答案接地于联网检索
   - 把对话信息整理成大纲
2. **Writing(成稿)**:按大纲分节检索 + 生成带引用正文 → polish(加导语 + 跨节去重)

`KnowledgeCuration → OutlineGeneration → ArticleGeneration → ArticlePolish`,每阶段产物落盘,`do_*` 开关可分段断点续跑。

**Co-STORM 多出:** 多 agent 圆桌(专家 + 主持人 + 人类)、动态 mind map 实时归档、`warm_start()` → 反复 `step()` → `generate_report()`。

## 可迁移的核心机制

### 1. 目录反推视角(perspective-guided question asking)

**不靠 LLM 凭空想视角,而是借现成同类文章的目录结构当「视角种子」**(`persona_generator.py`):

1. 让 LLM 针对主题推荐若干相关维基页面
2. 抓页面抽出标题 + 目录(TOC)
3. 把这些 TOC 作为灵感,让 LLM 产出一组代表不同视角的「编辑」角色,各附「他重点关注什么」
4. 永远在最前强插一个「Basic fact writer」兜底基础事实;默认 3 个视角

直觉:**用「同类成品的结构」反推「该主题的研究视角」,比直接问「这个主题有哪些角度」更接地、更不空泛。**

### 2. 接地问答循环(simulated conversation)

每个视角各开一场「写手 ↔ 专家」对话,并行(`knowledge_curation.py`):

- 写手:**一次只问一个问题**;无问题可问时输出固定终止话术;对话历史只展示最近 4 轮控 token
- 专家三步:`问题 → 转 ≤N 条搜索 query → 检索取 top-k → 基于片段作答`,prompt 强约束「每句要有检索支撑、不要幻觉、信息不足就拒答」

要点:对话不是闲聊,是**「提问→转检索 query→检索→接地作答」的信息采集循环**;视角驱动多样性,接地约束保可信。

### 3. 反收敛 / 挖盲区(Co-STORM 主持人,最高价值单点)

`engine.py` 的 turn policy:**连续 N 轮(默认约 3)都是「回答型」而无人提新问题时,强制主持人介入**,防止专家越聊越收敛、困在已知区。

主持人怎么挑问题:专挑「上次主持人发言以来、被检索到但**从未被引用**的 snippet」,按三维重排:

```
((1 - 与原始 query 的相似度)^w) * ((1 - 与已引用内容的相似度)^w) * (claim 相关性)
```

即偏好「**与初始问题不太像、又跟已聊不重复、但仍与主题相关**」的信息 —— 正是用户「不知道自己不知道」的盲区(serendipitous learning / unknown unknowns)。

### 4. 大纲两步法(outline_generation.py)

1. `WritePageOutline`:**只给主题**,先让 LLM 凭内部知识写一版 draft 大纲(骨架完整性)
2. `WritePageOutlineFromConv`:把(主题 + 清洗后对话 + draft 大纲)喂回,指令「用对话学到的信息**改进**大纲」(检索证据补盲点、纠结构)

要点:**先内知识起骨架,再用检索证据精修。** 避免一上来被检索碎片带偏结构,也避免纯内知识漏新信息。

### 5. 两套检索 + 引用可回溯(storm_dataclass.py / article_generation.py)

- **收集期 / 写作期两套检索**:调研期用关键词检索铺量;成稿期每节用 query 做**向量相似度 top-k** 精排取证。即「广撒网收集 + 按节精准取证」。
- **去重以 URL 为主键**:同 URL 多次命中只合并 snippet 去重,不重复建源。
- **引用 = 编号 + 可回溯重映射**:给每条 snippet 编号 → 正文写 `[n]` → 增删引用时重写编号并能反查回源文档。

### 6. mind map 即增量大纲(Co-STORM,基础设施较重)

一棵概念树。插入两阶段(向量选 top-8 候选 → LLM 在节点三选一:insert / 下钻 / 新建);攒够阈值 `_expand_node()` 自顶向下细化。`to_report()` 直接把 mind map 当章节标题转 markdown 综述 —— **mind map 直接就是大纲**。

## 与本仓库现有能力的映射

| STORM 机制 | 现有最接近的能力 | 关系 |
|---|---|---|
| 目录反推视角 | think-survey 子方向拆分 / write-outline 对齐表 | **缺**,值得新增 |
| 接地问答循环 | think-survey 子任务委派契约 / write-source 先读后登记 | 部分有,契约可强化 |
| 反收敛挖盲区 | 无 | **缺**,单点价值最高 |
| 大纲两步法 | write-outline 直接素材→对齐表 | **缺**,值得新增 |
| 两套检索 | write-source / think-survey 三层取证 | **缺**(降级为纪律,不上向量库) |
| 引用可回溯重映射 | write-source running citations 三风格 | 部分有,可补编号回溯 |
| 持续取材反问钩子 | write-source 反问钩子自检 | **已有**(借自 notebooklm-skill) |
| Research To-Do 内嵌 | write-outline Research To-Do | **已有**(借自 content-research-writer) |
| 多源分层 + 置信度 | think-survey 三层取证 + 置信度 | **已有** |

## 不要照搬(关键判断,非论文结论)

- **[推断] STORM 没有独立的事实核查 / NLI 校验**:引用只是「生成时强约束 + 编号可回溯」,引用是否真支撑句子仍依赖生成期约束。本仓库 `_shared/writing-constraints.md` 的真实性纪律其实更强,迁移时**不要被它带得降级**。
- **[推断] STORM 面向中立百科长文**,对强观点 / 论证型写作适配有限。视角发现那套可复用,**「中立罗列」的成稿风格别抄**。
- **mind map / 向量检索 / 多 agent 圆桌是重基础设施**。本仓库是 markdown-prompt 的 skill harness,应采纳**机制思想**(反收敛、两阶段取证的纪律),而非搬**机器实现**(向量库、概念树数据结构、ThreadPool 并发)。

## 参考

- STORM 论文:https://arxiv.org/abs/2402.14207
- Co-STORM 论文:https://arxiv.org/abs/2408.15232
- 仓库:https://github.com/stanford-oval/storm

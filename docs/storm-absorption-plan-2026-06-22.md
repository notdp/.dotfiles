# STORM 方法论吸收改造 Plan(2026-06-22)

> 输入:`docs/storm-methodology-2026-06-22.md`(方法论提炼)
> 状态:**SPEC,待批准。批准前不修改任何 skill。**
> 改造目标层(用户确认):`writing-skills`(write-source / write-outline / write-draft)+ `think-survey` + `think-research`

## 目标 / 非目标

**目标**
- 把 STORM 5 个可迁移机制,以「markdown-prompt 纪律」形态(非代码基础设施)落进上述 skill。
- 每个机制落地处要有明确触发条件,不污染 idle context,不破坏现有输出契约。

**非目标(显式排除)**
- 不引入向量库 / embedding / 概念树数据结构 / 多进程并发等 STORM 的运行时基础设施。
- 不收 STORM 代码进 `refs/`(已决:仅 docs 笔记)。
- 不削弱现有 `_shared/writing-constraints.md` 真实性纪律(STORM 反而更弱)。
- 不把「中立百科」成稿风格带进有观点的写作体裁。

## 改造项(按 ROI 排序,可独立勾选)

### P0-A 反收敛 / 挖盲区步骤 → think-survey(单点价值最高)　✅ 已落地 2026-06-23

- **现状**:think-survey 收集→归类→综述是单向的,无机制对抗「越查越收敛、困在已知区」。
- **改造**:在「收集与归类」与「输出综述」之间加一个**盲区自检步骤**(降级版主持人,无向量库):
  - 每完成一轮收集,扫一遍「检索到 / 读到但**没进任何归类卡片**」的素材;
  - 主动追问一个「与初始问题方向不同、且与已收集结论不重复」的反向角度;
  - 写进固定输出结构新增的「盲区与反向角度」小节(可为空但必须显式声明已自检)。
- **验收**:think-survey 输出结构含「盲区自检」证据;对一个测试主题能产出至少一个初始 query 不覆盖的角度。

### P0-B 目录反推视角 → think-survey「大主题判断」+ write-outline　◑ think-survey 部分已落地 2026-06-23(write-outline 部分未做)

- **现状**:think-survey 按「子方向」拆并行子任务,但子方向靠 agent 自拟;write-outline 直接素材→对齐表,结构靠经验。
- **改造**:
  - think-survey:在拆子方向前,增加可选步骤「抓 2-5 篇同类成品(综述 / 官方文档 / 竞品)的目录当视角种子」,再据此定子方向。强插一个「基础事实」兜底视角。
  - write-outline:在对齐表前,增加可选步骤「找同类优质文章的结构当骨架参考」。
- **验收**:两处 skill 文档写明该步骤的触发条件(开放/陌生主题时启用,熟悉主题可跳过)与「基础事实兜底」约束。

### P1-A 大纲两步法 → write-outline

- **现状**:write-outline 直接从素材生成对齐表。
- **改造**:对齐表前增加两步——① 只凭主题 + 写作意图先起一版 draft 骨架(内知识);② 再用已收集素材精修骨架、补盲点。draft 骨架的假设要可被素材推翻。
- **验收**:write-outline 文档体现「先骨架后证据精修」两步,且不与现有「证据先于措辞」冲突(措辞仍最后)。

### P1-B 接地问答循环纪律 → write-source + think-survey 子任务契约

- **现状**:write-source「先读后登记」是被动登记;think-survey 子任务契约是「搜索→抽取→卡片」。
- **改造**:把取材 / 子任务契约强化为显式循环「**研究问题 → 转检索 query → 检索 → 仅在有源时登记/作答,信息不足显式标缺口而非编造**」。一次一个问题、有终止信号。
- **验收**:write-source / think-survey 子任务契约出现「问题→query→检索→接地」四步;与现有反问钩子自检衔接不重复。

### P2 引用编号可回溯 → write-source

- **现状**:write-source 有 running citations 三风格,但无「增删引用时重写编号 + 反查回源」的规整纪律。
- **改造**:在「引用三风格」补一条编号一致性纪律:增删素材时重排 `[n]`、每个正文编号能反查回素材清单某条。
- **验收**:write-source 文档含编号一致性约束;为低优先级(现有机制已覆盖大部分)。

## 不做项(显式记录,避免未来重复评估)

- **mind map 增量大纲**:需概念树 + 向量插入,属重基础设施,与 markdown-prompt 形态不匹配 → 不做。其「结构即增量产物」的思想已被 write-outline 的「对齐表+Research To-Do」近似覆盖。
- **向量检索按节精排**:不引入 embedding 依赖。两套检索降级为「调研期广搜 / 成稿期按节针对性取证」的**纪律**,不上向量库。
- **独立事实核查 agent**:本仓库已有更强真实性纪律,不需要补 STORM 缺的这环。

## 风险

- **[推断] 过度加工风险**:这些 skill 已较成熟(write-source/outline 已吸收 notebooklm / content-research-writer)。新增步骤可能与现有「反问钩子」「Research To-Do」语义重叠,增 prompt 体积却收益边际。→ 缓解:每项落地前先核对是否与现有条款重复,能合并就合并,不新起平行小节。
- **prompt 竞争**:新增内容若写成默认强制步骤,违背本仓库「按需触发、零 idle 开销」原则。→ 缓解:P0-B / P1-A 均设为「开放/陌生主题时启用」的可选步骤,不默认全量。
- **体裁错配**:视角发现源自中立百科。→ 缓解:落 writing-skills 时注明仅适用于资料 / 解释型写作,观点稿慎用。

## 验证

- 每改一个 skill:`python3 scripts/verify_skills.py` 通过;
- 对 think-survey / write-outline 各跑一个测试主题,人工确认新增步骤产出预期证据(盲区角度 / 视角种子 / 两步大纲);
- 交付前 `bash scripts/run-verify.sh`。

## 落地顺序建议

1. P0-A(think-survey 反收敛)—— 独立、价值最高、不动写作链
2. P0-B(目录反推视角)—— 跨 think-survey + write-outline
3. P1-A(大纲两步法)—— write-outline
4. P1-B(接地问答循环)—— write-source + think-survey
5. P2(引用回溯)—— write-source,可选

建议每项作为独立 commit;P0-A 先做、验证形态可行后再推进其余,避免一次性大改 prompt 后难定位回归。

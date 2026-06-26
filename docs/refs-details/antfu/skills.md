# antfu/skills

- 上游仓库: `https://github.com/antfu/skills`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/antfu/skills`
- Source SHA: `50deaeb269d80d92db7a2c5a677290309ae307fc`（heads/main），分析日期: 2026-06-02
- ⚠️ **Source SHA stale**：当前 submodule gitlink 已为 `a74f281a27dadc02397bc1a174b0f2c97531b6ae`（≠ 上面分析 SHA）；本文档基于旧版本，重新吸收前先核对 `git log 50deaeb2..a74f281a`。
- 一句话总结: 不是一套"agent 行为/工作流 skill 集", 而是一条"从上游官方文档/上游 skill 仓库自动生成并持续同步领域知识 skill"的流水线 + 产物, 核心主张是用 git submodule 把 skill 的事实源锚定到上游, 让知识库可溯源、可更新、可分发。

## 思路哲学 (Why)

这个仓库和本仓库 (`~/.dotfiles`) 属于完全不同的物种, 需要先澄清定位再谈借鉴。

- **它解决的真问题是"领域知识 skill 的鲜度与可信度", 不是"agent 行为纪律"。** 本仓库的 skill 是 `think-*` / `dev-*` / `guard-*` 这类方法论与流程护栏; antfu/skills 的 skill 全是 Vue / Nuxt / Vite / VueUse / pnpm 这类"框架用法知识库"(README L43-67)。它默认的世界观是: LLM 训练数据里框架知识会过时、会有版本漂移, 因此 skill 的价值在于把"当前版本的正确用法"以可更新方式喂给 agent。

- **设计原则一: skill 的事实源必须可溯源、可 diff、可同步 (submodule-as-source-of-truth)。** `meta.ts` 把每个上游仓库声明为 submodule (L10-20 `submodules`, L25-68 `vendors`), `cli.ts` 用 `git submodule update --remote --merge` (cli.ts:184) 拉新, 用 `git rev-list HEAD..@{u} --count` 检测落后多少 commit (cli.ts:295,309)。每个生成的 skill 旁边都有 `GENERATION.md` 记录源 SHA (vue/GENERATION.md: `Git SHA: 01abf2d...`), 每个同步的 skill 旁边有 `SYNC.md` 记录 vendor SHA (vueuse-functions/SYNC.md)。更新流程不是"重写", 而是 `git diff {old-sha}..HEAD -- docs/` 看上游改了什么再增量更新 (AGENTS.md L105-112)。这是把"知识陈旧"问题工程化成"submodule 落后几个 commit"的可观测问题。

- **设计原则二: skill 是"按需 + 可分享"的知识单元, 与 AGENTS.md 是互补而非竞争关系。** README L77-83 作者明确表态: "AGENTS.md 全量前置加载所以 agent 一定遵守, 而 skill 可能 false-negative(该拉时不拉)"; 但 skill 的价值在 **shareable**(跨项目复用 prompt)和 **on-demand**(按需拉入, 突破单次上下文窗口上限)。结论是"想让某些 skill 永远生效, 就在 AGENTS.md 里直接引用它"。这是一个清醒的、不吹 skill 的定位判断 [事实, 来自 README 原文]。

- **设计原则三: 不重复 LLM 已知的东西, 只补"agent 真正缺的能力面"。** AGENTS.md L7-10 的生成铁律: "聚焦 agent 能力和实战用法; 忽略面向用户的入门/安装指南; 忽略 LLM 训练数据里已经很自信的内容; skill 尽量精简, 别造太多 reference。" 生成 instruction L91 再次强调 "对 LLM 已知的常识可以跳过"。这是一种"信息增量优先"的写作哲学, 与本仓库"信息密度优先"同源但目标不同。

- **设计原则四: opinionated 与 unopinionated 分层标注。** README 把 skill 分三类并显式标注立场: 手写 antfu skill 标 `> Opinionated`(L29), 文档生成 skill 标 `> Unopinionated but with tilted focus`(L39, 倾向 TS/ESM/Composition API), vendored skill 原样同步保留上游 license。这让消费者知道每个 skill 的"主观程度"。

- **它跟"堆功能型 skill 集"的根本区别**: 堆功能型靠人手写、越攒越多、无法回答"这条知识是哪个版本的、过时了没"。antfu/skills 把 skill 当作 **派生产物(derived artifact)**: 源在 submodule, 产物在 `skills/`, 中间靠 `meta.ts` 声明式配置 + `cli.ts` 幂等脚本连接。`meta.ts` 是单一事实源, `cleanup` 命令会把任何不在 `meta.ts` 里的 submodule/skill 当作"漂移"删掉 (cli.ts:382-455)。本质是把"配置即代码 / 声明式 reconcile"那套思路搬到 skill 治理上。

## 特殊技巧 (How)

- **三类 skill 来源, 三套不同的生成/同步机制 (AGENTS.md L12-37)**:
  - Type 1 生成型 (`sources/`): clone 上游 **文档仓库**(如 vuejs/docs)为 submodule, agent 读 `sources/{project}/docs/` 后**重写**成 skill, 产物落 `skills/{project}/`, 名字必须与 submodule key 同名 (AGENTS.md L65)。
  - Type 2 同步型 (`vendor/`): 上游**自己维护 skill**(如 vueuse/skills), 直接**复制**, 不准手改 (AGENTS.md L131 "Do NOT modify synced skills manually")。`meta.ts` 的 `skills: Record<sourceName, outputName>` 支持改名映射 (meta.ts:1-5,28-39)。
  - Type 3 手写型: 只有 `antfu` 一个, 放作者个人 taste, 脚本不碰。

- **声明式 reconcile + 幂等 CLI (cli.ts)**: 四个子命令 `init / sync / check / cleanup`。新颖点在 **drift detection**: `init`(cli.ts:91-93)和`cleanup`(cli.ts:382-393)都会把"`.gitmodules` 里有但 `meta.ts` 里没有"的 submodule 列为 extra 并提示删除; `cleanup` 还会扫 `skills/` 目录, 把不在期望集合(`getExpectedSkillNames`, cli.ts:328-350)里的 skill 删掉。`meta.ts` 是唯一事实源, 仓库状态向它对齐。这是把基础设施领域的"declarative reconcile"直接套到 skill 仓库治理。[事实]

- **同步脚本的"先删后建"保证干净 (cli.ts:219-241)**: 每次 sync 先 `rmSync(outputPath)` 整个删掉输出目录再重建复制, 避免上游删文件后本地残留 stale 文件。复制时还会自动从 vendor 仓库根目录探测并拷 LICENSE(cli.ts:244-251), 用大小写多变体列表兜底文件名。这是"同步必须是覆盖式而非增量式"的工程纪律。

- **GENERATION.md / SYNC.md 作为"轻量血缘元数据"**: 不引外部数据库, 就在每个 skill 目录放一个记录 `Source / Git SHA / Generated|Synced 日期` 的 md(AGENTS.md L183-205)。这让任何人(或下次 agent)只看目录就能回答"这个 skill 是哪个上游 commit 生成的、什么时候生成的"。文件即血缘记录, 是很可复用的低成本手法。

- **SKILL.md 的触发语义写法 (description 字段)**: 每个 SKILL.md frontmatter 的 `description` 都是"能力 + 触发场景"双段式, 且触发场景用具体 API/动作锚定而非泛泛。例如 vue/SKILL.md L3: "...Use when writing Vue SFCs, defineProps/defineEmits/defineModel, watchers, or using Transition/Teleport/Suspense/KeepAlive." antfu/SKILL.md L3 用 "...or when the user mentions Anthony Fu's preferences" 把"提到作者名"也作为触发钩子。web-design-guidelines/SKILL.md L3 直接把用户可能说的原话("review my UI" / "check accessibility")列进去当触发词。这是"用用户原话和具体 symbol 当触发锚点"的实用模式。[事实]

- **SKILL.md = 索引 + 速查, references/*.md = 单概念详档 (两级上下文管理)**: SKILL.md 本体保持小, 用 Markdown 表格 `| Topic | Description | Reference |` 列出所有子知识并链到 `references/{category}-{name}.md`(AGENTS.md L156-180; vue/SKILL.md L24-33)。reference 文件名强制带分类前缀(`core` / `features` / `best-practices` / `advanced`, AGENTS.md L92), 一文件一概念(L209)。SKILL.md 顶部还会嵌一段最高频的"Quick Reference"代码模板(vue/SKILL.md L37-84), 让 agent 不必拉 reference 就能用最常见的写法。这是典型的"渐进式披露(progressive disclosure)"上下文预算手法。

- **Invocation 分级标注 (vueuse-functions 独有)**: 每个函数表格多一列 `Invocation`, 取值 `AUTO`(可自动用) / `EXTERNAL`(需用户已装外部依赖才用, 否则先问) / `EXPLICIT_ONLY`(仅用户明确要求才用), 并声明 "用户 prompt 或 AGENTS.md 可覆盖默认规则"(vueuse-functions/SKILL.md L21-25)。把"这个能力 agent 该多主动"编码进数据表的一列, 是很新颖的、可被本仓库借鉴到"工具/能力主动性分级"的手法。[事实, 来自上游 vueuse, 非 antfu 原创但被采纳]

- **instructions/{project}.md 作为生成时的"项目级覆盖钩子"**: 与 skill 产物分开, `instructions/` 放针对某项目生成 skill 时的额外约束(AGENTS.md L97 提到读它)。内容极短且是硬倾向, 如 vue.md 全文 5 行("prefer shallowRef over ref", "Discourage Reactive Props Destructure"), vitest.md 3 行("Use expect.soft for non-critical assertions")。这些倾向最后被吸收进生成的 SKILL.md 的 Preferences 段(对比 instructions/vue.md 与 vue/SKILL.md L16-21 几乎一一对应)。把"生成指令"与"生成产物"解耦, 让 taste 可单独维护、可复算, 是个干净的分层。

- **`AGENTS.md` 本身就是一份"给 agent 的 skill-authoring 规范"**: 它不是项目硬约束, 而是把"如何从文档生成 skill"这件事写成可被 coding agent 执行的 SOP, 含文件格式模板、目录约定、写作 6 条 guideline(AGENTS.md L240-250: 为 agent 重写而非照抄、实用、精简、一文件一概念、必带代码、解释 why)。README L95 的工作流就是直接 "Ask your agent to `Generate skills for <project>`"——用一个长 prompt 规范驱动 agent 批量产出 skill。这是"用 AGENTS.md 当生成器规格说明书"的反直觉用法。

- **真正新颖/反直觉的几条**: (1) 把 skill 当 submodule 派生产物而非手写资产, 用 SHA 追踪鲜度; (2) `cleanup` 用 `meta.ts` 做声明式 reconcile, 主动删漂移; (3) `Invocation` 列把"主动性"编码进数据; (4) 用 AGENTS.md 当 skill 生成器的 spec。其余(两级 SKILL.md/references、description 触发语义)是 Anthropic Agent Skills 官方最佳实践的标准做法, 本仓库已大量采用。

## 资产盘点

- **skills (17 个产物目录)**: 手写 1 个(antfu); 文档生成型 8 个(vue/nuxt/pinia/vite/vitepress/vitest/unocss/pnpm); vendored 同步型 8 个(slidev/tsdown/turborepo/vueuse-functions/vue-best-practices/vue-router-best-practices/vue-testing-best-practices/web-design-guidelines)。注: `meta.ts` 已声明 nitro 的 submodule 但尚无产物。
- **reference 文件规模差异极大**: vueuse-functions 265 个、slidev 52、tsdown 38、turborepo 24、unocss 23、vue-best-practices 22、nuxt 18; 而 vue 仅 3、vite 6、antfu 5; vue-router-best-practices / vue-testing-best-practices / web-design-guidelines 为 0 个 reference(SKILL.md 自包含或运行时 WebFetch)。
- **commands / hooks**: 无 slash command, 无 Claude Code hook。唯一的"hook"是 `package.json` 的 `simple-git-hooks` pre-commit 跑 lint-staged + `prepare` 脚本自动 `git submodule update --init --recursive`(package.json)。
- **安装/分发资产**: 不自带安装器, 走 vercel-labs 的 `skills` CLI: `pnpx skills add antfu/skills --skill='*'`(`-g` 装全局)(README L11-19)。本仓库自己的 `scripts/cli.ts`(约 540 行)只负责 submodule 生命周期与同步, 不负责对外分发。
- **元数据/配置**: `meta.ts`(声明式来源清单)、`instructions/*.md`(9 个项目级生成倾向)、`AGENTS.md`(生成 SOP)、`GENERATION.md`/`SYNC.md`(每 skill 血缘)。

## 与本仓库的关联点

本仓库与 antfu/skills 是**互补物种**: 本仓库做 agent 行为/流程护栏, antfu 做领域知识库治理。可借鉴点偏"治理机制", 不是直接搬 skill。详细裁决留给后续 plan。

- **refs 血缘元数据可借鉴**: antfu 的 `GENERATION.md`/`SYNC.md`(记录上游 SHA + 日期)是个低成本手法。本仓库 `refs/` 下也是一堆 submodule, 但据我所知没有"每个 ref 当前指向哪个 SHA、上次分析于何时"的轻量记录。可考虑给 `docs/refs-details/` 体系加一行 ref SHA / 分析日期, 让 refs 分析结论可溯源、可判断是否过期。[推断, 需核对本仓库现状]

- **声明式 reconcile + drift 清理思路**: antfu 用 `meta.ts` 单一事实源 + `cleanup` 删漂移。本仓库已有 `scripts/verify_skills.py` 做 description 触发前缀校验, 但 [推断] 可能没有"skills/commands 目录与某份清单对账、报告孤儿/漂移"的能力。若 skill 数量继续增长, 一个"声明清单 vs 实际目录"的对账脚本可降低维护熵。

- **Invocation 主动性分级**: vueuse 那列 `AUTO/EXTERNAL/EXPLICIT_ONLY` 对应本仓库"能动性"表(被动 vs 主动)。可考虑在涉及外部依赖、生产副作用的 skill/工具描述里, 显式标注"默认主动性等级", 与现有 `guard-gitops` 触碰线上默认触发的约定一脉相承。[推断]

- **不直接吸收领域 skill 本身**: vue/vite/nuxt 这些是前端框架知识库, 与本仓库 `fe-*` skill 可能有重叠但定位不同(antfu 是版本锚定的用法速查, 本仓库 fe-* 是诊断/设计方法论)。是否纳入应由后续 plan 按实际前端工作量裁决, 不建议默认吸收。

- **AGENTS.md 作为"生成器 spec"的写法**: 本仓库 `docs/software-engineering-research/skill-authoring.md` 已是 skill 编写规范; antfu 的 AGENTS.md 额外提供了"从上游文档批量生成 skill"的 SOP 模板(目录约定 + 文件格式 + 6 条写作 guideline)。若本仓库未来要做"从某官方文档批量蒸馏 skill", 这套 SOP 的结构可直接参考。

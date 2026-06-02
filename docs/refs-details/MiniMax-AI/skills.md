# MiniMax-AI/skills

- 上游仓库: `https://github.com/MiniMax-AI/skills`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/MiniMax-AI/skills`
- Source SHA: `60aaae52bb2af8162732751a4332f62a5fef518b`（heads/main），分析日期: 2026-06-02
- 一句话总结: 一套面向「内容/媒体/应用产出」的领域 skill 库 (frontend / mobile / shader / PDF / PPTX / XLSX / DOCX / 多模态媒体)，核心不是流程纪律，而是把**专家级设计品味与产出 pipeline 编码成可触发的 SKILL.md + 脚本**，并用一个**可执行的 PR 校验脚本 + 双层 (硬规则/软指南) review skill** 守住 skill 库自身的质量与可移植性。

## 思路哲学 (Why)

它解决的真问题与本仓库 (`~/.dotfiles`) 不同：本仓库的 skill 体系是**过程纪律型** (think/dev/guard/readable，约束 agent 怎么干活)；MiniMax-AI/skills 是**产出能力型** (frontend-dev / minimax-pdf / pptx-generator，约束 agent 产出什么、长什么样)。两者是互补维度，不是同类。

设计原则与证据：

- **「设计品味即 prompt」——把专家审美显式编码成规则表，而非泛泛要求"做得好看"。** `minimax-pdf/SKILL.md:53-96` 把 15 种文档类型映射到固定的封面样式、字体、配色范围 (例如 `legal/finance → 深海军蓝 #1C3A5E`)，并明确反对"安全的"默认色：`pick it from the document's semantic context — not from generic "safe" choices`。`ppt-orchestra-skill/SKILL.md:74-86` 用一整张 "Avoid (Common Mistakes)" 表把 AI slop 信号显式化，最强一条是 `NEVER use accent lines under titles — these are a hallmark of AI-generated slides`。这是把"反 AI 味"沉淀成可检查清单，而不是靠模型自觉。

- **数据驱动 / 规则表优于散文。** 几乎每个 SKILL.md 的核心都是表：`minimax-pdf` 的 Route table (`SKILL.md:31-35`)、Doc-type→视觉身份表、content.json block-type 表 (`SKILL.md:98-120`)；`ppt-orchestra` 的字体配对表、字号表、间距规则。逻辑被压成查表而非一堆 if，符合"复杂逻辑写成表"。

- **触发语义是一等公民 (description = router)。** `quality-guidelines.md:14-22` 把 description 定义为"agent 用来决定是否激活 skill 的唯一依据"，并给出 Bad/Good 对照。多个 skill 在 description 里直接塞**用户原话样例**作为触发器：`minimax-pdf/SKILL.md:5-11` 列出 `"make a PDF"/"fill out this PDF"/"reformat this document"` 三组动词短语；`vision-analysis/SKILL.md` 把文件扩展名 (`.jpg/.png/...`) 和动词 (`analyze/OCR/...`) 都写进 description。`fullstack-dev/SKILL.md:3-12` 甚至显式写 `DO NOT TRIGGER when: pure frontend UI work` 来划边界。

- **跨工具可移植是底层约束，不是事后适配。** 同一个 `skills/` 目录通过四套薄打包层分发到 Claude Code / Cursor / Codex / OpenCode：`.claude-plugin/`、`.cursor-plugin/`、`.codex/`、`.opencode/`。Codex/OpenCode 用 `symlink 到 skills/` (`.codex/INSTALL.md`)，更新靠 `git pull` 即时生效。SKILL.md 本身保持纯 Markdown + frontmatter，不绑定任一 agent 的专有调用语法——这与本仓库 AGENTS.md 的"跨 agent 兼容"约定同源。

- **上下文预算是显式工程目标。** `CONTRIBUTING.md:107-114` 和 `quality-guidelines.md:25-31` 把"每个 token 都算数"写成规则：单个 .md 控制在 ~500 行内，超了就拆 (示范是 `minimax-docx/references/openxml_encyclopedia_part{1,2,3}.md`)，禁止内嵌 base64/大 API dump，优先外链。这是 progressive disclosure 的工程化：SKILL.md 当入口，`references/` 当按需加载的深水区。

- **质量靠"可执行校验 + 双层 review"守，而非靠口号。** 仓库为 skill 库**自身**配了一个 meta-skill `pr-review` (`.claude/skills/pr-review/SKILL.md`)：Phase 1 跑脚本做硬规则 (退出码 0/1)，Phase 2 才做内容软审查。硬/软分层明确——`structure-rules.md:50-52` 定义 ERROR (不可合并) vs WARN (flag 但不阻塞)。这是 fail-fast + 故障导向安全在 skill 治理上的落地。

与"堆功能型 skill 集"的根本区别：它不是把一堆 prompt 文件丢进目录就完事，而是 (1) 每个 skill 有固定结构契约 (`SKILL.md` + `references/` + `scripts/`)；(2) 有机器可执行的准入门禁 (`validate_skills.py`)；(3) 把领域专家的"怎么做才不丑"编码成查表和 Avoid 清单；(4) 一份内容多渠道分发。功能多但有治理骨架。

## 特殊技巧 (How)

- **description 内嵌"用户原话簇"作为触发锚点 (可复用)。** 不写抽象能力描述，而是把真实用户措辞分组列进 description。`minimax-pdf/SKILL.md:5-11` 按 CREATE/FILL/REFORMAT 三个路由各列一组引号短语；`fullstack-dev/SKILL.md` 用 `TRIGGER when:` / `DO NOT TRIGGER when:` 正反双写。机制：让 router 阶段的语义匹配有具体落点，降低误触发/漏触发。[推断] 这比本仓库以"能力+场景"为主的 description 在通用对话型触发上更激进。

- **SKILL.md = 路由表 + pipeline 编排，正文极短。** `minimax-pdf/SKILL.md:23` 开篇就是 "Three tasks. One skill."，紧接一张 Route table 把用户意图映射到**脚本执行链** (`palette.py → cover.py → render_cover.js → render_body.py → merge.py`)。SKILL.md 不讲实现细节，只做"判路由 + 调脚本 + 读哪个 reference"的调度。重活在 `scripts/` (9 个 py/js/sh) 和 `design/design.md`。这是"prompt 负责决策、脚本负责确定性产出"的分工。

- **确定性产出下沉到脚本，SKILL 只给契约。** `minimax-pdf/scripts/` 有完整 pipeline (`make.sh` 编排 + `palette.py` 生成设计 token + `render_*` 渲染 + `merge.py` 合并)；`frontend-dev/scripts/` 是 `minimax_image.py / minimax_video.py / minimax_tts.py / minimax_music.py` 四个 API 封装 + `templates/viewer.html`。机制：把容易在 LLM 自由发挥时出错的步骤 (排版、API 调用、PDF 合并) 固化成代码，LLM 只填参数。

- **"假设有 bug"式的强制 QA 循环 (反直觉，可复用)。** `ppt-orchestra-skill/SKILL.md:120-148` 把验证写成强心理预设：`Assume there are problems. Your job is to find them. ... If you found zero issues on first inspection, you weren't looking hard enough.`，并给出可执行的 grep 探针 `markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"` 来抓残留占位符，规定 `Do not declare success until you've completed at least one fix-and-verify cycle`。这把抽象的"自检"变成 (a) 对抗式心态 + (b) 具体命令 + (c) 闭环停止条件，与本仓库 guard-verify 的"闭环验证"哲学一致但写法更接地气。

- **token-based design system：先生成 token，再让 token 贯穿全程。** `minimax-pdf` 把"配色/字体/间距"抽成一层 design token (`palette.py` 产出，`design/design.md` 定义)，封面与正文都从同一组 token 渲染 (`SKILL.md:78` 的 `accent_lt` 由 accent 自动向白色提亮派生)。机制：单一事实源 (Single Source of Truth) 落到视觉层，避免封面和正文风格漂移。

- **多 agent 编排型 skill (pptx-plugin) 的分工模板。** `plugins/pptx-plugin/` 是独立子插件：`agents/` 下有 5 个角色 agent (cover/content/section-divider/summary/table-of-contents -page-generator)，`skills/ppt-orchestra-skill` 负责**先分类每张 slide 为 5 种固定页型之一** (`SKILL.md:9-29`)，再分发给子 agent 生成单文件 slide，最后 `compile.js` 聚合成 pptx。机制：用"固定页型枚举 + 强制视觉多样性"对抗 deck 的 layout drift，这是把 orchestrator/worker 模式应用到内容生产。

- **frontmatter 校验用零依赖手写 parser，不引 PyYAML。** `validate_skills.py:22-70` 自己实现了一个极简 frontmatter 解析器，支持 `|`/`>` 块标量、缩进续行，只做 top-level 字段存在性检查 (`name` 必须等于目录名、`description` 非空)。理由写在文件头 `Zero external dependencies`。机制：校验脚本要在任意 agent / CI 环境零安装即可跑，降低准入摩擦。[推断] 这是有意为之的可移植性取舍。

- **高置信度 secret 扫描而非大而全。** `validate_skills.py:76-80` 只匹配三类高置信模式 (OpenAI `sk-`、AWS `AKIA`、长 Bearer token)，`structure-rules.md:42-48` 明确说"其他形式的硬编码凭据不自动阻断，交人工 review"。机制：自动门禁只拦"几乎不可能误报"的，避免噪声把门禁变成摆设；其余下放软审查。这是对"故障导向安全"的务实裁剪。

- **CONTRIBUTING 把"一个 PR 一个目的"和 reference 拆分写成硬约定。** `CONTRIBUTING.md:22-28` 规定 PR 只能三选一 (加 skill / 修 bug / 改进)，`107-114` 把大文件拆分、禁内嵌大 blob 写成准入指引。机制：用贡献流程纪律守住 skill 库的上下文预算和可 review 性。

- **frontend-dev 把"反 AI 文案"也编码进 reference。** `references/asset-prompt-guide.md`、`motion-recipes.md`、`minimax-voice-catalog.md` 等把媒体生成 prompt、动效配方、可用音色目录都做成查表型 reference，SKILL.md 按需指路。机制：领域知识 (好 prompt 长什么样) 沉淀为数据，而不是每次现编。

真正新颖/反直觉的点：(1) description 内嵌用户原话簇做触发；(2) "假设有 bug + grep 探针 + 强制 fix-verify 循环"的 QA 写法；(3) 把"AI slop 信号"(标题下划线、居中正文、默认蓝) 显式列成 Avoid 清单当负向门；(4) 校验脚本刻意零依赖手写 parser 以保证跨环境可跑；(5) 一份 `skills/` 经四套薄打包层 + symlink 多 agent 分发。

## 资产盘点

- **领域 skills (`skills/`)：17 个**，类型覆盖：前端/全栈 (frontend-dev, fullstack-dev)、移动 (android-native-dev, ios-application-dev, flutter-dev, react-native-dev)、图形 (shader-dev)、文档产出 (minimax-pdf, pptx-generator, minimax-xlsx, minimax-docx)、多模态/媒体 (minimax-multimodal-toolkit, minimax-music-gen, minimax-music-playlist, gif-sticker-maker, vision-analysis)、彩蛋 (buddy-sings)。体量从 127 行 (gif-sticker-maker) 到 1037 行 (fullstack-dev)。
- **治理 meta-skill：1 个** `.claude/skills/pr-review/` (SKILL.md + 2 个 reference: structure-rules / quality-guidelines + `scripts/validate_skills.py`)。
- **子插件：1 个** `plugins/pptx-plugin/`，内含 5 个角色 `agents/*.md` + 5 个 sub-skill (color-font / design-style / ppt-editing / ppt-orchestra / slide-making) + 自带 `.claude-plugin/`。
- **脚本资产：** 至少 4 个 skill 带 `scripts/` (minimax-pdf 9 个、frontend-dev 4 个、minimax-xlsx、minimax-docx、gif-sticker-maker)，约定 `scripts/` 存在则必须有 `requirements.txt` + shebang + 清晰报错。
- **进度披露资产：** 多数 skill 带 `references/` (minimax-docx 18 个分片文件最典型) 与 `templates/`，SKILL.md 做入口、references 做按需深读。
- **分发/安装资产：** 4 套打包层 `.claude-plugin/{plugin,marketplace}.json`、`.cursor-plugin/{plugin.json,INSTALL.md}`、`.codex/INSTALL.md`、`.opencode/INSTALL{,_zh}.md`；无 hooks 资产 (未发现 hook 文件)。
- **没有的东西：** 无 commands/ (非 slash-command 体系)、无 hooks、无过程纪律型 skill (think/guard 那类)。这印证它是产出型而非流程型 skill 库。

## 与本仓库的关联点

可借鉴点 (详细裁决留 plan)：

1. **description 内嵌"用户原话簇"+ DO NOT TRIGGER 反例** —— 本仓库 skill 的 description 触发前缀已被 `verify_skills.py` 强制，但触发样例多偏"场景"。可考虑在高误触发的 skill 上补"正反短语簇"，对应 `skill-authoring.md` 的触发语义硬约束。证据：`minimax-pdf/SKILL.md:5-11`、`fullstack-dev/SKILL.md:11`。
2. **"假设有 bug + grep 探针 + 强制 fix-verify 循环"的验证体裁** —— 可吸收进 guard-verify / dev-tdd 的 acceptance 段，把"自检"从态度变成"对抗式心态 + 具体探针命令 + 不允许零问题收尾"的可执行清单。证据：`ppt-orchestra-skill/SKILL.md:120-148`。
3. **AI slop 负向门清单** —— 本仓库 fe-ui-lint-artifact / fe-ui-critique 已涉 AI slop，可补 MiniMax 这种"Avoid 清单 + NEVER 级硬禁"写法 (如标题下划线、居中正文、默认蓝)。证据：`ppt-orchestra-skill/SKILL.md:74-86`。
4. **零依赖手写校验 parser 的可移植性取舍** —— 本仓库 `scripts/verify_skills.py` 若依赖第三方库，可参考其"零依赖、退出码语义、ERROR/WARN 分层"做法保证任意 CI/agent 环境可跑。证据：`validate_skills.py:13-17,50-52`。
5. **high-confidence-only 的 secret 扫描分层** —— 自动门禁只拦极低误报模式、其余下放人工，避免门禁噪声化。可对照本仓库的 boundary/secret 相关 hook 思路。证据：`validate_skills.py:76-80`、`structure-rules.md:42-48`。
6. **一份 skills/ 多 agent 薄打包 + symlink 分发** —— 与本仓库"跨 agent 兼容"约定同向，可作为把 `skills/` 同步到多 agent 的工程模板参考。证据：`.codex/INSTALL.md`、`.cursor-plugin/plugin.json`。
7. **token-based design system / 单一视觉事实源** —— 对本仓库 fe-ui-design-system (DESIGN.md contract) 是同思路的成熟实现，可对照其 token 派生与贯穿手法。证据：`minimax-pdf/SKILL.md:78`、`design/design.md`。

注意：以上均为产出能力维度，与本仓库过程纪律维度互补；吸收时应保持本仓库 AGENTS.md "短小硬"原则，细则下沉到 skill/doc，不要回灌全局上下文。

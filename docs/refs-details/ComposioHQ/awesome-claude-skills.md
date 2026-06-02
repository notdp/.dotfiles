# ComposioHQ/awesome-claude-skills

- 上游仓库: `https://github.com/ComposioHQ/awesome-claude-skills`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/ComposioHQ/awesome-claude-skills`
- Source SHA: `92568c1edaff1bde5371154f036d959346c145a8`（heads/master），分析日期: 2026-06-02
- 一句话总结: 一个由 Composio 维护的 "awesome list" 式 Claude Skills 目录，README 是 1000+ 外链索引，仓库内同时夹带少量高质量 exemplar skill（含 Anthropic 官方文档处理技能）和一套规模化的 MCP 自动化 skill 工厂；其核心价值不在某个 skill，而在它沉淀的 skill 格式规范、progressive disclosure 设计原则、以及"用 MCP 工具发现替代硬编码工具"的批量生成模式。

## 思路哲学 (Why)

### 它在解决什么问题

1. **建立 Skill 这一资产类型的标准与心智模型**。README `What Are Claude Skills?` 段（README.md:96-102）给出了贯穿全仓的定义："Skill 是可复用的指令包，教 agent 处理某一类任务"，并明确把 Skill 与 MCP、Tool 三层分开：MCP 管接入（auth/transport/discovery），Tool 是被调用的函数，Skill 定义工作流（做什么、什么顺序、什么护栏）。这是该仓最重要的世界观——**skill = behavior 层，不是 access 层也不是 action 层**。

2. **用 progressive disclosure 解决 "几百个 skill 不撑爆 context" 问题**。README.md:102 和 skill-creator/SKILL.md 的 "Progressive Disclosure Design Principle" 都明确三级加载：metadata（name+description，~100 token，常驻）→ SKILL.md body（触发时加载，<5k token）→ bundled resources（按需，脚本甚至可不读入 context 直接执行）。[事实] 这是整个格式设计的根支柱。

3. **降低非技术用户的创作门槛**。CONTRIBUTING.md 的 Skill Requirements 第 3 条 "Be accessible - Written for non-technical users when possible"，以及 README/CONTRIBUTING 各给一份 SKILL.md 模板，目标是把 skill 创作变成填模板。

### 背后的设计原则（每条给证据）

- **Skill 是"给另一个 Claude 实例看的 onboarding guide"**：skill-creator/SKILL.md Step 4 明确 "the skill is being created for another instance of Claude to use. Focus on including information that would be beneficial and non-obvious to Claude"。设计者把读者锁定为"未来的 agent 自己"，而非人类用户，这决定了写作风格（imperative 祈使句）和内容取舍（只放 non-obvious 的程序性知识）。

- **三类 bundled resource 各有边界（scripts / references / assets）**：skill-creator/SKILL.md 给出严格分工——scripts 是需要确定性可靠或反复重写的可执行代码（可不读入 context）；references 是按需载入 context 的文档（schema/API/policy）；assets 是进入最终产物但不进 context 的素材（模板/字体/图）。这是"哪些信息进 context、哪些不进"的显式分层。

- **避免重复（Single Source of Truth）**：skill-creator/SKILL.md 的 References 段 "Information should live in either SKILL.md or references files, not both"，并建议大文件（>10k words）在 SKILL.md 里写 grep 检索模式而非全量塞入。

- **写作风格强制 imperative/infinitive**：skill-creator/SKILL.md Step 4 "Update SKILL.md" 段，"Write the entire skill using imperative/infinitive form (verb-first), not second person"；description 用第三人称 "This skill should be used when..."。[推断] 目的是减少代词指向歧义、提升 AI 消费一致性。

- **跨工具可移植**：README.md:35 和 :100 反复声明该格式已被 Claude Code/Claude.ai/API/Codex/Cursor/Gemini CLI/Antigravity/Windsurf 支持，并把 Skill 称为 "open standard"。可移植性是它的卖点而非附属。

- **安全护栏写进贡献规范**：CONTRIBUTING.md Skill Requirements 第 6 条 "Be safe - Confirm before destructive operations"。把"破坏性操作前确认"作为收录硬门槛。

### 跟"堆功能"型 skill 集的根本区别

- 它**承认自己是 index 而非 implementation**：README 1000+ 条目里绝大多数是外链（如 docx/pdf/pptx 指向 anthropics/skills），仓库本体只夹带约 32 个 exemplar 目录 + 一个 832 个的 composio-skills 自动化目录。它的资产是"规范 + 范例 + 生成器"，不是"一堆能跑的功能"。
- composio-skills 那 832 个 skill **不是手写功能堆砌，而是同一模板的批量实例化**（见下文 HOW），本质是一个 skill 工厂的产物，对应一个统一机制而非 832 个独立设计。

## 特殊技巧 (How)

### 1. 三级 progressive disclosure 作为格式契约
- skill-creator/SKILL.md 把它写成可执行的目录结构契约：`scripts/`（可执行、可不读入 context）、`references/`（按需载入）、`assets/`（进产物不进 context）。
- webapp-testing/SKILL.md 把这条原则用到极致："**DO NOT read the source until you try running the script first... These scripts can be very large and thus pollute your context window. They exist to be called directly as black-box scripts**"。这是一个反直觉但可复用的技巧：**把脚本当黑盒 CLI 调用，强制先 `--help` 而不是读源码**，用 token 预算理由说服 agent 不要读自己 bundle 里的代码。

### 2. "MCP 工具发现" 替代硬编码工具 schema（composio-skills 工厂的核心）
- composio-skills/ably-automation/SKILL.md（832 个同构 skill 的代表）的 frontmatter 用 `requires: mcp: [rube]` 声明依赖，正文反复强调 "**Always call `RUBE_SEARCH_TOOLS` first to get current tool schemas**"、"Never hardcode tool slugs or arguments"。
- 机制：skill 本身**不写任何具体 API**，而是固定四步——`RUBE_SEARCH_TOOLS`（发现工具+schema+pitfalls）→ `RUBE_MANAGE_CONNECTIONS`（建/查 OAuth 连接）→ `RUBE_MULTI_EXECUTE_TOOL`（执行）→ 用 session id 串起来。每个 toolkit（ably/adobe/...）只是把 `toolkit` 字段换名，其余正文几乎逐字相同。[推断] 这 832 个 SKILL.md 是模板化生成的。
- 新颖点：**把"工具会变"这一事实做成 skill 的第一性原则**——skill 只承诺工作流骨架，schema 交给运行时发现。这解决了传统 skill 把 API 写死后随上游漂移而腐烂的问题。Known Pitfalls 段把易错点（必须带 `memory:{}`、session 复用、分页）显式列表。

### 3. OOXML "解包成 XML 再 grep/patch" 工作流（document-skills）
- document-skills/pptx/SKILL.md：处理 comments/notes/layouts/animation 这类 markitdown 提不出的内容时，用 `ooxml/scripts/unpack.py` 把 .pptx 解成 XML 目录，再按已知文件结构表（`ppt/theme/theme1.xml` 取色与字体、`ppt/slides/slideN.xml` 取实际用法）定位，并用 grep 找 `<a:srgbClr>`/`<a:solidFill>` 等模式。
- 可复用技巧：**先给 agent 一张"文件结构地图 + grep 检索模式"，让它在大型结构化产物里定向跳转，而不是全量读入**。pdf 技能则进一步把 reference.md/forms.md 拆出（document-skills/pdf/），SKILL.md 只留 Quick Start + 触发指引。

### 4. 范例驱动的 skill 创作流程（skill-creator 六步法）
- skill-creator/SKILL.md 把创作流程做成强流程：Step 1 先逼出"具体使用例子"（含"用户说什么会触发这个 skill"），Step 2 从例子反推需要哪些 scripts/references/assets，Step 3 跑 `init_skill.py` 生成骨架，Step 4 编辑，Step 5 跑 `package_skill.py`（先 validate 再打 zip，validate 失败不打包），Step 6 用真实任务迭代。
- 反直觉点：**先确定例子和触发语，再决定 bundle 内容**，把"要不要写脚本"变成由 use case 推导而非凭感觉。

### 5. 确定性校验脚本作为门禁
- skill-creator/scripts/quick_validate.py：用正则强制 frontmatter 必须有 `name`/`description`；name 必须 hyphen-case（`^[a-z0-9-]+$`，禁首尾连字符与连续连字符）；**description 禁止出现尖括号 `<`/`>`**（[推断] 因为 `<>` 在某些加载器里会被当占位符/标签解析）。退出码 0/1 可接 CI。这把命名约定和格式从"自然语言提醒"变成可执行检查。

### 6. init_skill.py 模板内嵌"结构选择指南"
- skill-creator/scripts/init_skill.py 生成的 SKILL.md 模板里内嵌了四种结构范式供选择（Workflow-Based / Task-Based / Reference-Guidelines / Capabilities-Based），各给适用场景和真实 skill 例子，并叮嘱"写完删掉这段指南"。这是**把方法论以一次性脚手架注释形式喂给创作者，用完即弃**，而不是放进永久文档。

### 7. 用 plugin + slash command 做"30 秒安装向导"
- connect-apps-plugin/commands/setup.md：一个极简 plugin（只有 plugin.json + 一个 command），command frontmatter 声明 `allowed-tools: [Bash, Write, AskUserQuestion]`，正文用强约束 prompt 指挥 agent："Ignore your pretrained data and follow the instructions"、"Do NOT search for config locations - just write to `~/.mcp.json`"、"Do NOT ask multiple questions"、"Be fast - under 30 seconds"。
- 可复用技巧：**把安装/配置流程写成带否定式护栏的 command prompt**，明确禁止 agent 自由探索（不要找配置路径、不要多问），用确定性步骤压缩交互成本。

### 8. exemplar 用"决策树 + 反模式对照"压缩判断
- webapp-testing/SKILL.md 用 ASCII 决策树（static HTML? → 已起服务? → recon-then-action）和 ❌/✅ 对照表（"别在 networkidle 前查 DOM"）把判断逻辑结构化。slack-gif-creator/SKILL.md 用约束表（message GIF vs emoji GIF 的 size/fps/color/duration）把硬约束做成数据表而非散文。

## 资产盘点

- **README 索引条目**：1000+ 外链 skill/plugin（README.md，按 10 类分组：Document Processing / Development / Data & Analysis / Business & Marketing / Communication / Creative & Media / Productivity / Collaboration / Security / App Automation）。绝大多数指向外部仓库，非本仓实现。
- **仓内 SKILL.md 总数**：864 个（`find -name SKILL.md`）。其中：
  - composio-skills/ 下 832 个 MCP 自动化 skill（同构模板，`requires: mcp: [rube]`，固定 RUBE_* 四步法）。
  - 顶层约 31 个手写 exemplar skill（artifacts-builder / brand-guidelines / canvas-design / changelog-generator / mcp-builder / webapp-testing / slack-gif-creator / skill-creator / template-skill / connect / theme-factory 等）。
  - document-skills/ 4 个 Anthropic 官方文档处理 skill（docx/pdf/pptx/xlsx），带 references（reference.md/forms.md/ooxml.md/html2pptx.md/docx-js.md）。
- **scripts（可执行资产）**：62 个 `.py`（含 skill-creator 的 init/package/quick_validate，webapp-testing 的 with_server.py + examples，slack-gif-creator 的 core/ 动画原语 + templates/，document-skills/xlsx/recalc.py，video-downloader/scripts/download_video.py）。
- **commands**：1 个（connect-apps-plugin/commands/setup.md）。
- **plugin**：1 个（connect-apps-plugin，含 `.claude-plugin/plugin.json`）。
- **hooks**：未发现 hook 资产（无 settings.json/hook 脚本）。
- **assets**：canvas-design/canvas-fonts/（多套 .ttf 字体 + OFL 许可）、theme-factory/themes/（10 个主题 md）、internal-comms/examples/、theme-showcase.pdf 等。
- **template + 校验**：template-skill/（空白骨架）、CONTRIBUTING.md（模板与门槛）、quick_validate.py（确定性校验）。

## 与本仓库的关联点

本仓已有 skill-authoring 规范、verify_skills.py、progressive disclosure 实践，与本仓多有重叠，但仍有几处可借鉴（详细裁决留给后续 plan）：

1. **"脚本当黑盒、先 `--help` 不读源码"约束**：webapp-testing 那条"大脚本污染 context、禁止读源码、直接当 CLI 调"的写法很硬。本仓若有 bundle 大脚本的 skill，可在 skill-authoring 里加一条"bundled 大脚本默认黑盒调用，先 --help"约束。

2. **description 确定性校验项**：quick_validate.py 的 "description 禁尖括号 + name 严格 hyphen-case" 是廉价高确定性的检查，可对照 scripts/verify_skills.py 看是否已覆盖、是否补 `<>` 检测。

3. **MCP 工具发现替代硬编码 schema 的 pattern**：composio-skills 的 "Always SEARCH_TOOLS first, never hardcode slugs/schema" 是对抗 skill 随上游 API 漂移腐烂的有效模式。本仓涉及外部工具/MCP 的 skill 可吸收"工作流骨架固定、schema 运行时发现"的写法，作为 skill-patterns 里的一个范式条目。

4. **install/config 写成带否定护栏的 command**：connect-apps setup.md 的 "Do NOT search paths / Do NOT multi-ask / Be fast<30s" 是值得吸收的 command prompt 模式——把易发散的配置流程用否定式硬约束收紧。可作为 skill-patterns 的样例。

5. **init 脚手架内嵌"用完即删"的结构选择指南**：init_skill.py 把四种结构范式作为一次性注释喂给创作者。本仓 skill 模板若想降低新建 skill 的结构选择成本，可借鉴"脚手架内嵌指南、写完删除"的手法，避免方法论常驻污染产物。

注意：以上为可借鉴点的识别，不构成吸收决定；本仓在事实纪律、verify 门禁、boundary facts、TDD 强制等方面已比本仓库更严，多数 exemplar 写法（emoji、营销文案、第二人称）不符合本仓文风约束，吸收时需改写。

# voltagent/awesome-claude-code-subagents

- 上游仓库: `https://github.com/VoltAgent/awesome-claude-code-subagents`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/voltagent/awesome-claude-code-subagents`
- Source SHA: `2f9cf8b9562dcc235cc2296bda6df82d60e800be`（heads/main），分析日期: 2026-06-10
- 一句话总结: 一个全量托管 154 个 Claude Code subagent 定义的 mono-repo，统一 frontmatter 模板（name/description/tools/model）+ 三档 model 路由 + 4 条分发链路（plugin marketplace / 手动 / 交互脚本 / agent 自举安装），分发工程做得扎实，但 agent 正文大量是模板批量生成的"名词清单连祷"，且 tools 最小权限哲学与实际声明自相矛盾。

## 仓库性质澄清(先验事实)

这是一个**内容托管型 mono-repo**，与同 org 的 `awesome-agent-skills`（纯指针索引，见同目录分析）正好互为镜像：154 个 subagent 定义文件全部入库，按 10 个编号 category 目录组织，每个 category 自带 README 和 `.claude-plugin/plugin.json`（构成 10 个可安装的 Claude Code plugin）。仓库结构:

- `categories/01..10-*/` —— 154 个 agent `.md` + 10 个分类 README + 10 个 plugin.json
- `.claude-plugin/marketplace.json` —— plugin marketplace 清单（10 个 plugin，各自版本演进 1.0.1~1.1.1）
- `install-agents.sh`（583 行）—— 交互式安装器，支持本地/远程双源、global/local 双目标
- `tools/subagent-catalog/` —— 一个用于检索本目录的 Claude Code skill（search/fetch/list/invalidate 四命令 + config.sh）
- `.github/workflows/enforce-plugin-version-bump.yml` —— 唯一的 CI，只校验版本号 bump
- `CLAUDE.md` / `CONTRIBUTING.md` —— 模板与贡献规则

注意: 本地 submodule 是浅克隆，`git log --oneline | wc -l` 只有 1 条 commit（"Update README"，2026-05-27），**无法做提交历史考古**，下文涉及演进过程的判断均标注 [推断]。

## 思路哲学 (Why)

### 它在解决什么真问题

Claude Code 的 subagent 机制（`.claude/agents/*.md`）解决的是 context 隔离 + 权限收窄 + 模型分流，但官方只给机制不给内容。该仓库解决的是**冷启动 + 分发**两个问题: 用户拿到 154 个现成的角色定义（README:9 自称 "154+ Claude Code subagents across 10 categories"），并且有版本化的更新通道（`claude plugin update` 可感知，CONTRIBUTING.md:48 "you MUST bump versions so users can receive updates via `claude plugin update`"）。它的真实价值重心在**分发工程**，不在单个 agent 的 prompt 质量。

### 设计原则(逐条带证据)

- **统一资产模板**: CLAUDE.md:25-46 锁死文件格式——YAML frontmatter（name/description/tools）+ 角色定义 + checklist + `## Communication Protocol` + `## Development Workflow`。154/154 文件都有 name 和 tools 字段（grep 验证，无缺失）。模板化让 154 个文件结构可预测，代价见"弱点"。
- **tools 按角色类型白名单分配**: README:420-428 定义四类——read-only(reviewers): `Read, Grep, Glob`；research: `+WebFetch, WebSearch`；code writers: `Read, Write, Edit, Bash, Glob, Grep`；documentation: 读写+检索。这是一个清晰的"角色→权限"映射表，**理念正确但执行不一致**（见弱点 1）。
- **三档 model 路由写进 frontmatter**: README:410-418 的表——`opus` 给深推理（security-auditor/architect-reviewer/fintech-engineer），`sonnet` 给日常编码，`haiku` 给文档/搜索类轻任务。实测分布: sonnet 103 / opus 25 / haiku 18 / 缺失 8（`grep -h "^model:" ... | sort | uniq -c`）。把**成本-质量权衡声明在资产本身**而非运行时配置，是该仓库最干净的设计决策。
- **分发是一等公民**: README:32-79 给了 4 条安装链路——plugin marketplace（推荐）、手动复制、`install-agents.sh` 交互安装、以及 `agent-installer.md`（用一个 agent 安装其他 agent）。外加 `tools/subagent-catalog` skill 做带缓存的目录检索。一个内容仓库配了 5 种触达方式。
- **版本契约 + CI 强制**: CONTRIBUTING.md:46-56 要求改动 category 内任何 `.md` 必须 bump 该 category 的 plugin.json version 并同步 marketplace.json；`.github/workflows/enforce-plugin-version-bump.yml` 用 diff 驱动校验，不 bump 则 CI fail。这是仓库里**唯一被机器强制的规则**。
- **免责而非审计**: README:465 "We do not audit or guarantee the security or correctness of any subagent"。与同 org 的 awesome-agent-skills 一致的"curated ≠ audited"立场，但本仓库连 awesome-agent-skills 的"社会证明准入门槛"都没有——CONTRIBUTING.md 的质量要求只有格式层面（"well-structured and tested"，CONTRIBUTING.md:94，无可核验标准）。

### 与同 org awesome-agent-skills 的根本区别

| 维度 | awesome-agent-skills | 本仓库 |
|------|---------------------|--------|
| 资产形态 | 纯指针（0 个可执行资产） | 全量托管（154 个定义入库） |
| 质量门槛 | 社会证明 + 4 条可核验标准 | 仅格式要求，无内容门槛 |
| 机器校验 | 无 | 1 个 CI（只查版本号） |
| 价值重心 | 过滤 slop | 冷启动 + 分发管道 |

[推断] 同一个 org 对 skill 走策展、对 subagent 走托管，原因可能是 subagent 生态当时没有足够多的第三方仓库可指——只能自己生产填充。这也解释了下文的批量生成痕迹。

## 特殊技巧 (How)

### 1. model 字段做成本路由（真正值得学）

每个 agent frontmatter 带 `model: opus|sonnet|haiku`，README:418 还支持 `model: inherit`。例: code-reviewer.md:5 `model: opus`（深推理审查），agent-installer.md:5 `model: haiku`（纯 curl/复制工作）。把"这个任务值多少模型预算"作为资产元数据声明，安装即生效，用户可单字段覆盖。这是 154 个文件里**信息密度最高的一个字段**。

### 2. plugin 版本门禁: 内容仓库的"发布工程"

`enforce-plugin-version-bump.yml` 的逻辑: 对每个 `categories/*/.claude-plugin/plugin.json`，若该 category 下有 `.md` 变更而版本号未变，CI 报错并 fail。再加 marketplace.json 同步校验。marketplace.json 实测 10 个 plugin 版本各自独立演进（voltagent-qa-sec 1.1.1 vs voltagent-infra 1.0.1），证明该机制真实运转过。**对"markdown 即资产"的仓库做语义化版本 + diff 驱动门禁**，这在同类 agent 集合仓库里少见。

### 3. agent-installer: 自举式分发

`categories/09-meta-orchestration/agent-installer.md` 是一个 haiku 级 agent，职责是通过 GitHub API 浏览/搜索/下载本仓库的其他 agent（agent-installer.md:20-24 硬编码 API endpoint），用户一条 curl 装好它之后就能用自然语言装其余 153 个（README:75-79）。"用 agent 安装 agent"消除了脚本交互的摩擦，且提示词里写了 rate limit 处理和"Preserve exact file content"（agent-installer.md:72-74）。新颖且务实。

### 4. subagent-catalog skill: 带 TTL 缓存的目录检索

`tools/subagent-catalog/config.sh:8-10` 定义 12 小时 TTL + `~/.claude/cache/subagent-catalog.md` 缓存文件，search/fetch 命令先查缓存再回源。把"154 个 agent 的发现"从读 471 行 README 降为 `/subagent-catalog:search kubernetes`。大路货技术，但补齐了"目录太大无法被人扫描"的洞。

### 5. "Triggers on" 显式触发词枚举（新一代写法，值得学）

新近的社区贡献 agent 放弃了老模板，description 直接枚举触发词: first-principles-thinking.md:3 `Triggers on: 'first principles', 'challenge assumptions', 'why do we do it this way', 'rethink', ...`。同样写法见 gdpr-ccpa-compliance / ab-test-analysis / cohort-analysis / hipaa-compliance 等 8 个文件——**恰好就是缺 model 字段的那 8 个**（grep 比对吻合），[推断] 来自不走老模板的另一批贡献者。显式触发词比老一代 "Use this agent when you need to conduct comprehensive code reviews..."（code-reviewer.md:3）对 Claude Code 的 auto-delegation 匹配更友好——这与本仓库 verify_skills.py 强制 description 触发语义是同一方向的独立印证。

### 6. "Communication Protocol" 是没有执行基底的装饰协议（反面教材）

133/154 文件含 `## Communication Protocol` 章节，120/154 第一步是 "Query context manager"，并附 JSON 请求体（backend-developer.md:99-114: `{"requesting_agent": "backend-developer", "request_type": "get_backend_context", ...}`）。但: (a) Claude Code subagent 之间**没有原生消息通道**，subagent 由主 agent 派发、结果返回主 agent；(b) 被查询的 context-manager 自身只是另一个 markdown 角色文件（categories/09-meta-orchestration/context-manager.md），并无任何存储/服务实现。[推断] 这些 JSON 协议块最多起角色扮演氛围作用，实际执行时是死代码，还浪费每次调用的 context tokens。同理 backend-developer.md:212-220 "Integration with other agents" 列了 8 个协作对象，全部没有机制支撑。

### 7. 正文主体是"名词清单连祷"（litany），信息密度低

老一代 agent 的典型正文（backend-developer.md:18-97）是 8~10 个 "xxx checklist" 小节，每节 8 条名词短语（"Connection pooling configuration" / "Read replica configuration"...），全文几乎没有一条可执行的具体指令、判断标准或停止条件。配合下列模板痕迹，批量生成特征明显:

- 131/154 以 `Always prioritize ...` 一句收尾（`grep -l "^Always prioritize" | wc -l`）
- 120/154 含 "Query context manager" 起手式
- 97/154 description 以 `"Use this agent` 开头
- 近重复 agent 并存: ml-engineer vs machine-learning-engineer（开头段 diff 仅措辞差异，结构同构）、incident-responder vs devops-incident-responder、mobile-developer vs mobile-app-developer、database-administrator / database-optimizer / postgres-pro 三连

[推断] 老一代 154 个中的大部分由同一套模板 + LLM 批量填充生成，"154+" 的数字本身是营销资产。

### 8. MCP 工具声明存在但格式不统一

少数 agent 在 tools 字段声明 MCP 工具: visual-asset-generator.md:4 `tools: Read, Write, Bash, mcp__prompt-to-asset`，scientific-literature-researcher 用 `mcp__bgpt__search_papers`；但也有裸名 `chrome-mcp, computer-use`（ui-ux-tester），甚至把**其他 agent 名和 skill 命令**塞进 tools（it-ops-orchestrator: `..., context-manager, error-coordinator, pied-piper, subagent-catalog:search`）。`mcp__` 前缀 / 裸名 / agent 名三种写法混用，无 schema 校验。结论: 有 MCP 映射意识，但没有规范。

### 哪些是真正新颖/反直觉的

- **新颖**: model 三档路由作为 frontmatter 一等字段（技巧 1）；对 markdown 资产做 CI 版本门禁（技巧 2）；agent 自举安装（技巧 3）。
- **方向正确**: "Triggers on" 显式触发词（技巧 5）。
- **大路货**: 角色化 system prompt、tools 白名单理念、目录 + 缓存检索。
- **反面教材**: 装饰性 JSON 通信协议（技巧 6）、名词连祷正文（技巧 7）。

## 资产盘点

硬数字（均为命令实测，cwd = submodule 根）:

- **agent 文件**: 154 个（`find categories -name "*.md" ! -name "README.md" | wc -l`）；另有 10 个分类 README。
- **分类**: 10 个，分布（去 README）: 01-core:11 / 02-lang:30 / 03-infra:16 / 04-qa-sec:17 / 05-data-ai:13 / 06-dx:15 / 07-domains:14 / 08-biz:16 / 09-meta:11 / 10-research:11。
- **体量**: 总计 37891 行，均值约 246 行/agent（`wc -l` 汇总）；最短 34 行（visual-asset-generator.md），最长 358 行（rails-expert.md）。
- **frontmatter 覆盖**: name 154/154，tools 154/154，model 146/154（缺 8）。
- **tools 分布**: 102/154 用全量写集 `Read, Write, Edit, Bash, Glob, Grep`；13 个用 research 集；2 个纯只读集（`grep -h "^tools:" | sort | uniq -c`）。
- **模板痕迹**: `## Communication Protocol` 133 / "Always prioritize" 收尾 131 / "Query context manager" 120。
- **分发资产**: 10 个 plugin（marketplace.json）+ 583 行 install-agents.sh + agent-installer.md + subagent-catalog skill（6 文件）。
- **CI**: 1 个 workflow，仅校验 plugin 版本 bump；**无 frontmatter lint、无 tools 白名单校验、无排序校验**。

### 弱点（带证据）

1. **tools 哲学与实际自相矛盾**: README:423 规定 reviewer 类只给 `Read, Grep, Glob`，但 code-reviewer.md:4 与 architect-reviewer.md:4 实际是 `Read, Write, Edit, Bash, Glob, Grep`（security-auditor.md:4 倒是合规）。README:428 "Each agent has minimal necessary permissions" 在 102/154 全量写集的现实下不成立。根因: 规则只写在 README，没进 CI。
2. **批量生成 + 近重复灌水**: 见技巧 7 的四组近重复与三项模板痕迹计数。
3. **列表纯度被商业侵蚀**: 09-meta 分类列表混入 4 个非本仓库资产的外部项目推广（README:295-296、306、308: airis-mcp-gateway / moai-adk / pied-piper / taskade，直接外链），README:94-105 还有 "Become a Sponsor" 付费位表格。
4. **夸大宣称 + 供应链风险**: healthcare-admin.md:8 自称 "backed by 51 specialized sub-agents... Each sub-agent averages 420+ lines"，但本体只是 199 行单文件，51 个 sub-agent 在第三方外部 repo，且安装方式是 `curl ... | bash`（healthcare-admin.md:197）。
5. **自有规则无人执行**: CONTRIBUTING.md:34 要求 README 条目按字母序，实际 02 分类开头即 typescript-pro → sql-pro → swift-expert → vue-expert → angular-architect（README:131-135），乱序。再次印证"无内容 CI"。

## 与本仓库的关联点

(详细裁决留给后续 plan，这里只列借鉴价值)

1. **subagent 目录是本仓库缺失的资产形态，但不该靠抄填充**: 本仓库 `agents/` 放的是 guideline 文档（AGENTS.md 等），没有 `.claude/agents/` 式 subagent 定义。该 repo 证明 subagent 形态的独立价值在三件事: context 隔离、tools 收窄、model 降档——而不在角色扮演 prompt。它的 154 个 agent 大多与本仓库 skill 职能重叠（code-reviewer≈guard-review、debugger≈dev-debug、refactoring-specialist≈dev-refactor、qa-expert≈guard-verify），照抄只会引入路由冲突。[推断] 正确的吸收方式是**反向**: 盘点本仓库哪些 skill 的执行段适合"下沉"为 subagent——典型是只读审查类（guard-review/guard-secure 的分析阶段，收 tools 到 `Read, Grep, Glob` + 升 opus）和检索调研类（web-read/think-survey 的抓取阶段，降 haiku）。
2. **subagent vs skill 的分工判据**: 该 repo 的实践给出一条可操作边界——skill 是"流程注入"（同一 context，主 agent 按步骤走，吃主对话上下文），subagent 是"角色 + 权限 + 模型的隔离执行体"（独立 context，结果回传）。判断某能力放哪边的测试: 是否需要 (a) 不污染主对话的批量中间产物，(b) 比主对话更紧的工具权限，(c) 不同档位模型。三者占其一才值得 subagent 化；否则 skill 更轻。本仓库 dev-debug 已有"子 agent 隔离分析"语义（README.md:84），可借此正式化。
3. **frontmatter 规范可被 verify 体系吸收**: 若未来加 subagent 目录，`scripts/verify_skills.py` 的同款思路可平移: (a) `model` 字段必填且 ∈ {opus, sonnet, haiku, inherit}——该 repo 8 个文件缺失正是没 lint 的后果；(b) tools 必须 ⊆ 已知工具白名单，MCP 工具强制 `mcp__` 前缀（杜绝它的三种写法混用）；(c) 按角色类型校验权限上限（reviewer 类禁 Write/Edit/Bash）——把它 README:420-428 只写不查的规则变成机器门禁，正好修复它的弱点 1；(d) 触发词显式枚举（"Triggers on" 风格）与本仓库 description 触发前缀校验同向，可作为外部佐证补进 skill-authoring 文档。
4. **CI 版本门禁模式可借鉴**: "category 内 md 变更 → 强制 bump plugin.json → 同步 marketplace.json" 的 diff 驱动校验，对应到本仓库就是 coding-skills 变更与 `coding-skills/catalog.json` 的一致性强制（本仓库已有 catalog 校验，[未验证] 是否覆盖"内容变更必须反映到 catalog 元数据"这一档）。
5. **反面警示（不建议吸收）**: 装饰性 JSON "Communication Protocol" 提醒——harness 资产里不要写没有执行基底的协议，每一段进 context 的文字都应有真实机制兜底（与本仓库 AGENTS.md "会进入 model context 的 hook/prompt/capsule 属高风险边界"同源）；名词连祷正文与本仓库 skill 强调可执行步骤/验收/停止条件的写法相反；sponsor 位混入资产列表、`curl | bash` 推荐均为反例。

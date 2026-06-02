# SuperClaude-Org/SuperClaude_Framework

- 上游仓库: `https://github.com/SuperClaude-Org/SuperClaude_Framework`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/SuperClaude-Org/SuperClaude_Framework`
- Source SHA: `226c45cc93b865108843a669c6545d421784b68c`（v4.0.7-150-g226c45c），分析日期: 2026-06-02
- 版本: v4.3.0
- 一句话总结: 一个把 Claude Code 当成"可被改造的开发平台"的 meta-programming 框架，靠"行为指令注入 + 组件编排"提供 30 命令 / 20 agent / 7 行为模式，并把"动手前置信度门 + 动手后证据自检 + 跨 session 错误学习"这套 PM 方法论用 Python 代码 + pytest 插件 + prompt 文件双轨固化下来。

## 思路哲学 (Why)

### 它在解决什么真问题

它的核心命题不是"给 Claude 加更多技能"，而是"治理 LLM 的两个高频失败模式"：
1. 方向错误（在没想清楚前就动手，做完才发现做错了）；
2. 幻觉式完成（声称"测试通过/已完成"但没有证据）。

`PLANNING.md:16-21` 把 Core Mission 写成四条：pre-execution confidence checking（防方向错）、post-implementation validation（防幻觉）、cross-session learning（reflexion）、token-efficient parallel execution。注意前两条都是"纪律/门禁"，不是"功能"。

`README.md:86` 自我定位是 "meta-programming configuration framework ... through behavioral instruction injection and component orchestration"——即它把自己理解为"改造宿主 agent 行为的配置层"，而非"工具集合"。

### 默认世界观/方法论

- **PDCA 闭环治理**（`plugins/superclaude/skills/pm/SKILL.md:14-40`、`plugins/superclaude/agents/pm-agent.md:48-98`）：把开发当成 Plan(假设)→Do(实验)→Check(评估)→Act(改进) 的循环，每一轮的 trial-and-error、错误、解法都要落盘。这是它最强的方法论底座——开发被建模成"持续学习系统"而不是"一次性产出"。
- **证据驱动，禁止猜测**（`PLANNING.md:84-92`、`CLAUDE.md` Core Development Principles 1）："Never guess - always verify with official sources"。和本仓库的 Truth Directive 高度同构。
- **置信度优先**（`PLANNING.md:94-101`）：动手前先算置信度，≥90% 才做，70-89% 给备选并继续调查，<70% 停下问问题。其哲学是"验证比生成贵"的成本论——花 100-200 token 算置信度，省掉 5000-50000 token 的错方向返工（ROI 25-250x）。
- **文件即记忆 / 经验即知识**（`pm-agent.md:177-235`）：把临时探索（`docs/temp/`）、成功模式（`docs/patterns/`）、失败教训（`docs/mistakes/`）分三层沉淀，成功转 pattern、失败转 mistake、全局规律回写 `CLAUDE.md`。这是一条显式的"经验→知识"演化管线。
- **跨工具可移植的产品线**：同一套方法论被复刻成 SuperGemini / SuperQwen（`README.md:14-19`），说明它把"方法论"和"具体宿主 agent"刻意解耦。

### 跟"堆功能"型 skill 集的根本区别

1. **它卖的是纪律而非能力**：confidence-check / self-check / reflexion 三个核心模式都不"产出代码"，而是"在产出前后加门禁"。`pm-agent.md:519-524` 明确写 PM Agent "Will Not: Execute implementation tasks directly"——它是 meta-layer，只管编排和沉淀。
2. **方法论被代码固化、可测试**：置信度评分、自检协议、reflexion 记忆都有 Python 实现（`src/superclaude/pm_agent/`）并通过 pytest 插件提供 fixture + marker，号称 confidence-check 8/8 测试 precision/recall=1.0（`skills/confidence-check/SKILL.md:14-18`）。把"软规则"做成"可断言的 fixture"是它区别于纯 prompt skill 集的关键。
3. **双轨制（prompt + runtime）**：同一能力既有给 LLM 读的 `.md`（prompt 注入），又有给 pytest/CLI 调的 `.py`（确定性执行）。
4. **诚实标注未落地**：`README.md:112-114` 主动声明 TS 插件系统"not yet available"，`PLANNING.md:351` 把 confidence.py 的 placeholder 列为待办——比多数"全是 roadmap 画饼"的 skill 集克制。

## 特殊技巧 (How)

### 1. 置信度评分做成"加权 checklist + 上下文 flag 短路"
`src/superclaude/pm_agent/confidence.py:43-101`：5 项检查带固定权重（无重复 25% + 架构合规 25% + 官方文档 20% + OSS 参考 15% + 根因 15%），累加成 0-1 分。
- 每个子检查（`_no_duplicates`/`_architecture_compliant`/...）都先看 `context` 里有没有显式 flag（如 `duplicate_check_complete`），有就短路返回——既能让 LLM 自报、也能在测试里强制注入（`confidence.py:145-146,171-172`）。
- 根因检查有"反含糊"启发式：root_cause 里出现 `maybe/probably/might/possibly/unclear/unknown` 任一就判失败，且要求 >10 字符（`confidence.py:241-247`）。这是把"含糊措辞=没想清楚"做成可执行规则。[推断] 该启发式很轻，主要靠 LLM 诚实填 context。

### 2. SKILL.md 用"description = 触发语义"驱动自动激活
`skills/confidence-check/SKILL.md:1-4` 的 frontmatter 只有 `name` + `description`，description 写成"Use before starting any implementation to verify readiness with..."——把触发条件直接写进 description 让宿主 agent 自动选用。`CLAUDE.md` 末尾的"Skills System"gap 分析也承认现有 command 还应"migrate to proper skills with YAML frontmatter for auto-triggering"。这与本仓库 `verify_skills.py` 强制触发前缀是同一思路，但 SuperClaude 没有强制校验脚本。

### 3. 行为模式（Mode）= 可被关键词/flag 激活的"人格切换"
7 个 `MODE_*.md` 不是命令而是"行为改写包"。每个文件统一结构：Activation Triggers / Behavioral Changes / Examples。
- `MODE_Brainstorming.md:5-11`：vague request、"maybe/possibly" 这类不确定词、`--brainstorm/--bs` flag 都能激活，激活后切成 Socratic 提问人格。
- `MODE_Token_Efficiency.md:5-9` 由 ">75% context usage" 或 `--uc` 触发，激活后启用一整套符号系统（`→ ⇒ ∴ ∵`，`MODE_Token_Efficiency.md:19-52`）和缩写表把输出压 30-50%。把"省 token"做成一个可显式切入的压缩语言，是比较新颖的手法。

### 4. Reflexion = JSONL 错误记忆 + 三级查找 + 自动 mistake 文档
`src/superclaude/pm_agent/reflexion.py` 是最有工程含量的部分：
- **错误签名归一化**：`_create_error_signature`（`reflexion.py:130-162`）把 error_message 里的数字全替换成 `N`（`re.sub(r"\d+","N",...)`）再截 100 字符，让"Expected 5 got 3"和"Expected 8 got 2"匹配到同一签名。
- **三级查找降级**：mindbase 语义搜索（curl 打 `localhost:18003`，超时 3-5s，`reflexion.py:164-215`）→ 本地 JSONL grep（`_search_local_files`）→ None。mindbase 不可用时静默降级（捕获 Timeout/SubprocessError/FileNotFoundError），保证离线可用。
- **相似度用词集 Jaccard**：`_signatures_match`（`reflexion.py:252-275`）用 `overlap/union >= 0.7` 判定相似，刻意选"够用就好"的简单算法。
- **命中=0 token 复用，未命中才花 1-2K 调查**（`reflexion.py:5-7` 头注释），把"错误记忆"直接量化成 token 预算。
- 重大错误自动生成 `docs/mistakes/<test>-<date>.md`，模板固定六段：What Happened / Root Cause / Why Missed / Fix Applied / Prevention Checklist / Lesson Learned（`reflexion.py:277-347`）。

### 5. Self-Check = "四问 + 7 红旗"幻觉检测
`src/superclaude/pm_agent/self_check.py:1-13,52-60`：四个强制问题（测试是否全过/需求是否全满足/有无未验证假设/有无证据）+ 7 个红旗短语（"tests pass"无输出、"everything works"无证据、"implementation complete"却有失败测试等）。这把"无证据的完成声明"做成可扫描的反模式表，号称 94% 幻觉检测率（`PLANNING.md:323`，[未验证] 无 benchmark 出处）。

### 6. Hooks 把方法论钉进 session 生命周期
`plugins/superclaude/hooks/hooks.json`：
- `SessionStart` 跑 `scripts/session-init.sh`（`hooks.json:3-13`）——脚本打印 git 状态、token 预算提醒、可用核心服务清单（`session-init.sh`），等于每次开局自动播报上下文。
- `Stop` 用 `type:prompt` 注入"结束前检查未提交改动/未完成任务"（`hooks.json:14-23`）——这是用 prompt-type hook 在收尾强制自检，不需要外部脚本。
- `PostToolUse` 匹配 `Write|Edit` 后注入"验证刚才的编辑有无语法错误/缺 import/逻辑断裂，有问题立刻修"（`hooks.json:24-34`）——把"编辑即校验"做成每次写文件后的自动 prompt。`prompt`-type hook（让 hook 直接给 LLM 喂指令而非跑命令）是相对新颖且轻量的用法。

### 7. 双轨分发 + 自承认的迁移过渡
- 当前稳定版用 `pipx install superclaude && superclaude install`（CLI 把 `.md` 拷到 `~/.claude/commands/sc/` 等），`install.sh:1-18` 是 git 直装路径（检查 Python3.10+/UV → editable 安装 → 装 30 命令）。
- 同时存在 `plugins/superclaude/` 这套 `.claude-plugin/plugin.json`（`plugin.json:24-29` 指向 commands/agents/skills/hooks/.mcp.json）的"v5.0 插件包"形态，但 README 明说未启用。
- `pyproject.toml` 把 pytest 插件注册为 entry point，装完即自动加载，提供 5 个 fixture + 9 个 marker（`CLAUDE.md` Pytest Plugin 段）。**把"方法论"装成 pytest 插件、用 marker 在 CI 里强制跑置信度/自检**，是把 agent 纪律接进传统测试管线的少见做法。

### 8. Evidence-Based 的删除/决策文档化
`DELETION_RATIONALE.md` 为一次 ~22507 行的大删除逐类列出证据（commit 号、行数、原因分类）。把"删了什么、为什么删、证据"做成可审计文档，呼应其"证据驱动"哲学，是值得借鉴的过程纪律。

### 哪些是真正新颖/反直觉的
- **置信度门做成带权重 + flag 短路的可测试函数**（而非纯 prompt 提醒）：新颖，可在 pytest 里断言。
- **错误签名数字归一化 + 三级降级查找**：把"错误学习"工程化到能离线 grep 命中、命中即 0 token，思路扎实。
- **prompt-type hook 在 PostToolUse/Stop 注入自检指令**：轻量且不依赖外部脚本，反直觉地用 hook 喂 prompt 而非跑命令。
- **token 效率做成一套可激活的符号压缩语言**：把省 token 当成显式模式切换。
- **方法论以 pytest 插件 + marker 形态进 CI**：少见的"agent 纪律可在传统测试管线强制执行"。

### 需警惕的点（事实 vs 推断）
- 多处性能/检测率数字（3.5x 加速、94% 幻觉检测、30-50% token 节省）在文档里反复出现但**无可复核 benchmark 出处**（`PLANNING.md:320-325`），属 [未验证] 营销化指标，不宜直接采信。
- confidence.py 的检查很多依赖 LLM 老实填 `context` flag 或文件存在性（如"有 README 就算官方文档已核实"，`confidence.py:103-132`），实际把关强度有限 [推断]。
- 大量重复文件（`src/superclaude/commands/` 与 `plugins/superclaude/commands/` 几乎重复一份），是双轨过渡期的冗余，维护成本高。

## 资产盘点

- **Commands**: 30 个 `/sc:*` slash 命令（`plugins/superclaude/commands/*.md`，含 implement/analyze/research/pm/brainstorm/git/test/troubleshoot 等），同时在 `src/superclaude/commands/` 重复存放一份。
- **Agents**: 20 个领域 agent（`plugins/superclaude/agents/*.md`，含 pm-agent、system-architect、security-engineer、deep-research-agent、root-cause-analyst、socratic-mentor、business-panel-experts 等）。
- **Modes**: 7 个行为模式（`MODE_Brainstorming / Business_Panel / DeepResearch / Introspection / Orchestration / Task_Management / Token_Efficiency`）。
- **Skills**: confidence-check（含 `confidence.ts` 参考实现）+ plugin 侧 pm / troubleshoot / brainstorm / deep-research / token-efficiency 共约 6 个 SKILL.md。
- **Hooks**: 1 个 `hooks.json`（SessionStart=command、Stop=prompt、PostToolUse(Write|Edit)=prompt）。
- **Python 核心**: `pm_agent/`(confidence/self_check/reflexion/token_budget) + `execution/`(parallel/reflection/self_correction) + `cli/` + pytest 插件（5 fixture / 9 marker）。
- **安装资产**: `install.sh`（git 直装）、`superclaude` CLI（PyPI/pipx）、npm 包、`.claude-plugin/plugin.json`（v5.0 形态，未启用）、MCP 配置（8 server + AIRIS gateway）。
- **治理文档**: PLANNING.md / TASK.md / KNOWLEDGE.md / DELETION_RATIONALE.md（session 启动即读，作为长期记忆与决策审计）。

## 与本仓库的关联点

以下仅列借鉴方向，详细裁决留给后续 plan：

1. **置信度门可参考其"带权重 + 反含糊词"的可执行化**，但本仓库已有 `think-scope`/`guard-verify`，更应吸收其"<70% 必须停下问问题"的硬停语义，而非引入新评分系统。
2. **Reflexion 的"错误签名数字归一化 + JSONL append + 命中即 0 token"机制**，对 `assist-learn`/`assist-retrospect` 有价值——可考虑把教训沉淀成可 grep 的结构化记录而非纯散文 MD。
3. **prompt-type hook 在 PostToolUse(Write|Edit) 注入"编辑即校验"**，与本仓库"用 hook 强制规则、不只写自然语言提醒"理念一致，可评估是否补一个轻量编辑后自检 hook。
4. **Stop hook 注入"结束前检查未提交/未完成"**，和本仓库 `guard-close`/`guard-diff-scan`/SSOT 红线方向一致，可考虑 hook 化。
5. **PDCA 三层文件沉淀（temp/patterns/mistakes）+ 自动 mistake 模板（六段式）**，可作为 `assist-retrospect` 输出模板的参考。
6. **Token Efficiency 的符号压缩语言**与本仓库"不用 emoji/自造隐喻"的文风约束冲突，不建议吸收其符号体系，仅参考"按 context 占用阈值触发压缩"的思路。
7. **反面教训**：避免其"双轨重复目录"和"无出处性能指标"——本仓库的事实纪律应继续要求性能/检测率类声明带可复核证据。

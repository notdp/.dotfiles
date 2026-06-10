# anthropics/claude-code-security-review

- 上游仓库: `https://github.com/anthropics/claude-code-security-review`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/anthropics/claude-code-security-review`
- Source SHA: `0c6a49f1fa56a1d472575da86a94dbc1edb78eda`（heads/main），分析日期: 2026-06-10
- 一句话总结: Anthropic 官方的 AI 安全审查 GitHub Action——用 Python 编排层把 Claude Code 的非确定性安全审计包成可在 CI 确定性运行的 pipeline，核心资产不是审计 prompt 本身，而是一套三层 false-positive 过滤漏斗和 17 条"误报判例"。

## 仓库性质澄清(先验事实)

这是一个**可执行的 GitHub Action + Python pipeline 仓库**，不是 prompt 集合，也不是 skill 库。核心构成:

- `action.yml`(333 行) —— composite action，编排缓存、依赖安装、扫描、artifact 上传、PR 评论
- `claudecode/` —— Python 实现，25 个 `.py` 文件共 6594 行，其中 12 个 `test_*.py` 占 4205 行(174 个 test 函数)；真正的业务代码约 2400 行
- `claudecode/evals/` —— 单 PR 评测 runner(`run_eval.py` + `eval_engine.py`)，**不含任何标注数据集**
- `.claude/commands/security-review.md`(190 行) —— 同一套审计逻辑的 slash command 版本，即 Claude Code 内置 `/security-review` 的上游
- `scripts/comment-pr-findings.js`(246 行 + 570 行 bun 测试) —— 把 findings 转成 PR inline review comments
- `docs/` + `examples/` —— 两个客制化注入点(自定义扫描类别 / 自定义过滤规则)的说明和示例

工作流(README.md:88-92): PR 触发 → 拉 PR 元数据和 diff → 构造审计 prompt → subprocess 调 `claude` CLI 做 agentic 审计 → 输出 JSON findings → 两层过滤(正则硬排除 + Claude API per-finding 裁决) → exit code + PR 评论。

README.md:45 显式声明: 该 action **未对 prompt injection 做加固**，只应审查可信 PR。

## 思路哲学 (Why)

### 它在解决什么真问题

不是"如何让 LLM 找到漏洞"——找漏洞的 prompt 只占 175 行(prompts.py)。它解决的是两个工程问题:

1. **Alert fatigue / 误报泛滥**。传统 SAST 的核心痛点是噪音；LLM 审查若不约束反而更糟(每个理论上的问题都能被它说出花来)。整个仓库一半以上的设计是在做减法: prompt 内排除规则、29 条正则硬排除、16 条 LLM judge 排除 + 17 条判例。filter 的 system prompt 写明目标: "filter out false positives and low-signal findings to reduce alert fatigue. You must maintain high recall... while improving precision"(claude_api_client.py:189-193)。
2. **非确定性组件如何塞进确定性 CI**。LLM 输出格式漂移、超时、prompt 超长、API 抖动——pipeline 用 JSON schema 强制 + 三级 fallback 解析 + 重试/降级阶梯 + exit code 语义把这些都兜住(详见 How #4)。

### 设计原则(逐条带证据)

- **precision 优先，显式接受漏报**: 审计 prompt 要求 ">80% confident of actual exploitability" 才报(prompts.py:58)，结尾再压一次: "Better to miss some theoretical issues than flood the report with false positives"(prompts.py:164)。confidence < 0.7 直接不许报(prompts.py:161)。
- **职责分层: 审计层保 recall，过滤层保 precision**: 审计 prompt 和过滤 prompt 是两个独立角色("senior security engineer" vs "security expert reviewing findings from an automated tool")，后者单独裁决每条 finding(claude_api_client.py:145-184)。
- **只审增量，不审存量**: "focus ONLY on security implications newly added by this PR. Do not comment on existing security concerns"(prompts.py:55)。diff-aware 是控噪的第一道闸。
- **fail-open 偏向 recall**: 过滤层的 Claude API 调用失败时，finding 被**保留**并标记 confidence=10(findings_filter.py:297-306)——过滤器宕机不能变成漏报放大器。
- **排除规则即产品**: DOS、rate limiting、资源泄漏、open redirect 等类别被**三层重复排除**(prompt 内 prompts.py:61-64 与 166-171；正则 findings_filter.py:31-79；judge 指令 claude_api_client.py:243-259)。同一规则写三遍不是冗余失误，是对"LLM 不一定听话"的防御性设计。[推断] 这是实践中被 DOS 类误报反复打脸后的迭代产物。
- **审计方法论是 agentic 的，不是 diff-only 的**: prompt 要求三阶段——先用文件搜索工具研究仓库已有安全模式，再对比新代码是否偏离，最后做漏洞评估(prompts.py:106-124)。这利用了 Claude Code 的工具能力，是它和"把 diff 喂给 chat API"的本质区别。

### 与传统 SAST、与本仓库 guard-secure 形态的根本区别

- vs 传统 SAST: 规则引擎匹配语法模式；这里是语义理解 + 仓库上下文探索(README.md:120-125 自述)。代价是非确定性和按 token 计费，所以才需要整个工程外壳。
- vs 本仓库 `guard-secure`: guard-secure 是**纯 prompt 检查表**(STRIDE 六维 + grep 关键词)，运行在主对话上下文里，输出 markdown，无独立过滤层、无 schema、无确定性外壳；本仓库是 **Python 编排的 pipeline**，agent 只是其中一个 subprocess。两者各占一极: skill 形态零基础设施成本但不可在 CI 复跑、无定量过滤；pipeline 形态可 CI 化但带 6500 行 Python 维护负担。它的 slash command 版(见 How #6)恰好是两极之间的中间形态——纯 prompt 但内嵌了 subagent 过滤 pipeline。

## 特殊技巧 (How)

### 1. 三层 false-positive 过滤漏斗

实际代码中的过滤是**两层运行时机制 + 一层 prompt 预防**:

1. **预防层(审计 prompt 内)**: "IMPORTANT EXCLUSIONS - DO NOT REPORT" 5 条(prompts.py:166-171)，让多数噪音根本不被产出。
2. **硬规则层(确定性正则)**: `HardExclusionRules` 用 29 条预编译正则匹配 finding 的 title+description 文本(findings_filter.py:31-79)，分 7 组: DOS、rate limiting、资源泄漏、open redirect、内存安全、regex injection、SSRF。还有两条结构规则: Markdown 文件中的 finding 一律排除(findings_filter.py:92-94)；内存安全类 finding 仅在 C/C++ 扩展名文件中保留(findings_filter.py:133-143)。
3. **LLM judge 层(per-finding 裁决)**: 每条幸存 finding 单独调一次 Claude API，prompt 含 16 条 HARD EXCLUSIONS + 4 条 SIGNAL QUALITY 问题 + 17 条 PRECEDENTS(claude_api_client.py:243-284)，输出 `keep_finding` + 1-10 confidence + justification 的固定 JSON(claude_api_client.py:303-310)。

注意第 2 层的反直觉之处: 正则匹配的对象不是代码，而是 **LLM 生成的 finding 描述文本**——用确定性规则对非确定性输出做后过滤。便宜、零 API 成本、可单测(test_hard_exclusion_rules.py)，但也脆弱(见弱点)。

### 2. PRECEDENTS: 把安全团队的判例写成可移植规则(最有价值资产)

claude_api_client.py:267-284 的 17 条"判例"不是漏洞分类学，而是安全工程师的**裁决经验**，每条都在划"什么不算漏洞"的边界，例如:

- 4: 环境变量和 CLI flags 是可信值，依赖控制 env var 的攻击无效
- 2: UUID 视为不可猜测，无需校验
- 8: React 默认防 XSS，除非用了 `dangerouslySetInnerHTML`
- 10: 客户端 TS 缺权限检查不是漏洞，校验责任在服务端
- 13: 记录非 PII 数据不是漏洞，即使数据"看起来敏感"
- 14: shell 脚本里的命令注入通常不可利用，除非有具体的不可信输入路径
- 1: 记录 URL 假定安全，记录 request headers 假定危险(可能含凭证)

这类知识在 OWASP 文档里找不到，是真实误报数据蒸馏出来的。slash command 版还有平行的一套(security-review.md:158-170，含 "React and Angular"、regex injection 一律排除等差异)，两套未同步——说明它们是各自迭代的活规则。

### 3. per-finding 隔离裁决，附完整文件内容

过滤层不批量处理: 每条 finding 单独一次 API 调用(findings_filter.py:259-263)，prompt 里嵌入该 finding 所在**文件的完整内容**(claude_api_client.py:222-230)。设计意图 [推断]: 隔离裁决避免 findings 互相污染判断；带全文是因为 judge 没有工具，只能靠喂进去的上下文判断"这条 SQL 拼接到底有没有用户输入流入"。代价是 token 开销线性放大，且大文件无截断保护(代码中未见任何 file content 截断逻辑)。

### 4. 把 agent 包成确定性 CI 组件(工程外壳清单)

这是"LLM 审查 CI 化"的完整套路，值得逐条记录:

- **schema 强制**: prompt 给出精确 JSON schema 并以 "Your final reply must contain the JSON and nothing else" 收尾(prompts.py:128-150, 175)。
- **三级 JSON 解析 fallback**: 直接 parse → markdown code block 提取 → 全文扫描配对花括号逐个尝试(json_parser.py:12-89)。
- **subprocess 化 agent**: `claude --output-format json` 走 stdin 传 prompt(避免 argv 超长)，cwd 指向仓库目录让 agent 能用文件工具(github_action_audit.py:222-241)。
- **重试/降级阶梯**: 非零退出重试 3 次；`error_during_execution` 重试；`Prompt is too long` 触发**去 diff 重跑**——降级 prompt 只列文件名，让 agent 自己用工具去看改了什么(github_action_audit.py:258-264, 591-595)。降级路径复用了 agentic 能力，而不是简单截断。
- **exit code 语义**: 有 HIGH finding 退出码 1，否则 0(github_action_audit.py:636-637)。
- **错误也走 JSON**: 所有失败路径输出 `{"error": ...}` 到 stdout(github_action_audit.py:528, 557-570)，action.yml 用 `jq -e '.error'` 区分错误和结果(action.yml:269)。

### 5. 用 actions/cache 做"每 PR 只跑一次"的幂等标记 + 并发占位

action.yml:76-155 用 cache key `claudecode-{repo_id}-pr-{pr_number}-{sha}` + restore-key 前缀匹配实现: 同一 PR 已跑过则后续 commit 默认跳过，且在跑之前先写入 "reserved" marker 并立即 save cache 防并发 double-run(action.yml:123-155)。动机写在输入参数文档里: 每个 commit 都重跑 "may increase false positives... as the AI analyzes the same code multiple times"(action.yml:37)。**反直觉**: 把"重复运行 LLM"本身当作误报来源建模。代价是真实的安全缺口(见弱点)。

### 6. slash command 版: 单 prompt 内复刻整个 pipeline

`.claude/commands/security-review.md` 把 Python pipeline 压成纯 prompt 编排(security-review.md:183-189): (1) 起一个 sub-task 做审计；(2) **对每条 finding 起并行 sub-task** 做 FP 过滤，prompt 注入完整的 FALSE POSITIVE FILTERING 段；(3) confidence < 8 的丢弃。即: 不写一行代码，用 subagent 隔离复现了 "审计角色与裁决角色分离 + per-finding 裁决" 的架构。这对 skill 形态的 harness(本仓库)是最直接可抄的形态。过滤 sub-task 还被告知 "Do not use the bash tool or write to any files... just read the code"(security-review.md:136)——裁决者是只读的。

### 7. 客制化 = 两个 append-only 文本文件接口

扩展不靠 fork prompt，靠两个注入点: `custom-security-scan-instructions`(追加到审计 prompt 的漏洞类别之后，prompts.py:37-39, docs/custom-security-scan-instructions.md:55-58)和 `false-positive-filtering-instructions`(**整体替换**默认过滤规则段，claude_api_client.py:239-243)。examples/ 给了云原生组织的真实示例: "我们有 k8s resource limits 所以排除所有 DOS"、"我们全用 Prisma ORM，SQL 注入只在 raw query 时有效"(examples/custom-false-positive-filtering.txt:2, 24)。注意两个接口语义不对称(append vs replace)，文档未强调这一点。

### 8. diff 预处理: 生成文件剔除 + 目录排除三处生效

diff 按 `diff --git` 切段后剔除含 `@generated` / protoc-gen-go / OpenAPI Generator 标记的段(github_action_audit.py:159-186)；`exclude-directories` 在 PR file 列表、diff 文本、最终 findings 三个环节分别过滤(github_action_audit.py:112, 180-182, 489-493)——最后一道是兜底: 即使 agent 自己跑去看了被排除目录，结论也会被丢弃。

### 哪些真正新颖/反直觉

- **新颖**: PRECEDENTS 判例库——把"什么不是漏洞"作为一等资产维护，且承认它需要按组织替换。
- **新颖**: PROMPT_TOO_LONG 降级不截断而是"去 diff 换 agentic 探索"。
- **反直觉**: 用正则过滤 LLM 的输出文本；把"重跑"建模为误报来源；过滤器 fail-open 而非 fail-closed。
- **反直觉**: 三层重复写同一批排除规则，承认单层 prompt 指令不可靠。

## 资产盘点

(以下数字来自 `find`/`wc`/`grep` 实测)

- Python: 25 文件 / 6594 行；其中测试 12 文件 / 4205 行 / 174 个 test 函数(`grep -c "def test_"`)。业务代码核心 5 个文件: github_action_audit.py(646 行)、findings_filter.py(344)、claude_api_client.py(377)、prompts.py(175)、json_parser.py(89)。
- 审计 prompt 模板: prompts.py 全文 7079 字节，模板正文约 135 行；slash command 版 190 行。
- 硬排除正则: 29 条 `re.compile`(7 组)+ 2 条结构规则(.md 文件、非 C/C++ 内存安全)。
- LLM judge 默认指令: 16 条 HARD EXCLUSIONS + 4 条 SIGNAL QUALITY + 17 条 PRECEDENTS(claude_api_client.py:243-284)。
- 漏洞类别: 审计 prompt 5 大类约 24 个子项(prompts.py:66-101)。
- Action 接口: 9 个 inputs / 2 个 outputs(action.yml:5-58)。
- eval 用例: **0 条标注用例**。evals/ 只有一个对任意 `owner/repo#pr` 的 runner(run_eval.py:53-57)，用 git worktree 隔离多次评测(eval_engine.py:212-284)。
- PR 评论脚本: 246 行 js + 570 行 bun 测试；自动给每条评论加 +1/-1 reaction 收集人工反馈信号(comment-pr-findings.js:57-71)。
- 默认模型: `claude-opus-4-1-20250805`(constants.py:8)；审计 subprocess 超时 20 分钟(constants.py:22)；judge 单次调用超时 180s、重试 3 次(constants.py:9-10)。
- 自食其力: `.github/workflows/sast.yml` 用本 action 审查本仓库 PR，且 `run-every-commit: true`。

## 与本仓库的关联点

(详细裁决留给后续 plan，这里只列借鉴价值与冲突点)

1. **PRECEDENTS 判例库可直接吸收进 `guard-secure`**。guard-secure 的 STRIDE 检查表(coding-skills/guard-secure/SKILL.md:58-124)全是"找什么"，"不报什么"只有一句原则("只报告有证据的风险"，SKILL.md:173)。这 17 条判例 + 16 条排除恰好补上"负样本知识"，可做成 `references/false-positive-precedents.md`，在输出 findings 前过一遍。**但有一处正面冲突需要裁决**: guard-secure 的 D 维度(DoS，SKILL.md:106-114)整个被该仓库列为硬排除。两者威胁模型不同(它面向"PR 阻断"场景，本仓库 guard-secure 还服务架构审查)；建议保留 D 维度但标注"PR 模式下降权"，而非盲吸收。
2. **slash command 的 subagent 过滤架构是 skill 形态下最可抄的设计**(security-review.md:183-189): 审计产出 findings 后，每条起一个**只读、无 bash** 的并行 subagent 做对抗裁决，confidence < 8 丢弃。guard-secure 可加一个可选 phase 实现同样的 precision 提升，零基础设施成本。这也与本仓库 dev-debug "子 agent 隔离分析"的既有模式同构。
3. **"确定性外壳"清单对本仓库 hooks/验证体系的启发**(How #4): schema 强制 + 多级 fallback 解析 + 错误也走结构化输出 + 重试/降级阶梯。本仓库 `scripts/hooks/` 的 stop check、`scripts/run-verify.sh` 若未来要消费 agent 产出的结构化结论(如 boundary manifest)，这套模式是现成参考。其中"降级时换策略(去 diff 改 agentic 探索)而非截断"的思路尤其值得记入 harness 设计原则。
4. **审计三阶段方法论可补强 guard-secure**: "先研究仓库既有安全模式 → 对比新代码是否偏离"(prompts.py:108-118)是 guard-secure 目前没有的步骤——它直接进 STRIDE 检查，缺"以仓库自身惯例为基线"的相对分析。
5. **反面教训(各标注证据)**:
   - **CI gate 形同虚设**: audit 脚本认真设计了 exit code 1(github_action_audit.py:637)，但 action.yml:242-245 用 `|| CLAUDECODE_EXIT_CODE=$?` 吞掉退出码、只发 warning，PR 不会变红。整条 pipeline 实际是 advisory 的。这印证本仓库"闭环验证"红线的价值: 声称是门禁就要验证它真能拦截。
   - **eval 框架没有 ground truth**: 只有 runner 没有标注集，意味着 29 条正则和 17 条判例的迭代依据不在仓库内(无法回归验证过滤规则改动不伤 recall)。本仓库若沉淀 FP 判例库，应同时沉淀触发它的标注样例。
   - **默认跳过 PR 后续 commit**(action.yml:104-106): 用安全覆盖率换误报率的取舍至少被文档化了；做类似取舍时要像它一样显式写出 warning。
   - 细节质量信号: 两套 confidence 标尺不一致(审计 0-1，judge 1-10)；slash command 编号重复(两个 "16."，security-review.md:154-155)；prompt 内 typo "deseralization"(prompts.py:91)；`EVAL_MODE` 环境变量被设置但无消费者(run_eval.py:83，grep 全仓库无读取点)。说明 prompt 文本缺 lint——本仓库 `verify_skills.py` 这类静态校验对 prompt 资产同样适用。
6. **客制化形态佐证**: "默认 prompt + 项目级 append 文件"(How #7)与本仓库 skill 的 `$ARGUMENTS` / `references/` 注入同源，可作为"不 fork、只注入"客制化原则的外部佐证；但其 append/replace 语义不对称是个可借鉴的反例——注入接口的覆盖语义必须显式声明。

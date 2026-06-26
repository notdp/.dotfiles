# Refs Update & Absorption Report — 2026-06-25

方法论：[`docs/software-engineering-research/refs-absorption-methodology.md`](./software-engineering-research/refs-absorption-methodology.md)
上一轮：[`docs/refs-update-absorption-2026-05-14.md`](./refs-update-absorption-2026-05-14.md)

## Scope

本轮覆盖两件事：

- **Part A — 新增 3 个 refs**：`leonxlnx/taste-skill`、`jakubkrehel/make-interfaces-feel-better`、`google-labs-code/design.md`（design.md 此前已 vendored，本轮补血缘与吸收裁决）。逐仓库详情见 `docs/refs-details/<owner>/<repo>.md`。
- **Part B — 既有 refs 增量更新**：距上次更新（2026-05-14）后，对 67 个 submodule 跑 triage，编程 `refs/` 中 37 个有指针落后、19 个已最新、6 个 fetch 超时；写作 `writing-refs/` 中 5 个有更新（写作池单列）。

裁决分层 L0-L5、classify 七类、decision = absorb/observe/reject/research-later，默认 L0-L2；L4 runtime / L5 global rule 候选需单独审批。**本报告只产出裁决与文档，不直接改 runtime skill**。

分析方式：两个 Workflow 并行 fan-out（Part A 8 agent 深读+盘点+裁决+综合；Part B 每个有更新 ref 一个 agent 分析 `old..new` 增量），主 agent 交叉核对后写本报告。

---

## Part A — 新增 3 个 refs 吸收裁决

### A.0 三者共同命题

三个 repo 同属"前端 UI / 设计系统"域，共享一个核心命题：**把主观"审美/品味/手感"降维成 coding agent 可确定性执行/校验的产物**。三种角度互补不冲突：

- `taste-skill` 走 **负向工程**（穷举并禁止 AI tells）；
- `make-interfaces-feel-better` 走 **魔法常量化**（scale=0.96 / bounce=0 这类精确阈值）；
- `design.md` 走 **token-graph 机器校验**（broken-ref / contrast / lint）。

本仓库视觉链已较完整（`fe-ui-design-system` → `fe-ui-design` → `fe-ui-critique` → `fe-ui-visual-iterate` → `fe-ui-lint-artifact` → `fe-audit` → `commands/design-md`），**多数能力已覆盖**。真正的增量集中在三处：design.md 的 token 语义校验层、taste/make 的"软措辞→硬约束"元方法、少量确定性 anti-tell 信号。

### A.1 跨三 repo 优先级排序（actionable backlog）

| # | 吸收项 | 来源 | classify | Level | 决策 |
|--:|---|---|---|:--:|---|
| 1 | **三份 refs-details 覆盖判断文档 + refs-summary 登记** | ALL | docs | L1 | ✅ 已完成本轮 |
| 2 | **`scripts/lint_design_md.py`**：DESIGN.md token-graph 语义 linter（broken-ref + section-order + orphaned-tokens + WCAG contrast + 解析引擎 + P0/P1/P2 分桶） | design.md | script | L3 | ✅ **已实现 2026-06-25** |
| 3 | **binary-ban + contextual-override 配对成 anti-tell 规则书写模式** 写进 `skill-patterns.md` | taste-skill | method | L2 | **absorb** |
| 4 | **diff 回归门禁**：`lint_design_md.py --diff old new`，warnings/errors 变多即 regression | design.md | script | L3 | **absorb**（依赖 #2） |
| 5 | **"规则补适用边界 + 违反后果机理"两栏** 固化为 `skill-authoring.md` 写作规范 | make-interfaces | docs | L2 | **absorb** |
| 6 | **未知内容消费行为表** 固化进 `commands/design-md.md` 边界段 | design.md | guardrail | L2 | **absorb** |
| 7 | **3 个真实 DESIGN.md 样例 + 9 fixtures** 登记为 few-shot 语料指针（只放路径，不 inline） | design.md | docs | L1 | **absorb** |
| 8 | **"规则带 production 证据来由"的演进治理纪律** 补进 `skill-authoring.md` | taste-skill | docs | L1 | **absorb**（与 #5 同批） |
| 9 | **3 条确定性 anti-tell 正则**（em-dash + transition:all + 米色/黄铜 hex 族）入 `scan_ui_artifact.py` | taste/make | script | L3 | **absorb**（候选级，不进 gating） |
| 10 | 禁用色族反重复轮换规则（防 agent 跨任务趋同） | taste-skill | method | L0 | research-later（需真实跨任务 memory 状态） |

### A.2 明确 reject / observe（避免误吸收）

- **reject**：taste-skill 的风格 skill 矩阵（brutalist/minimalist/soft）、imagegen/brandkit 图生成、gpt-taste 的 Python RNG 强制 variance；make-interfaces 新增独立 `fe-ui-micro-polish` skill；design.md 的 spec-config codegen 工具链。理由统一：要么是**把审美冻结成固定 hex/字体字典**（与本仓库"原则非配方"路线冲突），要么是**新增竞争入口违反"不扩 skill 数量"**，要么是引入外部构建依赖。
- **observe**：taste-skill `research/laziness` 的成因分析（实验引用 **[未验证]**，不当事实）；make-interfaces 的框架自适应理念、review 输出体裁契约（本仓库 `fe-ui-critique`/`readable-*` 已覆盖）、4 条微规则（concentric radius / optical -2px / tabular-nums / image outline，**需先与 `fe-ui-design/refs` 逐行核对是否已覆盖**）；design.md 的 export/DTCG 互转（强依赖项目技术栈，无高频需求）。

### A.3 Premise collapse 与风险（A 部分通用）

1. **主观审美硬规则化是头号风险**：make 的 scale=0.96/bounce=0/outline 纯黑白、taste 的禁用 hex 色族，本质是作者一家 taste 默认而非普适真理。凡涉审美常量，**只能"默认值 + 可被设计契约覆盖"**，绝不进 gating 硬拦截，否则与本仓库"装饰服务信息层级、按任务判断"原则冲突。
2. **确定性可硬化 vs 主观需留软的分界必须守住**：只有 WCAG 对比度数学、token 断引用、section 顺序、孤儿 token、em-dash/transition:all 这类客观可机械检测项才能硬化；层级/节奏/密度/品牌契合等连续光谱 taste 维度强行 0/1 会制造新死板。`binary-ban` 模式吸收时必须同时吸收 `contextual-override` 作为安全阀。
3. **lint 脚本三个未验证前置**（落地前必须先核）：① 本仓库 `fe-ui-design-system` 产出的 DESIGN.md 是否严格遵循 design.md 的 `{path.to.token}` 语法与 8-section 顺序（不一致会对自家产物大面积误报）；② orphaned-tokens 内置 MD3 家族白名单需可配置化；③ 只移植算法最小子集（80–120 行 Python），不全量搬 413 行 TS + remark + bun/turbo。
4. **门禁不僵死**：diff regression 与 lint exit-code 不直接接交付硬门；保留 `--baseline` 显式更新、WCAG 大字号阈值标注"人工复核"，findings 默认"候选"非"绝对正误"。
5. **Truth Directive**：`research/laziness` 引用的激励实验（"$200 tip +45%"）无可核验出处，止于 observe + [未验证]。
6. **许可与血缘**：design.md = Apache-2.0、taste-skill/make-interfaces = MIT；吸收 lint/anti-tell 算法为 clean-room 重写非搬运；详情文档已记 Source SHA（06d6028 / 3845620 / upstream 2a19f5d）。

> ⚠️ **血缘异常**：`refs/google-labs-code/design.md` 是 2026-05-06 直接 copy 的 **vendored 普通文件**（非 submodule，不在 `.gitmodules`），与本仓库 refs 约定不一致，无法自动判断 upstream 落后量。建议择机转 submodule 统一血缘。详见 `docs/refs-details/google-labs-code/design.md.md`。

---

## Part B — 既有 refs 增量更新吸收裁决

分析方式：两个 Workflow（主 37 + 补析 4）各为每个有更新 ref 派一个 agent，**只读 `old..new` git object 增量**（不动工作树），按吸收方法论裁决；末尾各做一次综合。共分析 **41 个**编程 ref。

### B.0 Triage 总览（2026-06-25）

- 更新方式：逐 submodule `git fetch`（只 fetch 不动指针）+ `git rev-list --count HEAD..origin/HEAD`，对超时项用 `gtimeout` 重试。
- 编程 `refs/`：**41 个有更新已分析**、19 个已最新、**2 个 fetch 仍超时延后**（`awslabs/agentcore-samples`、`nexu-io/open-design`，超大库，下轮再取）。
- 写作 `writing-refs/`：5 个有更新（`JimLiu/baoyu-skills`+26、`KKKKhazix/khazix-skills`+4、`helloianneo/ian-xiaohei-illustrations`+3、`nexu-io/html-anything`+1、`dontbesilent2025/dbskill`+1）。**写作池按 `writing-refs-summary.md` 规则单列，本轮不并入编程吸收**（需要时另起一轮）。

### B.1 本轮总裁决

- **absorb：3 项**（全部 L1-L2，全部落到既有 asset，不新增 skill）。
- **research-later：12 项**（不是待办，是"需先验证痛点/去重/实测才能决策"）。
- **observe / reject：其余 26 个 ref 整体无吸收价值**（见 B.3 全覆盖列表）。

本轮 upstream 更新的跨仓库主题趋势：① **plugin/marketplace 形态全面化**（过半仓库在重构分发 manifest 而非内容创新）；② **多 agent host 适配军备竞赛**（Antigravity/Kimi/Codex/Pi 等 target，本仓库锁定 kilo/opencode/droid/cc/codex 无需跟进）；③ **prompt 安全从"识别"走向"机械化执行"**（多家把"外部/子 agent 输出当不可信输入"提升为 always-on 守则）；④ **规则措辞形式化方法论**出现（superpowers / context-mode 用实测数据治理"同一约束该用哪种措辞"）；⑤ **带评估器的自治优化循环**兴起（scientific 的 arbor / context-engineering 的 research-to-skill loop）。

> ⚠️ **供应链信号 [未验证]**：`gsd-build/get-shit-done` 维护者自述仓库曾被攻陷并迁移到 fork `open-gsd`。其思路可借鉴，但不应据此对已 fetch 的历史 commit 下信任结论；建议复核该 ref 的跟踪源是否切换。

### B.2 有吸收价值的候选（按收敛主题分组）

本轮真正可吸收的内容高度收敛到三个主题，且**全部落到既有 asset，零新增 skill**。

#### 主题 ①：prompt 注入 / 不可信内容入 context（本轮最强信号，多仓库印证）

| 候选 | 来源 | classify | Level | 决策 | 落点 |
|---|---|---|:--:|---|---|
| **把"外部抓取/子 agent/API 内容当不可信数据"升级为消费侧 always-on 守则**（Waza #28 给出可直接中文改写的成文守则：embedded directive / role override / urgency / authority → 上报而非执行，user 当前 turn 是唯一指令源） | context-mode + waza + scientific-agent-skills | guardrail | L1 | ✅ **已实现 2026-06-25** | `coding-skills/web-read/SKILL.md` 新增"## 不可信输入（消费侧 prompt 注入防护）"小节 |
| 二阶 prompt 注入围栏（子 agent 输出拼回下游 prompt 前用不可逃逸 fence 包裹 + 落盘路径白名单正则）+ adversarial fixture 回归集（指令覆盖/边界伪造/零宽 unicode/heredoc） | claude-plugins-official + get-shit-done | guardrail | L2 | research-later | `guard-secure` prompt-injection 章节 / `harness-ops.md`（先确认 capsule 链是否已有等价防护） |
| 注入信任边界加固（只注入经 SHA 证明的可信内容、未覆盖证明的自由文本不入 context、注入内容视为 data 非 instruction、注入源路径 realpath 容器化防逃逸） | planning-with-files | guardrail | L2 | research-later | **memory-vault / capsule 注入安全边界**（同构，最值得在该程序里专门评估） |

> 这是本轮**最值得动手**的方向：本仓库 `web-read` 把抓取内容直接喂给 `assist-learn`/`think-research`/`think-survey`，全文无 untrusted/injection 处理（injection 只作为 `guard-secure` 的审计 taxonomy 存在，非消费侧守则）；而 capsule/memory 注入层也存在"磁盘/外部内容进 model context"的同构风险。

#### 主题 ②：secret 防泄漏（契合"防 PUBLIC 仓库泄露"诉求）

| 候选 | 来源 | classify | Level | 决策 | 落点 |
|---|---|---|:--:|---|---|
| secret-file 暂存/提交硬拦截（R15：阻断 `git add/commit` 暂存 `.env/*.pem/*.key/id_rsa/.ssh/.aws/credentials`，含 quote-aware shell lexer 防 `git -C`/subshell 绕过） | claude-code-harness | guardrail | L2 | research-later | 真实差距：本仓库 secret 入库只有 `guard-gitops/guard-secure/guard-diff-scan` 散文劝导，**无 PreToolUse 强制 hook**。需重写为 kilo/opencode `.mjs` 形态并先验证拦截点（CC-native 采纳原则） |
| secret 扫描正则 fail-open 教训（`[A-Za-z0-9]{n,}` 类正则漏掉含 `-`/`_` 的现代 key：`sk-proj-`/`sk-svcacct-`/`sk-admin-`、base64url body） | gstack | guardrail | L1 | observe | 下次碰 secret/凭证扫描逻辑时用作回归用例 |
| `sandbox.credentials`（CC 原生从沙箱子进程剥离密钥） | shanraisshan/claude-code-best-practice | docs | L2 | research-later | 仅平台事实，无可迁移代码；kilo/opencode 无对等，采纳须差异化记录 |

#### 主题 ③：skill / harness 治理（契合 harness-governance 与 dev-long-run 程序）

| 候选 | 来源 | classify | Level | 决策 | 落点 |
|---|---|---|:--:|---|---|
| **"Match the Form to the Failure" 规则措辞形式选择方法论**（discipline 失败→禁止式+rationalization 表；output 形状错→正向配方；漏字段→模板 REQUIRED 槽位；条件行为→挂可观测谓词的条件式 + 先 micro-test 措辞再跑全量、variance 是指标） | obra/superpowers | method | L1 | ✅ **已实现 2026-06-25** | `coding-skills/assist-learn/references/learning-loop.md` 新增"## 规则措辞形式选择"一节 |
| **eval-first skill 覆盖地基**（每个 skill 至少一个零 LLM、每 PR 阻断的结构合规检查：frontmatter 必填 / catalog↔磁盘双向一致 / 空·重复 description） | gstack | guardrail | L1 | research-later | 真实差距：67+ coding-skills + writing-skills **零结构性自动校验**，全靠人肉。需先定 test runner（Python 既有 hooklib 或 node） |
| frontier-model skill 现代化方法论（PROTOCOL/JUDGMENT 二分 + orchestrator-model floor 论证 + 仅对 conditional 内容抽 reference + fresh-subagent eval） | EveryInc/compound-engineering | method | L2 | research-later | `skill-authoring.md` 增"大改 orchestration skill 的复核序列"，需与 `verify_skills.py` 门禁去重 |
| harness 四类面 surface 分类法（Locked / Editable / Append-only / Human-controlled） | context-engineering + designer-skills 系 | method | L2 | research-later | `harness-ops.md` / `dev-long-run` 循环边界检查项，需先与现有 Boundary facts 去重 |
| arbor HTR 自治优化方法论（评估器门控 + dev/test held-out merge gate + 失败即约束 + 防过拟合反馈信号） | K-Dense/scientific-agent-skills | method | L2 | research-later | 填补"带 evaluator 迭代优化"空缺（契合 capsule-routing F1 / governance 近邻区分度调优），需 `think-scope` 先确认高频场景 |

#### 其它（散落，单仓库）

| 候选 | 来源 | classify | Level | 决策 | 备注 |
|---|---|---|:--:|---|---|
| guard-secure 补 OWASP LLM Top 10 应用安全审查面（模型输出当不可信输入 / prompt injection / excessive agency / RAG 租户隔离 / token 递归上界） | addyosmani/agent-skills | docs | L2 | **absorb（rank 3）** | `guard-secure` + `guard-threat-model` 信任边界清单，中文改写不照搬 |
| 完成声明 × diff 残留物在 Stop 边界交叉拦截（claim done/fixed 命中且改动仍有 TODO/it.skip/未实现 throw 即提示） | Yeachan-Heo/oh-my-claudecode | guardrail | L1 | research-later | 本仓库已有 `scan_diff_residue.py` + `stop_check.py` 两半零件未耦合；需中文本地化 + 确认真实漏检 |
| append-only run-ledger + stall 检测（per-agent JSONL + 跨 agent 单调 tick + 读语义信号判 stall，而非 progress.md mtime） | planning-with-files | method | L2 | research-later | `dev-long-run` 现仅单态 `state.json`，无事件流/stall 信号 |
| 跨 LLM 家族 prompt-microcopy 经验规则（肯定式 deny 优于裸 NOT、大写 header 单 token、emoji bullet 跨家不稳） | mksglu/context-mode | method | L1 | research-later | 证据是小样本 A/B，须先在本仓库 kilo/opencode/droid 实测再落 |
| canonical 注册表 JSON + 无依赖 bash drift-guard / 跨 agent turn-phase·busy 检测 | agency-agents + hive | method | L2 | research-later | 需先确认本仓库确有"多处手维护 target 列表漂移"/调度痛点，否则增维护面 |

### B.3 无吸收价值列表（observe/reject — 证明已诚实全覆盖 26 个 ref）

> 列出以证明覆盖的是全部 41 个而非只挑亮点。括号内为一句话原因。已单列到 B.2 的 research-later 候选不在此重复。

- `millionco/react-doctor`（553 commits 几乎全是产品自身演进；product-thinking/find-similar-functions 内核已被 guard-close/think-scope/dev-simplify 覆盖且绑定 telemetry/truffler）
- `anthropics/claude-plugins-official`（95%+ 第三方 plugin submodule bump；code-modernization 是 legacy 迁移窄域、project-artifact 强依赖 CC-only Artifact 运行时）
- `affaan-m/everything-claude-code`（语言技能包/i18n/Rust 运行时/域专属；config-gc/IDD/orch-* 方法论被 skill-maintenance/think-scope/guard-close/memory-vault 更成熟覆盖）
- `gsd-build/get-shit-done`（GSD 单 runtime 内部工程；且维护者自述被攻陷，建议切 fork）
- `nyldn/claude-octopus`（council/事件流/provider 探针与 think-ideate/think-compare/dev-complete 重叠或绑定 octopus 计费基建）
- `Yeachan-Heo/oh-my-claudecode`（绝大多数 OMC runtime/CI 内部工程；ultragoal/risk-assess 被 dev-long-run/memory-vault/boundary_gate 覆盖）
- `pbakaus/impeccable`（前端设计 detector/浏览器运行时；hook 豁免治理被 hook capsule/guard-diff-scan/fe-ui-lint-artifact 同源覆盖）
- `github/awesome-copilot`（harness-engineering/postmortem/tiny-stepping 与 agent-harness-creator/assist-retrospect/dev-tdd 重叠且本仓库更成熟）
- `ChromeDevTools/chrome-devtools-mcp`（浏览器自动化 MCP 产品自身工具扩展，runtime 特定不同层）
- `tw93/Waza`（Python 迁移/分发/statusline；Triage/Testability Seam 与 think-scope/guard-review 重叠——untrusted-data 守则已并入 absorb）
- `K-Dense-AI/scientific-agent-skills`（领域科学计算 skill + 多 host 兼容；arbor 已单列 research-later）
- `EveryInc/compound-engineering-plugin`（内部重构/分发治理/docs；frontier-model 方法论已单列）
- `msitarzewski/agency-agents`（role-persona 内容灌注与 workflow-skill 定位正交；注册表 drift-guard 已单列）
- `vercel-labs/skills`（vercel skills 分发 CLI 自身实现，本仓库走各 agent 原生注入）
- `tirth8205/code-review-graph`（CRG Python MCP 工具发版工程；stdin-drain 是纯 shell hook 特有，本仓库 Python hook 不适用）
- `notdp/hive`（hive runtime 产品演进；duo/squad 与 dev-complete/dev-long-run 重叠——turn-phase 检测已并入）
- `vercel-labs/agent-skills`（Vercel 平台特定成本/性能审计，绑定 vercel CLI metrics）
- `voltagent/awesome-agent-skills`（纯 awesome-list README 目录维护，仓库内无 SKILL.md/源码）
- `google-labs-code/stitch-skills`（Google Stitch 设计-到-代码 MCP 产品自身 skill 包，与 think/dev/guard/fe-ui 池不重叠）
- `Shubhamsaboo/awesome-llm-apps`（LLM 示例应用目录，增量是 generative-ui/HN agent/保险理赔演示代码，无 harness 资产）
- `nextlevelbuilder/ui-ux-pro-max-skill`（UI/UX 资产仓自身安全加固/CI；XSS 转义/execFileSync 是 guard-secure/dev-guideLines 已覆盖的通用纪律）
- `vercel-labs/agent-browser`（agent-browser Rust CLI 自身 runtime，本仓库已作 vendored 只读 skill 接入）
- `Owl-Listener/designer-skills`（设计/UX marketplace 资产；visual-critique 与 fe-ui-* 重叠——harness 四类面已单列）
- `awslabs/agent-plugins`（AWS 领域知识 plugin 扩充 + CI 微调，sagemaker 路由是领域专属）
- `muratcankoylan/Agent-Skills-for-Context-Engineering`（researcher 自治研究运行时强绑该项目 corpus；mechanism registry 与 memory/guard-verify 重复——四类面已单列）
- `tanweai/pua`（PUA hook 毒打+奖励 persona 系统，与 think-unstuck/think-ideate/assist-learn 等价，hook 计数栈与本仓库 prompt 驱动不同）
- `notdp/.dotfiles`（个人环境管理 stow/tmux/statusline + 私有 skill lockfile 引用）
- `anthropics/skills`（95% 是 claude-api 平台/模型参考文档；frontend-design 内核被 fe-ui-*/write-* 覆盖）
- `voltagent/awesome-claude-code-subagents`（纯文档治理 + 一次 CC 专属 opus→inherit frontmatter 批改）
- `antfu/skills`（技术栈 reference pack 刷新 + UnoCSS/Vue 专属 antfu-design；anti-slop 被 fe-ui-*/slop_lint 覆盖）
- `lijigang/ljg-skills`（个人中文知识卡生成 skill，绑定 marswave/LISTENHUB 个人 provider）
- `frankbria/ralph-claude-code`（design-only ADR：把单 agent 改造成 provider-agnostic——本仓库本就是其目标态；capability matrix 5/7 重叠）
- `addyosmani/web-quality-skills`（仅 1 行 marketplace.json source 改本地路径，与跨 agent harness 无关）
- `mukul975/Anthropic-Cybersecurity-Skills`（安全 skill 内容库扩张 55 个 + MITRE 映射元数据；auto-index 工作流被本仓库 catalog.json + verify_skills.py 更强覆盖；两个 agentic-AI 安全 skill 域相邻仅 observe）
- `Chachamaru127/claude-code-harness`（CCH 自身 Go-binary + hooks.json 发布工程，与 kilo/opencode 配置型 harness 异构；R15 secret 拦截已单列 research-later）
- `garrytan/gstack`（gstack 自有领域 iOS device-farm/gbrowser/diagram/gbrain；AUQ prose 降级与 CC hook updatedInput 是宿主/CC 专属违反 CC-native 纪律；eval-first 覆盖地基已单列）

### B.4 吸收纪律与风险（Part B 通用）

1. **不扩 skill 数量红线**：多个 research-later（arbor HTR、frontier-model 现代化、harness 四类面）会诱导新建 skill。本仓库 memory 已记"技能多→渐进暴露假设 misframed，真问题是近邻区分度+发散缺口"——优先并入既有 asset（`assist-learn`/`guard-secure`/`skill-authoring`/`dev-long-run`/`web-read`），除非 `think-scope` 确认确有高频独立场景。
2. **premise-collapse 警示**：多数 research-later 的前提是"本仓库存在某痛点"但未经核实（注册表 drift、capsule 链无等价防护、声称完成留 stub 的漏检）。**不验证痛点就吸收 = 制造无人维护的死文档**，务必先查证。
3. **不照搬某 agent 特定功能**：本轮大量内容是 CC-only（Artifact 工具 / `sandbox.credentials` / `model:inherit` frontmatter / plugin marketplace）或单一 runtime（GSD CJS / octopus 计费 / hive tmux / CRG SQLite 图）。按 `cc-native-feature-adoption-policy`，引入前必须验证 kilo/opencode/droid 能否跟进，不能则差异化并显式记录不可用。
4. **上下文膨胀**：OWASP LLM Top10、prompt-microcopy、harness 四类面若全文照搬会显著增加常驻 context。落地按"按需阅读"——主文件只留一句话指针，细节下沉 `references/`；优先"折叠进已有 principle"而非 append（借鉴 waza anti-accretion）。
5. **absorb vs research-later 的边界**：本轮仅 3 项 absorb，其余 12 项 research-later **不是待办清单，是"需先调研/验证/去重才能决策"**；不应在未确认的情况下把推测当既定吸收。

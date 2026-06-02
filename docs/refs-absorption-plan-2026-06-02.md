# Refs 吸收/改造计划 (2026-06-02)

> 基于对 6 个外部 skill 开源项目 digest 的分析，结合本仓库 (`~/.dotfiles`) 现状核对后产出的吸收裁决与 roadmap。
> 方法论 SSOT：`docs/software-engineering-research/refs-absorption-methodology.md`（沿用其 L0-L5 吸收级别、Decision Matrix、Risk Gates）。
> 本文档只是**计划**，不改动任何 runtime（AGENTS.md / skill / command / hook）。

## 概览

### 来源项目（6 个）

| 简称 | repo | 类型 | 核心可吸收面 |
|---|---|---|---|
| SuperClaude | SuperClaude-Org/SuperClaude_Framework | 行为纪律框架 | reflexion 教训机器匹配、置信度硬停门、六段 mistake 模板、Stop/PostToolUse prompt hook |
| MiniMax | MiniMax-AI/skills | 能力型 skill 库 | TRIGGER/DO NOT TRIGGER 正反簇、对抗式 QA、AI slop 负向门、零依赖校验、high-confidence-only 扫描 |
| planning-files | OthmanAdi/planning-with-files | 文件即记忆单 skill | hook 强制注入计划、SHA-256 attestation、fail-open + 可移植 mtime 链、parity 数据表、=== 分隔符教训 |
| awesome-composio | ComposioHQ/awesome-claude-skills | 目录 + exemplar | 大脚本黑盒化、禁尖括号/hyphen-case、MCP 工具发现替代硬编码 schema、否定式护栏 command |
| antfu | antfu/skills | 知识 skill 生成流水线 | refs 血缘 SHA+日期、声明清单对账、主动性分级标注、生成器 SOP |
| voltagent | voltagent/awesome-agent-skills | 策展索引 | body 行数上限、绝对路径扫描、tools 通配黑名单、description what+when 浓缩、跨工具路径表 |

### 本仓库现状核对（事实，避免重复造轮子）

已经核对到本仓库**已有**以下能力，多个候选因此降级或拒绝：

- `scripts/hooks/context_capsule.py`：已在 `UserPromptSubmit` + `PostToolUse(ApplyPatch|Create|Edit)` 做关键词路由的 capsule 注入（7 个 capsule，含 `boundary-decision.md`、`operational-task.md`），有 2200 字符预算上限。**已覆盖** SuperClaude 的 PostToolUse prompt hook 与 planning-files 的"每轮注入关键约束"主体思路。
- `scripts/hooks/stop_check.py`：已在 `Stop` 事件做 validation evidence / 视觉证据 / boundary manifest 三类收尾自检。**已覆盖** SuperClaude 的 Stop+type:prompt 收尾自检与 guard-close 语义 hook 化。
- `scripts/hooks/boundary_gate.py` + `command_guard.py`：已有 `PreToolUse` 边界门与命令护栏。
- `scripts/verify_skills.py`：已有触发前缀、workflow quality 行阈值、methodology why、vague conditional、reference 存在性、可执行位、boundary reference、routing cases、deprecated concepts、agent/command/plugin manifest 校验。零第三方依赖（仅标准库）。**已覆盖** MiniMax 的零依赖取舍、awesome-composio 的部分确定性校验。
- `skills/assist-learn`：已有 frontmatter 检索字段 + `learnings_search.py` opt-in 回查 + `templates/learning-note.md`。**部分覆盖** SuperClaude reflexion 的"可检索教训"，但缺机器签名匹配。
- `skills/assist-retrospect`：已有苏格拉底式多轮复盘 + 技术防线，但**无固定六段 mistake 模板**。
- `docs/refs-micro-index.md`（registry）+ `docs/refs-summary.md` + `docs/refs-details/`：已有 refs 索引与 micro-ref status 词表，但 refs-details **未记录对应 upstream submodule SHA + 分析日期**。
- `.gitmodules`：refs 是 submodule，但本仓库**无 meta.ts 式声明清单**，skill 注册靠 `skills/catalog.json`。
- `scripts/tests/`：已有 30+ 测试，含 `test_skills_registry.py`，但**无 skill body 行数上限 / 绝对路径 / tools 通配校验**，也无"catalog vs 目录对账"测试。

---

## 候选点汇总表

| # | 主题 | 来源 | 动作 | 落点 | 优先级 | Level | 理由（证据） | 风险 |
|---|---|---|---|---|---|---|---|---|
| A1 | skill body 行数上限校验 | voltagent | add | `scripts/verify_skills.py` | P1 | L3 | 防正文膨胀挤占上下文，确定性可扫描，与渐进式披露取向一致（README:1750-1765 <500 行）。本仓库现仅有 workflow-quality 行阈值(80)，无上限 | 阈值需按现有最长 skill 校准，过严误伤；先统计再设阈值 |
| A2 | 绝对机器路径扫描 | voltagent | add | `scripts/verify_skills.py` | P1 | L3 | 与 AGENTS.md "不硬编码机器路径"、跨 agent 兼容同向，正则可确定匹配 | 需白名单 `docs/refs-details/` 等合法引用本机路径文档；本计划文件本身含 `/Users/` |
| A3 | frontmatter tools 通配黑名单 | voltagent | add | `scripts/verify_skills.py` | P2 | L3 | 最小权限原则可机器强制，符合 fail-fast/显式优于隐式（README tools:['*'] 禁项） | 需先盘点本仓库 skill 是否声明 tools 字段；多数 SKILL.md 无 tools，落地价值待确认 |
| A4 | description 禁尖括号 + name 严格 hyphen-case | awesome-composio | improve | `scripts/verify_skills.py` | P2 | L3 | 廉价高确定性门禁，填补现有空白（quick_validate.py） | 本仓库已有触发前缀+catalog name 校验，需比对是否已隐式覆盖，避免重复 |
| A5 | 教训机器签名匹配（数字归一化 + JSONL append + 命中复用） | SuperClaude | improve | `skills/assist-learn` + `scripts/` | P2 | L3 | 现有 `learnings_search.py` 是关键词搜，reflexion 做到 0-token 签名复用工程化更高（reflexion.py:130-275） | 需落地存储+查找脚本，签名过简易误命中；与现有 frontmatter 检索去重 |
| A6 | 六段式 mistake 模板（What/RootCause/WhyMissed/Fix/Prevention/Lesson） | SuperClaude | improve | `skills/assist-retrospect/templates/` | P1 | L4 | 复盘产物标准化，结构清晰（reflexion.py:277-347）。本仓库 assist-retrospect 现无固定模板 | 模板化可能过重；需与现有苏格拉底式流程兼容，作为可选产出 |
| A7 | TRIGGER / DO NOT TRIGGER 正反短语簇 | MiniMax | improve | `docs/.../skill-authoring.md` §1 | P1 | L2 | 降低通用对话型误触发/漏触发，比纯前缀更接地气（minimax-pdf/SKILL.md:5-11） | 塞太多膨胀 description；需与现有触发前缀硬约束对齐，作为高误触发 skill 的可选增强 |
| A8 | 对抗式 QA 体裁（假设有 bug + grep 探针 + 禁零问题收尾） | MiniMax | improve | `skills/guard-verify` 或 `dev-tdd` 正文 | P2 | L2/L4 | 把抽象自检变可执行闭环，与"闭环验证"红线同向（ppt-orchestra:120-148） | 探针领域特定，需抽象成通用模式而非硬塞 grep |
| A9 | AI slop 负向门清单（NEVER 级硬禁） | MiniMax | improve | `skills/fe-ui-lint-artifact` + `scripts/scan_ui_artifact.py` | P2 | L2/L3 | 把"标题下划线/居中正文/默认蓝"列成可检查项（ppt-orchestra:74-86） | 审美有主观性/时效性；本仓库 fe-ui 已有 slop 检查，需去重 |
| A10 | hook fail-open + 可移植 mtime/工具解析链 | planning-files | improve | `docs/.../` hook 健壮性约定 + 现有 hooks | P1 | L2 | resolve-plan-dir.sh 的 stat/date/python/perl 链可抄进 hook 约定，避免 BSD/macOS/Alpine 行为不一致 | fail-open 不适用安全/校验类 hook（应 fail-closed），需按 hook 类别分类套用 |
| A11 | refs-details 血缘记录（submodule SHA + 分析日期） | antfu | add | `docs/refs-details/` + `refs-micro-index.md` | P1 | L1 | refs 分析结论现无法判断是否对应当前 upstream 版本；antfu 用 SHA+日期把陈旧工程化（GENERATION.md/SYNC.md） | 低；维护成本是每次分析多写一行；需先确认现有 refs-summary 是否已部分记录 |
| A12 | catalog vs 目录对账脚本（孤儿目录/未注册 skill/漂移报告） | antfu | add | `scripts/` + `scripts/tests/` | P1 | L3 | 本仓库靠 catalog.json 注册，[推断] 缺"目录 vs 清单"反向对账；skill 增长后熵增（antfu cleanup） | reconcile 必须 dry-run/报告模式，禁自动删；需确认 test_skills_registry 是否已部分覆盖 |
| A13 | === 分隔符避开 frontmatter 保留符号 | planning-files | add | `docs/.../skill-authoring.md` | P2 | L2 | planning-files v2.38.1 实证：`---` 注入会截断 description；几乎零风险的具体教训 | 仅当本仓库存在向 SKILL.md/capsule 注入分隔符的场景才相关 |
| A14 | 大脚本黑盒调用（先 --help、不读源码、理由是 context 预算） | awesome-composio | add | `docs/.../skill-authoring.md` §8 | P2 | L2 | webapp-testing 把"禁读自己 bundle 源码、当 CLI 调"写成硬约束，对有大脚本 skill 场景有价值 | 本仓部分 skill 依赖读脚本做环境适配，需限定"大脚本/纯执行类"，避免与可 review 性冲突 |
| A15 | 外部依赖/副作用 skill 标注主动性等级（AUTO/需授权/仅显式） | antfu | improve | 相关 `guard-*` / 高风险 skill description | P2 | L2 | vueuse Invocation 列把主动性编码进数据，与本仓"被动 vs 主动"能动性表同构，减少越权/过度保守 | 属描述层标注不改行为；需避免与 guard-gitops 触发约定语义冲突 |
| A16 | 置信度硬停门语义（不引入加权评分系统） | SuperClaude | improve | `skills/think-scope` / `think-refine` 正文 | P2 | L2 | 真正有价值的是"前提不足/置信不够→硬停问问题"语义，非加权评分本身（confidence.py） | 加权评分依赖 LLM 老实填 flag，把关弱，不整体照搬；本仓已有 scope/refine 体系 |
| A17 | 高风险删除/大改可审计文档（commit/行数/原因） | SuperClaude | add | `docs/` 模板（按需，非常驻） | P2 | L1 | 呼应证据驱动与 Boundary decisions 纪律（DELETION_RATIONALE.md） | 仅适用大改动；日常小改写此文档成本过高，不要默认要求 |
| A18 | MCP 工具发现替代硬编码 schema 范式 | awesome-composio | add | `docs/.../skill-patterns.md` | P2 | L1 | 对抗 skill 随上游 API 漂移腐烂，适用涉外部工具/MCP 的 skill（composio-skills） | 运行时发现增不确定性，与本仓事实驱动/显式化有张力，需配 known-pitfalls 约束 |
| A18b | 否定式护栏 install/config command 样例 | awesome-composio | add | `docs/.../skill-patterns.md` | P2 | L1 | setup.md 用 Do NOT search/multi-ask + 时限收紧发散配置流（connect-apps-plugin） | "Ignore pretrained data"类需改写以符合事实纪律，不能照搬 |
| A19 | parity 数据表 + test_*_parity 治理多副本一致性 | planning-files | reject(P3) | — | P3 | — | 本仓库无 19 文件级多 IDE 副本；catalog.json 已是单一注册源，无 parity 漂移问题 | 投入产出比低，无对应回归 |
| A20 | SHA-256 attestation 防 plan 注入篡改 | planning-files | reject/observe | — | P3 | L0 | 本仓库 capsule 是仓库内静态文件、不接受 plan 文件按指针动态注入，威胁模型不成立 | 增用户 re-attest 步骤，对当前场景过重 |
| A21 | 8-agent 跨工具路径 cheat sheet | voltagent | observe | `docs/`（可选） | P3 | L1 | 支撑跨 agent 兼容声明的落地速查，但上游路径会演进失效 | 需标注抓取日期 + [未验证]；维护成本随上游漂移 |
| A22 | high-confidence-only secret 扫描策略 | MiniMax | observe | — | P3 | L0 | 本仓库 verify_skills.py 的 RISK_PATTERNS 已是 warning（不阻断），思路已对齐 | 降覆盖面可能漏真 secret，需人工兜底，不简单照搬 |
| A23 | Context Engineering 路由盲区自检 | voltagent | observe | `docs/`（启发） | P3 | L0 | 外部分类视角可暴露 think-/dev-/guard- 路由盲区，仅作启发 | 不照搬外部分类法改路由 |

---

## 新增 (add)

### P1

- **A11 refs-details 血缘记录 (L1, antfu)**
  落点：`docs/refs-details/<owner>/<repo>.md` 文件头补一行 `Source SHA / 分析日期`，并在 `docs/refs-micro-index.md` 或 `refs-summary.md` 登记。
  做法：分析每个 ref 时记录当时 `git submodule status` 的 SHA 与日期；后续 refs 更新 runbook（方法论 §Batch Refs Update Runbook 已要求记录 old/new HEAD）天然能产出该信息，只是落到 details 文档。
  理由（事实）：本仓库 refs 是 submodule，分析结论目前无法判断对应哪个 upstream commit。antfu 用 GENERATION.md/SYNC.md 把陈旧度变成可观测状态。
  风险：低。先确认 `refs-summary.md` 是否已部分记录，避免重复字段。

- **A12 catalog vs 目录对账脚本 (L3, antfu)**
  落点：新增 `scripts/scan_skill_registry_drift.py`（dry-run/报告模式）+ `scripts/tests/test_*`，或扩展现有 `test_skills_registry.py`。
  做法：列出 `skills/` 下有 `SKILL.md` 的目录 vs `catalog.json` 注册项，报告"目录存在但未注册"和"注册但目录缺失"。只报告不删除。
  理由（[推断]）：`verify_skills.py:load_catalog` 校验"catalog 项 → 目录存在"（`MISSING PATH`），但**未反向校验"目录 → 是否在 catalog"**，孤儿目录会静默漏检。
  风险：中。先跑一次确认现状是否已有孤儿；reconcile 永远 dry-run。

### P2

- **A4 description 禁尖括号 + name hyphen-case (L3, awesome-composio)**：先 grep 现有 description 是否含 `<>`，若有合法用途（如 `<owner>/<repo>` 占位）需先排除再决定是否开启。
- **A13 === 分隔符教训 (L2, planning-files)**：在 `skill-authoring.md` 注入/分隔符相关处补一条 convention（仅当存在向 SKILL.md 动态注入文本的路径才相关）。
- **A14 大脚本黑盒调用约定 (L2, awesome-composio)**：在 `skill-authoring.md` §8 Tool-backed skill 补"大脚本/纯执行类默认黑盒、先 --help、理由 context 预算"，限定范围避免与可 review 性冲突。
- **A17 高风险删除可审计文档模板 (L1, SuperClaude)**：作为按需模板，不进 AGENTS.md、不默认要求。
- **A18 / A18b skill-patterns 范式条目 (L1, awesome-composio)**：MCP 工具发现 + 否定式护栏 command，纯文档参考。

### P3（observe，不进 runtime）

- **A21 跨工具路径 cheat sheet**：可选写入 `docs/`，必须标抓取日期 + `[未验证]`。

---

## 改善 (improve)

### P1

- **A6 六段式 mistake 模板 (L4, SuperClaude)**
  落点：`skills/assist-retrospect/templates/mistake-note.md`（新模板文件），正文引用为**可选产出**。
  做法：固定六段 What Happened / Root Cause / Why Missed / Fix Applied / Prevention Checklist / Lesson Learned。
  理由（证据）：`assist-retrospect` 现为多轮苏格拉底式，无结构化落盘模板；六段模板让复盘产物可扫描、可复用（reflexion.py:277-347）。
  风险：模板化过重。作为可选，不取代苏格拉底式对话流程；与 `assist-learn` 的 learning-note 模板划清边界（一个记教训复盘，一个记可复用模式）。
  走 `/dev-tdd`：新增模板属文档/样式变更，可豁免 TDD；若动 skill 正文路由逻辑则需测试。

- **A7 TRIGGER / DO NOT TRIGGER 正反短语簇 (L2, MiniMax)**
  落点：`docs/software-engineering-research/skill-authoring.md` §1.3 之后，作为"高误触发 skill 的可选增强"。
  做法：允许在 description 能力段后或 SKILL.md 正文补一组"会触发 / 不会触发"的用户原话样例，与现有触发前缀硬约束共存（前缀仍是必填）。
  理由（证据）：现有前缀+场景化约束解决了"措辞结构"，但对通用对话型 skill 的误触发边界仍靠人工 review。正反簇把边界显式化（minimax-pdf/SKILL.md:5-11）。
  风险：description 膨胀。约束：正反簇放正文不放 frontmatter（避免 description 超长）；与 `1.3 场景化 vs 用户行为化` 对齐，不写"用户要求 X"。

- **A10 hook fail-open + 可移植解析链约定 (L2, planning-files)**
  落点：`docs/software-engineering-research/` 新增或现有 hook 健壮性约定文档；现有 hooks 已基本满足（`context_capsule.py`/`stop_check.py` 异常时返回 `suppressOutput`，未崩 loop），主要是把约定写下来 + 标注"安全/校验类 hook 应 fail-closed，注入/提示类 hook 应 fail-open"。
  理由（事实）：本仓库 hook 已 fail-open（如 `load_hook_input` 吞 JSONDecodeError），但**该约定未成文**，新 hook 作者可能写出会崩 loop 的实现。
  风险：fail-open 不能套到 `boundary_gate.py`/`command_guard.py` 这类应阻断的门；需按 hook 类别分别声明。

### P2

- **A5 教训机器签名匹配 (L3, SuperClaude)**：在 `learnings_search.py` 之上增 JSONL 签名 append + 数字归一化匹配。先评估"现有 frontmatter 关键词搜是否已够用"，避免过度工程。
- **A8 对抗式 QA 体裁 (L2/L4, MiniMax)**：在 `guard-verify` 或 `dev-tdd` 正文补"假设产物有缺陷 → 主动找证据反驳完成声明"的通用语气，不硬塞领域 grep。
- **A9 AI slop 负向门 (L2/L3, MiniMax)**：先 Read `fe-ui-lint-artifact` + `scan_ui_artifact.py` 现状去重，再决定补哪些 NEVER 项；按 `skill-authoring.md` §正向规则，硬禁仅限可观察质量问题。
- **A15 主动性等级标注 (L2, antfu)**：在高风险 skill description 能力段标注默认主动性，与能动性表对齐。
- **A16 置信度硬停门语义 (L2, SuperClaude)**：在 `think-scope`/`think-refine` 强化"前提/上下文不足时硬停问人"，**不引入加权评分**。

### P2（确定性校验，待统计后定阈值）

- **A1 body 行数上限 (L3, voltagent)**：先 `wc -l` 统计现有 SKILL.md 分布，再设阈值（[推断] 现有领域分册型 skill 入口可能接近上限，需含 refs 拆分豁免）。
- **A2 绝对路径扫描 (L3, voltagent)**：需白名单 `docs/refs-details/`、本计划文件等合法本机路径文档。
- **A3 tools 通配黑名单 (L3, voltagent)**：先确认 SKILL.md frontmatter 是否普遍声明 tools 字段，无则价值有限。

---

## 去掉 / 规避 (remove / avoid)

这些是对方项目暴露出的、本仓库**应避免引入或应保持现状**的模式。

| 模式 | 来源 | 为什么规避 |
|---|---|---|
| 加权置信度评分系统（25/25/20/15/15 累加 0-1 分） | SuperClaude | 依赖 LLM 老实填 context flag，把关强度有限，是"看起来量化"的伪确定性。本仓库已有 scope/verify 体系，只吸收硬停门语义（A16），不引入评分器 |
| 每次编辑都注入 prompt 的 PostToolUse 自检 hook（无范围限定） | SuperClaude | 本仓库 `context_capsule.py` 已做范围限定的 PostToolUse 注入；无差别注入会吃 token、打断节奏。不新增无差别编辑校验 hook |
| Token Efficiency 符号语言（→⇒∴∵ + 缩写表压缩 30-50%） | SuperClaude | 与 AGENTS.md "可读性优先、显式优于隐式、默认 ASCII"冲突；符号压缩降低可 review 性 |
| SHA-256 plan attestation 防注入（A20） | planning-files | 本仓库 capsule 是仓库内静态文件，不按指针动态注入 plan，威胁模型不成立；增 re-attest 步骤对当前场景过重 |
| 19 文件 parity 同步 + bump-version 数据表（A19） | planning-files | 本仓库无多 IDE 大规模副本，catalog.json 已是单一注册源，无 parity 漂移回归 |
| "Ignore pretrained data" 类强制护栏原话 | awesome-composio | 与 Truth Directive 事实纪律冲突；吸收"否定式护栏 + 时限"结构（A18b）时必须改写措辞 |
| 把删除决策做成**常驻**审计文档要求 | SuperClaude | DELETION_RATIONALE 仅适合大改动；日常小改强制写此文档成本过高。只作按需模板（A17），不进 AGENTS.md |
| high-confidence-only 自动门**降低**现有覆盖面 | MiniMax | 本仓库 RISK_PATTERNS 已是 warning（不阻断），思路已对齐；不应为"降噪"主动减少已有扫描覆盖 |
| 把 refs/ 当待复制代码库批量蒸馏新 skill | antfu | 与方法论"吸收目标是更稳更可验证，不是扩大 skill 数量"冲突；本仓库已有 52 skill，优先下沉/合并而非新增 |

---

## 分阶段 Roadmap

吸收顺序按 **风险低→高、L 级低→高、依赖关系** 排列。每阶段独立可验证，验证命令：
`python3 scripts/verify_skills.py` + `python3 -m unittest discover scripts/tests` + `python3 scripts/scan_diff_residue.py`。

### Phase 0 — 纯文档沉淀（L1-L2，零 runtime 风险）

先把"教训型"吸收写进 docs，不碰 skill/hook/脚本逻辑。

1. A11 refs-details 血缘记录格式（先在 `refs-absorption-methodology.md` 补字段约定）
2. A13 === 分隔符教训 → `skill-authoring.md`
3. A14 大脚本黑盒调用约定 → `skill-authoring.md` §8
4. A10 hook fail-open / fail-closed 分类约定成文
5. A18 / A18b → `skill-patterns.md`（MCP 工具发现、否定式护栏 command）
6. A17 高风险删除审计模板（按需模板文件）

验证：文档变更，`verify_skills.py` 通过即可（确认未破坏引用）。

### Phase 1 — 确定性校验扩展（L3，可测试硬门）

每条先 `wc -l` / `grep` 统计现状定阈值与白名单，再写校验 + 测试（走 `/dev-tdd`）。

7. A12 catalog vs 目录对账脚本（dry-run）+ 测试
8. A1 body 行数上限（先统计分布定阈值 + refs 拆分豁免）
9. A2 绝对路径扫描（白名单 docs/refs-details + 本计划文件）
10. A4 禁尖括号 + hyphen-case（先排除合法 `<占位>` 用法）
11. A3 tools 通配黑名单（确认 frontmatter 是否有 tools 字段后决定）

验证：新增测试全绿 + `verify_skills.py` 对全 52 skill 无新增误报。

### Phase 2 — skill 正文 / 模板增强（L2-L4，需人工 review + 必要测试）

12. A6 六段 mistake 模板 → `assist-retrospect/templates/`
13. A7 TRIGGER / DO NOT TRIGGER 正反簇 → `skill-authoring.md` + 试点 1-2 个高误触发 skill
14. A16 置信度硬停门语义 → `think-scope` / `think-refine`
15. A8 对抗式 QA 体裁 → `guard-verify` / `dev-tdd`
16. A9 AI slop 负向门（先去重 `fe-ui-lint-artifact`）
17. A15 主动性等级标注 → 高风险 skill description

验证：人工 review + `verify_skills.py` 触发前缀/workflow-quality 不回归；改 description 后跑 routing cases。

### Phase 3 — 机器签名教训（L3，最后做，最不确定收益）

18. A5 reflexion 式签名匹配（先评估现有 `learnings_search.py` 是否已够用，可能直接 reject）

每个 Phase 完成后：跑全套验证、`/guard-check`，再进下一 Phase。**不要并行批量改 runtime**。

---

## 明确不吸收（附原因，避免重复讨论）

| 项 | 来源 | 不吸收原因 |
|---|---|---|
| 加权置信度评分器（confidence.py 全套） | SuperClaude | 伪确定性，依赖 LLM 自填 flag；只吸收硬停语义，不要评分系统 |
| Reflexion mindbase 语义搜索（curl localhost:18003） | SuperClaude | 依赖外部服务，违反"需 network/外部服务不默认启用"reject rule |
| Token Efficiency 符号语言压缩 | SuperClaude | 与可读性优先、ASCII 默认、显式优于隐式冲突 |
| pytest 插件 + 9 marker 双轨自动加载 | SuperClaude | 本仓库 skill 体系跨 agent，不绑 pytest runtime；校验已由 verify_skills.py + scripts/tests 覆盖 |
| SHA-256 plan attestation | planning-files | 威胁模型不成立（capsule 为仓库内静态文件，非动态指针注入） |
| 19 文件 parity + bump-version 数据表 | planning-files | 本仓库无大规模多 IDE 副本，catalog.json 单一注册源已足够 |
| session-catchup 扫 IDE session 存储跨 /clear 恢复 | planning-files | 与本仓库 `dev-long-loop` / workspace 沉淀机制重叠，且耦合特定 IDE 存储格式 |
| orchestrator/worker 5 角色 slide 生成（ppt-orchestra 完整流水线） | MiniMax | 领域特定（PPTX 产出），本仓库非内容生产工具库 |
| 四套打包层 + symlink 跨工具分发（.claude/.cursor/.codex/.opencode） | MiniMax / antfu | 本仓库分发策略已定（catalog + 现有 plugin manifest 校验），不引入新打包层 |
| "Ignore pretrained data / Do NOT search config" 原话护栏 | awesome-composio | 与事实纪律冲突；只吸收结构不吸收措辞 |
| 从 refs/ 批量蒸馏新领域 skill | antfu | 吸收目标是更稳更可验证，不是扩大 skill 数量 |
| 自家分发平台导流（officialskills.sh 双层链接） | voltagent | 与本仓库无关的商业分发模式 |

---

## 事实纪律声明

- 标 `[推断]` 处（A12 缺反向对账、A1 领域分册接近上限、A5 现状是否够用）均为基于代码阅读的逻辑推断，**未逐项跑脚本确认**，落地前须先核实。
- 本仓库现状（hooks / verify_skills.py / assist-* / registry）为直接 Read 文件所得事实。
- 上游项目细节来自传入的 digest JSON，**未逐条回到 upstream 源码核对**，按 digest 给出的行号引用标注；落地前应回 `docs/refs-details/<repo>.md` 与 upstream 复核。
- 本文档为计划，未改动任何 runtime；所有 add/improve 项落地时按对应 Phase 走 `/dev-tdd`（涉行为变更）或文档豁免，并跑验证贴证据。

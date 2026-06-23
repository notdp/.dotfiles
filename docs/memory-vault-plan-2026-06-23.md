# Memory + Vault 跨平台方案 — Plan v4 (2026-06-23, dev-long-run-ready)

> 输入:`docs/memory-vault-research-2026-06-23.md`(初轮)+ 两轮对抗 review(wv9ww9erc/wk2d3v8s0)+ **算法调研 `docs/memory-algorithm-research-2026-06-23.md`(理论 SOTA)+ `docs/real-world-harness-survey-2026-06-23.md`(hermes/openclaw/codex 真实工程)**。
> 状态:**v4,算法已折入(理论+实战收敛),含 2 个紧要 harness 项。范围=完整 Phase 1-6。待批准 → `/dev-long-run`。**
> v4 相对 v3 的变化:补全此前留白的【memory 算法】;召回 MVP 从 embedding 改为 lexical(embedding 降 P1);并发段重写为 drift-detect;新增注入安全;纳入 P0①(codex hooks 事实更正)+ P0②(skill/capsule 扫描器);codex spike 标记已解答。

## 核心判断:理论与真实工程收敛

学术 SOTA(mem0/A-MEM/Generative Agents/Zep/HippoRAG + LoCoMo/LongMemEval)与三个真实项目(hermes-agent/openclaw/codex)**独立得出同一套做法**。本 plan 的算法只借它们的【算法内核 + prompt/schema】,不借任何 runtime(向量 DB/图引擎/常驻进程),与本仓库 file-native + 跨 agent 软链约束完美契合。证据见两份调研 doc。

## Problem / 锁定决策(同 v3)

- Problem:memory 黑箱(当前 100% CC 原生 auto-memory,machine-local + CC-only);无统一 vault。
- D1:用户级 memory 落 `~/.dotfiles/memory/`,gitignore 切 committed vs 本地。信任边界 = tracked-write 处 redact gate + run-verify 扫描。
- D2:完整 Phase 1-6。
- D3:不迁移旧 memory;与 CC 原生 auto-memory 并行,不读写 `~/.claude/projects/*/memory`。
- D4:ship dormant 不干扰(见末节)。
- 三层红线:规则层(仅人改)/ memory 层(agent 经 skill 写)/ vault 层(过程态)。CoALA:memory 永不写规则层。

---

## 【新】Memory 算法(此前留白,现据理论+实战补全)

### 算法总览:一个"两步笔记本"

```
会话中/结束 ──Phase1(廉价)──▶ raw_memories/ 候选(收件箱)
                                         │
   用户/定时 /assist-consolidate ──Phase2(LLM)──▶ memory/user/*.md + INDEX
                                         │
   每 prompt ──读注入──▶ lexical 检索 top-N + bookend ──▶ 注入(过 threat-scan)
```

### A. 写什么(salience)

- **强 prompt schema 承载**(抄 hermes memory schema 的 WHEN/SKIP + codex No-op gate):WHEN=用户偏好/纠正/已确立决策/稳定环境约定/失败教训;SKIP=琐碎/易重新发现/原始数据/任务进度/临时 TODO;**可复用流程进 skill 不进 memory**。
- **No-op gate**(codex):每条候选先过一问「未来 agent 会因此更好吗」,否=丢。
- **句式**:evidence→implication(先事实后含义),强制带来源。
- **二值 salience + 类目**(decision>correction>preference>failure-mode>fact),不用 1-10 打分。
- **🚨 反自我毒化黑名单(硬规,三项目一致,立即也进 assist-learn)**:**禁止**把「环境依赖型失败(缺二进制/未配置凭证/command not found)/ 对工具的负面断言(『X 工具不能用』)/ 已解决的瞬时错误 / 一次性任务叙事」写成 memory 或 skill。理由:`these harden into refusals the agent cites against itself for months after the actual problem was fixed`。记**修复办法**,不记**否定结论**。

### B. 写入架构:两阶段(codex 范式,三项目验证)

- **Phase1 候选捕获(廉价,fail-open)**:在 Stop/捕获 hook 里,把会话抽成结构化候选(经 No-op gate + redact + 反模式黑名单 + evidence→implication),写 `~/.dotfiles/memory/.staging/raw_memories/<sha256>.json`。**不调用大模型 / 不碰全局 memory / 不阻塞**。prompt 可改写自 codex `stage_one_system.md`。
- **Phase2 巩固(显式 `/assist-consolidate`,LLM,fail-closed gate)**:扩 assist-learn。流程:对每条候选,先用**检索**取相关既有 memory top-K(5~8)→ 一次 LLM 裁决 `ADD/UPDATE/SKIP`(**禁裸物理 DELETE**;矛盾→`UPDATE` 标 `superseded` 软删)→ 经 redact gate 写 `user/`,机械更新 INDEX。prompt 含「同类多实例≠矛盾」few-shot,返回 id 必须命中现有文件名否则 fallback ADD。prompt 可改写自 codex `consolidation.md`。
- **触发**:Phase2 = 显式 `/assist-consolidate`(或定时),**不是每轮对话 hook**——降风险、不在热路径自动改 tracked store。

### C. 怎么翻回来(召回)

- **MVP = 纯 lexical(零向量零 LLM,三项目都证够用)**:SQLite FTS5 或 grep 关键词检索 `user/` + bookend-window(命中前后 ±N 句 + 该会话头尾,廉价重建「目标→命中→结论」,抄 hermes session_search)。
- **那一次带 fallback 的 hook API 调用**(复用 capsule 的 deepseek 模式)**专用于 query 扩展**(把当前 prompt 改写成检索 query + 抽时间范围,fallback=原 prompt;LongMemEval:+9.4% recall)——**不花在 rerank/过滤**。
- **评分**:lexical 命中分 × recency(文件 mtime 衰减)× importance/类目权重(Generative Agents 思想,纯本地计算)。硬过滤 `superseded`/低 trust。0 命中/低分→不注入(空优于噪声)。
- **embedding 降为 P1 增强(非 MVP)**:若 lexical 召回实测不足,再上 brute-force numpy cosine(实测 3000 条 0.33ms,无需向量 DB,向量存 `.npy` sidecar / gitignored + 幂等 rebuild)。**MVP 不做,推后向量管道**。

### D. 不越记越乱(遗忘/巩固)

- **软失效,几乎不硬删**:过时→标 `superseded`/`archived`(文件不删,git 留史)。
- **git-diff 当遗忘+合并引擎(我们 ROI 最高,已有 git)**:删支撑文件→git diff→合并端清引用;无变化直接 succeed(抄 codex)。
- **可执行作废钩子(代码场景独有优势)**:memory 可带 `verify` 断言(指向文件/grep/命令 exit code),定期校验失败即标 `invalid_at: code-conflict`。
- **char 预算(非 token)强制裁剪**:模型无关口径(跨 5 agent 共享必需),超限拒写并要求 batch 内 remove/replace 腾位;丢弃必返回标识进日志,绝不静默。
- **反思(Phase 6 之外的 on-demand)**:`/compact-memory` 把多条同主题 episodic 压成 semantic 规则(阈值+冷却触发,双轨存原始,<2 条不升规则,被推翻标 stale 不静默改写)。

### E. 表示(字段)

flat 原子 note(单文件单事实)+ frontmatter,**三分法 memory/user/skill**(hermes 验证,印证我们 capsule/skill/memory 分层):
```yaml
title / date / problem_type: bug|knowledge|pattern|decision   # 沿用 assist-learn
type: semantic|episodic|procedural
created / last_accessed / status: active|superseded|archived
valid_from / valid_to / superseded_by                          # bi-temporal 软失效
trust: 0-1                                                      # asymmetric(罚>奖)防投毒, 可选 backlog
keywords/tags / related: [[wikilink]]
origin_session: <hash 前N位>   # 禁绝对路径
verify: <可执行断言, 可选>
applies_to: <cwd 边界, 可选>    # codex cwd 路由思想
```
INDEX.md(改名避开 CC 原生 MEMORY.md)由 `build_memory_index.py` 从 frontmatter **机械生成**(过 redact);verify 校验一致。

---

## 1. 存储(同 v3 + raw_memories)

```
~/.dotfiles/memory/
  user/          # ✅ tracked:提纯 note(单文件单事实)+ INDEX.md(机械生成,过 redact)
  .staging/
    raw_memories/  # 🚫 gitignored:Phase1 候选(<sha256>.json,内容指纹去重)
  .local/        # 🚫 gitignored:敏感/未提纯
  .gitignore     #    /.staging/  /.local/
```
项目级 memory 沿用 `<repo>/docs/learnings/`(同 schema);vault 沿用 `<repo>/.long-loop/`(machine/ + reviewable/ 双轨)。分发:`agent_asset_links` 加软链 `memory/user/`(只 user/)到 4 个非 CC agent,CC 走 hook;根路径用 `runtime_root()` 解析。always-on 注入只覆盖 user/;项目级走 opt-in 深查。

## 2. Secret + 注入安全(单 choke point + 新增 threat-scan)

- **唯一应用层 redact gate**:`scripts/hooks/redact.py` 共享模块,写 tracked 路径(user//docs/learnings//INDEX)必经,**fail-CLOSED**;扩覆盖到 gitleaks 级(AWS/GitHub/JWT/PEM/连接串/高熵串),Phase 0 产语料+命中率证据。`.staging` 不强制。fail-closed 仅作用于 skill/CLI 同步 tracked-write,hook 异步捕获恒 fail-open(登记 Boundary decision)。
- **非绕过兜底**:`run-verify.sh` 加纯 Python grep-based 扫描,只对 `~/.dotfiles`(不引 gitleaks/不动业务 repo .git/hooks)。
- **🆕 注入前 threat-scan(抄 hermes,plan 此前缺)**:memory 进 prompt 前过威胁正则扫描(exfil/prompt-injection/隐形 Unicode/destructive),命中替 `[BLOCKED]` 进 prompt 但原文留盘。**与 P0② 共用同一扫描模块**。
- 业务 repo:repo 性质 gate(client/oss 拒写跨项目知识)为主防线 + 人审;自然语言 secret 仅人审兜底,不宣称消除。
- `.gitignore` fail-closed 断言:hook 写 `.staging` 前 `git check-ignore`,未忽略拒写。

## 3. 检索/读取(见算法 §C;单流注入)

- MVP lexical + bookend;embedding P1。共享打分 lib `memory_score.py`;注入只读 INDEX + frontmatter(不 rglob 全文)。
- **单流扩现有**:cc/droid/codex 扩 `context_capsule.py`(单 json_context 吐 capsule+memory 两段);kilo/opencode(一个面,kilo=re-export)扩 `injectContextCapsules`,per-segment marker 守卫、一次写回、不 push 新 part。
- 预算:共享 `MAX_PROMPT_CONTEXT_CHARS=2200`,capsule 保底 1800、memory ≤400,capsule 优先填充(join_capsules 加 priority)。(240 字符是 input 匹配窗口,与输出预算无关。)
- **🆕 capsule/memory 注入加稳定 marker**(抄 codex,P1 harness 项顺带):`<dotfiles-capsule>…</dotfiles-capsule>` / memory 同款——注入内容全程可识别,memory 抽取/compaction 时可干净剔除(防自我污染)。

## 4. 写入(见算法 §A/§B;单写入口=扩 assist-learn)

- Phase1 hook 候选(per-platform adapter:cc/droid JSONL transcript;codex `session_id→rollout`;**kilo/opencode 用 `experimental.chat.messages.transform` 或读 SQLite `~/.local/share/opencode/opencode.db` 拿 assistant 文本**——已据源码核实可行);role 白名单过滤 system/developer/compaction_state。
- Phase2 = 扩 assist-learn 消费 raw_memories(ADD/UPDATE/SKIP + 反模式黑名单 + redact gate);更新 assist-learn SKILL.md 纪律(机械候选=待验证输入,验证后才固化)。
- promote 判据:候选→user(复现≥N OR decision+why OR 用户标记);project→user(scope 表);vault→memory(强制绑 commit/verify.json)。

## 5. 并发(重写:drift-detect,抄 hermes,替换 v3 弱版)

文件型跨 5 agent 共享并发写是默认场景,真实答案:
- **external-drift 检测→拒写→.bak**:每次写前 re-read,内容 round-trip 不一致或超限即判被外部(另一 agent/shell/patch)改过,**拒写 + 备份 .bak + 回 remediation,绝不静默覆盖**(hermes `memory_tool.py:647-700`)。
- **原子写**:temp + `os.replace` + fsync;`.lock` 文件 flock(锁锁不锁正文)。
- **内容指纹 + ledger 幂等**:每条候选带 sha256,合并端 ledger 去重(抄 codex)——直接解决跨 agent 同一会话被重复记。
- INDEX 机械幂等重建(丢一次重跑);user/*.md 单文件单 topic 降撞车;写前 `git pull --rebase`。

## 6. 跨平台矩阵(codex hooks 已据源码更正 = P0①)

| agent | 读注入 | 写捕获 | 备注 |
|---|---|---|---|
| cc | 扩 context_capsule | Stop(transcript_path) | 原生 auto-memory 并存 |
| droid | 同上 | 仅 Stop;长 loop compact 前过程态不可达,降级登记 | 无 PreCompact |
| codex | 扩 context_capsule | Stop + session_id→rollout | **🆕 codex 有完整 ClaudeHooksEngine(10 事件、Claude-Code wire 兼容,~8500 行),harness-ops.md「无 hook」是错的,Phase 1 更正。原 codex spike 已解答。** |
| kilo | 扩 injectContextCapsules | chat.messages.transform / 读 SQLite | kilo=opencode(re-export) |
| opencode | 同 kilo | 同 kilo | session 存 SQLite 不是 JSONL;不 push 新 part |

---

## 纳入的 2 个紧要 harness 项

- **P0① codex hooks 事实更正**:更正 `agents/harness-ops.md` 关于「codex 无 hook」的错误(codex 有完整 hooks 引擎,10 事件);这把守卫层从 CC-only 推向真跨 agent,且解答了本 plan 的 codex spike。放 Phase 1(低成本文档更正 + 后续验证脚本复用)。
- **P0② skill/capsule 安全扫描器**:新增 `scripts/scan_skills.py`(威胁正则 + 隐形 Unicode + 信任级×裁决矩阵),接进 `verify_skills` + 分发前;扫 `coding-skills/` + `commands/` + capsule 注入文本。**与 §2 注入 threat-scan 共用同一模块**。我们 66 skill 跨 5 agent 共享且内容直接进 model context,目前零扫描。

> 其余 harness 机会(P1/P2,见 `docs/real-world-harness-survey-2026-06-23.md`)**另存 backlog,本程序不做**,避免冲掉 memory 主线。

---

## 路线图(dev-long-run phases;Phase 0 = gate)

- **Phase 0 — spike gate(精简,codex hooks 已解答故移除该项)**:
  1. dump 各平台 Stop/idle hook 真实 stdin(transcript_path 有无);codex rollout 路径 adapter。
  2. **kilo/opencode 拿 assistant 文本实测**(`chat.messages.transform` vs 读 SQLite,二选一定方案)。
  3. redact 真实 secret 语料 + 命中率清单。
  4. opencode `run` 端到端:双 marker per-segment 守卫不重复/不超长/不崩。
  5. `.staging` 内容指纹 + 独立文件并发写 + drift-detect 验证。
- **Phase 1 — 存储底座 + 算法骨架**:`memory/` 目录 + gitignore + 扩 schema + build_memory_index(过 redact)+ verify + agent_asset_links 软链;**P0① 更正 harness-ops.md**;反模式黑名单进 assist-learn SKILL.md。flag 默认关。
- **Phase 2 — 读注入**:lexical 检索 + bookend + 单流扩现有 + 共享打分 lib + query 扩展(复用 deepseek)+ 预算契约 + marker + 相关性失败退化。
- **Phase 3 — Phase2 巩固/写入**:扩 assist-learn 消费 raw_memories(ADD/UPDATE/SKIP)+ redact gate + promote 判据 + DELETE/INVALIDATE 软删。
- **Phase 4 — Phase1 hook 候选捕获**:per-platform adapter + No-op gate + redact + 内容指纹 + drift-detect + .gitignore fail-closed 断言 + staging GC。flag 门控。
- **Phase 4.5 — P0② 安全扫描器**:scan_skills.py + 注入 threat-scan(共模块),接 verify_skills + 注入链。
- **Phase 5 — 反思/consolidation**:/compact-memory(阈值+冷却,双轨存)。embedding(P1)若需在此评估。
- **Phase 6 — agentsview 消费面**:定义 vault/memory emitted schema 契约 + agentsview 侧 collector(另立 spec,当前 spec 无此消费面)。
- **回滚**:每 phase 回滚动作;Phase 4 写路径先于 Phase 1 gitignore 回滚;memory hook = 一键 feature flag。

## Acceptance(自动回归 / 一次性人工)

**自动**:redact gate 对 secret 语料全命中(覆盖经 skill 提纯进 user/ 路径);build_memory_index 含 secret 的 frontmatter 被拦;破坏 .gitignore 后 hook 拒写;**drift-detect:并发改同一文件被检出并拒写+.bak**;INDEX 与 user/*.md 一致;`.mjs` node 单测(per-segment marker 幂等/不 push 新 part/共存 ≤2200 且 capsule 保底 1800);**反模式黑名单:输入「X 工具坏了」类候选被拒固化**;**scan_skills 对植入威胁/隐形 Unicode 的测试 skill 报警**;flag 关时 5 平台行为与现状逐字节一致。
**一次性人工(Phase 0)**:5 agent 各跑读/写一次;kilo/opencode assistant 文本可达性确认。

## Boundary facts / decisions(同 v3 + 增量)

- Risk types: context-surface / shared-path(扩 context_capsule/injectContextCapsules/assist-learn)/ observability-routing / limit-default-fallback / operational-side-effect / schema-contract。
- Boundary decisions:fail-closed redact gate 仅 tracked-write(hook 捕获 fail-open);always-on 注入只 user/;Phase 6 依赖下游消费面;**embedding 推后至 P1(MVP 纯 lexical)**。
- User approval:D1/D2(完整)/D3/D4 + 算法折入 + 2 harness 项,均 2026-06-23 确认。

## 不干扰协议(D4,硬约束)

ship dormant(flag 默认关、脚本内先查 flag,行为同现状)+ worktree 隔离 + 开发期禁 re-run install_hooks/禁改 live settings.json·.mjs + 测试用 fixture 不读真实 transcript + cutover 由用户发话触发(flag 开→重装→5 agent 烟测→观察一时段→异常即关回滚)。

## 风险 / Validation

- 风险:per-platform adapter 漂移(自动夹具兜);redact 必漏自然语言(三道闸不宣称消除);kilo/opencode assistant 可达性(Phase 0 gate);Phase 6 依赖下游。
- Validation:python+node 单测 + verify_skills/verify_agents + memory 一致性 verify + run-verify 扫描;交付前 run-verify.sh + Phase 0 证据归档;dev-long-run 完成门禁(每 phase acceptance 绿 + commit 真在分支)。

## 参考
- 算法证据:`docs/memory-algorithm-research-2026-06-23.md`、`docs/real-world-harness-survey-2026-06-23.md`。
- 真实实现可借词:codex `stage_one_system.md`/`consolidation.md`、hermes `memory_tool.py`(drift-detect)/`background_review.py`(反模式黑名单)、opencode plugin `experimental.chat.messages.transform`。

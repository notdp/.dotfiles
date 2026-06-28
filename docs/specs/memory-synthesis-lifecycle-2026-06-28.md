# Spec: Memory 合成层 + 分层生命周期 (2026-06-28)

## TL;DR
让 auto-memory 产出 **CC 级**(结构化、中文、按主题)的可读 memory,并给三层数据加**自动过期/硬删**,使磁盘只留「活的+近期」,git 历史做审计真相。
推荐方案:**合成层复用 `/compact-memory` 的 `compact_memory.py` + 新增 agentsview synthesize worker(同 consolidate 同构);统一写 `memory/user`;分层 TTL 硬删 + git 兜底**。

## 已锁定(用户已拍)
- 主题文档放 **统一 `memory/user/`**(原子源标 archived/stale,recall 已排除 non-active)。
- 合成走**自动 worker**(默认 OFF,UI 开),不只 on-demand skill。
- 合成/抽取产物用**源语言/中文**(A 已修 extract;B 的合成 prompt 同样要求中文)。
- 复用 dotfiles `compact_memory.py` 当确定性安全 SSOT(不在 Go 重写安全逻辑)。

## Goals
- G1 同主题原子 note(≥2)→ 一篇结构化中文主题文档(对齐 CC 格式:frontmatter + 正文 + `(because of <id>)` 引用 + `[[链接]]`)。
- G2 三层生命周期:候选 / 原子 / 主题,各有明确保留 + 自动硬删,git 兜底。
- G3 自动化:synthesize worker timer(像 consolidate),默认 OFF。

## Non-goals
- 不在 Go 重写 redact/promotion/citation 安全逻辑(全走 python SSOT)。
- 不改 CC 原生 memory(`~/.claude/.../memory`,CC 自管)。
- 不动 recall 的 non-active 排除逻辑(已正确)。
- 不做跨语言「翻译已 push 到 backup 的历史」——只对活跃磁盘内容生效。

## 数据三层 + 生命周期(用户问题的正式答案)

| 层 | 路径 | 性质 | 磁盘保留策略 | 审计真相 |
|---|---|---|---|---|
| 候选(inbox) | `memory/.staging/raw_memories/*.json` | 抽取/捕获原始候选 | 巩固时 drain→consumed/;**未处理 >14d 自动 gc 删**(现有 gc,**新增自动调用**) | 无需(临时) |
| 已消费归档 | `memory/.staging/consumed/*.json` | 已巩固的候选副本 | **>7d 自动删**(已 commit 进 memory/user,可从 git 恢复) | memory/user git |
| 原子 note(活) | `memory/user/*.md` status=active | 机器召回基底 | **保留**;被 supersede 或被合成折叠 → 标 archived/stale | memory/user git |
| 原子 note(归档/stale) | 同上 status≠active | 已被取代/已折叠进主题文档 | **>90d 自动硬删**(git 历史=审计,磁盘不留) | memory/user git + private backup |
| 主题文档(合成) | `memory/user/*.md` type=synthesized | CC 级人读层 | **保留**(人读主层) | git |

**核心原则**:磁盘 = 活的 + 近期;`memory/user` 本地 git repo(每次巩固/合成/删都 commit)+ private 备份 push = 持久审计。**故硬删旧候选/旧归档安全,不丢东西**(`git log`/backup 可恢)。所有 TTL 都是**可配默认值**。

### 用户两问的直接回答
1. **原子层要删吗?** 活跃原子 **不删**(是召回基底);**归档/stale 原子(含被合成折叠的源)→ 90d 后硬删**,因 git 历史是审计真相,磁盘清掉不丢。
2. **候选层要过期删吗?** **要**,且部分已存在(14d gc)但没自动跑。落实:**自动调用 gc + 给 consumed/ 加 7d TTL**。候选是临时收件箱,过期删正确且安全(下游已 commit)。

## 架构(合成 worker,同 consolidate 同构)

```
timer/after-consolidate ─▶ synthesize worker (agentsview Go, 默认 OFF)
  1. 读 memory/user active 原子 note
  2. 按主题聚类(embedding 余弦 + 同 problem_type 分组;阈值聚簇)
  3. 每个 ≥2 条的簇 → LLM 合成「结构化中文主题文档」决策(title/insight/source_ids/keywords + [[links]])
  4. shell out compact_memory.py --root <dotfiles> --decision-file <f>
     (校验 (because of <id>) 引用 + redact + 写 memory/user + 重建 INDEX + 源标 stale)
  5. GitCommitter.Commit + Resync + audit (.synthesize-audit.jsonl)
GC(可独立 timer 或并入 worker 尾部):
  - raw_memories 未处理 >14d → 删
  - consumed/ >7d → 删
  - memory/user 归档/stale >90d → 删 + 重建 INDEX + commit
```

## 改动 / 文件(方向级)
- **dotfiles**
  - `coding-skills/compact-memory/scripts/compact_memory.py`:合成 render 对齐 CC 富结构(frontmatter `type: synthesized` + 正文分节 + `[[links]]`);确认 decision-file 支持中文 insight + 多 source_ids(SKILL 已述)。
  - `scripts/hooks/memory_capture.py`:`gc_raw_memories` 扩到也清 `consumed/`(参数化 TTL);新增 `gc_archived_user_notes(root, ttl_days=90)`(删 status≠active 且 >ttl 的 user note + 重建 INDEX)。**纯函数 + TDD**。
- **agentsview**
  - `internal/synthesize/`(新包,镜像 `internal/consolidate/`):worker(聚类+LLM 合成决策+shell out compact_memory.py+commit+resync+audit)+ controller(timer,默认 OFF)+ audit。
  - `internal/llm` 复用;`SynthesizeLLM()` 配置(同 consolidate:reasoning 关、源语言中文、独立 model 可配)。
  - GC:Go 侧定时调 `memory_capture.py --gc`(候选/consumed)+ python `gc_archived_user_notes`(经新 CLI flag);或纯 python 一个 `--gc-all` 入口,Go timer 调用。**倾向后者**(安全逻辑留 python)。
  - `cmd/agentsview/main.go`:`startSynthesize` + `startMemoryGC`;config `synthesize_enabled/interval` + `retention_*`。
  - server:`registerSynthesizeRoutes`(audit + enable,镜像 consolidate);可选 staging viewer 标注 synthesized。
  - frontend:SynthesizePanel(开关+audit)+ Memory 页区分 synthesized/atomic(badge)。
- **config 默认**:`synthesize_enabled=false`、`synthesize_interval=24h`、`retention_candidate_days=14`、`retention_consumed_days=7`、`retention_archived_note_days=90`(全可配)。

## 阶段(建议顺序)
- **B2 生命周期(先,便宜、答用户关切)**:python gc 扩 consumed + archived-note gc(TDD)+ Go timer 调用 + config 默认。可独立交付验证。
- **B1 合成层(后,大)**:synthesize 包 + 聚类 + 合成 prompt(中文结构化)+ compact_memory.py render 对齐 + worker/controller/audit + UI + config。

## 风险 / Validation
- **合成质量**[未验证]:聚类粒度 + LLM 合成可能跑偏(过度合并/丢信息)。缓解:默认 OFF + 源 stale 不硬删(90d 内 + git 可恢)+ audit 可见每次合成的 source_ids;先在隔离/小主题验证再放量。
- **硬删安全**:删前必须已 commit(git 可恢);archived gc 删后重建 INDEX + commit;backup push 含 git 历史。**绝不删 active**。
- **成本**:合成 LLM 重(聚类+逐主题)。默认 OFF + interval 24h + 仅 ≥2 簇。
- **embedding 滞后**:聚类依赖 embedding;新 note embedding 未生成则该轮少聚一些,下轮补(非错误)。
- Validation:python TDD(gc 纯函数 + render);Go 单测(worker 决策→shell out→commit,fake store/script);端到端:真机 enable 一轮看主题文档产出 + 源标 stale + 90d gc 删归档(造旧 mtime 夹具)。

## spec-contract
```yaml
checks:
  - "≥2 同主题 active 原子 note → 1 篇 type=synthesized 中文主题文档,含 (because of <id>) 引用"
  - "raw_memories 未处理 >14d 被 gc 删;consumed >7d 被删;均自动(非手动 --gc)"
  - "memory/user status≠active 且 >90d 的 note 被硬删 + INDEX 重建 + commit;active 永不删"
  - "synthesize worker 默认 OFF;enable 后 timer 跑;reasoning 关、输出中文"
  - "所有安全(redact/citation/promotion)仍由 compact_memory.py 执行,Go 不重写"
non_goals:
  - "不改 CC 原生 memory;不改 recall non-active 排除;不翻译已 push 的 backup 历史"
locked_decisions:
  - "主题文档统一写 memory/user(方案 a)"
  - "合成走自动 worker 默认 OFF"
  - "git 历史=审计真相,磁盘硬删旧候选/旧归档"
  - "保留默认:候选14d/consumed7d/归档note90d(可配)"
validation_commands:
  - "python3 -m unittest scripts.tests.test_memory_capture scripts.tests.test_compact_memory"
  - "cd ~/Projects/agentsview && go test ./internal/synthesize/ ./internal/config/"
```

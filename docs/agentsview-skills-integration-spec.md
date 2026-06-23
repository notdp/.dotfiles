# Spec: agentsview Skill 体系治理观测层(工作流 C / C1+C2+C3 MVP,C4 设计预留)

> 性质:**集成 spec(实现前 SSOT)**。上游需求 = `harness-governance-prd-2026-06-23.md` 工作流 C 与"数据建模决策"。
> 状态:**待用户批准**。批准前禁止写实现代码(think-plan 硬门控)。
> 方法论:横向拆解(C1/C2/C3 三视图)+ 拓扑梳理(parser→db→server→ui 四层 + SQLite/PG 双后端)。
> 代码锚点均已对照真代码核实(行号 2026-06-23,可能漂)。

---

## TL;DR

把 agentsview 扩成 skill 体系的**治理观测层**:新增独立 `skills` 维度表 + `skill_health` 体检表,由一条**与 session 同步完全隔离**的 `SkillSyncer` 从 `~/.dotfiles/coding-skills/catalog.json` + 各 `SKILL.md` frontmatter 拉取缓变参考数据,经 `/api/v1/skills/*` 路由暴露,前端新增 `skills` 页(清单 / 静态成本 / 健康体检三视图)。**绝不复用 sessions/messages**(否则污染 stats trigger 与全量 analytics)。C4 使用统计仅出设计,复用现成 `tool_calls.skill_name`,不进 MVP。

推荐落地顺序:**C1 清单 → C3 静态成本 → C2 健康体检 → C4 设计预留**。

---

## 对 brief 的两处事实纠正(已现场验证,需用户确认采纳)

| # | brief 原文 | 核实结果(事实) | 影响 |
|---|---|---|---|
| 1 | "迁移要 bump db.go 里的 dataVersion" | `db.go:1445 init()` 每次 Open 都执行 `w.Exec(schemaSQL)`(`db.go:1449`),而 `schema.sql` 全部用 `CREATE TABLE IF NOT EXISTS`。新表会在下次 Open **自动幂等创建**。`dataVersion`(`db.go:152 = 37`)是 `PRAGMA user_version`,语义为"**parser 变更需重解析 session 文件**"(`db.go:24` 注释),bump 它会触发**全量 session 重解析**——对"加独立参考表"是昂贵且无关的副作用。 | **MVP(C1/C2/C3)不 bump dataVersion**。仅当 C4 需要让旧 agent 重新抽取 `skill_name` 时才考虑 bump,且那是 parser 改动,与本表无关。 |
| 2 | "catalog 目录是软链,discovery 必须 symlink-aware" | 本机 `cd ~/.dotfiles/coding-skills && pwd -P` 解析为**同路径**,即当前**不是软链**;`~/.dotfiles` 与各 `SKILL.md` 目录实测均为真实目录。 | symlink-aware **仍保留**为健壮性要求(其它机器 `~/.dotfiles` 可能软链、个别 skill 可能软链),但不要把"必然是软链"写进逻辑。复用 `discovery.go` 的 `filepath.EvalSymlinks` 模式即可。 |

---

## 已锁定(来自 PRD dual-review,不推翻)

- **数据建模 = B 为主 hybrid**。C1/C2/C3 → 独立 `skills` 维度表 + `skill_health`;C4 → 复用 `tool_calls.skill_name`。
- **禁止把 skill 伪装成 session/message**。理由(已验真):`stats` trigger(`schema.sql:98-112`)对所有 session 无 agent 过滤地全局计数;`GetStats/GetProjects/GetAgents`(`store.go:51-54`)**无 ExcludeAgent 参数**;`AnalyticsFilter`(`analytics.go:44`)只有 inclusive `Agent`、无 `ExcludeAgent`;仅 usage 侧(`usage.go:32 UsageFilter.ExcludeAgent`)有排除。伪 session 会污染 GetStats/Projects/Agents/ListSessions/trends,且 SQLite+PG 双后端要成对加 `agent!='skills'`,是长期陷阱。
- **不要改 `NormalizeToolCategory`**:`taxonomy.go:26` 的 `case "Skill": return "Tool"` 保持不变(改了会破坏现有 `/analytics/tools`)。C4 另起 skill 专属聚合。
- **静态成本独立于 usage/cost 管线**:usage 只统计 `messages.token_usage!='' && model!=''` 的真实请求;**绝不为复用而给假 message 写 token_usage**。C3 token 数是 `skills` 表上的派生列。
- **SQLite + PostgreSQL parity 必须保**(DuckDB 是只读镜像,跟随)。
- **agentsview 在 dotfiles 之外**:任何 commit/push 走 `/guard-gitops`,未经许可不动。

## 待决策(需用户拍板,阻塞对应 Phase)

| # | 决策点 | 候选 | 推荐 | 阻塞 |
|---|---|---|---|---|
| D1 | **C3 tokenizer 选型** | (a) `tiktoken-go`(`pkoukk/tiktoken-go`,`o200k_base`,新增直接依赖,需嵌入/离线 BPE 词表);(b) 硬编码 char→token 启发式表;(c) Anthropic `count_tokens` API | **(a)**。原因:**描述是中文**,char/N 启发式对 CJK 误差可达 2-3×,会让"终结成本争论"的数字失去说服力;(c) 需网络+API key,违反"本地静态"。**但必须诚实标注:tiktoken ≠ Anthropic 实际分词器,数字为近似**(`[推断]`,Anthropic 当代模型分词器未公开)。tokenizer 藏在 interface 后,可换。 | C3 |
| D2 | **是否 bump dataVersion** | (a) 不 bump(纠正 brief);(b) 按 brief bump | **(a)**,见上"事实纠正 #1"。 | C1 schema |
| D3 | **skills 目录配置 + 缺失行为** | env `AGENTSVIEW_SKILLS_DIR` + flag `--skills-dir`,默认探测 `~/.dotfiles/coding-skills` | 默认探测;**目录/catalog.json 不存在时 fail-open**:skills 表为空、页面显示"未配置 skill 目录",**绝不 crash、绝不阻塞 session 同步**。 | C1 config |
| D4 | **C2 体检范围** | (a) 仅 catalog 可推导的检查(软链/路径/wiring/重复/孤儿/legacy 悬挂);(b) 产品化整个 agent-health(含 hooks/MCP/全局规则) | **(a)**。hooks/MCP/settings 在 catalog 目录之外、不是 agentsview 的数据面;强行检查会引入大量 dotfiles 结构耦合。(b) 列 Non-goal。 | C2 |
| D5 | **MVP 是否推送 skills/skill_health 到 PG** | (a) MVP 即做双后端 parity(schema+store+push);(b) MVP 只 SQLite,PG 留 Phase | **(a)**,parity 是 CLAUDE.md 硬约束;表小(52 行),push 成本可忽略。但 SkillSyncer 只在 SQLite 侧跑,PG 经 `pg push` 全量替换。 | 全程 |
| D6 | **C3 "成本"语义** | 纯 token 数 vs 折算 $ | 主指标 = **token 数 + 占参考窗口(如 200k)百分比**;$ 作次要、明确标注"若每请求无缓存重发的输入成本估算"(用 `internal/pricing` 某参考模型 input 价)。避免把"常驻 prefix(可缓存)"误述成"每请求成本"。 | C3 |

## 可自由裁量(实现期定,不阻塞批准)

- `skills` 表具体列顺序、索引名;findings `check_type` 枚举字符串字面量。
- 前端三视图是 tab 还是单页分区;复用 `TermTable`/`TopSessionsTable` 还是新建轻表。
- SkillSyncer 周期(建议跟随 session 的 15min)与是否 watch catalog 目录(建议 watch catalog.json + SKILL.md)。

---

## 边界

**Goals**
- C1 浏览器可查 skill 清单(name/domain/role/enabled),比静态 catalog 更新活。
- C3 各 skill description 常驻 token 数 + 总量 + 占窗口比,用数据终结"常驻成本"争论。
- C2 软链完整性 / wiring(catalog↔frontmatter↔目录名一致)/ 重复 / 孤儿 / legacy 悬挂体检。
- C4 出**设计**:复用 `tool_calls.skill_name` 的 skill 专属调用聚合(不实现)。
- 双后端 parity;新功能**对现有 analytics 零污染**(可证)。

**Non-Goals**
- 不复用 sessions/messages 承载 skill;不给假 message 写 token_usage。
- 不改 `NormalizeToolCategory` 含义;不动现有 `/analytics/tools`。
- 不产品化 agent-health 的 hooks/MCP/settings 检查(D4)。
- C4 不实现;`skill_invocations` 物化 fact 表不做(仅记为"性能/归档需要时再上")。
- 不做动态 per-session capsule 注入追踪(PRD 标高难度,后置)。
- 不把 skills 接进 parser 的 AgentType Registry(见下"架构决策")。

**Constraints**
- `CGO_ENABLED=1` + `fts5` + `kit_posthog_disabled` 构建标签不变。
- 优先 stdlib;唯一可能新增直接依赖 = D1 的 tokenizer(`gopkg.in/yaml.v3 v3.0.1` 已在 go.mod,frontmatter 解析免新增)。
- Go 改动后 `go fmt ./...` + `go vet ./...`;新功能必须带单测(testify,`testDB(t)`)。

---

## 架构决策(ADR-lite):skills 不进 AgentType Registry,另起 `internal/skills` 包

- **难回退**:若先把 skills 塞进 `parser.Registry`(`types.go:69`)当伪 agent,后期剥离要改 discovery/sync/config 多处。
- **缺上下文会令人意外**:未来读者会问"skills 明明是参考数据,为什么在 agent 注册表里?"
- **真实 trade-off**:Registry 复用现成 discovery/watch;但 Registry 的 `DiscoverFunc` 产出的是 session,会把 skills 拖进 session 数据域——与"禁止伪 session"同源的污染风险。

**裁决**:新建 `internal/skills` 包(catalog reader + frontmatter 解析 + health checks + tokenizer),由 `main.go` 在 session sync engine **之外**独立调度。symlink-aware 复用 `discovery.go` 的 `filepath.EvalSymlinks` 模式(`discovery.go:881` 等),但**不经** `parser.Registry`。这是对 brief"扩展点含 parser/types.go+discovery.go"的有理由偏离,与"不污染 sessions"决策同逻辑延伸。

---

## 场景化推演(压测抽象方案,含失败路径)

| Scenario | Actor / Context | Step-by-step path | System touchpoints | Exposed issue | Requirement / Contract |
|---|---|---|---|---|---|
| S1 正常清单 | 用户开 skills 页 | 启动→SkillSyncer 读 catalog.json(52 条)+ 各 SKILL.md frontmatter→upsert `skills`→GET /api/v1/skills→表格渲染 | skills 表、ListSkills、router"skills" | 需要一次"全替换"upsert 语义(skill 删除后清掉旧行) | C1: ReplaceSkills 全量替换;UI 表含 name/domain/role/enabled/tokens |
| S2 软链断裂(失败路径) | catalog 某条 `path` 指向已删/断链目录 | SkillSyncer 对该条 `EvalSymlinks` 失败→**不 crash**,记 `skill_health` 一条 `symlink_broken`,该 skill `file_present=0` | skills.file_present、skill_health | 体检必须容错单条失败、继续处理其余 51 条 | C2: 单条解析失败降级为 finding,不中断整批;fail-soft |
| S3 wiring 漂移(失败路径) | 某 SKILL.md frontmatter `name` 与 catalog `name`/目录名不一致 | 对比三者→不一致→`name_mismatch` finding(severity=error) | skill_health、skills.frontmatter_name | 需要三方一致性校验,且 detail 带三个值 | C2: name_mismatch 检查含 catalog_name/frontmatter_name/dir_basename |
| S4 成本争论 | 用户想知道 52 条描述常驻多少 token | SkillSyncer tokenize 每条 description→存 `description_tokens`→GET /api/v1/skills/cost→显示总 token + 占 200k 比 + 按域柱状 | skills.description_tokens、GetSkillTokenCost | tokenizer 对中文必须可信;总数应落在 PRD 实测 ~1400-2000 量级 | C3: 总 token 与 PRD 量级吻合(spike 验证);标注"近似,非 Anthropic 分词器" |
| S5 目录未配置(失败路径) | 用户机器无 `~/.dotfiles/coding-skills` | SkillSyncer 探测不到→跳过,skills 表空,session 同步**照常** | config、SkillSyncer | 绝不能因 skills 缺失拖垮主功能 | D3: fail-open,页面显示"未配置";不阻塞 |
| S6 PG serve 模式 | 用户用 `pg serve` 看共享库 | `pg push` 把 skills/skill_health 全量替换进 PG→PG store ListSkills 读 PG | postgres/schema、postgres/skills、push | PG 端需镜像表 + store 方法 + push 纳入 | D5: 双后端 parity,push 全量替换小表 |
| S7 零污染回归 | 验证现有 analytics 不受影响 | 加 skills 数据后跑 GetStats/GetAgents/GetAnalyticsTools | stats、analytics | 必须证明 session_count/agent 列表/tool 聚合数字不变 | 见 Verification V1 |

---

## 需求 / 机制 fit 矩阵

需求:
- **R1** 浏览器可看 skill 清单(更新活,非静态 catalog)。
- **R2** 可看各 skill 描述常驻 token + 总量 + 占窗口比。
- **R3** 可看体检结果(软链/wiring/重复/孤儿/legacy)。
- **R4** 现有 analytics 零污染。
- **R5** SQLite/PG 双后端一致。
- **R6** C4 调用统计有可落地设计(不实现)。

机制:
- **S-A** `internal/skills` 包:catalog+frontmatter reader、health checks、tokenizer。
- **S-B** `skills` 维度表 + `skill_health` 表(schema.sql / postgres schema.go)。
- **S-C** Store 读方法 ListSkills/GetSkill/GetSkillHealth/GetSkillTokenCost(SQLite+PG)。
- **S-D** `/api/v1/skills/*` 路由(huma_routes_skills.go)。
- **S-E** 前端 `skills` 路由 + SkillsPage 三视图。
- **S-F** SkillSyncer 独立调度(main.go,session sync 之外)+ ReplaceSkills/ReplaceSkillHealth 写入 + pg push 纳入。
- **S-G**(设计)GetSkillUsage:join `tool_calls.skill_name`→sessions→left join skills。

| | S-A | S-B | S-C | S-D | S-E | S-F | S-G |
|---|---|---|---|---|---|---|---|
| R1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| R2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| R3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| R4 | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| R5 | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| R6 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

(R4 由 S-B 隔离建模 + S-F 独立写路径共同保证;每行有 ✅,无空行;无整列全 ❌。)

---

## 数据模型(落到具体结构)

### SQLite schema(`internal/db/schema.sql` 末尾追加;CREATE IF NOT EXISTS,自动建表,不 bump dataVersion)

```sql
-- Skills dimension table: slowly-changing reference data synced
-- from the coding-skills catalog. NOT sessions/messages.
CREATE TABLE IF NOT EXISTS skills (
    name                 TEXT PRIMARY KEY,   -- catalog name == frontmatter name == dir basename (体检校验)
    catalog_path         TEXT NOT NULL DEFAULT '',  -- catalog.json 里的 relative path
    resolved_path        TEXT NOT NULL DEFAULT '',  -- EvalSymlinks 后的绝对路径
    domain               TEXT NOT NULL DEFAULT '',
    role                 TEXT NOT NULL DEFAULT '',   -- canonical|legacy|brand-exception
    migration_state      TEXT NOT NULL DEFAULT '',   -- catalog.migration.state
    migration_canonical  TEXT NOT NULL DEFAULT '',   -- catalog.migration.canonical
    description          TEXT NOT NULL DEFAULT '',    -- SKILL.md frontmatter description
    frontmatter_name     TEXT NOT NULL DEFAULT '',    -- 实际 frontmatter name(供 wiring 校验)
    description_tokens   INTEGER NOT NULL DEFAULT 0,  -- C3 派生,SkillSyncer 写入
    tokenizer            TEXT NOT NULL DEFAULT '',    -- provenance, e.g. 'o200k_base'
    catalog_present      INTEGER NOT NULL DEFAULT 0,  -- 出现在 catalog.json
    file_present         INTEGER NOT NULL DEFAULT 0,  -- SKILL.md 实际存在
    health_error_count   INTEGER NOT NULL DEFAULT 0,  -- rollup,便于清单页角标
    source_mtime         INTEGER NOT NULL DEFAULT 0,
    synced_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_skills_domain ON skills(domain);
CREATE INDEX IF NOT EXISTS idx_skills_role   ON skills(role);

-- Skill health findings: one row per detected issue.
CREATE TABLE IF NOT EXISTS skill_health (
    id          INTEGER PRIMARY KEY,
    skill_name  TEXT,                         -- nullable(catalog 级 finding,如孤儿)
    check_type  TEXT NOT NULL,                -- symlink_broken|name_mismatch|missing_frontmatter|
                                              -- duplicate_name|orphan_file|orphan_catalog|legacy_dangling_canonical
    severity    TEXT NOT NULL DEFAULT 'warn', -- error|warn|info
    message     TEXT NOT NULL DEFAULT '',
    detail      TEXT NOT NULL DEFAULT '',     -- JSON(三方值等上下文)
    detected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_skill_health_skill ON skill_health(skill_name);
CREATE INDEX IF NOT EXISTS idx_skill_health_type  ON skill_health(check_type);
```

PG 镜像:`internal/postgres/schema.go` 的 `coreDDL` 常量追加等价 DDL(`TEXT`/`INTEGER`→PG `TEXT`/`INT`,时间用 `TIMESTAMPTZ`/字符串按现有 sessions 镜像惯例)。

### Store 接口(`internal/db/store.go` 追加,SQLite+PG 双实现)

读方法(进 `Store` interface):
- `ListSkills(ctx, SkillFilter) ([]Skill, error)` — filter: Domain/Role/Enabled。
- `GetSkill(ctx, name string) (*Skill, error)`。
- `GetSkillHealth(ctx, SkillHealthFilter) (SkillHealthReport, error)` — findings + 按 severity/check_type rollup。
- `GetSkillTokenCost(ctx) (SkillTokenCostReport, error)` — total tokens、by-domain、per-skill(排序),含 tokenizer provenance。

写方法(仅 SkillSyncer 用,实现在 `internal/db/skills.go` 的 `*DB` 上,PG 经 push 不需要写接口):
- `ReplaceSkills(ctx, []Skill) error` — 事务内 `DELETE` + 批量 `INSERT`(全量替换,catalog 删除即清行)。
- `ReplaceSkillHealth(ctx, []SkillHealthFinding) error` — 同上。

新模块文件:`internal/db/skills.go`(类型 + SQLite 查询)、`internal/postgres/skills.go`(PG 镜像,`$n` 占位 + paramBuilder)。参照 `secret_findings_list.go` 的自包含模块模式。`store_contract_test.go` 加 parity 用例。

### 路由(`internal/server/huma_routes_skills.go`,在 `huma_route_groups.go:registerTypedAPIRoutes` 注册 `s.registerSkillRoutes()`)

```
GET /api/v1/skills          → []Skill            (C1)
GET /api/v1/skills/{name}   → Skill              (C1)
GET /api/v1/skills/cost     → SkillTokenCostReport (C3)
GET /api/v1/skills/health   → SkillHealthReport  (C2)
GET /api/v1/skills/usage    → 501/占位            (C4 设计,MVP 不实现)
```

handler 为 `*Server` 方法,经 `s.db.ListSkills(...)` 调 Store,`jsonOutput[T]` 包裹(照 `huma_routes_analytics.go` 模式)。

### 前端(`frontend/src/`)

- `lib/stores/router.svelte.ts`:`Route` 联合类型加 `"skills"`,`VALID_ROUTES` Set 加 `"skills"`。
- `App.svelte` 路由 switch 加 `{:else if router.route === "skills"}<SkillsPage />`。
- `lib/components/skills/SkillsPage.svelte`:三视图(tab 或分区)——清单表 / 静态成本(总数+占窗口比+按域柱状,复用简单 SVG 模式如 `CostTimeSeriesChart`)/ 体检 findings(按 severity 分组)。
- `lib/stores/skills.svelte.ts`:fetchAll → 三个 GET,AbortController per endpoint(照 `usage.svelte.ts`)。
- API client:OpenAPI 生成或手写 `lib/api/types/skills.ts`,经 `callGenerated()`。

### 配置(`internal/config/config.go`)

新增 `SkillsCatalogDir`:env `AGENTSVIEW_SKILLS_DIR` + flag `--skills-dir`,默认探测 `~/.dotfiles/coding-skills`(`filepath.Join(home, ".dotfiles/coding-skills")`)。不存在→空,fail-open。

### 同步流程

```mermaid
flowchart TD
    A[main.go 启动] --> B{SkillsCatalogDir 存在?}
    B -- 否 --> Z[跳过, skills 表空, fail-open]
    B -- 是 --> C[SkillSyncer.Run]
    C --> D[读 catalog.json 52 条]
    D --> E[每条: EvalSymlinks 解析 path]
    E --> F[读 SKILL.md frontmatter yaml.v3]
    F --> G[tokenize description → tokens]
    G --> H[run health checks → findings]
    H --> I[ReplaceSkills + ReplaceSkillHealth 事务全替换]
    I --> J[pg push 时纳入 skills/skill_health]
    C -. 周期 15min / watch catalog.json+SKILL.md .-> C
    K[session sync engine] -. 完全独立, 互不影响 .-> C
```

---

## Phases

### Phase C1 — skill 清单(MVP 骨架)
**改**:config(SkillsCatalogDir)、`internal/skills`(reader+frontmatter,symlink-aware)、`schema.sql`+`postgres/schema.go`(skills 表)、`db/skills.go`+`postgres/skills.go`(Skill 类型 + ListSkills/GetSkill + ReplaceSkills)、`store.go`(接口)、SkillSyncer + main.go 调度、`huma_routes_skills.go`(GET /skills、/skills/{name})、前端 router+App+SkillsPage 清单视图+skills store。
**验证**:`make test`(skills 包 + db 单测,`testDB(t)`);手动 `make dev` 开 skills 页见 52 条;`store_contract_test.go` parity。
**依赖**:D2(不 bump)、D3(config)、D5(parity)。

### Phase C3 — 静态 token 成本
**改**:tokenizer(D1,藏 interface)、`description_tokens`/`tokenizer` 列已在 C1 schema、SkillSyncer 填 tokens、`GetSkillTokenCost`(SQLite+PG)、`GET /skills/cost`、SkillsPage 成本视图(总数+占窗口比+按域柱状,$ 次要标注 D6)。
**Spike(先做)**:用真 tokenizer 跑 52 条真实中文 description,核总 token 落在 PRD ~1400-2000 量级;偏离过大则回 D1。
**验证**:单测断言已知短描述 token 数稳定;UI 总数与 spike 吻合;断言 token 计算**不读/不写** messages/usage_events(零污染)。
**依赖**:D1、D6。可与 C2 并行(若 D1 卡住,先做 C2)。

### Phase C2 — 健康体检
**改**:`internal/skills` health checks(symlink_broken/name_mismatch/missing_frontmatter/duplicate_name/orphan_file/orphan_catalog/legacy_dangling_canonical)、`skill_health` 表已在 C1 schema、`GetSkillHealth`(SQLite+PG)、`ReplaceSkillHealth`、`GET /skills/health`、SkillsPage 体检视图(按 severity 分组)。
**验证**:单测构造断链/改名/重复/孤儿 fixture(`t.TempDir()` 造假 catalog+SKILL.md),断言对应 finding 产出且不中断整批(S2/S3)。
**依赖**:D4(范围)。

### Phase C4 — 使用统计(仅设计,不实现)
**产出**:在本 spec 追加或独立设计 note —— `GetSkillUsage(ctx, SkillUsageFilter)`:`SELECT skill_name, count(*) FROM tool_calls WHERE skill_name IS NOT NULL`(用 `idx_tool_calls_skill`)`JOIN sessions`(取 agent/project/time 过滤)`LEFT JOIN skills`(取 domain/role)。**不改** `NormalizeToolCategory`。新 `/api/v1/skills/usage` + UI。
**Spike(实现前必做)**:取 kilo/opencode/codex/droid 各一份真 session,验 `tool_calls.skill_name` 是否落值(R5 剩余未验证项);定 C4 跨 agent 范围(准/CC-only/lossy)。
**测量口径(写进 UI)**:只数走 skill 机制的调用;模型 inline 完成不计入。**"低调用数 ≠ 能力没用",不可据此单杀技能**。
**物化 `skill_invocations` fact 表**:仅当性能/历史归档需要时再上,MVP/本设计不做。

---

## 风险与验证

### Risks

- **R-污染(最高)**:任何让 skills 数据进 sessions/messages 的捷径都会污染 stats trigger + 全量 analytics。**缓解**:独立表 + 独立写路径 + 独立 syncer;验证 V1 强制回归。
- **R-双后端漂移**:SQLite 加了、PG 漏了,或查询形状不一致。**缓解**:`store_contract_test.go` parity 用例覆盖 skills;PG DDL 与 push 同 PR 落地(D5)。
- **R-tokenizer(D1)**:tiktoken ≠ Anthropic 实际分词器,数字是近似;中文 token 比英文高。**缓解**:interface 隔离可换;UI 明确标"近似,非 Anthropic 精确分词器";C3 spike 先对 PRD 量级。
- **R-C4 跨 agent 未验证**:非 CC agent 是否落 `skill_name` 仍 `[未验证]`。**缓解**:C4 spike 前置;MVP 不依赖。
- **R-fail-open**:skills 目录缺失/损坏不得拖垮 session 同步或 server 启动。**缓解**:S5 场景 + D3 fail-open 单测。

### Premise Collapse

- `If schema.sql 每次 Open 幂等重跑(已验证 db.go:1449 + CREATE IF NOT EXISTS),新表自动建。` —— **已验证为事实**,故 MVP 不 bump dataVersion、不触发 session resync。若该前提被未来重构破坏(改成只在 fresh DB 跑 schema),则需显式加建表迁移。
- `If tiktoken-go o200k 对中文 description 的 token 数与 Anthropic 实际相差可接受(同量级),则可作"终结成本争论"的近似。If does not hold, 数字失去说服力,需换 count_tokens API 或标更大误差带。` —— C3 spike 前置。
- `If kilo/opencode/codex/droid 的 parser 也落 tool_calls.skill_name,则 C4 跨 agent 可用。If does not hold, C4 退化 CC-only,UI 须标口径。` —— C4 spike 前置。

### Verification

- **V1 零污染(必做,acceptance)**:同一 DB,导入 skills 数据前后,断言 `GetStats`(session_count/message_count)、`GetAgents` 列表、`GetAnalyticsTools` 聚合**数字完全不变**;断言 `sessions`/`messages`/`tool_calls` 行数不因 skill 同步增加;断言 skills 表无 'session'/'message' 伪行。SQLite+PG 各跑一遍。
- **V2 C1**:SkillSyncer 跑后 `skills` 行数 == catalog 条数(52);ListSkills 返回 name/domain/role 正确;catalog 删一条后再同步,旧行被清(全量替换语义)。
- **V3 C3**:已知短描述 token 数稳定可断言;总 token 与 spike 量级吻合;C3 路径不触碰 messages/usage_events。
- **V4 C2**:fixture(断链/改名/重复/孤儿/legacy 悬挂)各产出对应 finding;单条失败不中断整批。
- **inner-loop**:`make test`(`fts5,kit_posthog_disabled`)、`make lint`、`go fmt`/`go vet`;PG parity 经 `make test-postgres`(pgtest tag)。
- **acceptance**:`make dev` + 浏览器开 skills 页,三视图各自有数据(V2/V3/V4 的人工可观察证据)。

### Rollback

- 纯增量、无破坏性迁移:`skills`/`skill_health` 是新表,不动既有表/列/trigger。
- 回滚 = 还原本次代码 + `DROP TABLE skills; DROP TABLE skill_health;`(独立表,无外键指向核心域,删除不影响 sessions/messages/tool_calls)。
- 未 bump dataVersion → 回滚不触发任何 session 重解析。
- PG 端同样 DROP 两表;push watermark 不受影响(skills 全量替换,无水位)。

---

## 自审清单(think-plan §5)

- [x] 读者(agentsview 维护者 / 实现 agent)、产物(集成 spec)、最小可验收(三视图可见 + V1 零污染)已明确。
- [x] 已锁定 / 待决策(D1-D6)/ 可自由裁量已分区。
- [x] 7 个具体场景含 4 条失败路径压测。
- [x] 无 TBD/TODO 占位;每 Phase 有文件路径 + 验证方式。
- [x] 排除项显式(Non-goals)。
- [x] 方向无环(C1→C3/C2 并行→C4 设计);垂直切片(按视图,非按层)。
- [x] Mermaid 同步流程图已附。
- [x] 改动局部,核心 session 域零触碰。
- [x] 矛盾(brief vs 真代码:dataVersion / symlink)已显式列入纠正区,未沉默选边。

---

```yaml
# spec-contract
checks:
  - "V1: 导入 skills 前后 GetStats/GetAgents/GetAnalyticsTools 数字完全不变(SQLite+PG)"
  - "V1: sessions/messages/tool_calls 行数不因 skill 同步增加;skills 表无伪 session/message 行"
  - "V2: SkillSyncer 后 skills 行数==catalog 条数;catalog 删条后再同步旧行被清"
  - "V3: 已知短描述 token 数可稳定断言;C3 路径不读写 messages/usage_events"
  - "V4: 断链/改名/重复/孤儿/legacy 悬挂 fixture 各产出对应 skill_health finding,单条失败不中断整批"
  - "skills 页三视图(清单/成本/体检)在 make dev 下各有数据"
  - "store_contract_test.go 覆盖 ListSkills/GetSkill/GetSkillHealth/GetSkillTokenCost 的 SQLite/PG parity"
non_goals:
  - "不复用 sessions/messages 承载 skill;不给假 message 写 token_usage"
  - "不改 NormalizeToolCategory;不动现有 /analytics/tools"
  - "不实现 C4;不物化 skill_invocations fact 表"
  - "不产品化 agent-health 的 hooks/MCP/settings 检查"
  - "不把 skills 接进 parser AgentType Registry"
  - "不做动态 per-session capsule 注入追踪"
validation_commands:
  - "make test"
  - "make test-postgres"
  - "make lint"
  - "go fmt ./... && go vet ./..."
  - "make dev  # 浏览器开 skills 页人工验收"
locked_decisions:
  - "数据建模 B-hybrid:C1/C2/C3 独立 skills+skill_health 表;C4 复用 tool_calls.skill_name"
  - "禁止伪 session;禁止改 NormalizeToolCategory;静态成本独立于 usage/cost 管线"
  - "SQLite+PG parity 必保;DuckDB 只读镜像跟随"
  - "MVP 不 bump dataVersion(纠正 brief,已验 db.go:1449 幂等建表)"
  - "skills 不进 AgentType Registry,另起 internal/skills 包"
derisk_spikes:
  - type: "第三方库实际契约 + 数据形态边界(CJK)"
    question: "tiktoken-go o200k 对 52 条真实中文 description 的总 token 是否落在 PRD ~1400-2000 量级?"
    method: "实现前用选定 tokenizer 跑真实 catalog,对 PRD 实测量级"
    status: "spike-before-implement"
  - type: "第三方 API/SDK 实际契约"
    question: "kilo/opencode/codex/droid 的 parser 是否也落 tool_calls.skill_name?"
    method: "取各一份真 session 查 tool_calls.skill_name 是否非空"
    status: "deferred(C4 实现前必做;MVP 不依赖)"
  - type: "schema 迁移机制"
    question: "新表是否在现有 DB 的下次 Open 自动创建,无需 bump dataVersion?"
    method: "读 db.go init() 流程"
    status: "verified(db.go:1449 每次 Open Exec schemaSQL + CREATE IF NOT EXISTS)"
```

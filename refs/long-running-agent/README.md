# Long-Running Agent 参考笔记

来源：本地文章草稿 `草稿_20260430_Long-Running-Agent/article.html`。

> 说明：本文是对该草稿内容的工程化摘录。文章中关于未公开产品、泄露源码、第三方实验数据的描述，在本文中均按 `[未验证]` 或 `[推断]` 处理；不能当作官方事实直接引用。

## 核心问题

Long-running agent 不是“让一个更聪明的 agent 跑更久”，而是要解决三类系统性故障：

| 墙 | 问题 | 典型症状 | 工程化补丁 |
|---|---|---|---|
| 上下文腐化 | 长任务中上下文越堆越散，早期约束被稀释 | agent 忘记边界、重复探索、状态报告污染规则文件 | context compaction、只回灌摘要、文件系统作为 SSOT |
| 无持久状态 | 新会话失忆，交接依赖模型记忆 | 重复做同一件事、不知道上一轮为何这样改 | append-only logs、progress 文件、spec / plan / assertion 文件 |
| 无自我验证 | agent 自己觉得完成，但实际未满足验收 | “完成感”早于真实交付 | Judge / verifier subagent、Stop hook、外部验证脚本 |

## 三层分离架构

文章归纳的通用结构：

| 层 | 职责 | dotfiles 映射 |
|---|---|---|
| Brain | 模型 + 推理循环，决定下一步 | `skills/`、custom droids、mission runtime |
| Hands | 沙箱、工具、命令执行、文件修改 | Droid tool layer、scripts、browser/TUI skills |
| Memory | append-only 事件日志、状态文件、spec/plan | `docs/`、`refs/`、mission artifacts、future `.long-loop/` |
| Judge | 独立验证者，不参与执行，只判断是否继续/停止 | `guard-verify`、`guard-check`、review/security validators |

关键判断：[推断] 仅有 Brain + Hands + Memory 仍不足以长跑，必须有独立 Judge，否则 Memory 只是记录“agent 说自己完成了”。

## Cursor 拓扑演进

文章描述的三版模式：

1. **Flat multi-agent**：多个 worker 平等协作，容易进入锁和协调地狱。
2. **Integrator centralization**：所有结果汇入中央整合者，Integrator 进入关键路径，形成串行瓶颈。
3. **Planner / Worker / Judge**：Planner 拆独立任务，Worker 自行提交共享状态，Judge 旁路采样，发现跑偏就停止单条路径。

适合吸收的原则：

- Worker 不应该互相等；任务拆分要尽量独立。
- Judge 不应负责合并结果；否则会变成 Integrator 瓶颈。
- Judge 慢一点可以接受；它是旁路安全机制，不是主流程收口点。

## Ralph Loop

最小形式：

```bash
while :; do <agent> < PROMPT.md; done
```

完整版不是无限循环，而是文件系统驱动的四阶段 harness：

1. **Requirements**：用独立 context 消化原始资料和 breaking changes。
2. **Planning**：把资料压缩为 `specs/<name>.md`，下游只读 spec。
3. **TODO**：把 spec 转成 `IMPLEMENTATION_PLAN.md`。
4. **Incremental Loop**：每轮只做一个 todo，跑验证，更新 plan，提交存档点。

### Ralph 三件套

| 文件 | 作用 | 约束 |
|---|---|---|
| `PROMPT.md` | 每轮完整重读的静态指令 | 短、硬、引用其它文件，不不断膨胀 |
| `fix_plan.md` / `IMPLEMENTATION_PLAN.md` | 按优先级排序的 todo | 一轮只消一个 item；完成后立即更新 |
| `AGENT.md` / `ASSERT.md` | build/test/验收规则 | 只放规则和命令，不放状态报告 |

适用前提：

- 目标明确。
- 验收命令明确。
- 预算上限明确。
- 可接受每轮 commit 作为恢复点。

不适用：

- 开放探索任务。
- 没有验收标准的“你试试看”。
- 需要频繁人类产品判断的任务。

## Claude Code / Codex 路径

新版文章把实践路线拆成三档：

1. **Ralph Loop**：今晚就能抄的最小闭环。
2. **CC / Codex 原生扩展点**：规则文件、hooks、subagents、headless/action/SDK。
3. **规模化形态**：托管服务、云端 sandbox、自研多 agent 编排、自托管 runtime。

这三档不互斥。合理路线是先把边界 / 验收 / 预算落盘，再逐步补 hooks、Judge、runtime。

### Claude Code vanilla

文章给出的组件：

- `CLAUDE.md`：项目规则、目录结构、禁动作、测试命令。
- Hooks：`PostToolUse` 做格式化 / 小测试，`Stop` 在“完成”时检查 todo 和验证结果。
- Sub-agents：隔离资料查找、测试、review。
- Headless / GitHub Action / SDK：外部入口。

[推断] 对 dotfiles 的启发不是照搬 Claude hooks，而是把相同功能放到 Droid 可执行的 scripts / skills / mission validation 中。

### Codex `/goal`

文章称 Codex CLI `0.128.0` 引入 `/goal`，通过 continuation / budget prompts 自循环运行。[未验证] 该版本和行为需要后续用官方文档或本地 CLI 验证。

### Droid / 通用 CLI

只要 agent 支持：

- 非交互入口；
- 从文件或 stdin 读 prompt；
- 能读写文件；
- 能在命令结束后返回；

就能用 Ralph 风格外层 harness 包装。

## 对本 dotfiles 的可吸收设计

### 1. 新增 long-loop 参考/命令骨架

[推断] 可新增 `commands/long-loop.md` 或 `skills/dev-long-loop/`，但不应一开始做重型 runtime。先从“生成 loop workspace + prompt 三件套 + 验证脚本”开始。

明确用法：

```bash
/long-loop help
/long-loop plan "实现 X 长任务"
/long-loop approve
/long-loop run --once --agent-cmd '<agent command>'
/long-loop run --max-iterations 3 --max-minutes 45 --agent-cmd '<agent command>'
/long-loop status
/long-loop tail --lines 80
/long-loop watch --interval 10
/long-loop watch --interval 10 --iterations 1
/long-loop pause --reason "调整计划"
/long-loop stop --reason "需要人工判断"
```

建议 workspace：

```text
.long-loop/
├── PROMPT.md
├── SPEC.md
├── IMPLEMENTATION_PLAN.md
├── ASSERT.md
├── progress.md
├── logs/
│   └── YYYY-MM-DD.md
└── state.json
```

### 2. Brain / Hands / Memory / Judge 映射

| 架构角色 | 初版实现 |
|---|---|
| Brain | Droid 非交互命令，读取 `.long-loop/PROMPT.md` 和审批后的计划 |
| Hands | 当前工具层 + scripts |
| Memory | `.long-loop/progress.md` + append-only logs |
| Judge | 每轮后强制 `scripts/run-verify.sh` + `guard-diff-scan` + 可选 review subagent |

### 3. 每轮协议

每一轮只允许：

0. 先生成 `SPEC.md` / `IMPLEMENTATION_PLAN.md` / `ASSERT.md`，人工确认后执行 `approve`。
1. 读取 `PROMPT.md`、`SPEC.md`、`IMPLEMENTATION_PLAN.md`、`ASSERT.md`。
2. 选择最高优先级的一个未完成 item。
3. 实现该 item。
4. 运行该 item 的最小验证。
5. 更新 `IMPLEMENTATION_PLAN.md` 和 `progress.md`。
6. 全部验证通过后 commit；失败则写 Handoff 并停止或进入下一轮修复。

### 4. Stop 条件

必须停止的条件：

- `IMPLEMENTATION_PLAN.md` 没有未完成 item。
- 验证连续失败 2 次。
- 预算达到时间 / 金额 / 轮数上限。
- diff scan 命中未处理调试残留。
- 工作树出现非本轮引入的冲突或不明修改。
- 人工 `pause` 介入，等待修改计划并重新 `approve`。
- 需要用户产品判断或外部副作用授权。

### 5. 预算文件

`ASSERT.md` 应明确：

- 最大轮数。
- 最大 wall clock 时间。
- 最大 spend/token 预算（如果工具可观测）。
- 每轮必须跑的验证命令。
- 不允许触碰的目录和外部系统。

## 建议实施路线

### Phase 1：文档与手动流程

- 新增 `docs/software-engineering-research/long-running-agent.md`，沉淀本文规则。
- 新增 command 草案：生成 `.long-loop/` 三件套，不自动循环。
- 先让人手动运行 1-3 轮，观察文件格式是否够用。

### Phase 2：轻量脚本 harness

- 新增 `scripts/long_loop.sh`：
  - 读取 `PROMPT.md`；
  - 调用用户指定 agent 命令；
  - 每轮后跑验证；
  - 达到 stop 条件退出。
- 不默认 push；commit 也要可配置。

### Phase 3：Judge 增强

- 引入 `guard-verify` / `guard-diff-scan` / `guard-review` 作为每轮 Judge。
- 对失败写标准 Handoff。
- 支持 resume：从 `.long-loop/state.json` 恢复。

## 风险与坑

- [确认] 无限循环不是能力，是风险；必须有轮数、时间和预算上限。
- [确认] 状态报告不能污染规则文件；`AGENT.md` / `ASSERT.md` 只写规则，状态写 progress/logs。
- [确认] 一轮多个 todo 会显著增加漂移和验证困难。
- [推断] 在当前 Droid 环境里，直接默认 `git push` 风险过高；初版最多自动 commit，不自动 push。
- [推断] 如果没有独立 Judge，long-loop 最终会退化成“模型自评完成”。

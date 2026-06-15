# 从 Ralph 吸收：dev-long-run 的提升建议

- 对照对象：`refs/frankbria/ralph-claude-code`（分析见 [`docs/refs-details/frankbria/ralph-claude-code.md`](../refs-details/frankbria/ralph-claude-code.md)）
- 被改对象：`coding-skills/dev-long-run/`（`SKILL.md` / `lr.py` / `docs/specs/dev-long-run/overview.md`）
- 文档状态：建议 1、2 **已实现**(2026-06-12,见 spec L26 + `lr.py` `verify_fingerprint`/`update_stuck`/`summarize_metrics`/`cmd_stats` + `test_lr.py` StuckDetection/SummarizeMetrics 测试);3-6 **未实现**。每条标了证据来源和置信度。

## 0. 先划清边界：哪些**不要**搬（防华而不实）

两个系统哲学相反——Ralph 是**无人值守自主循环**，我们是**人在环监督 + 硬门禁**。以下 Ralph 的卖点对我们是**降级或无关**，明确不搬：

| Ralph 特性 | 为什么不搬 |
|---|---|
| 自主退出启发式（completion_indicators 计数 + EXIT_SIGNAL） | 我们有"每 phase 人工确认 + L23 硬门禁（verify 真跑/blocker ID 对账/commit 证据）"，比启发式**强**。搬启发式 = 给硬门禁开后门，纯降级。 |
| Docker / E2B 沙箱 | 我们用 worktree 隔离，更轻且贴合监督模式。沙箱是为"丢进 CI 无人看管"准备的，我们用户全程在场。 |
| 速率限制（calls/tokens per hour） | 我们是人工节奏（每 phase 停等用户），不是机器狂刷，限流无意义。 |
| 多 issue 队列 + 依赖图调度 | 我们是"单任务多 phase"，phase 顺序已由 planner 定。队列是 Ralph 批处理多 issue 的形态，scope 不同。 |

**只搬"机械可靠性"那几处——Ralph 在这上面确实比我们成熟。** 共性是：**把现在靠 orchestrator（我）记忆/肉眼判断的东西，变成磁盘上可计算的确定信号**。这条恰好踩中我们自己的红线"记忆不可信 / SSOT"。

---

## 1. 【高】卡死/失败计数器持久化到磁盘（borrow: circuit_breaker）

### 现状缺口
- `SKILL.md` 的停止条件写了"**连续 2 次验证失败**"。但**谁来数这个 2**？是 orchestrator（我）从对话记忆里数。
- 全局规则明确"你的记忆不可信"。一个靠记忆维护的计数器，跨 compact、跨 resume 会丢——这正是我们自己反复强调要避免的。
- 在 phase 内的 `send(review) → coder 改 → verify` 回合里，如果 coder 反复改、反复在**同一个失败点**栽，目前没有确定性信号告诉我"这是在原地打转，该 escalate 了"，全靠我主观感觉。

### Ralph 怎么做（已核实 `lib/circuit_breaker.sh:151-336`）
- 跨轮持久化 `consecutive_no_progress` / `consecutive_same_error` 到状态文件。
- 进展信号四选一即重置计数（`files_changed>0` / 有完成信号 / 报告改了文件 / 不在反问）。
- 错误指纹比对（`detect_stuck_loop`）：要求"当前所有错误行都出现在最近 3 个历史输出里"才判 stuck，刻意防"错误在演化"被误判为卡死。

### 落点（具体、最小）
- `lr.py verify` 每次跑完，把**失败摘要的指纹**（如 verify.json 里失败用例名/首条 error 行的 hash）写进 phase 状态：`phases/<id>/stuck.json`，字段 `{consecutive_fail, last_error_fingerprint}`。
- 规则：本轮 verify 通过 → 清零；失败且指纹与上轮**相同** → `consecutive_fail++`；失败但指纹**不同** → 重置为 1（错误在变 = 还在推进，不算卡死，这点直接抄 Ralph）。
- `lr.py gate` / `await` 在 `consecutive_fail >= 2` 时返回一个**明确的 STUCK 信号**（带指纹和历史），orchestrator 看到就按 `/think-unstuck` escalate，而不是凭感觉。
- **置信度 [高]**：和我们既有停止条件语义完全一致，只是把"记忆计数"换成"磁盘计数"，零哲学冲突，纯增可靠性。落地小（一个 json + verify 时算个 hash）。

---

## 2. 【高】per-phase / per-iteration 结构化 metrics（borrow: metrics.jsonl, Issue #21）

### 现状缺口
- 我们有 `state.json`、`verify.json`、`logs.md`，但**没有一条 append-only 的机器可读运行流水**。
- 想回答"这次 run 跑了几个 phase、每个 phase 改了多少文件、verify 重试几次、卡过几次"——目前得翻 logs.md 散文，或靠我复述。

### Ralph 怎么做（已核实 `ralph_loop.sh:827-846` + `ralph-stats.sh`）
- 每轮 `record_loop_result()` 向 `.ralph/logs/metrics.jsonl` 追加一行 JSON（duration、calls、files_modified、success、circuit_breaker_state）。
- `ralph-stats.sh` 读它出汇总。监控面板 2s 刷新读同一份。

### 落点
- `lr.py` 在 phase 关键节点（planner 完成 / coder DONE impl / verify / complete-phase）各追加一行到 `.long-loop/<ws>/metrics.jsonl`：`{phase, role, event, ts, files_changed, verify_ok, blocker_count, consecutive_fail}`。
- 加一个只读子命令 `lr.py stats --workspace <ws>` 出汇总，orchestrator 用它给用户报进度，**不靠记忆复述**。
- **它还顺便喂了第 1 条**（stuck 计数本就是 metrics 的派生）。
- **置信度 [高]**：纯增量、零风险（append-only 文件），直接改善可观测性 + 给用户的进度播报有据可查。和我们"无证据的完成不接受"一脉相承。

---

## 3. 【中高】完成门禁区分 optional / blocking（borrow: Issue #239）

### 现状缺口
- `complete-run` 门禁 = "**fix_plan 全勾** + acceptance 过"。
- 但全局规则又说"未被用户请求的相邻工作只能列为**可选 backlog**，不能默认继续执行"。
- 矛盾：如果 planner 或用户往 fix_plan 里塞了 nice-to-have，当前门禁会**逼着把它们做完**，否则不让收尾——要么超 scope 硬做，要么手动删条目（而我们禁止手翻 fix_plan）。

### Ralph 怎么做（已核实 `_count_blocking_unchecked()` + Issue #239）
- `fix_plan.md` 里 `Optional` / `Future` / `Nice to Have` 标题下的未勾项**不阻塞退出**，awk 维护 `optional_active` 状态只数阻塞项，段名 `OPTIONAL_SECTIONS` 可配。

### 落点
- `lr.py complete-run` / `complete-phase` 数未完成项时，跳过 `## Optional` / `## Backlog` / `## Future` 等约定标题下的条目。
- 收尾时这些项自动进 `BACKLOG.md`（我们已有这个产物 + `CLEANUP_PROPOSAL.md` 习惯），而不是卡住门禁。
- **置信度 [中高]**：和我们"可选 backlog"规则完美对齐，解决一个真实的门禁僵局。唯一要小心的是**别让它变成绕过门禁的后门**——必须约定"只有明确标在 optional 标题下的才豁免，默认全是 blocking"，这点 Ralph 也是这么守的（无标记时等同全量计数）。

---

## 4. 【中】超时用 worktree diff 自动区分"慢"vs"卡"（borrow: productive/idle timeout）

### 现状缺口
- `lr.py await` 有 `4 TIMEOUT` 和 `6 IDLE`，但**区分靠 orchestrator 读 pane tail 主观判**。
- SKILL.md 自己记了个坑：worker 跑大型测试套件时画面静止会被**误判 IDLE**（false-IDLE）。

### Ralph 怎么做（已核实 `ralph_loop.sh` 超时守卫）
- 超时后对比 `.loop_start_sha`，git **有改动** = "productive timeout"（继续），**无改动** = "idle timeout"（失败）。一个 `git diff` 就把"在干活的慢"和"真卡死"分开了。

### 落点
- 我们本来就在 worktree 里，`git diff --stat` 相对"本轮 worker 启动时记录的 SHA"是现成的。
- `lr.py await` 在 TIMEOUT/IDLE 时**自动附带** "自启动以来 worktree 是否有改动 + 改了哪些文件"，把这个客观信号和 pane tail 一起给 orchestrator。有改动 → 大概率 false-IDLE/productive，倾向于调大 timeout 继续；无改动 → 倾向于真卡死。
- **置信度 [中]**：直接缓解我们记在案的 false-IDLE 坑，信号客观。注意它是**辅助信号不是自动决策**——我们是监督模式，最终还是 orchestrator/用户拍板，但给的是事实而非猜测（符合"信息不足先加可观测性"）。

---

## 5. 【中低】repo 级构建/测试命令文件，降低 fresh coder 重新发现成本（borrow: AGENT.md）

### 现状缺口
- 每 phase **fresh coder** 靠 `HANDOFF.md` + spec 续接。但"这个 repo 怎么跑测试 / build / lint"如果每个 fresh coder 都重新摸一遍，是重复开销。
- 我们有 per-phase `verify.sh`，但那是**验收命令**，不等于"日常 build/test/lint 入口"的稳定参考。

### Ralph 怎么做
- `templates/AGENT.md` 持久化项目 setup/test/build 命令，自动维护，跨轮给 fresh agent 看。

### 落点
- scaffold 阶段把探到的 build/test/lint 命令落到 `.long-loop/<ws>/AGENT.md`（或并进 `SPEC_OVERVIEW.md` 一节），fresh coder 的 `[MUST READ]` 加这一项。
- **置信度 [中低]**：部分已被 verify.sh / SPEC_OVERVIEW 覆盖，增益看项目复杂度。属于"锦上添花"，优先级低于 1-4。

---

## 6. 【低 / 待定】权限拒绝作为一等停止信号（borrow: Issue #101/#243）

### 现状缺口
- coder pane 撞上权限确认弹窗时，可能表现为静默 IDLE，我们目前没有专门的"这是权限问题，去调 allowlist"识别路径。

### Ralph 怎么做
- 权限拒绝累计达阈值直接 halt，并区分"compound-command 落在 allowlist 内"的良性情况只告警不停。

### 为什么标低 / 待定
- **[未验证] Ralph 的权限检测是针对 Claude Code 的 `--allowed-tools` JSON 输出做的**；我们主用 kilo/opencode（见 [[user-primary-agents]]），权限模型和输出格式不同，不能直接照搬解析逻辑。
- 要落地得先确认 kilo/opencode 在权限被拒时 pane 里输出什么可识别 token——这是个前置调研，没调研清楚不要写。
- **置信度 [低]**：方向合理，但跨 agent 适配是真功夫，列为"待调研"而非"建议实现"。

---

## 优先级总表

| # | 建议 | 置信度 | 落地大小 | 和我们原则的关系 |
|---|---|---|---|---|
| 1 | stuck/失败计数持久化到磁盘 | 高 | 小 | 直接补"记忆不可信"漏洞，强化既有"连续2次失败"停止条件 |
| 2 | per-phase metrics.jsonl + `lr.py stats` | 高 | 小 | 可观测性 + 进度播报有据，呼应"无证据不算完成" |
| 3 | 门禁区分 optional/blocking | 中高 | 小 | 对齐"可选 backlog"规则，解门禁僵局 |
| 4 | 超时用 worktree diff 区分慢/卡 | 中 | 小 | 缓解 false-IDLE 坑，给客观信号 |
| 5 | repo 级 AGENT.md 命令文件 | 中低 | 小 | 降 fresh coder 重发现成本，部分已覆盖 |
| 6 | 权限拒绝一等停止信号 | 低/待定 | 需前置调研 | 方向对，但 kilo/opencode 适配未验证 |

## 建议执行顺序

1. 先做 **2（metrics）**，因为 **1（stuck 计数）** 是它的派生，一起做最省。
2. 再做 **3（optional 门禁）**，独立、小、收益明确。
3. **4（超时 diff）** 顺手做（worktree SHA 现成）。
4. **5** 视项目复杂度按需。
5. **6** 单独开一个"kilo/opencode 权限输出格式"的前置调研，调清楚再决定做不做。

> 一句话总结：Ralph 值得我们学的不是它的"自主"，而是它把"卡没卡住、完没完成、改了没"全部落成磁盘上可计算的确定信号——这恰好补我们当前最依赖 orchestrator 记忆和肉眼的那几处。自主退出/沙箱/限流是它为无人值守付的税，我们有人在环，不用交这个税。

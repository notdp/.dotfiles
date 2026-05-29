---
name: dev-long-loop
description: 当任务目标明确但需要跨多轮执行、上下文沉淀或阶段验收时使用；由当前 agent 作为 orchestrator 生成 workspace，并用 tmux worker 自动执行单轮交付（纯人工逐阶段推进改用 dev-long-task-scaffold，跨子系统/不可逆大改用 dev-large-delivery）。
argument-hint: <任务目标或需求>
---

# Dev Long Loop

本 skill 是 agent-orchestrated long-loop 的工作流入口。它把用户目标转成可审阅、可验证、可多轮推进的文件系统 workspace；当前 agent 作为 orchestrator 做调度判断，tmux 中的新 coding agent 作为 worker 执行单轮交付。

本仓库不再提供 long-loop command；本 skill 是唯一用户入口。`skills/dev-long-loop/long_loop.py` 只作为 workspace scaffold、observe、legacy run helper，不是调度脑。Hive 不作为主路径或 hard dependency；需要多 agent 协作时可以另行加载 Hive，但本 workflow 必须能只依赖 tmux 与 workspace 文件运行。

## Decision Principles

- long-loop 优化的是跨阶段任务的连续性、可观测性和状态沉淀，不是替代正常的短循环开发。
- 只有当任务目标明确、影响面大、需要多轮验证或用户无法持续盯盘时才值得启动；普通单文件修复、小重构、一次性调研不应升级。
- token budget 是风险和成本边界：任务越大越需要阶段验收和停止点，不能用更大预算掩盖需求不清。
- 文件系统 workspace 是 SSOT，因为长流程最容易丢失上下文；所有状态、证据和阻塞都必须落到文件里，不能依赖模型记忆。
- LLM 负责调度判断：选下一轮 item、决定继续/停止/blocked、判断验证证据是否足够。Python helper 只做机械创建、展示或兼容运行。
- worker 每次只执行一个明确 round，不自动跨 phase；下一轮由 orchestrator 读取 evidence 后再决定。

## 工作流

1. 明确任务目标，不接受只有一句话的模糊目标直接开跑。
2. 当前 agent 进入 orchestrator 角色，先做只读代码调研，记录事实、相关文件、现有约定和风险。
3. 必要时驳斥或修正用户不合理需求。
4. 自动给出 token budget：
   - 小任务：`500K`
   - 中任务：`1M`
   - 大任务：`2M`
5. 解析 harness 路径（与本 skill 同目录）；如果不存在，停止并说明缺少 harness，禁止手动拼 `.long-loop/` workspace：
   - `LONG_LOOP_HARNESS="$(dirname "$SKILL_PATH")/long_loop.py"`
   - `test -f "$LONG_LOOP_HARNESS"`
6. 调用底层脚本创建 workspace：
   - `python3 "$LONG_LOOP_HARNESS" plan --goal "<goal>" --token-budget <500K|1M|2M>`
7. 补齐 workspace Markdown：
   - `ORCHESTRATOR.md`
   - `WORKER_PROMPT.md`
   - `HANDOFF.md`
   - `SPEC_OVERVIEW.md`
   - `fix_plan.md`
   - `qa.md`
   - `phases/*/spec.md`
   - `phases/*/qa.md`
   - `phases/*/research.md`
   - `phases/*/plan.md`
8. 让用户 review 非平凡任务的 workspace；批准后由 orchestrator 启动一个 tmux worker round。
9. worker 完成一轮后必须更新 `HANDOFF.md`、`logs.md`、`fix_plan.md` 和对应 phase 文件，然后停止。
10. orchestrator 读取 handoff、git diff/status、验证输出和日志，再决定下一轮、完成、blocked 或询问用户。

## 文件契约

| 文件 | 责任 |
|---|---|
| `ORCHESTRATOR.md` | 当前 agent 的调度协议：如何选 item、何时继续、何时 stop/blocked/AskUser |
| `WORKER_PROMPT.md` | 注入 tmux worker 的单轮执行协议；worker 只做一个 round |
| `HANDOFF.md` | worker 最新交接：状态、已改文件、验证、阻塞、风险、下一步建议 |
| `SPEC_OVERVIEW.md` | 任务理解、代码事实、非目标、风险、阶段拆分、整体验收 |
| `fix_plan.md` | 任务 SSOT；每个 item 有状态、phase、证据要求和 QA 指针 |
| `qa.md` | 整体端到端验收方案 |
| `logs.md` | append-only 日志，记录每轮工作、验证证据、风险和下一步 |
| `PROMPT.md` | 兼容旧 runner 的 prompt；新主路径优先使用 `WORKER_PROMPT.md` |
| `runtime.log` | 可选兼容日志；tmux 主路径不能把它当唯一进度来源 |
| `observe.html` | 可选浏览器观测页；用于辅助观察，不替代 workspace 文件 |
| `phases/*/research.md` | 按 `/think-research` 思路写阶段代码事实 |
| `phases/*/plan.md` | 按 `/think-plan` 思路写阶段实施计划 |
| `phases/*/qa.md` | 阶段验收标准 |

## Orchestrator Contract

- 每次调度前读取 `ORCHESTRATOR.md`、`SPEC_OVERVIEW.md`、`fix_plan.md`、`qa.md`、recent `logs.md`、`HANDOFF.md` 和 git status。
- 用 LLM 判断当前最高价值的下一轮，不让 Python 根据固定规则选择任务。
- 启动 worker 时默认在当前 `TMUX_PANE` 所在 tab/window 中 split 新 pane；只有用户显式选择 window mode 时才开新 tmux window。
- 启动 worker 必须用 `long_loop.py launch-worker`；不要手写 `tmux new-session` 或自定义 tmux 启动命令绕过 workspace contract。
- 不在 tmux 环境时，不伪装已启动 worker；交付 workspace 路径和手动 worker prompt。
- worker 返回后，orchestrator 必须检查 `HANDOFF.md`、`logs.md`、`fix_plan.md`、phase QA、验证输出和 git diff。
- worker 是否完成以 `HANDOFF.md + fix_plan.md + phase QA` 为 evidence；如果 handoff complete 但 worker process still running，先按观测冲突复核 workspace 文件，不要只凭进程或空输出判断卡死。
- 只有 evidence 支持继续时才启动下一轮；遇到 blocked、权限、secret、push/deploy/DB/第三方副作用时停止并问用户。

## Worker Contract

- worker 每轮必须 fresh context，不能依赖上轮模型记忆。
- worker 只执行 orchestrator 指定的一个 item 或 phase。
- 编辑前重新搜索仓库并更新 phase `research.md`。
- 实现前更新 phase `plan.md` 和 `qa.md`。
- 实现后运行 phase QA 和相关仓库 validator。
- 结束前更新 `HANDOFF.md`、`logs.md`、`fix_plan.md` 和 phase QA evidence。
- worker 不自动开始下一轮，不自动跨 phase，不自动 commit，除非当前 workspace 或用户明确授权。

## tmux Launch Guidance

- 默认在当前 tmux tab/window 中 split 新 pane，cwd 使用目标 repo root。
- 通过 `long_loop.py launch-worker --dir <workspace>` 启动 worker，让 helper 生成 `WORKER_LAUNCH_PROMPT.md`、agent settings 和 tmux split 命令。
- 不直接运行 `droid exec -f <prompt>`；worker 应作为可观察的 interactive coding agent 启动，并用初始 prompt 读取 `WORKER_LAUNCH_PROMPT.md`。
- `--tmux-mode window` 会打开新 tmux window，必须显式加 `--allow-new-window`；默认和常规路径必须留在 coordinator 当前 tab/window 的 split pane 内。
- worker pane 中启动 coding agent 后，让它读取 workspace 内 `WORKER_PROMPT.md`，再执行指定 item。
- 用户可以直接观察或接管 worker pane；接管后仍以 workspace 文件为 SSOT。
- 如果 tmux 不可用，输出手动步骤，不调用 `long_loop.py run` 冒充 agent-orchestrated flow。

## 质量门禁

- 每个阶段必须能独立验收。
- 每轮只能推进一个 `fix_plan.md` item。
- `fix_plan.md` 合法状态只允许 `pending / in_progress / done / blocked`。
- `blocked` item 不是 runnable；遇到 blocked 必须停止等待用户判断或授权。
- worker 实现前必须补阶段 `research.md` 和 `plan.md`。
- 阶段完成必须满足阶段 `qa.md`。
- 每轮必须更新 `logs.md` 和所选 item 在 `fix_plan.md` 中的状态。
- 每轮必须更新 `HANDOFF.md`，否则 orchestrator 不能声称该轮完成。
- 定期用 `/guard-close` 思路判断是否发散或该停止。
- 不自动 push、deploy、改数据库、改 secrets 或触碰第三方系统。

## Legacy Helper Boundary

- `long_loop.py plan` 仍可用于生成标准 workspace。
- `long_loop.py observe` 仍可用于查看兼容状态和日志。
- `long_loop.py run` 是 legacy/helper path；不要把它描述成主流程，也不要让它承担 LLM 调度判断。
- `state.json` 如果存在，只记录状态和元数据；它不是 scheduler。

## Gotchas

- 不要恢复旧 command；用户入口只保留本 skill。
- 不要把“开了后台脚本”当成 long-loop；主路径必须由 orchestrator 读 evidence 后调度下一轮。
- 不要默认依赖 Hive；Hive 是可选协作层，不是此 workflow 的 SSOT。
- 不要假设目标项目自带 harness；scaffold helper 永远来自 skill 自身目录的 `long_loop.py`。
- 如果 harness 缺失，停止并报告，不要手写 `state.json` 伪装 plan 成功。
- 不要把状态报告写进 `PROMPT.md`。
- 不要依赖模型记忆；文件系统是 SSOT。
- 不要为了“自动化完整”加入复杂 pause/resume。中断后让用户看 `logs.md`、`HANDOFF.md` 和 git status，再由 orchestrator 决定下一步。

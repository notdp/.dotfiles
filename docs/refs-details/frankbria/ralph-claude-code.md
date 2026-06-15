# frankbria/ralph-claude-code

- 上游仓库：`https://github.com/frankbria/ralph-claude-code`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/frankbria/ralph-claude-code`
- 主分类：**多智能体协作与工作流编排**（具体形态：单 agent 自主长循环 harness）
- 能力标签：`长任务/长循环`, `研发流程`, `可观测/监控`, `沙箱隔离`
- 一句话总结：Geoffrey Huntley "Ralph" 技巧的工程化 bash 实现——把 Claude Code 包成**无人值守的自主开发循环**，靠"完成信号双门控 + 熔断器 + 速率限制 + 沙箱"四件套在迭代数十轮直到 fix_plan 清空，全程不需要人介入。

## 定位与本仓库的关系（先说结论）

- Ralph 和我们的 `dev-long-run` **哲学相反**：
  - Ralph = **无人值守自主**。没有 per-phase 人工确认，单 pane Claude，靠启发式信号自己判断"完成/卡住/该停"，目标是丢进 CI 跑到底。
  - `dev-long-run` = **人在环监督**。当前 agent 即 orchestrator，每 phase 用户自然语言确认，多 pane（planner/coder/reviewer），L23 硬门禁，worktree 隔离。
- 因此 Ralph 的"自主退出启发式 / 沙箱 / 速率限制 / 多 issue 队列"**大部分不适合直接搬**（我们用人工确认 + 硬门禁，比启发式更强，搬过来反而是降级）。
- 但 Ralph 在**机械可靠性**上有几处比我们成熟，值得吸收：把"卡死检测/失败计数"从 orchestrator 记忆变成磁盘上可计算的信号、per-loop 结构化 metrics、completion gate 区分 optional/blocking、超时时用 git diff 自动区分"在干活的慢"和"真卡住"。
- 详细的吸收裁决见：[`docs/software-engineering-research/dev-long-run-improvements-from-ralph.md`](../../software-engineering-research/dev-long-run-improvements-from-ralph.md)

## 能力概览

- **核心是一个 bash 主循环**（`ralph_loop.sh`，约 154KB 单文件）：每轮调一次 `claude`，分析输出，更新状态，判断是否退出，循环直到 `fix_plan.md` 清空或触发停止。
- **完成判定靠"双门控"**：自然完成指标累计 ≥2 **且** Claude 在 `---RALPH_STATUS---` 块里显式写 `EXIT_SIGNAL: true` 才退出（防止代码/注释里的 "complete" 字样误触发）。JSON 模式下完全禁用启发式，只认显式信号（Issue #224）。
- **熔断器（circuit breaker）做卡死检测**：跨轮持久化计数器，`consecutive_no_progress ≥ 3`（git 无改动且无完成信号）或 `consecutive_same_error ≥ 5`（同一错误指纹反复出现）或 `permission_denials ≥ 2` 就开路停循环；状态机 CLOSED→HALF_OPEN→OPEN，带冷却自动恢复（默认 30 分钟）。
- **速率/预算控制**：`MAX_CALLS_PER_HOUR`（默认 100）、可选 `MAX_TOKENS_PER_HOUR`、`CLAUDE_TIMEOUT_MINUTES`（默认 15），计数写 `.ralph/.call_count` 等文件按小时重置。
- **任务源可插拔**：本地 `fix_plan.md` / GitHub Issues（带标签/里程碑过滤）/ Beads / PRD 文档；队列管理支持依赖感知选取（`depends on #N`，BFS 环检测）。
- **沙箱隔离**：Docker（持久容器 + bind mount）或 E2B（云沙箱，按秒计费 + 成本预算告警）；通过 `.ralphignore` + `SYNC_INCLUDE/EXCLUDE` 控制同步，`.git` 双向排除。
- **GitHub 生命周期联动**：进度评论、完成时建 PR（`Closes #N`）、扫 TODO/FIXME 建 follow-up issue、自动关 issue 加标签。
- **可观测**：`ralph_monitor.sh` 实时面板（loop 数、API 用量、Claude 进度、沙箱、issue 队列、熔断器状态，2s 刷新）；`metrics.jsonl` 每轮一条结构化记录，`ralph-stats.sh` 汇总。

## 关键机制（机制级事实，已抽查源码核实）

- **完成判定**：`should_exit_gracefully()`（`ralph_loop.sh`）按优先级检查 权限拒绝 → 完成信号累计 → fix_plan 清空 → done 信号 → 安全断路器。`MAX_CONSECUTIVE_DONE_SIGNALS=2`、`MAX_CONSECUTIVE_TEST_LOOPS=3`（纯测试循环 3 次判 "test_saturation" 退出，防 agent 无限打磨测试）。
- **进展信号**（`lib/circuit_breaker.sh:217-238`，已核实）：四个信号任一为真即重置 `consecutive_no_progress`——`files_changed>0` / `has_completion_signal==true` / Claude 报告改了文件 / 不在反问问题。
- **错误指纹比对**（`lib/response_analyzer.sh` `detect_stuck_loop`）：两段过滤（先 `grep -v '"[^"]*error[^"]*":'` 去掉 JSON 字段名，再 `grep -E` 匹配真错误前缀），然后要求"当前所有错误行都出现在最近 3 个历史输出里"才判 stuck——刻意防"错误在演化"被误判。
- **超时区分**（`ralph_loop.sh` 超时守卫）：`portable_timeout` 返回 124 后，对比 `.loop_start_sha` 看 git 是否有改动——有改动 = "productive timeout"（继续，分析可能被截断的 JSON），无改动 = "idle timeout"（判失败）。
- **文件保护**（`lib/file_protection.sh:8-35`，已核实）：`RALPH_REQUIRED_PATHS`（`.ralph/`、`PROMPT.md`、`fix_plan.md`、`AGENT.md`、`.ralphrc`）每轮前 `validate_ralph_integrity()` 校验存在性，缺失即停；外加 `ALLOWED_TOOLS` 白名单默认禁 `git clean/rm/reset`（Issue #149 防 Claude 删自己的基础设施）+ PROMPT 里的禁改警告，三层防护。
- **optional sections**（Issue #239）：`fix_plan.md` 里 `Optional`/`Future`/`Nice to Have` 等标题下的 `- [ ]` **不阻塞退出**，`OPTIONAL_SECTIONS` 可配；`_count_blocking_unchecked()` 用 awk 维护 `optional_active` 状态只数阻塞项。
- **per-loop metrics**（Issue #21，`ralph_loop.sh:827-846`，已核实）：每轮 `record_loop_result()` 向 `.ralph/logs/metrics.jsonl` 追加一行（duration、calls、files_modified、success、circuit_breaker_state 等），`ralph-stats.sh` 读它出汇总。

## 资产盘点

- 顶层 6 个 `ralph_*.sh` 入口脚本（loop / monitor / queue / import / enable / stats）。
- `lib/` 15 个 bash 模块 + 1 个 `e2b_helper.py`（circuit_breaker / response_analyzer / file_protection / task_sources / issue_analyzer / queue_manager / github_lifecycle / sync / sandbox_docker / sandbox_e2b / timeout_utils / date_utils / log_utils / enable_core / wizard_utils）。
- `templates/`：`PROMPT.md`（每轮静态 prompt，含 CRITICAL 的 `RALPH_STATUS` 输出契约）、`AGENT.md`（项目构建/测试命令，自动维护）、`fix_plan.md`、`ralphrc.template`、`.ralphignore`。
- 51 个 bats 测试文件（unit/integration/e2e 三层），自述 784 tests 100% pass（v0.11.x）。
- 文档：README（54KB）、CLAUDE.md（38KB，给 agent 的指令文件）、SPECIFICATION_WORKSHOP.md、docs/ 下 CLI_OPTIONS / DOCKER_SANDBOX / E2B_SANDBOX / SANDBOX_SYNC / QUEUE_MANAGEMENT。

## 关键文件

- `ralph_loop.sh`（主循环 + 完成判定 + 超时/限流守卫）
- `lib/circuit_breaker.sh`（卡死检测状态机）
- `lib/response_analyzer.sh`（输出解析 + stuck/错误检测）
- `templates/PROMPT.md`（`RALPH_STATUS` 输出契约）
- `templates/ralphrc.template`（全配置项 + 默认值）
- `CLAUDE.md`（工作哲学与约束）

## 备注

- 自主退出是**启发式**的（信号计数 + 阈值），作者用大量 Issue 编号（#101/#194/#224/#239…）记录踩坑修补——侧面说明"让 agent 自己判断何时停"很难做稳，这正是我们用"人工确认 + L23 硬门禁"绕开的同一个坑。
- 明确不做：跨多仓库、实时人工介入（要改 PROMPT/fix_plan 后重启）、非沙箱下降权限、>24h 长会话、并发处理多 issue（队列单线程顺序跑，理由是避免分支冲突/会话污染/成本失控）。
- 沙箱 provider 集合已"封板"（只 Docker + E2B，Daytona/Cloudflare 明确不做）。

## 最近 14 天更新（基线 `origin/main` @ `d3428ed`，2026-06-11）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main` @ `d3428ed`
- [事实] 提交数：`292`
- [事实] 代表提交：
  - `2026-06-11` `feat(ci): publish ralph-sandbox image to GHCR on release tags (#298)`
  - `2026-06-11` `feat(sync): sandbox file sync filtering — .ralphignore, --sync-include/--sync-exclude (#76)`
  - `2026-06-11` `feat(sandbox): E2B cloud sandbox execution — ralph --sandbox e2b (#75)`
  - `2026-06-09` `feat(sandbox): local Docker sandbox execution — ralph --sandbox docker (#74)`
- [推断] 近期主线是**沙箱化**（Docker + E2B 云沙箱 + 文件同步过滤 + GHCR 发镜像），把"无人值守循环"推向 CI/云端隔离执行；与此同时持续补 bats 测试卫生（如 #303 修 bare `!` 静默 no-op）。
<!-- recent-updates:end -->

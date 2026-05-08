---
name: dev-long-loop
description: 当任务目标明确但需要跨多轮执行、上下文沉淀或阶段验收时使用；先做代码调研和规格化，再生成 long-loop workspace 让脚本执行简单可靠循环。
argument-hint: <任务目标或需求>
---

# Dev Long Loop

本 skill 是 long-loop 的工作流入口。它负责把用户的一句话或初步想法，转成可执行、可验证、可循环的文件系统 workspace。

本仓库不再提供 long-loop command；本 skill 是唯一用户入口。底层 harness 与本 skill 同目录：`skills/dev-long-loop/long_loop.py`，跨项目使用时不依赖目标仓库自带 harness。验证优先使用目标仓库脚本，缺失时使用 dotfiles 自带 fallback。

## 工作流

1. 明确任务目标，不接受只有一句话的模糊目标直接开跑。
2. 结合代码调研需求，记录事实、相关文件、现有约定和风险。
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
   - `SPEC_OVERVIEW.md`
   - `fix_plan.md`
   - `qa.md`
   - `phases/*/spec.md`
   - `phases/*/qa.md`
   - `phases/*/research.md`
   - `phases/*/plan.md`
8. 让用户 review 后，再运行：
   - `python3 "$LONG_LOOP_HARNESS" run --dir .long-loop/<workspace> --repo-root "$PWD" --max-iterations 3 --idle-timeout-seconds 300 --agent-cmd '<agent command>'`
   - 需要本地回滚点时，用户明确同意后追加 `--checkpoint-commits`；它只在 phase 完成且验证通过后创建本地 checkpoint commit，不 push。

## 文件契约

| 文件 | 责任 |
|---|---|
| `SPEC_OVERVIEW.md` | 任务理解、代码事实、非目标、风险、阶段拆分、整体验收 |
| `fix_plan.md` | 任务 SSOT；每个 item 有状态、phase、证据要求和 QA 指针 |
| `qa.md` | 整体端到端验收方案 |
| `logs.md` | append-only 日志，记录每轮工作、验证证据、风险和下一步 |
| `runtime.log` | agent 命令 stdout/stderr；用于 hands-off 监控和 idle timeout 诊断 |
| `phases/*/research.md` | 按 `/think-research` 思路写阶段代码事实 |
| `phases/*/plan.md` | 按 `/think-plan` 思路写阶段实施计划 |
| `phases/*/qa.md` | 阶段验收标准 |

## 质量门禁

- 每个阶段必须能独立验收。
- 每轮只能推进一个 `fix_plan.md` item。
- `fix_plan.md` 合法状态只允许 `pending / in_progress / done / blocked`。
- `blocked` item 不是 runnable；遇到 blocked 必须停止等待用户判断或授权。
- Worker 实现前必须补阶段 `research.md` 和 `plan.md`。
- 阶段完成必须满足阶段 `qa.md`。
- 每轮必须更新 `logs.md` 和所选 item 在 `fix_plan.md` 中的状态。
- 定期用 `/guard-close` 思路判断是否发散或该停止。
- 不自动 push、deploy、改数据库、改 secrets 或触碰第三方系统。

## hands-off 运行契约

- hands-off 前必须先由 harness `plan` 生成 workspace；禁止手写 `state.json` 或手拼 `.long-loop/` 冒充成功。
- hands-off 不等于无人监管的后台 loop。运行时必须依赖 `runtime.log`、`state.json.last_heartbeat_at`、`stop_reason` 判断是否继续。
- `idle timeout` 是主要卡死保护：agent 命令超过 `--idle-timeout-seconds` 没有 stdout/stderr 增量时，harness 必须停止并写入 `runtime.log`。
- checkpoint 只在用户明确授权 `--checkpoint-commits` 时启用；启用前如果目标 repo 已有非本轮脏改动，必须停止，不得 `git add -A` 混入未知修改。

## Gotchas

- 不要恢复旧 command；用户入口只保留本 skill。
- 不要假设目标项目自带 harness；harness 永远来自 skill 自身目录的 `long_loop.py`。
- 如果 harness 缺失，停止并报告，不要手写 workspace 伪装 plan 成功。
- 不要把状态报告写进 `PROMPT.md`。
- 不要依赖模型记忆；文件系统是 SSOT。
- 不要为了“自动化完整”加入复杂 pause/resume。中断后让用户看 `logs.md` 再手动重新 run。

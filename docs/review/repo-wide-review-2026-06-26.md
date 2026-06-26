# Repo-wide Review 2026-06-26

## Review Scope

本次 review 是只读全仓库审查，未修改文件。

范围：`scripts/`、hooks、tests、`commands/`、`coding-skills/`、`writing-skills/`、`writing-hooks/`、`.kilo/`、`.factory/`、`bin/`、`docs/`、`refs` 登记与 wiring。

未覆盖：第三方 `refs/` 和 `writing-refs/` 的内部实现，只审本仓库如何登记、引用和解释它们。

## Summary

当前仓库不适合直接进入交付/发布状态。主要阻断点集中在：

- 命令护栏可绕过或 fail-open。
- `droid-mod` 会修改仓库外二进制，但缺少强制审批/回滚门禁。
- 多个用户入口脚本已经失效。
- agent/skill 维护脚本存在旧路径和模型配置漂移。
- writing 与 refs 文档存在事实漂移，会误导后续维护。
- 全局 Kilo 配置中发现明文 API key，属于仓库外但高危风险。

## Verification Evidence

| Check | Result |
|---|---|
| `git status --short` | 无输出，工作树没有可见未提交改动 |
| `python3 scripts/verify_skills.py` | `validated 65 skills`，同时有若干 warning |
| `python3 scripts/hooks/command_guard.py <<< ...python subprocess rm...` | 输出 `{"suppressOutput": true}`，确认绕过存在 |
| `python3 scripts/hooks/command_guard.py <<< ...git push --force-with-lease=...` | 输出 `{"suppressOutput": true}`，确认 force 变体未拦截 |
| `python3 scripts/hooks/command_guard.py <<< ...git push origin +feature...` | 输出 `{"suppressOutput": true}`，确认 plus refspec 未拦截 |
| `bin/longrun --help` | 报 `can't open file ... scripts/longrun_dashboard.py` |
| `bin/droid-observe --help` | 报 `can't open file ... scripts/droid_observe.py` |

## Critical Findings

| ID | Location | Issue | Impact | Recommendation |
|---|---|---|---|---|
| C1 | `scripts/hooks/command_guard.py:720-723` | `python -c` 只把源码文本交给 `embedded_text_decision()`，没有解析 Python AST 或 `subprocess.run([...])` 参数数组。实测 `subprocess.run(["rm","-rf","/etc"])` 被放行。 | 破坏性命令可通过 Python 包装绕过命令护栏。 | 对 `python -c` 增加 AST 检测，覆盖 `os.system`、`subprocess.run/call/Popen/check_*` 的字符串命令和 argv list；补测试覆盖危险 argv、字符串 shell、无害 Python。 |
| C2 | `scripts/opencode/dotfiles_hooks.mjs:22-43`, `scripts/opencode/dotfiles_hooks.mjs:162-172`, `scripts/kilo/dotfiles_hooks.mjs:1-4` | Kilo/OpenCode 共用 hook plugin；`runPythonHook()` 在 command guard 脚本失败、非 0 或 JSON 解析失败时只返回 `systemMessage`，`applyCommandGuard()` 不 deny、不 throw。 | [推断] command guard runtime 失效时，危险命令可能继续执行，只显示提示。该行为不符合护栏应阻断高风险命令的目标。 | command guard 失败路径改为 fail-closed：返回 deny 或 throw；context capsule/memory 仍可 fail-open，但 command guard 不应复用同一失败策略。 |
| C3 | `commands/droid-mod.md:6`, `commands/droid-mod.md:20-23`, `commands/droid-mod.md:63-68` | `/droid-mod apply/restore` 文档允许直接修改 `~/.local/bin/droid`，但没有强制 `/guard-gitops`、明确人工批准、备份路径和回滚证据。 | 修改仓库外二进制，违反本仓库 AGENTS 中“仓库外二进制必须先过 gitops/审批”的边界纪律。 | `/droid-mod` 默认只读 `status`；`apply/restore` 前要求 `/guard-gitops`、用户明确批准、记录 droid 路径/版本/备份/预期变更/回滚命令。 |
| C4 | `scripts/droid-mod/apply.py:170-197` | 多个 mod 中任一 `run_mod()` 失败时只累加 `fail`，后续仍继续补偿、签名并打印“完成”。 | 外部 droid 二进制可能处于部分修改状态，但自动化调用方看到成功完成提示。 | `fail > 0` 时停止签名和完成提示，非 0 退出；更稳妥的是从备份恢复并输出失败摘要。 |
| C5 | `/Users/zhenninglang/.config/kilo/kilo.json:22` | [范围外但高危] Kilo 全局配置中存在明文第三方 API key。未复述 secret 值。 | 凭据可能通过备份、日志、会话 transcript 或误提交外泄。 | 立即轮换该 key；配置改为环境变量或 ignored secret 文件；仓库侧补 secret 扫描，至少覆盖 provider 配置。 |

## Important Findings

| ID | Location | Issue | Impact | Recommendation |
|---|---|---|---|---|
| I1 | `scripts/hooks/command_guard.py:427-480` | `git push` force 解析只识别 `--force`、`--force-with-lease`、`-f` 精确 token，未识别 `--force-with-lease=<value>` 和 refspec `+branch`。实测两种都放行。 | force push 到 feature 分支可绕过远端历史修改护栏。 | 支持 `--force-with-lease=` 前缀；识别以 `+` 开头 refspec，至少 warn，建议默认 deny。 |
| I2 | `scripts/opencode/dotfiles_hooks.mjs:50-53`, `scripts/opencode/dotfiles_hooks.mjs:208-213` | 注释明确说不能 push 缺 runtime schema 的新 `output.parts`，但 `appendTextPart()` 仍 push `{type,text,synthetic}`，且 deny/systemMessage 路径会调用。 | [推断] guard deny 或 hook error 提示路径可能触发 Kilo/OpenCode runtime UnknownError，而不是稳定展示阻断原因。 | 复用 `injectContextCapsules()` 的“修改已有 text part”策略；无 text part 时使用 runtime 支持的状态/错误字段。 |
| I3 | `scripts/preflight.sh:44` | secret grep 使用 `["\x27]`，对 BSD/GNU `grep -E` 不可靠，单引号包裹的 secret 可能漏检。 | 交付前敏感信息扫描可能错误报告 `no hardcoded secrets detected`。 | 复用 `scripts/hooks/redact.py scan-repo .`，或改为可移植正则并补单引号/双引号/无引号样本测试。 |
| I4 | `scripts/run-verify.sh:60-65` | 顶层 `tests/test_*.py` 存在但无 `pyproject.toml` 且无 `pytest` 时，fallback unittest 不会运行。 | 纯 stdlib unittest 项目可能被验证脚本漏跑。 | 当 `tests/test_*.py` 存在且 `python3` 可用时，无 pytest 就运行 `python3 -m unittest discover -q`，不应依赖 `pyproject.toml`。 |
| I5 | `bin/longrun:5`, `README.md:40` | `bin/longrun` 指向不存在的 `scripts/longrun_dashboard.py`。已复现报错。 | README 暴露失效命令，longrun dashboard 入口不可用。 | 删除旧入口和 README 描述，或改到当前有效的 `coding-skills/dev-long-run/lr.py` 子命令。 |
| I6 | `bin/droid-observe:5`, `README.md:39` | `bin/droid-observe` 指向不存在的 `scripts/droid_observe.py`。已复现报错。 | README 暴露失效命令，Droid observe 入口不可用。 | 删除旧入口和 README 描述，或迁到当前有效观察命令。 |
| I7 | `coding-skills/agent-health/scripts/collect_data.sh:11-12`, `coding-skills/agent-health/scripts/collect_data.sh:29-32`, `coding-skills/agent-health/scripts/collect_data.sh:68-71` | `agent-health` collector 硬编码旧布局 `skills/catalog.json` 和 `repo_root/skills`，但当前 SSOT 是 `coding-skills/catalog.json` 与 `coding-skills/*/SKILL.md`。 | 健康审计会误报 `SKILLS: 0`、catalog missing，掩盖真实状态。 | 优先探测 `coding-skills/`，必要时兼容 `skills/`，并在 summary 打印实际采用目录。 |
| I8 | `commands/skill-maintenance.md:75-77` | Phase 3 要求 subagent “猜测该项目做这些变更的目的”，但未要求按 Truth Directive 标注 `[猜测]` / `[推断]`。 | refs 调研可能把上游作者意图写成事实，污染后续 harness 决策。 | 改为“基于 diff 给出 `[推断]` 变更意图；无法证实时标 `[猜测]`，并与事实增减分栏”。 |
| I9 | `commands/skill-maintenance.md:81-85`, `commands/skill-maintenance.md:161-167` | Phase 3 默认写 `docs/skill-maintenance-runs/refs-research-<date>.md`，但同文件默认禁止自动 apply patch。 | 只读维护审查命令可能变成写文件命令，语义冲突。 | 默认在最终报告输出建议文档摘要；只有用户批准后才落盘。 |
| I10 | `commands/skill-maintenance.md:54-57`, `commands/skill-maintenance.md:171-176`, `.kilo/agent/skill-maintenance-reviewer-b.md:4` | Reviewer B 默认模型 `cliproxy/claude-opus-4-7` 与安装脚本/Kilo provider 可见模型不一致。 | [推断] 双 reviewer 派发可能失败或 runtime fallback，导致“双模型 review”不可验证。 | 统一到当前 provider 声明的模型，或同步 provider 配置与 agent 默认模型。 |
| I11 | `coding-skills/compact-memory/SKILL.md:25-27` | 可执行步骤使用相对路径 `coding-skills/compact-memory/scripts/compact_memory.py`。 | 在目标项目 cwd 调用时可能找不到脚本，或误命中目标项目同名路径。 | 改为 `${HOME}/.dotfiles/coding-skills/compact-memory/scripts/compact_memory.py`，并说明脚本从 dotfiles 解析。 |
| I12 | `docs/specs/writing-skills/overview.md:34`, `docs/specs/writing-skills/overview.md:69-72`, `docs/specs/writing-skills/overview.md:187-199`, `README.md:25` | writing spec 仍要求写作 skill 不暴露给编程 agent；README 当前说明写作 skill 已并入 `coding-skills/` 编程池。 | 架构事实冲突，后续维护者可能误删或误注册 write-*。 | 把 spec 改成历史决策，明确当前架构是“写作 skill 并入编程池，靠 `write-*` 域路由隔离”。 |
| I13 | `writing-hooks/slop_lint.py:30-36`, `writing-hooks/dehumanize_score.py:21-24`, `docs/specs/writing-skills/overview.md:175-177` | 跨行“首先/其次/最后”三段套未被 hook 检出；`TRIAD` 未跨换行匹配，`slop_lint` 只含同一行词组。 | spec 宣称 golden 样本/共享规则会覆盖，但实际 hook 漏掉常见机器稿结构。 | 增加跨行状态机或全文 regex；补 golden 正反样本测试。 |
| I14 | `writing-hooks/verify_writing.py:69-135`, `docs/specs/writing-skills/overview.md:175-177`, `docs/specs/writing-skills/overview.md:187-193` | spec 声称 `verify_writing.py` 校验 `_shared` 漂移，但脚本只校验 catalog、命名、description、孤儿目录。 | 共享写作约束被复制/漂移时不会被发现。 | 实现 shared contract 检查，或把 spec 中“共享前缀漂移”降级为未实现 backlog。 |
| I15 | `README.md:222`, `.gitmodules:1-204` | README 仍写“完整 56 个 submodule”，当前 `.gitmodules` 有 68 个 top-level submodule，其中 `refs/` 59 个、`writing-refs/` 9 个。 | refs 盘点入口事实过期。 | 删除硬编码数量，改为完整清单以 `.gitmodules` 为准；summary 只做研究摘要。 |
| I16 | `docs/refs-summary.md:7`, `docs/refs-update-absorption-2026-06-25.md:1` | summary 仍把最近一次全量 refs 更新指向 `2026-05-14`，但已有 `2026-06-25` 报告。 | 后续维护可能基于旧结论做吸收/排除判断。 | 更新 summary 的“最近一次”链接；保留 05-14 为历史批次。 |
| I17 | `docs/refs-summary.md:30-88`, `.gitmodules:136-150`, `.gitmodules:202-204` | summary 未登记 6 个当前 `.gitmodules` 中的 `refs/` submodule，包括 `gastownhall/beads` 等。 | `docs/refs-summary.md` 不能作为完整 refs 决策入口。 | 给 6 个项目补 summary；为 `gastownhall/beads` 增加 detail 文档或标记待研究。 |
| I18 | `docs/refs-details/anthropics/claude-plugins-official.md:5`, `docs/refs-details/OthmanAdi/planning-with-files.md:5`, `docs/refs-details/antfu/skills.md:5`, `docs/refs-details/voltagent/awesome-claude-code-subagents.md:5`, `docs/refs-details/voltagent/awesome-agent-skills.md:5` | 多个 refs detail 的 `Source SHA` 与当前 submodule gitlink 不一致，且没有 stale/current 标记。 | 可追溯性变弱，旧版本研究结论可能被当成当前事实。 | 拆成 `Analyzed SHA` 和 `Current gitlink SHA`；不一致时标 `stale`，或更新对应 detail。 |

## Minor / Cleanup

| ID | Location | Issue | Recommendation |
|---|---|---|---|
| M1 | `commands/droid-mod.md:52-60`, `scripts/droid-mod/status.py:15-102` | `/droid-mod` 文档列的 mod 编号和当前 status 输出不一致，文档还包含已归档项。 | 从 mod registry/status 生成列表，或标注归档编号。 |
| M2 | `coding-skills/dev-long-run/SKILL.md:137-139`, `coding-skills/assist-review-doc/SKILL.md:55`, `coding-skills/guard-gitops/SKILL.md:99` | 多处仍引用旧 `skills/...` 路径。 | 统一为 `coding-skills/...`；跨 cwd 执行用 `${HOME}/.dotfiles/...`。 |
| M3 | `docs/specs/writing-skills/overview.md:87`, `docs/specs/writing-skills/overview.md:156-159`, `docs/specs/writing-skills/overview.md:201-202` | writing spec 混用旧路径 `writing-skills/hooks/`、`scripts/verify_writing.py` 与真实 `writing-hooks/`。 | 统一路径，或把旧路径标为历史草案。 |
| M4 | `writing-hooks/_hooklib.py:20`, `writing-hooks/_hooklib.py:65-71` | hook 内部只按后缀判断写作产物，若外部 settings matcher 写宽，会误拦技术文档。 | 增加内部 allowlist，例如 `WRITING_ARTIFACT_GLOBS` 或默认 `drafts/`、`articles/`、`.writing/`。 |
| M5 | `.git/index.lock` | 仓库内存在 `.git/index.lock`。`git status` 可读，但后续 `git add/commit` 可能被锁阻塞。 | 在确认没有 git 进程运行后再删除；本轮只读 review 未处理。 |

## No Finding Areas

| Area | Result |
|---|---|
| `coding-agents/claude/*` 与 `coding-agents/opencode/*` | agent 双格式定义通过 `verify_skills.py` 的 agent asset 校验；未发现权限契约明显冲突。 |
| `scripts/kilo/dotfiles_hooks.mjs` | 只是复用 OpenCode plugin；问题已归并到 `scripts/opencode/dotfiles_hooks.mjs`。 |
| `.factory/settings.json` Droid hook wiring | 子审查复核显示 repo-local Droid hook check 通过。 |
| `writing-skills/catalog.json` | 子审查复核显示 12 个 writing skills 双向登记无缺失。 |
| `.gitmodules` 到 git index gitlink | 子审查复核显示登记的 top-level submodule path 均有 `160000` gitlink。 |

## Suggested Fix Order

1. 先处理 C5：轮换全局 Kilo 配置里的明文 API key，并移出明文配置。
2. 再处理 C1/C2/I1：命令护栏绕过和 fail-open 是 harness 的核心风险。
3. 再处理 C3/C4：`droid-mod` 涉及仓库外二进制，必须把 apply/restore 门禁和失败退出补齐。
4. 再处理 I5/I6/I7/I11：失效入口和旧路径会直接破坏日常工作流。
5. 最后批量处理 writing/refs/docs 漂移：这些主要影响后续维护决策，不是立即运行时风险。

## Residual Risks

- 未联网 `git fetch`，所以 refs 上游最新状态未核验。
- 未启动真实 Kilo/OpenCode/Claude/Droid session，涉及 runtime schema 的影响有一部分是基于代码和注释的 [推断]。
- 未深入审第三方 submodule 内部实现。
- 未执行任何写操作，包括 secret 轮换、删除 `.git/index.lock` 或调整配置。

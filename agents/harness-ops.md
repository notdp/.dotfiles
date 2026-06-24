# Harness 体系维护

## 指令分层与路由

- `AGENTS.md` 只放全局硬约束、验证门禁、事实纪律；保持短、小、硬
- 高频重复 inner-loop 工作流优先放 `commands/`
- 领域能力、流程方法、专项约束优先放 `skills/`
- 调研沉淀、refs 分析、背景材料放 `docs/`
- 能靠配置、脚本、hook、测试强制的规则，不要只写成自然语言提醒
- 不要继续把解释性内容堆进 `AGENTS.md`；细则优先下沉，避免全局上下文膨胀


## Skill 编写规范

- 新增或大改 skill 前读 `~/.dotfiles/docs/software-engineering-research/skill-authoring.md`（触发语义硬约束、结构模板、输入输出格式）
- 可复用 prompt 模式样例见 `~/.dotfiles/docs/software-engineering-research/skill-patterns.md`
- `description` 触发前缀由 `~/.dotfiles/scripts/verify_skills.py` 强制校验

## Subagent 编写规范（coding-agents/）

- subagent vs skill 分工判据：需要 (a) 不污染主对话的批量中间产物、(b) 比主对话更紧的工具权限、(c) 不同档位模型——**三占其一才 subagent 化**，否则用 skill（流程注入更轻）
- 不写角色扮演型 subagent（与 skill 路由重叠）；不写没有执行基底的协议文字，每段进 context 的内容必须有真实机制兜底
- 双格式目录：`coding-agents/claude/`（Claude Code：必填 name/description/tools/model，tools 白名单）；`coding-agents/opencode/`（OpenCode 与 Kilo 共用，Kilo 底座即 OpenCode：必填 description/mode，permission 三态收权，tools 字段已弃用禁写，model 省略=继承默认）
- 命名约定即权限契约：`*-judge` / `*-reviewer` / `*-auditor` 后缀为只读角色——claude 侧禁 Write/Edit/Bash/NotebookEdit/PowerShell；opencode 侧必须 `permission.edit/bash = deny`（运行时强制已实测，2026-06-10）
- 全部规则由 `~/.dotfiles/scripts/verify_agents.py` 强制（run-verify.sh 自动挂载），规则改动必须同步该脚本——只写文档不进门禁的规则视为不存在
- skill 引用 subagent 时保持跨 agent 降级：优先按名派发（Claude Code），不支持的平台降级为 prompt 内联同等约束的子任务

## 跨 agent 兼容

本 skill 体系设计为可在 kilo / opencode（当前主用）/ Claude Code / droid / codex 等多种 coding agent 中使用。约定：

- 子任务派发用通用描述（"派发只读子任务"），不绑定特定 subagent 名
- 工具引用使用通用名（Read / Grep / Glob / WebSearch / Edit），不引用 droid 专属 `Task` 调用语法或 `/missions` 概念
- 路径默认相对仓库根（`docs/threat-model.md`、`scripts/`），不依赖 `~/.factory` 或 `.factory/`
- 派发并行子任务在不支持的平台降级为主流程顺序执行（每个 skill 内部已声明降级策略）
- 例外与能力分叉统一登记在下方「平台能力矩阵」（如 `hive` 为 droid 专属，不要求跨 agent 兼容）

## 平台能力矩阵（capability matrix）

记录各 steering / harness 能力在不同 agent 上的可用性，让 SSOT 诚实反映分叉，而不是默认跨平台平价。本矩阵是能力分叉的单一登记处；既有一次性例外（如 hive）逐步并入。

图例：✅ 原生支持 ｜ ⚠️ 可降级 / 近似（备注注明方式）｜ ❌ 确认无等价机制 ｜ ❓ 未验证（尚未核实，**不得当作平价或不可用**，是待办项）

| 能力 | Claude Code | opencode/kilo | droid | codex | 证据 / 处理（非 CC 列实测 2026-06-20）|
|---|:--:|:--:|:--:|:--:|---|
| hive（多 agent runtime 协作） | ❌ | ❌ | ✅ | ❌ | droid 专属，不要求跨 agent 兼容 |
| path-scoped rules（按文件路径触发规则，`.claude/rules/`+`paths:`） | ✅ | ⚠️ | ❓ | ❓ | oc/kilo：Config 类型（sdk `types.gen.d.ts:1016`）无 `rules` 键、仅 always-on `instructions[]`；可经 plugin `chat.message`/`tool.execute.before`+路径判断近似（=现有 PostToolUse 扫描器）。CC 证据：`refs/anthropics/steering-claude-code-*.md`。droid/codex 未验证 |
| output-styles（替换式系统提示，顶掉默认工程指令） | ✅ | ⚠️ | ❓ | ❓ | oc/kilo：无 outputStyle config 键；但有 plugin 钩子 `experimental.chat.system.transform` 可程序化改写系统提示。harness 现用 `readable-*` skill 追加体裁更安全 |
| append-system-prompt（追加式系统提示） | ✅ | ✅ | ✅ | ❓ | oc/kilo：`instructions[]`（config 注入文件，always-on 而非 per-invocation flag）；droid：`--append-system-prompt[-file]`（实测 `--help`）；codex：AGENTS.md 注入，专属 flag 未见 |
| skill 压缩重注入（预算内、最旧先丢） | ✅ | ⚠️ | ❓ | ❓ | oc/kilo：有 compaction（config `{auto,threshold_percent,reserved,preserve_recent_tokens}`）但属 summarize 模型 + `experimental.session.compacting` 定制压缩 prompt，非「skill 重注入预算/最旧先丢」语义 |
| PreCompact 钩子（压缩前触发） | ✅ | ✅ | ❓ | ❓ | oc/kilo：`experimental.session.compacting`（压缩前，plugin `index.d.ts:271`）+`experimental.compaction.autocontinue`（压缩后）+`session.compacted` 事件；droid：`.factory` 仅接 UserPromptSubmit/Pre·PostToolUse/Stop，无 PreCompact；codex：本仓库 `scripts/install_hooks.py` 已生成 `[features] hooks = true` 以及 UserPromptSubmit/PreToolUse/PostToolUse/Stop hook 配置，PreCompact 等价能力未在本 phase 复核 |

小结（2026-06-20 实测；codex hook 配置源于 2026-06-24 本仓库复核）：opencode/kilo 缺的是 CC 那几个**声明式**特性（path-scoped rules、output-styles），但其 **plugin 钩子更通用**（`experimental.chat.system.transform` / `session.compacting` / `chat.messages.transform`），多数能力可经现有 `dotfiles_hooks.mjs` 程序化实现而非声明式；PreCompact 等价（`experimental.session.compacting`）已具备。droid 走 CC 式 hook 生命周期 + `--append-system-prompt`；codex 不是“无 hook 体系”：本仓库安装脚本已能渲染 codex hook 配置，具体外部运行时事件完备性仍按 ❓ 登记，避免把未复核细节写成事实。**这 5 项里真正"CC-only 不可跨"的几乎没有**——主要差异是声明式 vs 插件式，及 droid/codex 的 ❓ 待补测。kilo plugin 即 `import` opencode plugin（同源），故两列合并。

登记纪律：

- 何时加 / 更新一行：评估或采纳某个平台特定 / CC 原生特性时，或发现某能力在某平台不可用、需降级时——顺手登记。
- 一行必须含：能力、各平台图例、降级 / 处理方式、证据（refs 链接或实测日期，体例参照 Subagent 段「运行时强制已实测，2026-06-10」）。
- ❓ 是待办不是终态：核实后用实测证据替换 ❓ 并注日期。
- 禁止用未验证猜测填 ✅ / ❌ / ⚠️——那是把推测洗成事实；没核实一律 ❓。
- 采纳 CC-only 特性的决策：能跨平台 → 实现一次；不能 → 允许 CC-only 差异化，但必须在本矩阵留一行 ❌ / 降级说明，不静默分叉（见记忆 `cc-native-feature-adoption-policy`）。

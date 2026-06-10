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
- 例外：`hive` skill 是 droid 专属能力，不要求跨 agent 兼容


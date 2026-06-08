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

## 跨 agent 兼容

本 skill 体系设计为可在 droid / Claude Code / Cursor / Aider 等多种 coding agent 中使用。约定：

- 子任务派发用通用描述（"派发只读子任务"），不绑定特定 subagent 名
- 工具引用使用通用名（Read / Grep / Glob / WebSearch / Edit），不引用 droid 专属 `Task` 调用语法或 `/missions` 概念
- 路径默认相对仓库根（`docs/threat-model.md`、`scripts/`），不依赖 `~/.factory` 或 `.factory/`
- 派发并行子任务在不支持的平台降级为主流程顺序执行（每个 skill 内部已声明降级策略）
- 例外：`hive` skill 是 droid 专属能力，不要求跨 agent 兼容


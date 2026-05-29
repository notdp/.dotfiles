# Owl-Listener/designer-skills

- 上游仓库：`https://github.com/Owl-Listener/designer-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/Owl-Listener/designer-skills`
- 当前引用提交：`70cfd54`（`2026-05-06`，`Merge pull request #16 from Owl-Listener/claude/add-ux-design-principles-EE5WD`）
- 主分类：**前端 UI / 设计系统**
- 能力标签：`design workflow`, `Claude Code plugin`, `Gemini extension`, `user research`, `design systems`, `UI design`, `interaction design`, `design ops`
- 一句话总结：面向设计工作的 Claude Code / Gemini CLI skill collection，把用户研究、设计系统、UX 策略、UI、交互、原型测试、Design Ops 和设计师工具箱拆成 8 个插件、87 个 skills、27 个 commands。

## 能力概览

- [事实] `README.md` 声明仓库包含 8 个 plugins、87 个 skills、27 个 commands。
- [事实] 8 个插件是 `design-research`、`design-systems`、`ux-strategy`、`ui-design`、`interaction-design`、`prototyping-testing`、`design-ops`、`designer-toolkit`。
- [事实] Claude Code 入口是 `.claude-plugin/marketplace.json`；Gemini CLI 入口是 `.gemini/extensions/*/gemini-extension.json` 和编译后的 `GEMINI.md`。
- [事实] `CONTRIBUTING.md` 明确约定 skills 是名词型 domain knowledge，commands 是动词型 workflow。
- [推断] 该仓库对本仓库的最大价值不是单个设计 prompt，而是“同一批 skills 同时面向 Claude Code plugin 和 Gemini extension 打包”的组织方式。

## 关键文件

- `README.md`：总览、安装方式、8 个插件数量表和全部 command 列表。
- `.claude-plugin/marketplace.json`：Claude Code marketplace 清单，列出 8 个插件。
- `.gemini/extensions/*/gemini-extension.json`：Gemini CLI extension manifest。
- `.gemini/extensions/*/GEMINI.md`：由各插件 skills 和 command 摘要编译出的 Gemini 上下文文件。
- `*/README.md`：每个插件的 skills/commands 摘要。
- `*/skills/*/SKILL.md`：单个设计 skill，frontmatter 使用 `name` 和 `description`。
- `*/commands/*.md`：工作流命令，frontmatter 使用 `description` 和 `argument-hint`。
- `scripts/build-gemini.sh`：从各插件 `SKILL.md` 编译 `.gemini/extensions/*/GEMINI.md`。
- `CONTRIBUTING.md`：贡献约束，包括 skill/command 命名、frontmatter、禁止跨插件引用等。

## 插件结构

| 插件 | Skills | Commands | 主题 |
|---|---:|---:|---|
| `design-research` | 12 | 4 | 用户研究、persona、empathy map、journey map、访谈、可用性测试、卡片分类、调研仓库 |
| `design-systems` | 11 | 3 | tokens、组件、可访问性、主题、motion、治理、本地化 |
| `ux-strategy` | 11 | 3 | 竞品分析、设计原则、体验地图、信息架构、内容策略、service blueprint |
| `ui-design` | 14 | 4 | layout grid、色彩、字体、响应式、数据可视化、Gestalt/感知原则 |
| `interaction-design` | 15 | 3 | micro-interactions、状态机、手势、反馈、认知定律、表单、onboarding、导航、搜索 |
| `prototyping-testing` | 8 | 4 | 原型策略、可用性测试、启发式评估、A/B 实验 |
| `design-ops` | 9 | 3 | critique、handoff、sprint、团队流程、设计债、impact reporting |
| `designer-toolkit` | 7 | 3 | 设计理由、演示、案例研究、UX writing、系统采纳、协商 |

## 结构观察

- [事实] command 通过步骤链式调用同插件 skills，例如 `design-research/commands/discover.md` 串联 `user-persona`、`empathy-map`、`journey-map`，再输出 research summary。
- [事实] `scripts/build-gemini.sh` 会按插件遍历 `skills/`，把每个 `SKILL.md` 拼进对应 `.gemini/extensions/<plugin>/GEMINI.md`，并追加 command 摘要。
- [事实] 示例 skill `design-research/skills/user-persona/SKILL.md` 包含 `Context`、`Domain Context`、`Instructions`、`Further Reading`。
- [事实] 示例 command `design-research/commands/discover.md` 只保留流程步骤和收尾建议，不重复展开各 skill 的知识正文。
- [推断] 这种结构适合本仓库对齐“skills 放领域知识，commands 放高频 inner-loop 工作流”的分层原则。

## 适配风险

- [事实] 仓库主要面向 Claude Code 和 Gemini CLI，没有 Droid/Codex 专用打包入口。
- [事实] 部分 skill 会要求 agent “Ask for clarification” 或 “save it as a markdown document”，与本仓库“需要澄清时用 AskUser”以及“非请求不写 docs/README”的规则需要适配。
- [事实] `CONTRIBUTING.md` 要求 command 不跨插件引用；这利于独立安装，但会限制跨域设计流程编排。
- [事实] 内容主要是 prompt/workflow，不是带自动化测试的可执行软件包。

## 对本仓库的参考价值

1. **名词 skill + 动词 command**：适合继续强化本仓库 `skills/` 与 `commands/` 的职责分离。
2. **多平台打包**：可借鉴 `scripts/build-gemini.sh`，从一个 skill SSOT 编译到不同 agent 的运行时入口。
3. **插件级领域边界**：以 `design-research`、`ui-design`、`design-ops` 这类插件边界组织能力，比把所有设计能力塞到单一 skill 更清晰。
4. **command 只编排不塞知识**：workflow command 引用 skill 名称，减少重复，便于更新知识正文。

## 不建议照搬

- 不建议照搬其中“自然语言询问澄清”的写法，应改为本仓库的 AskUser 纪律。
- 不建议照搬“输出很大就保存 markdown”的默认行为；本仓库只在用户明确要求时写 docs/README。
- 不建议保持“command 禁止跨插件引用”作为全局硬约束；本仓库已有跨 skill 工作流，应该按任务风险和复用性决定是否跨域编排。

## 2026-05-29 本地 range 调研

> 信号来源：本地 remote-tracking（未联网）。本轮 range `70cfd54dba3f..5446f2a8eb8f`，`git log` 核实 4 commits（`5446f2a` merge #18、`987777d` 更新 README/build/Gemini extension、`a81c9a1` merge #17、`3948e7e` 新增 plugin）。

- [事实] 新增第 9 个 plugin **`visual-critique`**（commit `3948e7e` "Add visual-critique plugin with four critique skills and /critique-screen command"），含 4 个 critique skill：`critique-visual-hierarchy`、`critique-brand-consistency`、`critique-composition`、`critique-typography`，以及 `/critique-screen` 命令（`visual-critique/commands/critique-screen.md`），输出 P1/P2/P3 分级表。
- [事实] commit `987777d` 同步更新 README、build 脚本和 `.gemini/extensions/visual-critique/` Gemini extension manifest，使新 plugin 在 Claude Code 与 Gemini CLI 两侧都可用。
- [事实] README 计数随之从 8 plugin 更新到 **91 skills / 28 commands / 9 plugins**（`git show 5446f2a8eb8f:README.md` 核实）。本文件开头“8 个插件、87 个 skills、27 个 commands”的旧表述对应 range 起点 `70cfd54`，已被本轮 range 取代。
- [推断] `visual-critique` 把“视觉评审”从 `design-ops` 的 critique workflow 中独立成名词型 skill 集合，与本仓库 `fe-ui-critique` / `fe-ui-lint-artifact` 同域，可作为分级输出（P1/P2/P3）格式的参考。

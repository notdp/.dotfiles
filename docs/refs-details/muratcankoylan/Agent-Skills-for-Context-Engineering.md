# muratcankoylan/Agent-Skills-for-Context-Engineering

- 上游仓库：`https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/muratcankoylan/Agent-Skills-for-Context-Engineering`
- 主分类：**上下文 / 记忆管理**
- 能力标签：`技能集合与市场`, `多智能体架构`, `评测`
- 一句话总结：围绕 context engineering 的 Agent Skills 集合，重点讲生产级 agent 的上下文设计、记忆、工具与评测。

## 能力概览

- 提供 context fundamentals、degradation、compression、optimization 等核心技能。
- 覆盖 multi-agent architecture、memory systems、tool design、filesystem context、hosted agents。
- 提供 evaluation / advanced-evaluation、LLM-as-a-judge、rubric、pairwise comparison。
- 附带 digital-brain、x-to-book、SFT pipeline 等示例系统。

## 资产盘点

- 13 个核心 skills。
- 5 个 examples。
- 2 个插件清单文件。
- docs/ 下多篇专题文档与约 11 个示例脚本。

## 关键文件

- `README.md`
- `SKILL.md`
- `.plugin/plugin.json`
- `skills/hosted-agents/SKILL.md`
- `examples/digital-brain-skill/README.md`

## 2026-05-27 本地 range 调研

- [事实] 本轮 range：`7a95d94c364e25c869a86896a45791dfda6db8bf..25e1fa79a33f0985793bcab3c64dde8d020c5132`。
- [事实] 上游发布 `v2.2.0` / `v2.3.0`，新增 `researcher/` operating system，包含 benchmarks、claims、corpus、discovery、mechanisms、orchestration、queue、rubrics、runbooks、runs、scripts 与 templates。
- [事实] 新增 `harness-engineering` skill、router benchmark plan、SDK runner scaffold、published router results 与 `render_router_report`，并根据 benchmark 调整 skill descriptions。
- [推断] 该仓库已不只是技能库 + 示例集，而是在把 skill routing、description quality、claim ledger 和 corpus hardening 变成可评测系统。
- [推断] 本仓库可吸收“description 是可评测接口”的方法，先为关键 skills 建立 routing cases / holdout 测试；不应直接引入 continuous loop 或 launchd 自动化。

## 备注

- 更像技能库 + researcher OS + routing benchmark 体系，不是单一可运行应用。

## 最近 14 天更新（2026-03-31 ~ 2026-04-14）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main`
- [事实] 提交数：`0`
- [事实] 这段时间没有新提交可列。
- [事实] 默认分支近 14 天无新提交。
<!-- recent-updates:end -->

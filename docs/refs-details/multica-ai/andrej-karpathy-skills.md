# multica-ai/andrej-karpathy-skills

- 上游仓库：`https://github.com/multica-ai/andrej-karpathy-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/multica-ai/andrej-karpathy-skills`
- 主分类：**行为协议 / 提示工程**
- 能力标签：`Claude Code Guidelines`, `Agent Skills`, `Cursor Rules`, `Simplicity First`, `Surgical Changes`, `Goal-Driven Execution`, `Verification`
- 一句话总结：用一个轻量 `CLAUDE.md` / skill / Cursor rule，把“先澄清、少抽象、精准改动、目标驱动验证”四条编码行为约束打包成跨工具可复用指南。

## 能力概览

- [事实] README 说明该仓库核心是一个单一 `CLAUDE.md`，用于改善 Claude Code 行为，来源于 Karpathy 对 LLM 编码陷阱的观察。
- [事实] 四个原则是：Think Before Coding、Simplicity First、Surgical Changes、Goal-Driven Execution。
- [事实] `CLAUDE.md` 要求显式假设、避免未请求功能、只改必要代码、把任务转成可验证目标。
- [事实] 仓库同时提供 Claude Code plugin manifest、Cursor alwaysApply rule、个人 skill 版本和中英文 README。
- [事实] `EXAMPLES.md` 给出隐藏假设、过度抽象、顺手重构、模糊验证等反例与修正示例。
- [推断] 对本仓库最有价值的不是新增一个平行 workflow skill，而是把“每条改动可追溯到用户请求”“成功标准先行”“不新增未要求灵活性”等检查点下沉到现有 `think-plan`、`dev-tdd`、`dev-simplify`、`guard-verify`、`guard-close`。

## 资产盘点

- 1 个核心指南：`CLAUDE.md`
- 1 个 Claude/Cursor skill：`skills/karpathy-guidelines/SKILL.md`
- 1 个 Cursor rule：`.cursor/rules/karpathy-guidelines.mdc`
- 2 个 Claude plugin / marketplace manifest：`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`
- 2 个 README：`README.md`、`README.zh.md`
- 1 个 Cursor 使用说明：`CURSOR.md`
- 1 个案例集：`EXAMPLES.md`
- [事实] 未发现 `commands/`、`references/`、`scripts/` 目录。

## 关键文件

- `README.md`
- `README.zh.md`
- `CLAUDE.md`
- `CURSOR.md`
- `EXAMPLES.md`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.cursor/rules/karpathy-guidelines.mdc`
- `skills/karpathy-guidelines/SKILL.md`

## 吸收建议

| 推荐项 | 吸收位置 | 理由 |
|---|---|---|
| “每一行修改必须能追溯到用户请求”检查 | `dev-simplify`、`guard-close`、`guard-review` | [推断] 本仓库已有 scope creep 停止规则，可增强为 diff 检查问题。 |
| “不为一次性代码建抽象 / 不加未请求灵活性” | `dev-simplify`、`dev-refactor`、`think-quality` | [推断] 本仓库已有 KISS/YAGNI，可补成 finding 类型。 |
| “成功标准先行，把命令式任务改成可验证目标” | `think-plan`、`dev-tdd`、`guard-verify` | [推断] 与本仓库 verifier 分层高度一致。 |
| 反例库模式 | `docs/software-engineering-research/skill-patterns.md` | [推断] `EXAMPLES.md` 的 wrong / should happen 对照比抽象规则更容易复用。 |
| 多平台同步资产清单 | refs detail 记录即可 | [推断] 可作为“跨 harness 资产同步”的小样本。 |

## 不吸收项

- [推断] 不把整个 `CLAUDE.md` 直接追加到 `agents/AGENTS.md`：本地 AGENTS 已有事实纪律、TDD、scope、验证门禁，直接追加会重复并增大上下文。
- [推断] 不吸收 `.cursor/rules/karpathy-guidelines.mdc` 的 `alwaysApply: true`：本仓库已有自己的全局规则与 skill 路由，照搬 alwaysApply 会形成平行规则源。
- [推断] 不吸收 `.claude-plugin` manifest：本仓库当前 refs 吸收重点是 docs/skills/workflows，不需要引入该 plugin 分发形态。
- [推断] 不原样迁入上游 skill frontmatter：本仓库 skill description 有触发词规范，若未来迁入需要改写。

## 备注

- [推断] 不宜整包吸收为默认 always-on skill；更适合拆成现有 `think-*`、`dev-*`、`guard-*` 工作流中的检查点。
- [推断] “uncertain, ask / stop and ask” 在非交互执行场景下需要改写为“先自查、列假设、写 contract cases 或报告阻塞”，不能照搬。
- [未验证] 仓库上游归属存在不一致：任务给定 URL 是 `multica-ai/andrej-karpathy-skills`，本地 README 安装命令出现 `forrestchang/andrej-karpathy-skills`，未联网核对。

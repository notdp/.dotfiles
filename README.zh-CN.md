# dotfiles

[English](./README.md)

让 30+ AI 编程 Agent 共享 commands、skills 和全局 Agent 指令。

## 安装

```bash
npx github:notdp/.dotfiles install
```

交互式安装器，两种模式：

- **新建** — 从预置 skills & commands 开始，选择需要的
- **导入** — 克隆你自己的 git 仓库

## 卸载

```bash
npx github:notdp/.dotfiles uninstall
```

## 其他命令

```bash
npx -y github:notdp/.dotfiles status   # 检查软链状态
npx -y github:notdp/.dotfiles fix      # 合并独立目录到 dotfiles
```

## 做了什么

将单一源目录软链到每个 agent 的配置路径：

```
~/.claude/commands   → ~/.dotfiles/commands
~/.codex/prompts     → ~/.dotfiles/commands
~/.factory/commands  → ~/.dotfiles/commands
~/.claude/CLAUDE.md  → ~/.dotfiles/agents/AGENTS.md
~/.codex/AGENTS.md   → ~/.dotfiles/agents/AGENTS.md
~/.factory/AGENTS.md → ~/.dotfiles/agents/AGENTS.md
```

改一处，全生效。

### Skills

Skills 由独立的 [`skills`](https://www.npmjs.com/package/skills) CLI 管理，不走本仓库的 installer。它从 GitHub 拉取 skill 包到统一池子，再软链到每个 agent：

```bash
npx skills add <github-repo> -g --all   # 全局安装 skill 包到所有 agent
npx skills ls -g                         # 查看已装的全局 skills
npx skills update -g                     # 把全局 skills 更新到 upstream HEAD
```

布局：

```
~/.agents/skills/<name>/         ← skill 内容（每个 skill 一个目录，从上游拉取）
~/.claude/skills/<name>          → ~/.agents/skills/<name>
~/.codex/skills/<name>           → ~/.agents/skills/<name>
~/.factory/skills/<name>         → ~/.agents/skills/<name>
~/.dotfiles/skills/.skill-lock.json  ← 可移植的锁文件，已 commit 用来追踪版本
```

## Terminal dotfiles (stow)

单目标 dotfile（tmux、ghostty 等）用 [GNU stow](https://www.gnu.org/software/stow/) 管理，与上面的 agent fanout 分开：

```bash
brew install stow            # 一次性
cd ~/.dotfiles && stow -d config -t ~ tmux ghostty
```

每个 package 镜像 home：

```
~/.dotfiles/config/tmux/.tmux.conf                   → ~/.tmux.conf
~/.dotfiles/config/ghostty/.config/ghostty/config    → ~/.config/ghostty/config
```

编辑 `~/.dotfiles/config/...` 下的源文件（home 路径是 symlink 指过来）, commit, 完事。`stow -d config -t ~ -D <pkg>` 拆 symlink。

## 支持的 Agent

33 个 agent + 6 个 universal agent，完整列表：

AdaL, Amp, Antigravity, Augment, Claude Code, Cline, CodeBuddy, Codex, Command Code, Continue, Crush, Cursor, Droid, Gemini CLI, GitHub Copilot, Goose, iFlow CLI, Junie, Kilo Code, Kimi Code CLI, Kiro CLI, Kode, MCPJam, Mistral Vibe, Mux, Neovate, OpenClaw, OpenCode, OpenHands, Pi, Pochi, Qoder, Qwen Code, Roo Code, Trae, Windsurf, Zencoder

## Skills

| Skill | 说明 |
|-------|------|
| **[duoduo](./DUODUO.md)** | Opus + Codex 交叉审查 PR |
| **chrome-devtools-mcp-fix** | 修复 chrome-devtools MCP 连接问题 |
| **chrome-devtools-mock** | 通过 Chrome DevTools 注入脚本 mock 前端 API 数据 |
| **droid-bin-mod** | 修改 droid 二进制以禁用输出截断 |
| **find-skills** | 发现和安装 agent skills |
| **frontend-design** | 创建生产级前端界面 |
| **react** | React 组件开发指南 |
| **react-best-practices** | Vercel 工程团队的 React/Next.js 性能优化指南 |
| **react-doctor** | 诊断和修复 React 代码库健康问题 |
| **shadcn-ui** | shadcn/ui 组件库指南 |

## Commands

| 命令 | 说明 |
|------|------|
| `clip` | 复制内容到剪贴板 |
| `ec` | 编辑配置 |
| `eh` | 编辑历史 |
| `install-react-grab` | 安装 react-grab 组件 |
| `learn` | 从代码库模式中学习 |
| `simplify` | 简化复杂代码 |

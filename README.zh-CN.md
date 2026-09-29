# dotfiles

[English](./README.md)

让 37 个 AI 编程 Agent 共享 slash commands 和全局 Agent 指令。Skills **不**由这里管，归独立的 [`skills`](https://www.npmjs.com/package/skills) CLI（见 [Skills](#skills)）。

## 安装

```bash
npx github:notdp/.dotfiles install
```

交互式安装器，两种模式：

- **新建** — 从预置 commands 开始，选择需要的
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
~/.agents/commands   → ~/.dotfiles/commands     ← 通用池（Amp、Codex、Gemini CLI……）
~/.claude/commands   → ~/.dotfiles/commands
~/.codex/prompts     → ~/.dotfiles/commands
~/.factory/commands  → ~/.dotfiles/commands
~/.claude/CLAUDE.md  → ~/.dotfiles/agents/AGENTS.md
~/.codex/AGENTS.md   → ~/.dotfiles/agents/AGENTS.md
~/.factory/AGENTS.md → ~/.dotfiles/agents/AGENTS.md
```

改一处，全生效。`commands/` 目前是空的——链路搭好了，内容还没往里放。

## Skills

Skills 由独立的 [`skills`](https://www.npmjs.com/package/skills) CLI 管理，不走本仓库的 installer。它从 GitHub 拉取 skill 包到统一池子，再软链到每个 agent：

```bash
npx skills add <github-repo> -g --all   # 全局安装 skill 包到所有 agent
npx skills ls -g                         # 查看已装的全局 skills
npx skills update -g                     # 把全局 skills 更新到 upstream HEAD
```

布局：

```
~/.agents/skills/<name>/     ← skill 内容（每个 skill 一个目录，从上游拉取）
~/.claude/skills/<name>      → ~/.agents/skills/<name>
~/.factory/skills/<name>     → ~/.agents/skills/<name>
```

通用 agent（Amp、Codex、Gemini CLI……）直接读 `~/.agents/skills`，不会有每个 agent 一份的软链。

这套东西里只有 lock 文件归本仓库。它放在 `skills/` 外面，好让发布目录保持干净，再手工链到 CLI 会读的两个位置：

```
~/.agents/.skill-lock.json          → ~/.dotfiles/state/.skill-lock.json
~/.claude/skills/.skill-lock.json   → ~/.dotfiles/state/.skill-lock.json
```

有个每日 routine 跑 `npx skills update -g -y` 并提交 lock 变更。

## 定时任务

Claude Code 的 routine 放在 `scheduled-tasks/`，手工链接（不经过 installer）：

```
~/.claude/scheduled-tasks → ~/.dotfiles/scheduled-tasks
```

其中两个是本机专用的，已 gitignore。

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

编辑 `~/.dotfiles/config/...` 下的源文件（home 路径是 symlink 指过来），commit，完事。`stow -d config -t ~ -D <pkg>` 拆 symlink。

## 目录结构

| 路径 | 是什么 | 谁连的 |
|------|--------|--------|
| `commands/` | slash commands，所有 agent 共享 | installer |
| `agents/AGENTS.md` | 全局 agent 指令 | installer |
| `skills/` | 本仓库**对外发布**的 skill —— `npx skills add notdp/.dotfiles` | skills CLI |
| `state/` | 本机状态，目前只有 `.skill-lock.json` | 手工链接 |
| `scheduled-tasks/` | Claude Code routine | 手工链接 |
| `config/` | terminal dotfiles 的 stow package | stow |
| `bin/` | 辅助可执行文件，按绝对路径被引用 | — |
| `statusline.sh` | Claude Code statusline，在 `~/.claude/settings.json` 里配 | — |
| `scripts/` | installer 本体 | — |
| `.arch/` | 早期的脚手架（duoduo 双 agent PR review），现在没被任何东西引用 | — |

## 支持的 Agent

37 个。其中 6 个（Amp、Codex、Gemini CLI、GitHub Copilot、Kimi Code CLI、OpenCode）直接读通用池 `~/.agents`，不需要单独软链。

AdaL, Amp, Antigravity, Augment, Claude Code, Cline, CodeBuddy, Codex, Command Code, Continue, Crush, Cursor, Droid, Gemini CLI, GitHub Copilot, Goose, iFlow CLI, Junie, Kilo Code, Kimi Code CLI, Kiro CLI, Kode, MCPJam, Mistral Vibe, Mux, Neovate, OpenClaw, OpenCode, OpenHands, Pi, Pochi, Qoder, Qwen Code, Roo Code, Trae, Windsurf, Zencoder

## 本仓库发布的 Skills

```bash
npx skills add notdp/.dotfiles -g
```

| Skill | 说明 |
|-------|------|
| **polish** | 去掉 PR、commit、文档、消息里的机器味 |
| **ccd-account-switch** | 切 Claude 账号后，把 session 列表和 routine 迁到新账号 |

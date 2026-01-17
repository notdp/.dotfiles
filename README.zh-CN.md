# dotfiles

[English](./README.md)

让 Claude Code、Codex、Droid、Antigravity 共享 commands、skills 和全局 Agent 配置。

## 做了什么

**Commands:**

```plain
~/.claude/commands   → ~/.dotfiles/commands (软链)
~/.codex/prompts     → ~/.dotfiles/commands (软链)
~/.factory/commands  → ~/.dotfiles/commands (软链)
~/.gemini/antigravity/global_workflows → ~/.dotfiles/commands (软链)
```

**Skills:**

```plain
~/.claude/skills                → ~/.dotfiles/skills (软链)
~/.codex/skills                 → ~/.dotfiles/skills (软链)
~/.factory/skills               → ~/.dotfiles/skills (软链)
~/.gemini/antigravity/skills    → ~/.dotfiles/skills (软链)
```

**全局 Agent 配置 (AGENTS.md):**

```plain
~/.claude/CLAUDE.md  → ~/.dotfiles/agents/AGENTS.md (软链)
~/.factory/AGENTS.md → ~/.dotfiles/agents/AGENTS.md (软链)
~/.codex/AGENTS.md   → ~/.dotfiles/agents/AGENTS.md (软链)
```

改一处，全生效。

## 可用资源

### Skills

| Skill | 说明 |
|-------|------|
| **[duoduo](./DUODUO.md)** | Opus + Codex Cross-review PR，支持本地或 GitHub Actions |
| **agent-browser** | 自动化浏览器操作：网页测试、截图、数据提取 |
| **react-best-practices** | Vercel 工程团队的 React/Next.js 性能优化指南 |
| **web-design-guidelines** | 检查 UI 代码是否符合 Web 界面设计规范 |
| **droid-bin-mod** | 修改 droid 二进制以禁用输出截断 |

### Commands

| 命令 | 说明 |
|------|------|
| `commit` | 智能 git commit，自动生成提交信息 |
| `cross-review` | Cross-review 当前 PR |
| `clip` | 复制内容到剪贴板 |
| `learn` | 从代码库模式中学习 |
| `simplify` | 简化复杂代码 |
| `pptx` | 生成 PowerPoint 演示文稿 |

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/install.sh | bash
```

## 支持的 CLI

- Claude Code (`~/.claude/commands`)
- Codex (`~/.codex/prompts`)
- Droid (`~/.factory/commands`)
- Antigravity (`~/.gemini/antigravity/global_workflows`)

想添加新 IDE/CLI 支持？欢迎 PR 到 `scripts/config.json`。

## 卸载

```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/uninstall.sh | bash
```

## 高级用法（可选）

- 自定义安装路径（默认 `~/.dotfiles`）：

```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/install.sh | bash -s -- ~/.my-dotfiles
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/uninstall.sh | bash -s -- ~/.my-dotfiles
```

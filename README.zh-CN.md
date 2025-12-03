# dotfiles

[English](./README.md)

让 Claude Code、Codex、Droid、Antigravity 共享同一个 commands 目录。

## 做了什么

```
~/.claude/commands   → ~/.dotfiles/commands (软链)
~/.codex/prompts     → ~/.dotfiles/commands (软链)
~/.factory/commands  → ~/.dotfiles/commands (软链)
~/.gemini/antigravity/global_workflows → ~/.dotfiles/commands (软链)
```

改一处，全生效。

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

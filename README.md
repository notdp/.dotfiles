# dotfiles

[中文](./README.zh-CN.md)

Share commands, skills, and global agent instructions across Claude Code, Codex, Droid, and Antigravity.

## What it does

**Commands:**
```
~/.claude/commands   → ~/.dotfiles/commands (symlink)
~/.codex/prompts     → ~/.dotfiles/commands (symlink)
~/.factory/commands  → ~/.dotfiles/commands (symlink)
~/.gemini/antigravity/global_workflows → ~/.dotfiles/commands (symlink)
```

**Skills:**
```
~/.claude/skills                → ~/.dotfiles/skills (symlink)
~/.codex/skills                 → ~/.dotfiles/skills (symlink)
~/.factory/skills               → ~/.dotfiles/skills (symlink)
~/.gemini/antigravity/skills    → ~/.dotfiles/skills (symlink)
```

**Global Agent Instructions (AGENTS.md):**
```
~/.claude/CLAUDE.md  → ~/.dotfiles/agents/AGENTS.md (symlink)
~/.factory/AGENTS.md → ~/.dotfiles/agents/AGENTS.md (symlink)
~/.codex/AGENTS.md   → ~/.dotfiles/agents/AGENTS.md (symlink)
```

Edit once, apply everywhere.

## Install
```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/install.sh | bash
```

## Supported CLIs

- Claude Code (`~/.claude/commands`)
- Codex (`~/.codex/prompts`)
- Droid (`~/.factory/commands`)
- Antigravity (`~/.gemini/antigravity/global_workflows`)

Want another IDE/CLI? PR to `scripts/config.json`.

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/uninstall.sh | bash
```

## Advanced (optional)

- Custom install path (defaults to `~/.dotfiles`):

```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/install.sh | bash -s -- ~/.my-dotfiles
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/uninstall.sh | bash -s -- ~/.my-dotfiles
```

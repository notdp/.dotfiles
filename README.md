# dotfiles

[中文](./README.zh-CN.md)

Share commands, skills, and global agent instructions across Claude Code, Codex, Droid, and Antigravity.

## What it does

**Commands:**

```plain
~/.claude/commands   → ~/.dotfiles/commands (symlink)
~/.codex/prompts     → ~/.dotfiles/commands (symlink)
~/.factory/commands  → ~/.dotfiles/commands (symlink)
~/.gemini/antigravity/global_workflows → ~/.dotfiles/commands (symlink)
```

**Skills:**

```plain
~/.claude/skills                → ~/.dotfiles/skills (symlink)
~/.codex/skills                 → ~/.dotfiles/skills (symlink)
~/.factory/skills               → ~/.dotfiles/skills (symlink)
~/.gemini/antigravity/skills    → ~/.dotfiles/skills (symlink)
```

**Global Agent Instructions (AGENTS.md):**

```plain
~/.claude/CLAUDE.md  → ~/.dotfiles/agents/AGENTS.md (symlink)
~/.factory/AGENTS.md → ~/.dotfiles/agents/AGENTS.md (symlink)
~/.codex/AGENTS.md   → ~/.dotfiles/agents/AGENTS.md (symlink)
```

Edit once, apply everywhere.

## Available Resources

### Skills

| Skill                     | Description                                                                      |
| ------------------------- | -------------------------------------------------------------------------------- |
| **[duoduo](./DUODUO.md)** | Cross-review PRs with Opus + Codex. Works via GitHub Actions or locally with [duo-cli](https://github.com/notdp/duo-cli) |
| **agent-browser**         | Automates browser interactions for web testing, screenshots, and data extraction |
| **react-best-practices**  | React/Next.js performance optimization guidelines from Vercel Engineering        |
| **web-design-guidelines** | Review UI code for Web Interface Guidelines compliance                           |
| **droid-bin-mod**         | Modify droid binary to disable output truncation                                 |

### Commands

| Command        | Description                                  |
| -------------- | -------------------------------------------- |
| `commit`       | Smart git commit with auto-generated message |
| `cross-review` | Cross-review current PR                      |
| `clip`         | Copy content to clipboard                    |
| `learn`        | Learn from codebase patterns                 |
| `simplify`     | Simplify complex code                        |
| `pptx`         | Generate PowerPoint presentations            |

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

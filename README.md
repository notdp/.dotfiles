# dotfiles

[中文](./README_CN.md)

Share a single commands directory across Claude CLI, Codex CLI, and Factory CLI.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/bootstrap.sh | bash
```

## Advanced Install (with version control)

**1. Fork & Clone**

```bash
git clone https://github.com/<your-username>/.dotfiles.git <target-dir>
```

`<target-dir>` is the directory you want to version control (e.g., `~/.dotfiles`).

**2. Create symlinks**

```bash
cd <target-dir>
./scripts/install.sh
```

## What it does

```
~/.claude/commands   → <target-dir>/commands (symlink)
~/.codex/prompts     → <target-dir>/commands (symlink)
~/.factory/commands  → <target-dir>/commands (symlink)
```

All three tools share the same directory. Edit once, apply everywhere.

## Configuration (Advanced)

Edit `config.json`:

```json
{
  "link_targets": [
    "~/.claude/commands",
    "~/.codex/prompts",
    "~/.factory/commands"
  ]
}
```

- `link_targets`: Directories to symlink

Re-run `./scripts/install.sh` after changing config.

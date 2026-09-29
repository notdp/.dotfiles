# dotfiles

[中文](./README.zh-CN.md)

Share slash commands and global agent instructions across 37 AI coding agents. Skills are **not** handled here — they are managed by the standalone [`skills`](https://www.npmjs.com/package/skills) CLI (see [Skills](#skills)).

## Install

```bash
npx github:notdp/.dotfiles install
```

Interactive installer with two setup modes:

- **Create new** — copy this repo's `commands/` and `agents/` as a starting point
- **Import existing** — clone your own git repository

## Uninstall

```bash
npx github:notdp/.dotfiles uninstall
```

## Other commands

```bash
npx -y github:notdp/.dotfiles status   # check symlink status
npx -y github:notdp/.dotfiles fix      # merge standalone dirs into dotfiles
```

## What it does

Symlinks a single source directory to every agent's config path:

```
~/.agents/commands   → ~/.dotfiles/commands     ← universal pool (Amp, OpenCode, …)
~/.claude/commands   → ~/.dotfiles/commands
~/.codex/prompts     → ~/.dotfiles/commands
~/.factory/commands  → ~/.dotfiles/commands
~/.claude/CLAUDE.md  → ~/.dotfiles/agents/AGENTS.md
~/.codex/AGENTS.md   → ~/.dotfiles/agents/AGENTS.md
~/.factory/AGENTS.md → ~/.dotfiles/agents/AGENTS.md
```

Edit once, apply everywhere. `commands/` is currently empty — the fanout is wired up, the content isn't there yet.

## Skills

Skills are managed by the standalone [`skills`](https://www.npmjs.com/package/skills) CLI, not this installer. It pulls skill packages from GitHub into a universal pool and symlinks them into each agent:

```bash
npx skills add <github-repo> -g --all   # install a skill package globally to every agent
npx skills ls -g                         # list global skills
npx skills update -g                     # refresh global skills to upstream HEAD
```

Layout:

```
~/.agents/skills/<name>/     ← skill content (one dir per skill, fetched from upstream)
~/.claude/skills/<name>      → ~/.agents/skills/<name>
~/.factory/skills/<name>     → ~/.agents/skills/<name>
```

Universal agents (Amp, Codex, Gemini CLI, …) read `~/.agents/skills` directly and get no per-agent symlink.

The lock file is this repo's only piece of that setup. It lives outside `skills/` so the publish catalog stays clean, and is hand-linked into both paths the CLI reads:

```
~/.agents/.skill-lock.json          → ~/.dotfiles/state/.skill-lock.json
~/.claude/skills/.skill-lock.json   → ~/.dotfiles/state/.skill-lock.json
```

A daily routine runs `npx skills update -g -y` and commits the bump.

## Scheduled tasks

Claude Code routines live in `scheduled-tasks/`, hand-linked (not by the installer):

```
~/.claude/scheduled-tasks → ~/.dotfiles/scheduled-tasks
```

Two of them are machine-local and gitignored.

## Terminal dotfiles (stow)

Plain single-target dotfiles (tmux, ghostty, ...) are managed with [GNU stow](https://www.gnu.org/software/stow/), kept separate from the agent fanout above.

```bash
brew install stow            # one-time
cd ~/.dotfiles && stow -d config -t ~ tmux ghostty
```

Each package mirrors home:

```
~/.dotfiles/config/tmux/.tmux.conf                   → ~/.tmux.conf
~/.dotfiles/config/ghostty/.config/ghostty/config    → ~/.config/ghostty/config
```

Edit the file under `~/.dotfiles/config/...` (the home paths are symlinks pointing here), commit, done. `stow -d config -t ~ -D <pkg>` removes the symlinks.

## Layout

| Path | What | Wired by |
|------|------|----------|
| `commands/` | slash commands, shared by every agent | installer |
| `agents/AGENTS.md` | global agent instructions | installer |
| `skills/` | skills **published** from this repo — `npx skills add notdp/.dotfiles` | skills CLI |
| `state/` | machine state, currently just `.skill-lock.json` | hand-linked |
| `scheduled-tasks/` | Claude Code routines | hand-linked |
| `config/` | stow packages for terminal dotfiles | stow |
| `bin/` | helper executables, referenced by absolute path | — |
| `statusline.sh` | Claude Code statusline, set in `~/.claude/settings.json` | — |
| `scripts/` | the installer itself | — |
| `.arch/` | older scaffolding (duoduo dual-agent PR review), not referenced by anything here | — |

## Supported agents

37 agents: 33 have a path of their own, and 6 (Amp, Codex, Gemini CLI, GitHub Copilot, Kimi Code CLI, OpenCode) read from the universal `~/.agents` pool. Codex and Gemini CLI are in both groups — they get a per-agent symlink *and* read the pool.

AdaL, Amp, Antigravity, Augment, Claude Code, Cline, CodeBuddy, Codex, Command Code, Continue, Crush, Cursor, Droid, Gemini CLI, GitHub Copilot, Goose, iFlow CLI, Junie, Kilo Code, Kimi Code CLI, Kiro CLI, Kode, MCPJam, Mistral Vibe, Mux, Neovate, OpenClaw, OpenCode, OpenHands, Pi, Pochi, Qoder, Qwen Code, Roo Code, Trae, Windsurf, Zencoder

## Skills published here

```bash
npx skills add notdp/.dotfiles -g
```

| Skill | Description |
|-------|-------------|
| **polish** | Strip AI-speak out of PRs, commits, docs, and messages |
| **ccd-account-switch** | After switching Claude accounts, carry sessions and routines over to the new one |

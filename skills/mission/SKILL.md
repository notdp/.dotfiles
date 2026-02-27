---
name: mission
description: Coordinate multiple droid agents working in parallel via tmux panes. Use when the user explicitly asks for an "agent team", "mission", "teammates", or when the task requires agents that can see each other's work, communicate directly, share a task list, or when the user wants to observe and steer multiple agents in real-time. Do NOT use for simple parallel tasks where subagents suffice — mission is for persistent, interactive, collaborative teams. Also activates automatically when MISSION_AGENT_NAME environment variable is set (you are a teammate). Do not read mission source code — use the CLI commands below.
---

# Mission — Multi-Agent Collaboration

> All operations use the `mission` CLI. Do not operate tmux directly.

Environment variables `MISSION_TEAM_NAME` and `MISSION_AGENT_NAME` are auto-detected. When set, `-t` can be omitted.

## Commands

```bash
# Lifecycle
mission create <team-name> -d "description"
mission spawn <agent> -m <model> --skill <skill> -e KEY=VALUE -p "prompt"
mission delete <team-name>

# Communication
mission type <agent> "prompt text"     # send prompt to agent session

# Observe
mission status                         # agent health (JSON)
mission capture <agent>                # view agent pane output
mission interrupt <agent>              # press Escape in agent
```

### `spawn` options

| Flag | Description |
|------|-------------|
| `-m` | Model ID (temporarily sets in settings.json, restores after) |
| `--skill` | Skill to load on startup (default: `mission`, use `none` to skip) |
| `-e` | Extra env var `KEY=VALUE` (repeatable) |
| `-p` | Initial prompt (typed into TUI after skill loads) |
| `--cwd` | Working directory for the agent |

## Guidelines

- Give each agent a **self-contained prompt** with all needed context
- Size tasks so agents can work **independently** without editing the same files
- Use `mission capture` to observe progress
- Use `mission type` to send follow-up instructions
- Shut down agents before deleting the team

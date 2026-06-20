# Steering Claude Code: CLAUDE.md files, skills, hooks, rules, subagents and more

Source: https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
Original author: Anthropic (official Claude Code blog)
Published: 2026-06-18
Source type: official vendor blog / product documentation
Confidence: confirmed from fetched source (full body; the short intro paragraph before the "Rules" section was truncated at fetch start)
Fetched: 2026-06-19

> Harness relevance: canonical vendor description of Claude Code "steering surfaces" and the
> underlying trade-off — **context cost vs instruction-following weight**. Use as vocabulary and
> a decision lens, not as implementation authority.
>
> Multi-platform caution: several mechanisms here are **Claude-Code-native** — path-scoped rules
> (`.claude/rules/` + `paths:`), output styles, `append-system-prompt`, plugins, and the specific
> compaction / skill re-injection behavior. Cross-agent parity (kilo / opencode / droid / codex) is
> **unverified** and must be checked before adopting any of them into the multi-platform harness.
> Where another platform cannot follow, treat the capability as an explicit CC-only differentiation
> and record the divergence (do not silently assume SSOT parity).

---

### Rules

[Rules](https://code.claude.com/docs/en/memory) are markdown files in `.claude/rules/` that give Claude specific constraints or conventions.

Unscoped rules behave like CLAUDE.md in that they are always loaded at session start and get re-injected on compaction. This can waste tokens by loading context even when it's not relevant for the task at hand.

Path-scoped rules allow you to load rule instructions only when they are relevant by adding a `paths` field that controls when they load.

For example: a rule scoped to `src/api/**` stays out of context during a docs-only session. It would only be loaded whenever Claude reads files within that `src/api/` directory.

Here's what that looks like:

```
---
paths:
  - "src/api/**"
  - "**/*.handler.ts"
---
All API handlers must validate input with Zod before processing.
```

**Tip**: A file-specific constraint, like "migrations are append-only," fits best as a **rule** placed in your paths: frontmatter. Reach for a path scoped rule over a nested CLAUDE.md file when the instruction regards a cross-cutting concern or file that appears in multiple (but not all) corners of the codebase.

### Skills

[Skills](https://code.claude.com/docs/en/skills) live in `.claude/skills/` as folders of instructions, scripts, and resources that Claude loads dynamically. Each skill has a `SKILL.md` file with a name, description, and body.

Only the name and description load at session start; the full body loads when Claude invokes the skill, either through a slash command (/code-review) or by auto-matching the task.

_[image caption] Skills are triggered via your system prompt._

For example, `/code-review` is a built-in skill that reviews your current diff and reports its findings without editing files. The skill defines the playbook so Claude follows the same structured approach every time you invoke it.

On compaction, Claude Code re-injects invoked skills up to a total budget across all invoked skills. If you've invoked many skills during a session, the oldest ones drop first.

**Tip:** Instructions that are procedural, like deploy workflows, release checklists, or review processes, belong in a skill rather than in CLAUDE.md.

Claude Code ships with skills, but you can also write your own custom skills.

### Subagents

[Subagents](https://code.claude.com/docs/en/sub-agents) are markdown files in `.claude/agents/` that define isolated assistants for specific side tasks. Each file uses YAML frontmatter (name, description, plus optional fields for model and tool access) followed by a body that becomes that subagent's system prompt.

Subagents are similar to skills in that the name, description, and tool list load at session start, but the larger context within the body of the agent doesn't auto-invoke. Claude calls them via the Agent tool, passing in a prompt string.

_[image caption] Claude Code's context window holds everything Claude knows about your session._

Not only does the larger instructional context within the body of the subagent not auto-invoke, it never enters the parent conversation at all.

The subagent then runs in its own fresh context window, and the only thing that returns to your main session is the subagent's final message (often the aggregated result of many subtasks) plus metadata.

This pattern scales: subagents can nest up to five levels deep, and [dynamic workflows](https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code) orchestrate tens to hundreds of background agents without requiring you to specify each detail of the subagent architecture. The orchestration plan and intermediate results live in script variables rather than in Claude's context window, which enables scale without losing instructional fidelity.

**Tip:** That isolation is one of the main reasons to reach for a subagent instead of a skill. Use a subagent when a side task like deep search, a log analysis pass, or a dependency audit would clutter your main conversation with intermediate results you won't reference again. Use a skill when you want the procedure to play out inside the main thread so you can see and steer each step.

### Hooks

[Hooks](https://code.claude.com/docs/en/hooks-guide) are user-defined commands, HTTP endpoints, or LLM prompts that provide more deterministic control over Claude's behavior by firing on specific events in Claude's lifecycle like file edits, tool calls, or session start.

_[image caption] A map of events in a Claude Code session when a hook can fire._

You register hooks in `settings.json`, managed policy settings, or skill/agent frontmatter.

There are several types of hooks: command, HTTP, mcp_tool, prompt, and agent. All hooks are deterministically triggered. The first three execute deterministically while the latter two, prompt and agent, use Claude's judgment rather than a set of rules to determine the output.

Hooks have low context costs because the configuration or instruction lives outside the main context window. The harness runs the handler (command, http, mcp_tool) or makes model calls with separate windows (prompt, agent) depending on the hook type.

Some hooks may have the output saved to the main context window. For example, a blocking hook's standard error is saved within context so Claude knows why the call was denied.

But most hooks won't have the output saved to the main window unless the configuration explicitly returns it. If you backed up your chat history into another file for later reference before compaction using the `PreCompact` event, Claude wouldn't know which file had the chat history saved.

This makes these hook types fundamentally different from CLAUDE.md, rules, and skills.

**Tip:** Use hooks for anything that should happen deterministically: running linters after edits, posting to Slack on completion, or blocking specific commands before they execute. A `PreToolUse` hook can inspect any tool call and exit code 2 to deny it.

They have low context cost because they are code that the harness runs rather than instructions to Claude that get loaded into context.

### Output styles

[Output styles](https://code.claude.com/docs/en/output-styles) are files in `.claude/output-styles/` that inject instructions into the system prompt. They never get compacted, load at the start of every session, and are cached after the first request within a session, meaning they have a moderate context cost.

Because they sit in the system prompt, output styles carry the highest instruction-following weight of any method that we've covered so far and should be used judiciously.

**Changes to the output style will replace the default output style** (unless you set keep-coding-instructions: true in the style's frontmatter).

In Claude Code, this would remove instructions that tell Claude it is helping users with software engineering tasks and contains other critical default instructions such as:

- How to scope changes;
- When to add or omit code comments;
- What to do about security concerns; and
- Verification habits like running tests before declaring work complete.

By default, a custom output style drops all of this and Claude Code becomes more of a general assistant than a software engineer assistant.

**Tip**: Before writing a custom output style, check the built-in styles. **Proactive**, **Explanatory**, and **Learning** cover the most common needs (autonomy, teaching mode, collaborative coding) without you having to maintain a style file.

### Appending the system prompt

An alternative to modifying output styles is the `append-system-prompt` flag. Whereas modifying output style files can have large, unintended changes to Claude's behavior, the append flag is only additive to the original system prompt. It doesn't modify Claude's role; it just adds instructions to its default role.

It is also passed at invocation time, and only applies to that invocation, rather than persisted as a file across sessions.

Appending the system prompt can have a higher context cost compared to other methods of passing instructions. It increases input tokens, though prompt caching reduces this cost after the first request in a session. Instructing Claude to use a more verbose or longer style also increases output tokens.

**Tip:** Appending the system prompt is best for adding specific coding standards, output formatting, or domain-specific knowledge. Keep in mind that appending the system prompt has diminishing returns for adherence. Generally, the more instructions you provide using this method, the less strictly Claude will follow them, particularly if any contradict.

## Quick tips for Claude Code customization

If you find yourself doing one of the following, you may want to consider an alternative location for your instructions:

**"Every time X, always do Y" in CLAUDE.md.** If the behavior should happen reliably, like running prettier after every edit or posting to Slack on completion, use a hook in `settings.json` instead. The model choosing to run a formatter is different from the formatter running automatically.

**"Never do this" in CLAUDE.md.** When there's something that absolutely must not happen, an instruction is the wrong tool. Claude will follow the instruction most of the time, but when under pressure, in a long session or an ambiguous situation, or due to a prompt injection in a file accessed as part of the task, the model can fail to follow a prompted rule. A real guardrail needs to be deterministic, and the enforcement methods are hooks and permissions. A `PreToolUse` hook can inspect a call and exit with code 2 to block it. Managed settings go further: they are admin-deployed, cannot be overridden by a user's local config, and are the only way to enforce a deterministic, organization-wide guardrail.

**A 30-line procedure in CLAUDE.md.** Procedures belong in skills. CLAUDE.md is for facts Claude should hold all the time: build commands, monorepo layout, team conventions. A deployment runbook or a security review checklist should live in `.claude/skills/`, where the body loads only when invoked.

**An API-specific rule without paths.** If a rule only applies to `src/api/**`, scoping it with `paths:` keeps it out of context during unrelated work. An unscoped rule is mechanically identical to putting the content in CLAUDE.md: always loaded, always costing tokens.

**Writing personal preferences to a project-level CLAUDE.md file.** All file-based methods have a user-level counterpart loaded for every Claude Code session regardless of which repo you're in. Use local files for personal preferences (always use semantic commit messages). Keep project-level files for preferences that are team-wide but specific to a given codebase.

## Getting started

You can find more tips and patterns for getting the most out of Claude Code in the best practices for Claude Code documentation.

Once you have a few of these working, you can bundle many of them (skills, subagents, hooks, output styles) as a [plugin](https://code.claude.com/docs/en/plugins) to share a coherent setup across teammates or projects.

---

## Steering-surface comparison (derived from the article)

| Mechanism | When it enters context | Instruction weight | Survives compaction? | CC-native? |
|---|---|---|---|---|
| CLAUDE.md / unscoped rules | Every session start; re-injected on compaction | medium | yes (re-injected) | shared concept |
| Path-scoped rules (`paths:`) | Only when a matching file is read | medium | only while relevant files in play | **CC-native** |
| Skills | name+desc at start; body on invoke | medium | re-injected up to a budget; **oldest invoked drop first** | shared concept |
| Subagents | name+desc+tools at start; body never enters parent | medium | body N/A; only returned final message lives in context | shared concept |
| Hooks | config lives **outside** context | **highest (deterministic)** | unaffected (code, not context) | shared concept |
| Output styles | injected into **system prompt** | **highest** | never compacted | **CC-native** |
| `append-system-prompt` | system prompt, invocation-scoped | high (diminishing returns) | n/a (per invocation) | **CC-native flag** |

## Decision tips (where an instruction belongs)

- "Every time X always do Y" -> hook (deterministic), not CLAUDE.md.
- "Never do X" -> hook / permissions / managed settings (real guardrails are deterministic), not an instruction.
- 30-line procedure -> skill (body loads only when invoked), not CLAUDE.md.
- Rule only relevant to part of the tree (e.g. `src/api/**`) -> path-scoped rule, not an unscoped/always-on rule.
- Personal preference -> user-level file, not project-level CLAUDE.md.

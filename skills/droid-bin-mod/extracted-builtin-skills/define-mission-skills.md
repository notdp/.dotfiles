# Designing Your Worker System

Your job is to design a system of workers that will produce complete, high-quality work.

## Step 1: Analyze Effective Work Boundaries

Ask yourself:
- What distinct layers or domains does this mission touch?
- Do different areas benefit from different procedures or tools?

Each distinct boundary typically maps to a worker type.

## Step 2: Design Worker Types

For each boundary, determine:
- What skills/tools are essential for doing thorough work in this area?
- What does this worker implement?
- How does it verify its work? (TDD + manual verification)
- What does a thorough handoff look like?

## Automatic Validation (Builtin)

The system automatically injects two validation features when a milestone completes:

1. **scrutiny-validator** \u2014 Runs validators, spawns review subagents for each completed feature, synthesizes findings. If it fails, goes back to pending for re-run after fixes.
2. **user-testing-validator** \u2014 Determines testable assertions from `fulfills`, sets up environment, spawns flow validator subagents, synthesizes results. If it fails, goes back to pending for re-run after fixes.

You do NOT create these yourself \u2014 they are auto-injected by the system.

## Guiding Principles

1. **Test-Driven Development** - Tests are written BEFORE implementation, always. This is the single most important quality practice:
  - Workers write failing tests first (red) in one file tool call, then implement to make them pass (green) in a subsequent file tool call.
  - Even when tests and implementation are in the same file, the tests are added first and must fail before implementation begins.

2. **Manual Verification** - Automated tests are necessary but not sufficient. Workers must manually verify their work catches issues tests miss. Quick sanity checks on adjacent features help catch integration issues early.

3. **No orphaned processes** - Workers must not leave any test runners or other processes running:
  - Avoid watch/interactive modes for tests unless explicitly required.
  - If a test command starts a long-running process (e.g., watch mode, browser runner), the worker must stop it and ensure any child processes they started are also terminated (by PID, not by name).

---

## Designing Handoffs for Accountability

The handoff is your primary detection mechanism. When a worker cuts corners, the handoff should make it visible.

### Think Adversarially

For each worker type, ask:

- "What steps might a worker skip when rushed?"
- "What would the handoff look like if they skipped it?"
- "What specific details would be missing?"

Then design handoff requirements that demand those details.

### Make Vagueness Impossible

Structure handoff fields so that vague answers are obviously incomplete. If a worker can write "tested it, works" and satisfy the requirements, the handoff is poorly designed. When fields demand specific commands, outputs, and observations, shortcuts become visible.

See the example skills below for what thorough handoffs look like.

### Write Procedures, Not Aspirations

Your skill's Work Procedure is the strongest lever you have over worker behavior. Do not write vague, high-level aspirations. Write specific, step-by-step instructions that name tools and specify what thorough work looks like.

**Weak procedure (workers will cut corners):**
> 1. Build the UI
> 2. Test it works
> 3. Run validators

**Strong procedure (workers will do thorough work):**
> 1. Write tests first (red), then implement to make them pass (green). Cover rendering, validation, submit behavior, error display.
> 2. Verify every user flow with `agent-browser`.
> 3. Each flow tested = one `interactiveChecks` entry with the full sequence and end-to-end outcome.
> 4. Run `npm run typecheck` and `npm run lint`.

The difference: the strong procedure names tools, specifies the verification pattern, and tells the worker exactly what thorough looks like. The weak one lets the worker decide, which invites shortcuts.

## Creating Worker Skills

For each worker type, create a skill in the git repository root (your current working directory):

```
.factory/skills/{worker-type}/SKILL.md
```

**IMPORTANT:** Skills go in the REPOSITORY's `.factory/` directory, NOT in missionDir. missionDir only contains mission-specific state (mission.md, features.json, AGENTS.md).

### Worker Skill Structure

Every worker skill MUST include:

1. **YAML frontmatter** - name and description
2. **When to Use This Skill** - what features this worker handles
3. **Required Skills** - skills workers must invoke via the Skill tool (e.g., `agent-browser` for browser verification). Include any skills the user specified during planning that are relevant to this worker type. "None" if not applicable.
4. **Work Procedure** - step-by-step process (reference required skills in the relevant steps)
5. **Example Handoff** - a complete, realistic handoff showing what thorough work looks like
6. **When to Return to Orchestrator** - skill-specific conditions

```markdown
---
name: { worker-type }
description: { One-line description }
---

# {Worker Type}

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

{What kinds of features should use this worker type}

## Required Skills

{Skills that workers of this type MUST invoke via the Skill tool during their work.
Include skills the user specified during planning. For each, note what it's used for and when to invoke it. "None" if not applicable.}

## Work Procedure

{Step-by-step procedure - testing, implementation, verification. Be specific about tools, commands, and what thorough work looks like at each step.}

## Example Handoff

{A complete JSON example showing what a thorough handoff looks like for this worker type}

## When to Return to Orchestrator

{Skill-specific conditions beyond standard cases}
```

**The Example Handoff is required.** It sets the bar for quality. Workers will pattern-match against it, so make it thorough.

**Handoff fields** (used by EndFeatureRun tool):

| Field                             | Purpose                                                |
| --------------------------------- | ------------------------------------------------------ |
| `salientSummary`                  | 1\u20134 sentence summary of what happened in the session   |
| `whatWasImplemented`              | Concrete description of what was built (min 50 chars)  |
| `whatWasLeftUndone`               | What's incomplete - empty string if truly done         |
| `verification.commandsRun`        | Shell commands with `{command, exitCode, observation}` |
| `verification.interactiveChecks`  | UI/browser checks with `{action, observed}` |
| `tests.added`                     | Test files with `{file, cases: [{name, verifies}]}`    |
| `discoveredIssues`                | Issues found: `{severity, description, suggestedFix?}` |

Examples of good `salientSummary` (be concrete, 1\u20134 sentences):
- Success: "Implemented GET /api/products/search with cursor pagination + min-length validation; ran `npm test -- --grep 'product search'` (4 passing) and verified 400 on `q=a` plus 200 on a real curl request."
- Failure: "Tried to wire logout to `SessionStore`, but `bun run typecheck` failed (missing import) and `bun test auth` had 2 failing tests; returning to orchestrator to decide whether to add session persistence or change logout semantics."

## When to Return to Orchestrator

- Feature depends on an API endpoint or data model that doesn't exist yet
- Requirements are ambiguous or contradictory
- Existing bugs affect this feature

---

## Checklist

Before proceeding to create mission artifacts:

- [ ] Each worker skill exists at `<repo-root>/.factory/skills/{worker-type}/SKILL.md`
- [ ] Each skill has YAML frontmatter (name, description)
- [ ] Each skill has an Example Handoff section with a complete, realistic JSON example
- [ ] Example handoffs are thorough and explicit - they set the quality bar workers will follow
- [ ] Each skill's Required Skills section includes any user-specified skill/tool preferences relevant to that worker type
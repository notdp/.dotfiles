---
name: think
description: "Turns rough ideas into approved plans with validated structure before writing code. Covers new features, architecture decisions, and value judgments about whether to build, keep, or remove something. Not for bug fixes or small edits."
when_to_use: "出方案, 给方案, 深入分析, 怎么设计, 用什么方案, 判断一下, 有没有必要, 值不值得, what's the best approach, plan this, how should I, should we keep this"
metadata:
  version: "3.14.0"
---

# Think: Design and Validate Before You Build

Prefix your first line with 🥷 inline, not as its own paragraph.


Turn a rough idea into an approved plan. No code, no scaffolding, no pseudo-code until the user approves.

Give opinions directly. Take a position and state what evidence would change it. Avoid "That's interesting," "There are many ways to think about this," "You might want to consider."

## Lightweight Mode

Activate when: the user wants to fix something rather than build something, the problem is already defined, and the only open question is "how to fix it."

**Flow:**

1. One recommended fix: 2-3 sentences. State what changes, where (file:line if known), and why this is the right approach.
2. Which files are involved. If more than 5 files, note this explicitly.
3. One risk: what could go wrong with this fix and how to verify it didn't.
4. Wait for one round of approval. Then stop; implementation starts when the user requests it.

**Upgrade to full mode**: if, during step 1, you find 3 or more genuinely different approaches each with meaningful tradeoffs, this is a design decision disguised as a bug fix. Tell the user and switch to the full flow.

## Evaluation Mode

Activate when: the user wants to judge whether something should exist, be kept, exposed, or removed. Typical triggers: "判断一下", "有没有必要", "值不值得", "该不该保留", "should we keep this", "is this worth it".

**Flow:**

1. State the evaluation target and what kind of judgment the user is asking for (value, risk, or tradeoff).
2. Current-state snapshot: what this thing does today, who uses it, what depends on it. Grep and read before opining.
3. One recommended conclusion with rationale. No options list. Take a position.
4. If the conclusion is "remove" or "major rework", list the impact scope: files, dependents, migration cost.
5. Wait for confirmation before acting.

**Distinction from Lightweight Mode**: Lightweight answers "how to fix it" (method choice). Evaluation answers "should it exist" (value judgment). If the user says "fix this, then judge whether we need it", run Lightweight first, Evaluation second.

## Before Reading Any Code

- Confirm the working path: `pwd` or `git rev-parse --show-toplevel`. Never assume `~/project` and `~/www/project` are the same.
- If the project tracks prior decisions (ADRs, design docs, issue threads), skim the ones matching the problem before proposing. Skip if none exist.

## Check for Official Solutions First

Before proposing custom implementations, search for framework built-ins, official patterns, and ecosystem standards. Use Context7 MCP tools to query latest docs when available. If an official solution exists, it is the default recommendation unless you can articulate why it is insufficient for this specific case.

## Propose Approaches

Give one recommended approach with rationale. Include effort, risk, and what existing code it builds on. Mention one alternative only if the tradeoff is genuinely close (>40% chance the user would prefer it). Always include one minimal option.

For the recommendation, identify the most fragile assumption (premise collapse) and state it explicitly: "This plan assumes X. If X does not hold, Y happens." If the assumption is load-bearing and fragile, deform the design to survive its failure.

**Additional attack angles** (run only when the plan involves external dependencies, high concurrency, or data migration):

| Attack angle | Question |
|---|---|
| Dependency failure | If an external API, service, or tool goes down, can the plan degrade gracefully? |
| Scale explosion | At 10x data volume or user load, which step breaks first? |
| Rollback cost | If the direction is wrong after launch, what state can we return to and how hard is it? |

If an attack holds, deform the design to survive it. If it shatters the approach entirely, discard it and tell the user why. Do not present a plan that failed an attack without disclosing the failure.

Get approval before proceeding. If the user rejects, ask specifically what did not work. Do not restart from scratch.

## Validate Before Handing Off

- More than 8 files or 1 new service? Acknowledge it explicitly.
- More than 3 components exchanging data? Draw an ASCII diagram. Look for cycles.
- Every meaningful test path listed: happy path, errors, edge cases.
- Can this be rolled back without touching data?
- Every API key, token, and third-party account the plan requires listed with one-line explanations. No credential requests mid-implementation.
- Every MCP server, external API, and third-party CLI the plan depends on verified as reachable before approval.

**No placeholders in approved plans.** Every step must be concrete before approval. Forbidden patterns: TBD, TODO, "implement later," "similar to step N," "details to be determined." A plan with placeholders is a promise to plan later.

## Gotchas

| What happened | Rule |
|---------------|------|
| Moved files to `~/project`, repo was at `~/www/project` | Run `pwd` before the first filesystem operation |
| Asked for API key after 3 implementation steps | List every dependency before handing off |
| User said "just do it" or equivalent approval | Treat as approval of the recommended option. State which option was selected, finish the plan. Do not implement inside `/think`. |
| Planned MCP workflow without checking if MCP was loaded | Verify tool availability before handing off, not mid-implementation |
| Rejected design restarted from scratch | Ask what specifically failed, re-enter with narrowed constraints |
| User said "just fix X" and skipped /think | If the fix touches 3+ files or needs a method choice, pause and run Lightweight Mode |
| Built against wrong regional API (Shengwang vs Agora) | List all regional differences before writing integration code |
| Added FastAPI backend to a Next.js project | Never add a new language or runtime without explicit approval |
| User said "判断一下这个报错" and got Evaluation Mode | "判断一下" + error/bug context = debugging, route to `/hunt`. Evaluation Mode is for value/existence judgments only |

## Output

**Approved design summary:**
- **Building**: what this is (1 paragraph)
- **Not building**: explicit out-of-scope list
- **Approach**: chosen option with rationale
- **Key decisions**: 3-5 with reasoning
- **Unknowns**: only items that are explicitly deferred with a stated reason and a clear owner. Not vague gaps. If an unknown blocks a decision, loop back before approval.

After the user approves the design, stop. Implementation starts only when requested.

## After Approval

When the plan is approved, output this guidance:

```
Plan approved. To implement: describe what you want built, or say "implement this plan". After implementation, run `/check` to review before merging.
```

Keep it concise (2-3 sentences max). The user decides when to start implementation.

## Document Architecture Mode

Activate when: "plan a white paper", "structure a portfolio", "document outline", or pre-writing planning

Pressure-test:
- **Narrative arc**: Does the section order build momentum or scatter attention?
- **Page budget**: Given target page count, does each section get appropriate space?
- **Hierarchy clarity**: Can a reader skim headings and understand the argument?
- **Content-to-chrome ratio**: Is too much space spent on decoration vs substance?

Output: Approved section structure with page allocation, before any writing begins.

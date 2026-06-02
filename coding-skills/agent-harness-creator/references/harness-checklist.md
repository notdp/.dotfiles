# Harness Checklist

Use this checklist to turn observed coding-agent or human friction into a scoped harness decision.

## Evidence Intake

| Signal | Evidence to collect | Common false positive |
|---|---|---|
| Repeated agent confusion | user corrections, repeated missing context, inconsistent edits | one-off unclear prompt |
| Diff drift | unrelated file changes, behavior + refactor mixed, style churn | intentional broad refactor with spec |
| Validation gap | no runnable tests, no acceptance verifier, manual-only checks | task genuinely has no automated surface |
| History hotspot | churn, co-change, bug-fix touch frequency | generated files, docs, config, or healthy integration points |
| Long wait | slow build/test/dev server, repeated manual setup | rare full-suite check |
| Parallel friction | port conflicts, worktree setup pain, stash/checkout churn | project rarely runs parallel streams |
| Unsafe side effect | DB apply, deployment, secrets, runtime config | read-only diagnosis |
| Context bloat | long global rules, stale docs, conflicting skills | specialized long reference loaded only on demand |

## Loop Framing

Use this before selecting a harness type:

| Lens | Diagnostic question | Harness implication | Source influence |
|---|---|---|---|
| Why loop | Is the failure caused by unclear goals, priorities, product judgment, or architecture intent? | Keep a human approval / planning point; do not fully automate. | Humans and Agents in Software Engineering Loops |
| How loop | Is the failure caused by execution, missing context, slow feedback, or repeatable mistakes? | Add guide, sensor, test, script, hook, or CI path. | Humans and Agents in Software Engineering Loops; Harness Engineering |
| Outside loop | Can the human safely delegate and inspect only outcomes? | Require strong feedback sensors and rollback. | Humans and Agents in Software Engineering Loops |
| In loop | Does the human need to approve each risky step? | Add approval gate or AskUser decision point. | Humans and Agents in Software Engineering Loops; Pi discussion |
| On loop | Does the human supervise periodic progress rather than every step? | Add status, checkpoints, summaries, and stop conditions. | Humans and Agents in Software Engineering Loops; Neil Kakkar |

## Theory-of-Constraints Pass

Before adding a harness, name the current bottleneck:

| Bottleneck | Evidence | Good harness | Bad harness |
|---|---|---|---|
| Formatting / handoff | repeated PR description or release note toil | command or ship checklist | global prompt reminding agent to write better |
| Waiting | slow rebuild/test/preview blocks loop | faster script, scoped test, preview path | parallel agents before feedback is fast |
| Verifying | agent claims done without observable proof | acceptance verifier, screenshot, smoke script | more prose in final answer |
| Parallel work | worktrees, ports, env files collide | worktree helper, port allocator | daemon runner without conflict evidence |
| Context retrieval | same context is repeatedly supplied by humans | feedforward guide or local reference | always-on long global rule |

Only the top observed bottleneck gets `implement now` by default. Secondary ideas should usually be `observe`.

## Harness Types

| Harness | Use when | Preferred asset | Reject when | Source influence |
|---|---|---|---|---|
| Feedforward guide | agents repeatedly miss stable context or convention | skill, command, local reference | context is one-off or unstable | Harness Engineering |
| Feedback sensor | issue is mechanically detectable | script, linter, CI, hook | issue requires subjective judgment | Harness Engineering; Maintainability sensors |
| Architectural constraint | agents repeatedly cross layers or create parallel systems | tests, dependency rules, architecture checks | team has not agreed on boundary | Harness Engineering; Maintainability sensors |
| Verification harness | completion cannot be proven repeatably | test script, acceptance checklist, guard-verify route | no observable user goal exists | Neil Kakkar; Harness Engineering |
| Operational harness | long task, dry-run/apply, migration, backfill, data repair | dev-operational-task contract, script flags | no data or external side effect | Harness Engineering |
| GitOps harness | remote/DB/secrets/runtime state can drift | guard-gitops route, declarative SSOT | only local code changes | Harness Engineering |
| Parallel harness | multiple agents or humans block each other | worktree helper, port allocator, command | no repeated parallel workflow | Neil Kakkar; Claude Code Unpacked |
| Review harness | same review finding repeats | guard-review checklist, diff scanner | reviewer preference is not a correctness issue | Maintainability sensors |
| Garbage collection | old rules/scripts/skills conflict or are unused | remove, merge, or demote references | asset is still used and low-cost | Harness Engineering |

## Necessity Gate

Recommend `implement now` or `plan first` only if at least one is true:

- A bug, failed validation, rollback, or review finding already happened.
- The same manual step has been repeated enough to be a workflow bottleneck.
- The same missing context has been supplied repeatedly by humans.
- The risk is high enough that one failure is sufficient evidence: secrets, production, DB, deployment, destructive commands.
- A deterministic check can prevent a known class of mistakes with low false positives.
- Existing harness exists but is not discoverable or not wired into the right workflow.

## Anti-harness Gate

Reject or observe when:

- The candidate is justified by novelty rather than friction.
- It duplicates an existing skill, command, script, hook, or CI check.
- It adds global context for a rare task.
- It automates a decision that requires human judgment.
- It cannot be validated except by “seems better”.
- It introduces remote, DB, secret, deployment, or runtime side effects without GitOps scope.
- It turns a simple workflow into a platform.

## Decision Rubric

| Criterion | High | Medium | Low |
|---|---|---|---|
| Evidence strength | observed repeated failure or high-risk incident | plausible friction with partial evidence | no concrete evidence |
| Leverage | prevents a class of issues | improves one workflow | cosmetic or speculative |
| Validation | deterministic or scripted | structured manual check | subjective |
| Context cost | loaded only when relevant | short global reminder | long always-on rule |
| Maintenance cost | small, local, owned | moderate updates needed | external dependency or high upkeep |
| Reversibility | delete file or remove route | migration needed | hard to unwind |

## Output Guidance

### Good recommendation

```markdown
| Candidate | Type | Source influence | Necessity | Existing assets | Decision | Next route | Validation | Rollback |
|---|---|---|---|---|---|---|---|
| Add diff residue scan to pre-commit flow | Feedback sensor | Maintainability sensors | 3 recent reviews caught debug logs | `scripts/scan_diff_residue.py` exists | route existing | guard-diff-scan / guard-ship | scanner reports 0 hits | remove route |
```

### Bad recommendation

```markdown
| Candidate | Type | Source influence | Necessity | Existing assets | Decision |
|---|---|---|---|---|---|
| Add multi-agent daemon | Parallel harness | Claude Code Unpacked | useful for agents | none | implement now |
```

Why bad: no observed bottleneck, no validation, no rollback, and likely adds runtime complexity.

## Garbage Collection Checks

Harness debt appears as:

- Multiple skills giving conflicting instructions.
- `AGENTS.md` growing with task-specific rules.
- Scripts that are not referenced by skills, commands, CI, or docs.
- Hooks that fail often and are bypassed.
- Commands that duplicate newer skills.
- References that are treated as runtime rules without source status.

Possible decisions:

- `merge`: combine overlapping rules into one canonical skill.
- `demote`: move rarely used runtime instructions to docs/references.
- `delete`: remove stale assets with validation.
- `route`: keep asset but make entry point discoverable.
- `observe`: leave as-is until evidence is stronger.

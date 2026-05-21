---
name: agent-harness-creator
description: 当目标项目需要审计 coding-agent / human 开发摩擦、验证护栏或 harness 资产时使用；基于代码、diff、历史和现有配置输出证据驱动的 harness 改进裁决（与 agent-health 的区别是本 skill 面向目标项目工作流摩擦，不只审计 agent 配置栈）。
argument-hint: <项目路径|diff|history|模块路径|留空=当前仓库>
---

# Agent Harness Creator

Design harness only when there is evidence of real friction. This skill audits a target project and proposes the smallest useful guardrail, sensor, workflow, or cleanup path for coding agents and humans.

It does not directly implement the harness. Large changes still go through `/think-plan`; behavior changes go through `/dev-tdd`; delivery goes through `/guard-verify` and `/guard-check`.

## 1. Scope

Use for:

- Auditing a project for missing coding-agent guardrails.
- Finding repeated friction from current diff, code structure, git history, review comments, failed validation, or manual workflow steps.
- Deciding whether to create a skill, command, script, hook, CI check, documentation reference, or no new harness.
- Cleaning up stale or conflicting harness assets.

Do not use for:

- Adding harness because it sounds advanced.
- Replacing existing specialist skills.
- Remote writes, deployment, DB writes, secret changes, runtime state changes, or production apply commands.
- Pure code review without a harness decision; use `/guard-review`.

## 2. Evidence Intake

Collect only the evidence needed for the selected scope:

| Source | What to inspect | Purpose |
|---|---|---|
| Current diff | changed files, drift, validation gaps, debug residue | detect immediate friction |
| Git history | churn, co-change, bug-fix hotspots | detect repeated friction |
| Code structure | boundaries, conventions, testability | detect agent-unfriendly surfaces |
| Scripts / CI | discoverability, coverage, failure mode | detect missing sensors |
| Agent assets | `AGENTS.md`, skills, commands, hooks, MCP | detect config and routing gaps |
| User notes | incidents, review pain, repeated manual steps | include human friction evidence |

Git history and code structure are evidence, not conclusions. Confirm hotspots by reading relevant files or diff context before proposing harness.

## 3. Loop and Constraint Framing

Before proposing a harness, classify what loop it changes:

| Question | Use it to decide |
|---|---|
| Is this a Why-loop problem? | Keep or add human judgment, planning, approval, or product/architecture decision points. |
| Is this a How-loop problem? | Add execution guidance, deterministic checks, tests, scripts, or workflow automation. |
| Should the human be outside, in, or on the loop? | Decide whether the harness should require approval, keep humans reviewing periodically, or allow delegation with sensors. |

Then apply a theory-of-constraints pass:

1. Name the current largest observed bottleneck.
2. Tie it to evidence from diff, history, validation, or user notes.
3. Propose only the smallest harness that relieves that bottleneck.
4. Leave lower-priority harness ideas in `observe` unless they block the next loop.

## 4. Compose Existing Skills

Prefer routing to existing skills instead of copying their checklists:

| Need | Route |
|---|---|
| Agent config stack health | `/agent-health` |
| Modifiability / architecture friction | `/think-quality` |
| Current diff correctness and drift | `/guard-review` |
| History hotspots | `/dev-refactor history` method |
| Verification gap | `/guard-verify` |
| Operational / dry-run / apply / long task risk | `/dev-operational-task` |
| Remote / DB / secret / runtime side effect | `/guard-gitops` |
| Stop / continue decision | `/guard-close` |

## 5. Necessity Gate

A harness candidate needs at least one concrete signal:

- Same failure or review comment appears repeatedly.
- Current diff shows validation gaps, drift, or unsafe manual steps.
- Git history shows high churn, co-change, or bug-fix hotspots that map to a real smell.
- Agent repeatedly needs the same missing context or convention.
- A manual workflow is repeated and error-prone.
- Risk touches security, data, remote systems, production, or irreversible operations.

If no signal is found, output `observe` or `reject`. Do not build harness for its own sake.

## 6. Harness Decision Types

| Decision | Meaning |
|---|---|
| `implement now` | Small, local, evidence-backed harness with clear validation. |
| `plan first` | Larger or cross-cutting harness requiring a spec. |
| `route existing` | Existing skill/script/CI already fits; improve discoverability or routing only. |
| `observe` | Signal exists but evidence is too weak or too new. |
| `reject` | No real friction, or cost exceeds benefit. |
| `need decision` | Requires user/project owner to choose a boundary, risk appetite, or convention. |

## 7. Output Contract

```markdown
## Harness Audit

### Scope
- Project:
- Mode: current / diff / history / module
- Evidence sources:
- Loop framing: Why / How; human outside / in / on loop
- Current constraint:

### Friction Ledger
| Signal | Evidence | Source | Frequency | Impact | Confidence |
|---|---|---|---|---|---|

### Harness Decision Matrix
| Candidate | Type | Source influence | Necessity | Existing assets | Decision | Next route | Validation | Rollback |
|---|---|---|---|---|---|---|---|

### Rejected / Observed
| Candidate | Reason | Revisit trigger |
|---|---|---|

### Assessment
- Highest leverage harness:
- Do not build:
- Need user decision:
```

## 8. Stop / Escalation

- If the scope is unclear, ask for the target project, diff, history window, or module path.
- If evidence is missing, stop at `observe` or `reject`.
- If a candidate changes remote, DB, secret, deployment, runtime, or third-party state, route to `/guard-gitops`.
- If a candidate changes auth, data handling, network boundary, permissions, or supply chain, route to `/guard-secure`.
- If a candidate changes behavior, require `/dev-tdd`.
- If the harness would add global context to every task, require explicit benefit and a rollback path.

## Gotchas

- More harness can make agents worse by increasing context cost and rule conflicts.
- Prompt rules are the weakest harness when deterministic sensors or tests are possible.
- Git churn alone is not proof; high-churn files can be healthy integration points.
- Removing useful human judgment is a regression, not progress.
- Stale skills, hooks, and docs are harness debt and may need garbage collection.

## References

- `references/harness-checklist.md`
- `docs/harness-refs/`

## Related Skills

- Config stack audit -> `/agent-health`
- Structure quality -> `/think-quality`
- Diff review -> `/guard-review`
- Validation evidence -> `/guard-verify`
- Operational safety -> `/dev-operational-task`
- Remote / DB / secret / runtime side effects -> `/guard-gitops`

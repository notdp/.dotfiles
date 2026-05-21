# Harness Refs

This directory records harness engineering sources that have been read or queued for absorption.

It is research material, not runtime instruction. Runtime behavior should be implemented through `skills/`, `commands/`, `scripts/`, hooks, or CI only after a specific friction point has evidence.

## Source Status

| Status | Meaning |
|---|---|
| `fetched` | Page content was fetched and reviewed in this repo context. |
| `search-summary` | Search result metadata was reviewed, but full page content was not fetched. |
| `user-summary` | The source is represented by user-provided notes and must not be treated as independently verified. |
| `mixed` | More than one status applies; notes must say which claim comes from which source. |

## Record Format

Use `sources.md` for the source ledger:

```markdown
| Source | Status | Core idea | Harness pattern | Caution |
|---|---|---|---|---|
```

## Absorption Principles

- Start from observed friction, not from a desire to add harness.
- Prefer existing skills, commands, scripts, hooks, and CI before adding a new runtime path.
- Keep long background material here; runtime skills should link to concise checklists.
- Treat external agent architecture posts as vocabulary and inspiration, not as implementation authority.
- Preserve useful human judgment and review friction where automation would hide risk.

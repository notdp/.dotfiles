# agentsview Memory/Vault Emitted Schema

This document fixes the emitted-side contract for the dotfiles memory and dev-long-run vault data that agentsview may consume later. This repository owns the emitted files and schema. It does not implement the agentsview collector.

## Downstream Out Of Scope

This phase does not implement the agentsview collector, database tables, API routes, or UI ingestion. Those belong to the downstream agentsview repository. This phase also does not move dev-long-run state files into a new physical `machine/` directory.

## Vault Discovery

Collectors should discover dev-long-run workspaces by scanning configured dotfiles roots for `.long-loop/<run-slug>/` directories. The `.long-loop` directory is process state and may be gitignored. A collector must treat missing optional files as incomplete run state, not as a fatal parse error for the whole workspace.

The emitted files are:

- `<workspace>/state.json`
- `<workspace>/metrics.jsonl`
- `<workspace>/acceptance.json`
- `<workspace>/phases/<phase-dir>/verify.json`
- `<workspace>/phases/<phase-dir>/stuck.json`

## Logical Machine Layer

The term `machine/` in the higher-level plan is a logical layer: machine-readable files inside the workspace and phase directories. Current dev-long-run code emits these files at the existing root and phase paths above. This contract does not relocate them.

## Versioning

New `metrics.jsonl` files start with a schema header:

```json
{"_schema":"dotfiles.long_loop.metrics","_version":1}
```

Legacy `metrics.jsonl` files without this header remain valid for ingestion. Collectors should mark them as `legacy metrics accepted` and parse event rows using the same event schema. Future incompatible changes must bump `_version` and keep old readers able to reject unknown versions with a file-specific error.

Schema ownership: `coding-skills/dev-long-run/lr.py` is the emitter SSOT, `scripts/validate_agentsview_emitted_schema.py` is the enforcement SSOT, and this document is the downstream handoff contract. Any `_schema` or `_version` change must update all three surfaces together.

## metrics.jsonl

`metrics.jsonl` is append-only JSONL. Each non-header record must contain `ts` as a UTC timestamp string and `event` as one of the supported event names.

Supported event records:

- `verify`: required fields are `ts`, `event`, `phase`, `ok`, `exit`, `fail_streak`, and `fingerprint`; `fingerprint` may be null.
- `acceptance`: required fields are `ts`, `event`, `ok`, and `exit`.
- `complete_phase`: required fields are `ts`, `event`, and `phase`.
- `complete_run`: required fields are `ts` and `event`.

Collectors must ignore header rows for run statistics. Unknown event names are schema errors for this emitted contract even though older stats code may ignore unknown records.

## state.json

`state.json` is a single JSON object. Required fields:

- `state`: string
- `phase`: string or integer
- `role_in_flight`: string
- `worktree_path`: string
- `branch`: string
- `goal`: string
- `repo_root`: string
- `slug`: string
- `dirty_main_at_start`: boolean
- `in_place`: boolean

## verify.json

Each phase may emit `phases/<phase-dir>/verify.json`. Required fields:

- `ok`: boolean
- `exit`: integer
- `output_tail`: string

## acceptance.json

The workspace may emit `acceptance.json` with the same shape as `verify.json`:

- `ok`: boolean
- `exit`: integer
- `output_tail`: string

## stuck.json

Each phase may emit `phases/<phase-dir>/stuck.json`. Required fields:

- `consecutive_fail`: integer
- `fingerprint`: string or null

## Memory Discovery

Collectors should read tracked memory notes from `memory/user/*.md` and may use `memory/user/INDEX.md` as an index/hint. `INDEX.md` is mechanically generated from note frontmatter and should not be treated as the only source of truth.

## Memory Frontmatter Facets

The agentsview facets are frontmatter fields already accepted by `scripts/build_memory_index.py`:

- `problem_type`
- `type`
- `origin_session`
- `status`

The current required frontmatter fields are `title`, `date`, and `problem_type`. Optional inactive statuses such as `superseded`, `archived`, and `stale` are valid emitted values, not ingestion errors.

## Collector Handoff

An agentsview collector should:

- Discover `.long-loop` workspaces and `memory/user` directories from explicit configuration first, then from the default dotfiles root.
- Parse JSON/JSONL/frontmatter using this schema and store source file paths for diagnostics.
- Treat file path plus event line number as the idempotency key for `metrics.jsonl` rows.
- Treat memory note relative path plus frontmatter values as the idempotency key for memory facets.
- Report malformed files with the offending path and line number where applicable.

## Idempotency

Vault metrics are append-only. Re-ingesting the same workspace should upsert the same line keys, not duplicate rows. Snapshot files such as `state.json`, `verify.json`, `acceptance.json`, and `stuck.json` should be replaced by source path.

## Failure Handling

Collectors should fail a malformed file independently and continue with other workspaces or notes when possible. Schema errors must include the file path. Missing optional files such as `acceptance.json` or absent phase `stuck.json` files are not errors.

# Operational Task Capsule

This prompt looks like long-running, batch, data-changing, migration, or complex CLI work. Load `/dev-operational-task` before implementation.

Check the contract before coding and before delivery:

- Efficiency: bounded concurrency, batch size, backpressure, rate limit.
- Resumability: cursor/checkpoint/state file/idempotency key; interrupted work can continue.
- Observability: phase, current/total, percentage, rate, ETA, heartbeat, recent success/failure samples.
- Robustness: retry/backoff, timeout, partial failure set, safe rerun behavior.
- CLI UX: safe defaults, presets or interactive wizard; each choice explains impact and prints the underlying copyable command.
- Dry-run data accuracy: planned counts, samples, diff/aggregation, invariants, failed examples.
- Apply safety: `--apply` needs explicit confirmation, rollback, and post-apply validation.
- Critical ops: for stop/reclaim/release/downsize/no longer needed/cut cost touching cost, cloud, prod, data, permission, or irreversible state, clarify goal before command.
- Reply with goal, acceptance criteria, retained assets, rollback, and validation. Separate runtime state from billing state. Use `/guard-gitops` only for declaration, drift, deploy, or repo SSOT.

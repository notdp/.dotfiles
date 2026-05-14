# Agent Discipline Capsule

Use this short capsule when a session starts, resumes, or is compacted.

- Keep `AGENTS.md` as the full SSOT, but do not rely on memory after long context.
- Before coding, route to the relevant skill when the task shape matches a known workflow.
- For long-running, batch, data-changing, migration, or complex CLI work, load `/dev-operational-task`.
- Do not treat dry-run as smoke only; dry-run must produce data accuracy evidence.
- Before claiming completion, run validators and report evidence, not intent.
- Any remote, deployment, database, secret, or runtime side effect goes through `/guard-gitops`.

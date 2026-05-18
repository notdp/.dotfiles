# Security / GitOps Capsule

This prompt touches auth, permissions, secrets, deployment, production, remote machines, databases, or external state.

- Load `/guard-secure` for auth/data/network/supply-chain risk.
- Load `/guard-gitops` before remote, deploy, DB, secret, runtime, third-party, push, or release side effects.
- Read-only diagnosis is allowed when scoped to observation and reported back.
- Remote writes, deploys, DB writes, push/release, or apply commands need explicit scope, rollback, and validation evidence before proceeding.
- Broad destructive cleanup, force-push, destroy, delete, or schema-destructive DB commands remain blocked.
- Before delivery, report what changed, where it is declared in git, and how rollback works.

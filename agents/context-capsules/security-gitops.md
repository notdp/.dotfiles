# Security / GitOps Capsule

This prompt touches auth, permissions, secrets, deploys, production, remote machines, databases, or external state.

- Load `/guard-secure` for auth/data/network/supply-chain risk.
- Load `/guard-gitops` before remote, deploy, DB, secret, runtime, third-party, push, or release side effects.
- Read-only diagnosis is allowed when scoped to observation and reported back.
- Remote writes, deploys, DB writes, push/release, or apply need explicit scope, rollback, and validation evidence.
- External security testing, including scans, exploit/C2/phishing, credential access, lateral movement, brute force, or auth bypass, needs explicit authorization scope, allowed actions, stop conditions, and validation evidence.
- Broad destructive cleanup, force-push, destroy, delete, or schema-destructive DB commands remain blocked.
- Before delivery, report what changed, where it is declared in git, and how rollback works.

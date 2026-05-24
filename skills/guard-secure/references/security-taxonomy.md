# Security taxonomy reference

Use this as a lightweight checklist when `/guard-secure` needs a wider lens than STRIDE alone. It is not an ATT&CK, NIST, or OWASP coverage source of truth.

## Review domains

| Domain | Look for | Route / evidence |
|---|---|---|
| App / API Security | Injection, XSS, SSRF, IDOR, CSRF, deserialization, mass assignment, schema abuse | Data flow from input to sink, `file:line`, exploitability evidence |
| Auth / IAM | Authentication, authorization, session handling, role checks, token scope, privileged actions | Actor, permission boundary, denied/allowed cases |
| Data / Privacy | PII, secrets, logs, over-broad responses, retention, encryption, backup exposure | Data class, storage/output path, redaction/encryption evidence |
| Cloud / IaC / Container | IAM policies, public exposure, network boundaries, runtime privileges, image provenance | Provider/config path, effective permission or exposure evidence |
| Supply Chain / CI/CD | New dependencies, lockfiles, build scripts, artifact signing, workflow permissions | Manifest/lockfile diff, CI permission scope, scanner output |
| Agent / Prompt / Tooling | Hooks, capsules, model context, MCP/tools, prompt injection, tool permissions | Context surface, caller path, allowed/blocked tool behavior |
| IR / DFIR / Observability | Incident handling, audit logs, detection gaps, retention, alert routing | Log/event source, timeline, detection or response evidence |
| Dual-use / Offensive Boundary | External scans, exploit validation, C2, phishing simulation, credential access, lateral movement, brute force, auth bypass | Explicit authorization scope, allowed actions, stop conditions, validation evidence |

## Dual-use boundary contract

- Read-only code review and local static analysis may continue with evidence-based findings.
- External target testing or attack simulation needs explicit scope before execution.
- If authorization is missing, report the missing scope and offer a read-only review path.

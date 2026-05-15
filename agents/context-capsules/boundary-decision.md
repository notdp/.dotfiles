# Boundary-Decision Capsule

This task looks like it may change a service, wrapper, adapter, schema, metric, data source, production path, or agent context surface. Boundary decisions multiply in these tasks.

Before acting, surface facts or ask the user when you might change:

1. spec-external input validation, rejection, or 4xx/5xx behavior
2. skip, truncate, fallback, silent catch, retry, backoff, or sleep behavior
3. default values, limits, cost caps, concurrency caps, or sampling boundaries
4. shared code paths used by multiple callers
5. API request/response schema, envelope, or field semantics
6. canonical/raw data source, snapshot source, limit scope, or platform coverage
7. metric name, label, route, StatsStore bucket, or observability ownership
8. production writes, database changes, deployments, or external side effects
9. hooks, prompts, capsules, CLAUDE.md, AGENTS.md, or anything entering model context

Use this manifest when a boundary changed or was considered:

```markdown
Boundary decisions:
- <type>: <description> (file:line, evidence: <why allowed or user-approved>)
```

Allowed `<type>` values:

```text
input-validation / rejection / default-value / limit / fallback /
behavior-branch / shared-path / observability-routing /
schema-contract / data-source / sampling-boundary /
operational-side-effect / context-surface
```

For wrapper or adapter code, write contract cases for accept/reject/schema behavior before implementation. For shared functions, list callers before changing behavior. For metrics, verify with a synthetic call that data lands on the intended route or label before opening real traffic.

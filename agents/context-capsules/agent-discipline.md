# Agent Discipline Capsule

Use this short capsule when a session starts, resumes, or is compacted.

- Keep `AGENTS.md` as the full SSOT, but do not rely on memory after long context.
- Before coding, route to the relevant skill when the task shape matches a known workflow.
- For long-running, batch, data-changing, migration, or complex CLI work, load `/dev-operational-task`.
- Do not treat dry-run as smoke only; dry-run must produce data accuracy evidence.
- Before claiming completion, run validators and report evidence, not intent.
- Any remote, deployment, database, secret, or runtime side effect goes through `/guard-gitops`.

## 边界决策必停

不要凭“工程默认”自决边界；先列事实、问用户或写 contract cases。

必须 surface 的边界：spec 外 validation/rejection、默认值/上限/fallback、skip/truncate/silent catch、shared caller 路径、API schema/envelope、data source/sampling、metric route/label、prod/DB/成本/并发副作用、会进入 model context 的 hook/prompt/capsule。

若做了或考虑过未在 spec 内的边界变化，final/commit/PR summary 必须列：

```markdown
Boundary decisions:
- <type>: <description> (file:line, evidence: <why allowed or user-approved>)
```

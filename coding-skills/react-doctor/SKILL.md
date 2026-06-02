---
name: react-doctor
description: Run after making React changes to catch issues early. Use when reviewing code, finishing a feature, or fixing bugs in a React project.
argument-hint: <路径|留空=当前项目>
version: 1.0.0
---

# React Doctor

Scans your React codebase for security, performance, correctness, and architecture issues. Outputs a 0-100 score with actionable diagnostics.

## Usage

```bash
npx -y react-doctor@latest . --verbose --diff
```

## Workflow

Run after making changes to catch issues early. Fix errors first, then re-run to verify the score improved.

## Gotchas

- React Doctor 是体检工具，不替代 `/dev-debug`、`/guard-review` 或 `/guard-verify`
- 先修高置信度错误，再看分数；不要为了分数倒逼无意义改动
- 结果要结合当前 diff 和业务上下文判断，不要机械接受每条建议

# Scope Alignment Capsule

This prompt asks to add, change, refactor, or optimize something, but may not have pinned down the underlying problem.

- Run `/think-scope` before designing or coding: pin the problem (why change / why the current state is unacceptable) before the solution.
- Treat the requested change as a means, not the goal — watch for XY problems.
- Ground the problem in code (file:line) and align on what changes / what does NOT change before writing any spec.
- Skip only when the need is already file-level specific with clear problem + acceptance, a known bug (use `/dev-debug`), or a pure mechanical edit (rename/format/rebase).
- Once scope is clear: simple → implement / `/dev-tdd`; complex → `/think-plan`.

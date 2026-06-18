# Planning Task Capsule

This prompt asks for approach, architecture, options, phase plan, or a large change.

- First confirm scope is aligned (what problem / what changes / what does NOT). If not, run `/think-scope` before planning — don't let plan mode converge on a solution before shared understanding.
- Then `/think-plan`, staying in spec mode until the plan is approved.
- Scan the approach for fragile points (unknown external deps, unproven tech/API, algorithm/data edges) and spike each into fact before implementing — see `/think-plan` Premise Collapse.
- Use `/think-research` first when technical facts or options are uncertain.
- Separate goals, non-goals, constraints, risks, validation, and rollback.
- If there are equally strong options, ask the user to choose before finalizing.
- Do not start implementation from an unapproved design.

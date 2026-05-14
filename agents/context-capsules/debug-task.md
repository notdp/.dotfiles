# Debug Task Capsule

This prompt looks like a bug, error, flaky behavior, failing test, traceback, or incident.

- Load `/dev-debug` before changing code.
- First build a feedback loop: failing test, CLI fixture, HTTP check, browser check, or trace replay.
- Do not guess and patch. State hypotheses and verify one at a time.
- After two failed hypotheses, switch to `/think-unstuck` with a handoff.
- Final claim needs original repro evidence plus regression validation.

# Debug Task Capsule

This prompt looks like a bug, error, flaky behavior, failing test, traceback, or incident.

- Load `/dev-debug` before changing code.
- Observability first (排错纪律#3): before listing hypotheses, add the cheapest probe (log/print/breakpoint) to make internal state visible, reproduce once, then narrow — don't guess-and-patch.
- Build a feedback loop: failing test, CLI fixture, HTTP check, browser check, or trace replay.
- State hypotheses and verify one at a time, each from real probe evidence.
- After two failed hypotheses, switch to `/think-unstuck` with a handoff (carry evidence from real probes, not guesses).
- Final claim needs original repro evidence plus regression validation.

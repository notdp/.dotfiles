---
name: hunt
description: Invoke when debugging any error, crash, unexpected behavior, or failing test. Finds root cause before applying any fix. Not for code review or new features.
metadata:
  version: "3.9.0"
---

# Hunt: Diagnose Before You Fix

Prefix your first line with 🥷 inline, not as its own paragraph.


A patch applied to a symptom creates a new bug somewhere else.

**Do not touch code until you can state the root cause in one sentence:**
> "I believe the root cause is [X] because [evidence]."

Name a specific file, function, line, or condition. "A state management issue" is not testable. "Stale cache in `useUser` at `src/hooks/user.ts:42` because the dependency array is missing `userId`" is testable. If you cannot be that specific, you do not have a hypothesis yet.

## Rationalization Watch

When these surface, stop and re-examine:

| What you're thinking | What it actually means | Rule |
|---|---|---|
| "I'll just try this one thing" | No hypothesis, random-walking | Stop. Write the hypothesis first. |
| "I'm confident it's X" | Confidence is not evidence | Run an instrument that proves it. |
| "Probably the same issue as before" | Treating a new symptom as a known pattern | Re-read the execution path from scratch. |
| "It works on my machine" | Environment difference IS the bug | Enumerate every env difference before dismissing. |
| "One more restart should fix it" | Avoiding the error message | Read the last error verbatim. Never restart more than twice without new evidence. |

## Progress Signals

When these appear, the diagnosis is moving in the right direction:

| What you're thinking | What it means | Next step |
|---|---|---|
| "This log line matches the hypothesis" | Positive evidence found | Find one more independent piece of evidence to cross-validate |
| "I can predict what the next error will be" | Mental model is forming | Run the prediction; if it matches, the model is correct |
| "Root cause is in A but symptoms appear in B" | Propagation path understood | Trace the call chain from A to B and confirm each link |
| "I can write a test that would fail on the old code" | Hypothesis is specific and testable | Write the test before applying the fix |

Do not claim progress without observable evidence matching at least one of these signals.

## Hard Rules

- **Same symptom after a fix is a hard stop; so is "let me just try this."** Both mean the hypothesis is unfinished. Re-read the execution path from scratch before touching code again.
- **After three failed hypotheses, stop.** Use the Handoff format below to surface what was checked, what was ruled out, and what is unknown. Ask how to proceed.
- **Verify before claiming.** Never state versions, function names, or file locations from memory. Run `sw_vers` / `node --version` / grep first. No results = re-examine the path.
- **External tool failure: diagnose before switching.** When an MCP tool or API fails, determine why first (server running? API key valid? Config correct?) before trying an alternative.
- **Pay attention to deflection.** When someone says "that part doesn't matter," treat it as a signal. The area someone avoids examining is often where the problem lives.
- **Visual/rendering bugs: static analysis first.** Trace paint layers, stacking contexts, and layer order in DevTools before adding console.log or visual debug overlays. Logs cannot capture what the compositor does. Only add instrumentation after static analysis fails.
- **Fix the cause, not the symptom.** If the fix touches more than 5 files, pause and confirm scope with the user.

## Confirm or Discard

Add one targeted instrument: a log line, a failing assertion, or the smallest test that would fail if the hypothesis is correct. Run it. If the evidence contradicts the hypothesis, discard it completely and re-orient with what was just learned. Do not preserve a hypothesis the evidence disproves.

## Gotchas

| What happened | Rule |
|---------------|------|
| Patched client pane instead of local pane | Trace the execution path backward before touching any file |
| MCP not loading, switched tools instead of diagnosing | Check server status, API key, config before switching methods |
| Orchestrator said RUNNING but TTS vendor was misconfigured | In multi-stage pipelines, test each stage in isolation |
| Race condition diagnosed as a stale-state bug | For timing-sensitive issues, inspect event timestamps and ordering before state |
| Reproduced locally but failed in CI | Align the environment first (runtime version, env vars, timezone), then chase the code |
| Stack trace points deep into a library | Walk back 3 frames into your own code; the bug is almost always there, not in the dependency |

## Outcome

### Success Format

```
Root cause:  [what was wrong, file:line]
Fix:         [what changed, file:line]
Confirmed:   [evidence or test that proves the fix]
Tests:       [pass/fail count, regression test location]
```

Status: **resolved**, **resolved with caveats** (state them), or **blocked** (state what is unknown).

### Handoff Format (after 3 failed hypotheses)

```
Symptom:
[Original error description, one sentence]

Hypotheses Tested:
1. [Hypothesis 1] → [Test method] → [Result: ruled out because...]
2. [Hypothesis 2] → [Test method] → [Result: ruled out because...]
3. [Hypothesis 3] → [Test method] → [Result: ruled out because...]

Evidence Collected:
- [Log snippets / stack traces / file content]
- [Reproduction steps]
- [Environment info: versions, config, runtime]

Ruled Out:
- [Root causes that have been eliminated]

Unknowns:
- [What is still unclear]
- [What information is missing]

Suggested Next Steps:
1. [Next investigation direction]
2. [External tools or permissions that may be needed]
3. [Additional context the user should provide]
```

Status: **blocked**

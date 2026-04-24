---
name: hunt
description: "Finds root cause of errors, crashes, unexpected behavior, and failing tests before applying any fix. Not for code review or new features."
when_to_use: "排查, 查查, 报错, 崩溃, 不工作, 不对, 跑不通, debug, why broken, not working, what's wrong, fix error, stack trace"
metadata:
  version: "3.14.0"
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

## Bisect Mode

Activate when the symptom is "used to work, now broken" or "broke after an update". Random-walking forward from the current state wastes context and produces random fixes.

**Flow:**

1. Find `last-known-good`: use the most recent tag where the behavior was correct (`git tag --sort=-version:refname | head -5`). Do not use a date or a raw SHA as the anchor.
2. Define a pass/fail test command before starting. The command must be runnable non-interactively and produce an unambiguous exit code. Write it down once; reuse it at every step.
3. Run `git bisect start`, `git bisect bad` (current), `git bisect good <tag>`. Let bisect drive; do not jump ahead.
4. Context conservation: do not re-read large files at each step. Read once, note the key function or line, reference from notes. Bisect output is the state; keep it in the terminal, not in context.
5. When bisect names the culprit commit: read only that commit's diff, not surrounding history. Identify the specific line that introduced the regression.

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
Root cause:        [what was wrong, file:line]
Fix:               [what changed, file:line]
Confirmed:         [evidence or test that proves the fix]
Tests:             [pass/fail count, regression test location]
Regression guard:  [test file:line] or [none, reason]
```

Status: **resolved**, **resolved with caveats** (state them), or **blocked** (state what is unknown).

**Regression guard rule**: for any bug that recurred or was previously "fixed", the fix is not done until:
1. A regression test exists that fails on the unfixed code and passes on the fixed code.
2. The test lives in the project's test suite, not a temporary file.
3. The commit message states why the bug recurred and why this fix prevents it.

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

## Rendering Bug Mode

Activate when: "PDF looks wrong", "page break issue", "font not rendering", or broken PDF output

Diagnosis checklist:
- **WeasyPrint bugs**: `rgba()` causes double-rectangle bug (use solid hex), `page-break-inside: avoid` ignored (use explicit breaks)
- **Font loading**: Check @font-face paths, CORS headers, file format support
- **Page overflow**: Calculate content height vs page height, suggest line-height/padding reduction
- **Browser print CSS**: Confirm `@media print` rules, `@page` margins, orphan/widow control

Static analysis first (CSS review), then reproduce if needed.

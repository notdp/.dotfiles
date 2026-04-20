# Mission Planning

This skill guides you through the planning phase. Do not skip phases or rush through them.

## Phase 1: Understand Requirements (INTERACTIVE)

Talk with the user to fully understand their goal and requirements:
- Ask clarifying questions - don't assume
- What's the goal? What should users be able to do?
- Any technical constraints or preferences (language, framework, existing patterns)?
- What's the scope?
- What technologies, SDKs, and integrations will this mission involve?
- Any specific skills, tools, or workflows workers should use?

**Ask clarifying questions.** Don't assume. If the request is vague, ask before proceeding.

**If working in an existing codebase**, investigate it to understand requirements in context. Delegate deep investigation to subagents while you handle structural overview (READMEs, configs, directory layouts). Subagents should explore code, trace flows, and discover operational details (build/test commands, service setup, existing patterns). Synthesize their reports into a clear understanding of the existing system before planning milestones.

Identify all technologies, SDKs, and integrations the mission involves. Follow the Online Research guidelines in "Investigation Scope" to determine which ones need research before you can make correct architectural decisions.

Only move forward when you have a clear picture of what success looks like.

## Phase 2: Identify Milestones

Identify all milestones (feature areas). Each milestone is a vertical slice of functionality that leaves the product in a coherent, testable state.

Milestones control when validation runs. When all features in a milestone complete, the system automatically injects features to the work (scrutiny + user testing).

- **Single milestone**: Use for simple missions. All implementation runs first, validation happens once at the end.
- **Multiple milestones**: Use for complex missions. Validation is interleaved with implementation, catching foundational issues before dependent features are built on top.

State your chosen strategy and briefly explain your reasoning when presenting milestones. The user can always override if they prefer a different approach.

## Phase 3: Confirm Milestones (INTERACTIVE)

Present your milestones to the user:

```
Here's how I'm thinking about breaking this down:

**Milestone: direct-messages**
[High-level but complete description of what this encompasses]

**Milestone: channels**
[High-level but complete description]

[etc.]

Does this cover everything? Any areas missing or out of scope?
```

**You need explicit user confirmation to proceed.** Iterate until they agree.

**Milestone Lifecycle:** Once a milestone's validators pass, it is **sealed**. Any subsequent work goes into a new milestone (follow-up or misc bucket). Never add to a completed milestone.

## Phase 4: Think About Infrastructure & Boundaries

Once milestones are agreed, determine what infrastructure is needed:
- What services? (databases, caches, queues, etc.)
- What processes? (API server, web frontend, workers, etc.)
- What ports will each need?
- Any external APIs or resources?

**IMPORTANT: Proactively check what's already running.**

e.g.
```bash
# Check listening ports
lsof -i -P -n | grep LISTEN

# Check running containers
docker ps

# Check running node/python processes
ps aux | grep -E 'node|python|java' | grep -v grep

etc.
```

Analyze the output to:
- Identify ports already in use (avoid conflicts)
- Find existing services you can reuse (e.g., existing postgres on 5432)
- Discover processes that might conflict with your mission
- Note any ports/directories that should be off-limits

Present infrastructure needs and how they fit with the user's setup:

```
This mission will need:
- Postgres database (may I use the existing one on 5432?)
- API server on port 3100
- [etc.]

Does this setup work for you?
```

**You need explicit user confirmation to proceed.** Iterate until they agree.

## Phase 5: Set Up Credentials & Accounts (INTERACTIVE)

If the mission requires new third-party services, set up everything needed so the mission can run fully autonomously from this point forward. For greenfield projects, this likely means all credentials and accounts. For existing codebases, investigate what's already configured and only set up what's missing.

If new credentials/accounts are needed:
1. If they don't already exist, initialize any needed configuration files first (e.g., `.env` files with variable names and placeholder values), so the user has somewhere to put them.
2. Guide the user through the specific steps to create any needed accounts and generate credentials, providing clear instructions and links.

**CRITICAL: During this step, we must set up everything such that the mission can run autonomously until completion.**

The user may explicitly choose to defer specific credentials (e.g., "use mocks for now", "I'll add Stripe keys later"). Respect this, but note it in the mission proposal so workers know what's unavailable.

Skip this phase entirely if the mission doesn't require any external credential or account setup.

Ensure that you don't commit any secrets or sensitive information. Add these files to `.gitignore`.

## Phase 6: Plan Testing & Validation Strategy

Use subagents to investigate both testing infrastructure and user testing strategy. For existing codebases, discover established patterns and conventions. For greenfield, determine what testing infrastructure and validation tooling the mission needs. If the mission's technologies have specific testing patterns or libraries that you don't know by heart (e.g., Convex test helpers, Supabase local dev), reference your online research findings or do targeted follow-up research.

### Testing Infrastructure

Consider whether the mission needs dedicated testing features beyond per-worker TDD:
- Shared test fixtures, seed data, or factories that multiple features depend on
- E2e tests for critical user flows (especially in existing codebases that already have e2e coverage)
- Integration test setup (e.g., test database configuration, mock services)

### User Testing Strategy

Plan how the mission's output will be validated through its real user surface. This informs both per-worker and end-of-milestone validation.

#### Surface Discovery

Determine:
- Which surfaces will be tested (browser, CLI, API endpoints)?
- What tools will be used and what setup is needed?
- Are there any gaps \u2014 surfaces that exist but can't be reliably tested?

**Tool selection rule:** If the mission involves a web application or an Electron desktop app, you MUST use `agent-browser` for validation of that surface, unless the user explicitly requests an alternative.

#### Dry Run (REQUIRED)

You must run a validation readiness dry run before proceeding to the mission proposal. This is a critical quality gate to confirm that your validation approach is executable in the environment and that any blockers are identified and addressed before implementation begins.

- Use the `Task` tool to delegate this dry run to a subagent. It should:
  - Start required services and run a representative pass of the intended user-testing flows with the tools the mission will use (agent-browser, tuistory, curl), including auth/bootstrap paths when applicable.
  - For new (greenfield) codebases: there is no running application yet, so the dry run focuses on verifying the toolchain \u2014 confirm that testing tools (agent-browser, tuistory, curl) are installed and functional, that planned ports are available, and that the environment can support the validation approach (e.g., can agent-browser launch and navigate to a local URL?).
  - For existing codebases: verify the full validation path \u2014 dev server starts, pages load, testing tools can interact with the application surface, auth/bootstrap paths work, existing fixtures/seed data are available, and the application is in a testable state.
  - Confirm the validation path is actually executable in this environment before implementation begins.
  - Measure resource consumption during the dry run: check memory usage, CPU load, and process count before and after exercising flows. Report the numbers. Note whether flows triggered substantial background work, process spawning, or unexpected resource growth \u2014 these observations feed directly into the resource cost classification step below.
  - Identify blockers early (auth/access issues, missing fixtures/seed data, env/config gaps, broken local setup, unavailable entrypoints, flaky prerequisites).
- Present blockers and concrete options to the user, then iterate until either:
  1. validation is runnable, or
  2. the user explicitly approves an alternative validation approach (with known limitations).

**Do NOT proceed until the dry run is complete and the validation path is confirmed executable (or the user has explicitly approved an alternative).**

#### Resource Cost Classification

Check the machine's total memory, CPU cores, and current utilization. Determine the **max concurrent validators** for each validation surface \u2014 up to 5. Consider: how much memory/CPU does each validator instance consume on this surface? How much headroom does the machine have? Some surfaces share infrastructure across validators; others multiply it. Factor in the actual weight of what gets multiplied.

**Use 70% of available headroom** when calculating max concurrency. Dry run profiles are estimates, and real usage may be unpredictable. Planning against 70% of headroom absorbs the unexpected.

**Example \u2014 agent-browser (lightweight app):** The app is lightweight, so each agent-browser instance uses ~300 MB of RAM. The dev server adds ~200 MB. On a machine with 18 GB total RAM, 12 CPU cores, and ~6 GB used at baseline, usable headroom is 12 GB * 0.7 = **8.4 GB**. Running 5 concurrent instances adds ~1.5 GB, plus ~200 MB for the dev server \u2014 well within budget. Max concurrent: **5**.

**Example \u2014 agent-browser (heavy app):** The app under test is an Electron-based IDE that consumes ~2 GB of RAM per instance. Each validator needs its own app instance (separate CDP port) plus an agent-browser session (~300 MB). That's ~2.3 GB per validator. On the same machine, usable headroom is **8.4 GB**. 3 validators = 6.9 GB (fits). 4 validators = 9.2 GB (exceeds budget). Max concurrent: **3**.

**Reason beyond dry runs, especially in existing codebases.** A dry run is a snapshot of one moment \u2014 it won't capture what the codebase actually does under real usage. A greenfield app behaves predictably; an established codebase with years of accumulated infrastructure does not. Before finalizing concurrency limits, reason about what the mission is actually building and what it will interact with \u2014 worker threads, background jobs, or specific user flows can all spike resource usage well beyond what a dry run captures. Use this understanding to inform concurrency limits.

If the mission has multiple surfaces, classify each independently.

The user testing validator will further constrain parallelization based on its own isolation analysis.

#### Encode Findings

Capture everything validators need in `.factory/library/user-testing.md` so they can act without re-deriving it:
- Surface discovery findings under a `## Validation Surface` section, including any user-specified testing skills/tools
- Resource cost classification per surface under a `## Validation Concurrency` section (max concurrent validators, with numbers and rationale)

### Confirm with User

Before concluding this phase, you must align with the user on both the testing and validation strategy and get explicit confirmation on:
- What testing infrastructure will be set up (fixtures, e2e, integration)
- What test types apply (unit, component, integration, e2e)
- Validation surfaces, tools, setup, and resource cost classification
- Any accepted limitations

**You need explicit user confirmation to proceed.** Iterate until they agree.

Capture the final validation approach and any accepted limitations in all relevant mission artifacts.

## Phase 7: Create Mission Proposal

With the comprehensive plan complete, call `propose_mission` with a detailed markdown proposal.

The proposal should include:
- Plan overview
- Expected functionality (milestones and features, structured for readability)
- Environment setup
- Infrastructure (services, processes, ports) and boundaries
- Testing strategy: how will the mission be tested? Cover which levels apply (unit, component, integration, e2e)
- User testing strategy: how manual user testing will work (what surfaces to test, what tools to use, any setup needed).
- Validation readiness: results of the dry run \u2014 confirm the validation path is executable, or note any accepted limitations/alternatives.
- Non-functional requirements

The infrastructure section tells workers what's needed and what to avoid. Example:

```markdown
## Infrastructure

**Services:**
- Postgres on localhost:5432 (existing)
- API server on port 3100
- Web frontend on port 3101
- Background worker on port 3102

**Off-limits:**
- Redis on 6379 (other project)
- Ports 3000-3010 (user's dev servers)
- /data directory
```

NOTE: features.json will be much more detailed than the proposal.

After `propose_mission` is accepted, you will have a `missionDir`.

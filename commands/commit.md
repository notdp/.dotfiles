# Commit Message

You are preparing a Conventional Commits style message for the current repository state.

1. Inspect the repo to understand pending changes (`git status -sb`, `git diff --stat`, and specific diffs as needed).
2. Identify the primary impact, scope, and motivation. Highlight fixes that prevent container npm login failures if applicable.
3. Compose a single English commit summary using the format `type(scope): concise summary`, max 72 characters, lowercase type.
4. Reply with two lines: the commit message on the first line, and on the second line ask the user if they would like you to commit it now.

If there are no staged or unstaged changes, reply with `noop` and skip the follow-up question.

**Do NOT add any Co-authored-by lines.**

---
name: read-droid-session
description: 当需要在 OpenCode 或其他非 Droid agent 中通过短 session hash 查找、读取、恢复 Droid session 历史时使用；提供 `~/.factory/sessions` 的路径规则、搜索命令和交接输出边界。
---

# Read Droid Session

Use this skill to find and read Droid session history from OpenCode or another agent that does not have Droid's builtin `session-navigation` skill loaded. The usual input is a short session hash like `264f0a81`.

## Where Droid sessions live

Droid stores sessions under `~/.factory/sessions/`, grouped by encoded project path. Slashes in the project path become dashes.

```text
~/.factory/sessions/
├── -Users-name-code-myapp/
│   ├── <session-id>.jsonl
│   └── <session-id>.settings.json
└── -Users-name-dotfiles/
    ├── <session-id>.jsonl
    └── <session-id>.settings.json
```

Two files matter:

- `<session-id>.jsonl`: conversation records, tool calls, tool results, metadata, cwd, title.
- `<session-id>.settings.json`: model, token usage, autonomy settings, timing.

## Common tasks

### Find a known session id or short hash

```bash
rg -l "264f0a81" ~/.factory/sessions
```

If the id is a file prefix, a glob is often faster:

```bash
find ~/.factory/sessions -name "264f0a81*.jsonl" -print
```

If multiple sessions match the short hash, sort by mtime and read the metadata before choosing:

```bash
for f in $(find ~/.factory/sessions -name "264f0a81*.jsonl" -print | xargs ls -t); do
  echo "=== $f ==="
  head -1 "$f" | jq -r '{id, sessionTitle, title, cwd}'
done
```

### List recent sessions for the current repo

First encode the project path. Example: `/Users/zhenninglang/.dotfiles` becomes `-Users-zhenninglang-.dotfiles`.

```bash
ls -lt ~/.factory/sessions/-Users-zhenninglang-.dotfiles/ | head
```

Show titles:

```bash
for f in $(ls -t ~/.factory/sessions/-Users-zhenninglang-.dotfiles/*.jsonl | head -10); do
  echo "=== $f ==="
  head -1 "$f" | jq -r '.sessionTitle // .title // "Untitled"'
done
```

### Search by content

```bash
rg "opencode" ~/.factory/sessions/-Users-zhenninglang-.dotfiles/
rg -C 2 "gpt-5.5-fast" ~/.factory/sessions/
```

### Read a session safely

Use read-only commands. Avoid printing secrets or large payloads directly into the final answer.

```bash
head -1 ~/.factory/sessions/-Users-zhenninglang-.dotfiles/<session-id>.jsonl | jq .
cat ~/.factory/sessions/-Users-zhenninglang-.dotfiles/<session-id>.settings.json | jq .
wc -l ~/.factory/sessions/-Users-zhenninglang-.dotfiles/<session-id>.jsonl
```

Summarize roles and tool calls:

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("~/.factory/sessions/-Users-zhenninglang-.dotfiles/<session-id>.jsonl").expanduser()
for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    obj = json.loads(line)
    msg = obj.get("message") or {}
    role = msg.get("role", "")
    tools = [part.get("name") for part in (msg.get("content") or []) if part.get("type") == "tool_use"]
    texts = [
        (part.get("text") or "").replace("\n", " ")[:180]
        for part in (msg.get("content") or [])
        if part.get("type") == "text"
    ]
    print(f"{i:03d} {obj.get('type')} {role} tools={tools} {' | '.join(texts)[:220]}")
PY
```

## Restore working context

When resuming a session, extract:

1. User goal and acceptance criteria.
2. Files changed and current git status from that session.
3. Commands already run and their outcomes.
4. Open todos or interrupted/cancelled requests.
5. Any warnings about external file modifications.

Return a short handoff before continuing:

```markdown
## Resumed Droid session

- Session: `<id>`
- Goal: ...
- Last known state: ...
- Modified files: ...
- Verified commands: ...
- Next step: ...
```

## Evidence and safety

- Treat session files as potentially sensitive.
- Quote only the minimal lines needed to support the handoff.
- If a session contains secrets, credentials, private URLs, or large logs, summarize the existence of sensitive content without reproducing it.
- If the session was interrupted or cancelled, do not retry cancelled tool calls automatically; continue from the last safe state.

## Verification

Before claiming a session was found, provide the matched path and one metadata field from the first JSONL line, such as `sessionTitle`, `cwd`, or `id`.

If no session matches a short hash, report the exact search commands tried and ask for a longer prefix or project path.

---
name: read
description: Invoke when given any URL, web page link, or PDF to read. Fetches the content as clean Markdown via proxy cascade and saves to Downloads. Not for local text files or source code already in the repo.
metadata:
  version: "3.9.0"
---

# Read: Fetch Any URL or PDF as Markdown

Prefix your first line with 🥷 inline, not as its own paragraph.


Convert any URL or local PDF to clean Markdown and save it. No analysis, no summary, no discussion of the content unless explicitly asked.

## Routing

| Input | Method |
|-------|--------|
| `feishu.cn`, `larksuite.com` | Feishu API script |
| `mp.weixin.qq.com` | Proxy cascade first, built-in WeChat article script only if the proxies fail |
| `.pdf` URL or local PDF path | PDF extraction |
| GitHub URLs (`github.com`, `raw.githubusercontent.com`) | Prefer raw content or `gh` first. Use the proxy cascade only as fallback. |
| Everything else | Proxy cascade |

After routing, load `references/read-methods.md` and run the commands for the chosen method.

## Output Format

```
Title:  {title}
Author: {author} (if available)
Source: {platform}
URL:    {original url}

Content
{full Markdown, truncated at 200 lines if long}
```

## Saving

Save to `~/Downloads/{title}.md` with YAML frontmatter by default.
Skip only if user says "just preview" or "don't save". Tell the user the saved path.

If `~/Downloads/{title}.md` already exists, append `-1`, `-2`, etc., to the filename. Never overwrite an existing file without explicit confirmation.

## Hard Rules

- **Do not summarize or analyze the content.** Your job is conversion and storage, not interpretation.
- **Never overwrite without confirmation.** If the target filename already exists, use an auto-incremented suffix.
- **Stop after the save report.** Do not suggest follow-up actions ("Would you like me to summarize?", "Next, you could...") unless the user asks.

## Gotchas

| What happened | Rule |
|---------------|------|
| Fetched a paywalled article and returned a login page as Markdown | Inspect the first 10 lines for paywall signals ("Subscribe", "Sign in", "Continue reading"). If found, stop and warn the user. Do not save the login page. |
| r.jina.ai or defuddle.md returned empty for a JS-heavy site | Try the local fallback (`agent-fetch` or `defuddle parse`) before giving up. |
| Network failures | Prepend local proxy env vars if available and retry once. |
| Long content | `| head -n 200` to preview first; mention truncation when reporting the save. |
| Local fallback tools returned JSON | Extract the Markdown-bearing field. Raw JSON is not a valid final output for `/read`. |
| All methods failed | Stop and tell the user what was tried and what failed. Suggest opening the URL in a browser or providing an alternative. Do not silently return empty or partial results. |

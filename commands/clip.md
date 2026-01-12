---
description: Copy content to clipboard
argument-hint: <content to copy>
---

Copy the provided content to the system clipboard.

## Commands

- macOS: `printf '%s' 'content' | pbcopy`
- Linux: `printf '%s' 'content' | xclip -selection clipboard`
- Windows: `printf '%s' 'content' | clip`

## Rules

1. Execute the command, don't just output
2. Use `printf '%s'` instead of `echo` (avoids trailing newline issues)
3. For multi-line or special characters, use heredoc:
   ```bash
   pbcopy <<'EOF'
   content here
   EOF
   ```
4. Confirm after execution: "Copied"
5. Do not modify the original content

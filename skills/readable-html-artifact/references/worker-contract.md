# HTML Artifact Worker Contract

## Purpose

Generate or refresh an HTML companion artifact from a Markdown SSOT without returning full HTML to the parent agent context.

## Inputs

| Field | Meaning |
|---|---|
| `source_md` | Existing Markdown source of truth |
| `output_html` | HTML file to create or refresh |
| `profile` | `generic`, `plan`, or `research` |
| `title` | Optional display title |
| `style_constraints` | Optional short visual constraints |

## Allowed actions

- Read `source_md`.
- Write only `output_html`.
- Run the renderer or equivalent local validation commands.
- Report concise metadata and validation evidence.

## Forbidden actions

- Do not return full HTML, CSS, or JavaScript in the final response.
- Do not modify `source_md`.
- Do not create unrelated docs or README files.
- Do not fetch remote assets or depend on network access.
- Do not execute raw HTML or JavaScript from Markdown.

## Preferred command

```bash
python3 scripts/render_html_artifact.py --source <source_md> --output <output_html> --profile <profile>
```

## Return format

```markdown
## HTML Artifact Worker Result

| Field | Value |
|---|---|
| Source | `<source_md>` |
| Output | `<output_html>` |
| Profile | `<profile>` |
| Validation | `<command/result>` |

Summary:
- <1-3 bullets about generated sections or notable constraints>

Known gaps:
- <none or concise list>
```

## Compatibility

- Droid may implement this through a subagent.
- Claude Code may use its equivalent task/subagent mechanism.
- Codex may run the renderer directly.
- If no subagent mechanism is available, run the renderer in the main process and keep the same return format.

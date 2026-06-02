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
- Resolve the target repo root for reporting and relative path handling.
- Resolve the renderer path separately from the target repo root.
- Run the renderer or equivalent local validation commands.
- Report concise metadata and validation evidence.

## Forbidden actions

- Do not return full HTML, CSS, or JavaScript in the final response.
- Do not modify `source_md`.
- Do not create unrelated docs or README files.
- Do not fetch remote assets or depend on network access.
- Do not execute raw HTML or JavaScript from Markdown.

## Preferred command

Do not assume the worker's current directory is the target repo root, and do not assume the target repo contains the renderer.

First resolve `source_md` and `output_html` to absolute paths. Then resolve `target_repo_root` from the source or output parent directory for reporting. Resolve `renderer_path` separately in this order:

1. `<target_repo_root>/scripts/render_html_artifact.py` if the target project intentionally overrides the renderer.
2. `<skill_dir>/render_html_artifact.py` for the renderer wrapper installed with this skill.
3. `<skill_dir>/../../scripts/render_html_artifact.py` when running directly from the dotfiles source checkout.

Then run:

```bash
python3 "<renderer_path>" --source <source_md> --output <output_html> --profile <profile>
```

If `target_repo_root` cannot be resolved, report that fact but continue if `source_md` and `output_html` are absolute and valid. If the renderer is missing after checking all candidate absolute paths, report the checked paths.

## Return format

```markdown
## HTML Artifact Worker Result

| Field | Value |
|---|---|
| Source | `<source_md>` |
| Output | `<output_html>` |
| Profile | `<profile>` |
| Target repo root | `<target_repo_root or unresolved>` |
| Renderer | `<renderer_path>` |
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

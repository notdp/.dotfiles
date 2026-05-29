#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
from pathlib import Path


PROFILES = {"generic", "plan", "research"}

INLINE_CODE = re.compile(r"`([^`]+)`")
INLINE_BOLD = re.compile(r"\*\*([^*]+)\*\*")
ORDERED_ITEM = re.compile(r"^\d+\.\s+(.*)$")


def escape_text(value: str) -> str:
    return html.escape(value, quote=True)


def render_inline(value: str) -> str:
    """行内 markdown: 先 escape(防 XSS), 再在转义后文本上跑 `code` 和 **bold** 正则。"""
    escaped = escape_text(value)
    escaped = INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = INLINE_BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    return escaped


def is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if not cells:
        return False
    return all(cell and set(cell) <= {"-", ":"} and "-" in cell for cell in cells)


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_table(lines: list[str], start: int) -> tuple[str, int] | None:
    if start + 1 >= len(lines) or "|" not in lines[start] or not is_table_separator(lines[start + 1]):
        return None

    headers = split_table_row(lines[start])
    rows: list[list[str]] = []
    index = start + 2
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        rows.append(split_table_row(lines[index]))
        index += 1

    header_html = "".join(f"<th>{render_inline(cell)}</th>" for cell in headers)
    row_html = []
    for row in rows:
        padded = row + [""] * max(0, len(headers) - len(row))
        cells = "".join(f"<td>{render_inline(cell)}</td>" for cell in padded[: len(headers)])
        row_html.append(f"<tr>{cells}</tr>")

    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(row_html)}</tbody></table>", index


def render_markdown_body(markdown: str) -> tuple[str, int]:
    lines = markdown.splitlines()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    ordered_items: list[str] = []
    quote_lines: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    headings = 0

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(part.strip() for part in paragraph).strip()
            if text:
                blocks.append(f"<p>{render_inline(text)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            items = "".join(f"<li>{render_inline(item)}</li>" for item in list_items)
            blocks.append(f"<ul>{items}</ul>")
            list_items.clear()

    def flush_ordered() -> None:
        if ordered_items:
            items = "".join(f"<li>{render_inline(item)}</li>" for item in ordered_items)
            blocks.append(f"<ol>{items}</ol>")
            ordered_items.clear()

    def flush_quote() -> None:
        if quote_lines:
            text = " ".join(quote_lines).strip()
            blocks.append(f"<blockquote>{render_inline(text)}</blockquote>")
            quote_lines.clear()

    def flush_all() -> None:
        flush_paragraph()
        flush_list()
        flush_ordered()
        flush_quote()

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if in_code:
            if stripped.startswith("```"):
                lang_attr = f' data-lang="{escape_text(code_lang)}"' if code_lang else ""
                blocks.append(f"<pre{lang_attr}><code>{escape_text(chr(10).join(code_lines))}</code></pre>")
                in_code = False
                code_lang = ""
                code_lines.clear()
            else:
                code_lines.append(line)
            index += 1
            continue

        if stripped.startswith("```"):
            flush_all()
            in_code = True
            code_lang = stripped[3:].strip()
            index += 1
            continue

        table = render_table(lines, index)
        if table is not None:
            flush_all()
            table_html, next_index = table
            blocks.append(table_html)
            index = next_index
            continue

        if not stripped:
            flush_all()
            index += 1
            continue

        if stripped.startswith("#"):
            marker = stripped.split(" ", 1)[0]
            if marker and set(marker) == {"#"} and 1 <= len(marker) <= 6 and len(stripped) > len(marker):
                flush_all()
                level = len(marker)
                text = stripped[len(marker) :].strip()
                blocks.append(f"<h{level}>{render_inline(text)}</h{level}>")
                headings += 1
                index += 1
                continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            flush_ordered()
            quote_lines.append(stripped[1:].strip())
            index += 1
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            flush_ordered()
            flush_quote()
            list_items.append(stripped[2:].strip())
            index += 1
            continue

        ordered = ORDERED_ITEM.match(stripped)
        if ordered:
            flush_paragraph()
            flush_list()
            flush_quote()
            ordered_items.append(ordered.group(1).strip())
            index += 1
            continue

        flush_list()
        flush_ordered()
        flush_quote()
        paragraph.append(line)
        index += 1

    if in_code:
        lang_attr = f' data-lang="{escape_text(code_lang)}"' if code_lang else ""
        blocks.append(f"<pre{lang_attr}><code>{escape_text(chr(10).join(code_lines))}</code></pre>")
    flush_all()
    return "\n".join(blocks), headings


def infer_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def render_html_artifact(*, source: Path, title: str | None, profile: str) -> tuple[str, int]:
    markdown = source.read_text(encoding="utf-8", errors="replace")
    resolved_title = title or infer_title(markdown, source.stem)
    body, heading_count = render_markdown_body(markdown)
    generated_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_text(resolved_title)}</title>
<style>
:root {{ color-scheme: light; --bg: #f8fafc; --panel: #ffffff; --text: #111827; --muted: #64748b; --border: #dbe3ef; --accent: #1f4b99; }}
body {{ margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.55; }}
main {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 48px; }}
header {{ background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-bottom: 18px; }}
section {{ background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 22px; }}
h1, h2, h3, h4, h5, h6 {{ line-height: 1.2; margin: 1.4em 0 0.5em; }}
header h1 {{ margin-top: 0; }}
p {{ margin: 0.75em 0; }}
ul {{ padding-left: 1.4rem; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #0f172a; color: #e5e7eb; padding: 14px; border-radius: 10px; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th, td {{ border: 1px solid var(--border); padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background: #eef4ff; }}
.meta {{ color: var(--muted); font-size: 0.92rem; }}
.badge {{ display: inline-block; background: #e0ecff; color: var(--accent); border-radius: 999px; padding: 2px 10px; font-size: 0.82rem; margin-right: 8px; }}
</style>
</head>
<body>
<main>
<header>
<span class="badge">{escape_text(profile)}</span>
<h1>{escape_text(resolved_title)}</h1>
<div class="meta">Source: {escape_text(str(source))}</div>
<div class="meta">Generated: {escape_text(generated_at)}</div>
</header>
<section>
{body}
</section>
</main>
</body>
</html>
""", heading_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a static HTML companion from a Markdown SSOT file.")
    parser.add_argument("--source", type=Path, required=True, help="Markdown source file.")
    parser.add_argument("--output", type=Path, required=True, help="HTML output file.")
    parser.add_argument("--title", help="Optional HTML title. Defaults to the first H1 or source stem.")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="generic")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.source.exists():
        sys.stderr.write(f"ERROR: missing source: {args.source}\n")
        return 2
    if not args.source.is_file():
        sys.stderr.write(f"ERROR: source is not a file: {args.source}\n")
        return 2

    html_text, heading_count = render_html_artifact(source=args.source, title=args.title, profile=args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    sys.stdout.write(f"wrote {args.output} headings={heading_count} profile={args.profile}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

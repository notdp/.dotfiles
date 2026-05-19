#!/usr/bin/env python3
"""Render a review-managed Markdown doc into an interactive HTML review artifact.

Each heading becomes an anchored section with its own comments thread and a textarea
for new comments. Existing comments are loaded from <doc>.comments.json. Draft input
persists in sessionStorage so re-rendering does not lose unsaved work. The export button
packages all non-empty textareas plus existing comments into a downloadable JSON file.

This script is separate from scripts/render_html_artifact.py because review artifacts
have interactive UI requirements (textareas, sessionStorage, export) that do not belong
in the single-direction publish path that render_html_artifact serves.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from render_html_artifact import escape_text, render_markdown_body
from review_doc_ids import Anchor, slugify_heading


@dataclass(frozen=True)
class Section:
    anchor: Anchor | None
    body_md: str


def split_sections(md_text: str) -> list[Section]:
    """Split MD into per-anchor sections. Pre-heading content forms an anchor-less prelude."""
    lines = md_text.splitlines()
    in_code_fence = False
    current_anchor: Anchor | None = None
    current_body: list[str] = []
    sections: list[Section] = []
    seen_slugs: dict[str, int] = {}

    def flush() -> None:
        sections.append(Section(anchor=current_anchor, body_md="\n".join(current_body)))

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            current_body.append(line)
            continue
        if not in_code_fence and stripped.startswith("#"):
            marker, _, rest = stripped.partition(" ")
            heading_text = rest.strip()
            if marker and set(marker) == {"#"} and 1 <= len(marker) <= 6 and heading_text:
                flush()
                base = slugify_heading(heading_text)
                count = seen_slugs.get(base, 0) + 1
                seen_slugs[base] = count
                anchor_id = base if count == 1 else f"{base}-{count}"
                current_anchor = Anchor(id=anchor_id, heading=heading_text, level=len(marker), line=index)
                current_body = [line]
                continue
        current_body.append(line)

    flush()

    if sections and sections[0].anchor is None and not sections[0].body_md.strip():
        sections = sections[1:]

    return sections


def render_comment(comment: dict) -> str:
    role = str(comment.get("role", "user"))
    status = str(comment.get("status", "open"))
    text = str(comment.get("text", ""))
    response = comment.get("response")
    parts = [
        f'<li class="comment role-{escape_text(role)} status-{escape_text(status)}" '
        f'data-role="{escape_text(role)}">',
        f'  <div class="comment-meta">{escape_text(role)} · {escape_text(status)}</div>',
        f'  <div class="comment-text">{escape_text(text)}</div>',
    ]
    if response:
        parts.append(
            f'  <div class="comment-response">agent: {escape_text(str(response))}</div>'
        )
    parts.append("</li>")
    return "\n".join(parts)


def render_anchor_section(section: Section, comments: list[dict]) -> str:
    assert section.anchor is not None
    body_html, _ = render_markdown_body(section.body_md)
    anchor_id = section.anchor.id

    open_comments = [c for c in comments if c.get("status") == "open"]
    closed_comments = [c for c in comments if c.get("status") != "open"]

    thread_parts: list[str] = []
    if closed_comments:
        items = "\n".join(render_comment(c) for c in closed_comments)
        thread_parts.append(
            f'<details class="resolved-thread"><summary>已解决 ({len(closed_comments)})</summary>'
            f'<ul class="comments">{items}</ul></details>'
        )
    if open_comments:
        items = "\n".join(render_comment(c) for c in open_comments)
        thread_parts.append(
            f'<div class="open-thread"><h4 class="thread-label">进行中 ({len(open_comments)})</h4>'
            f'<ul class="comments">{items}</ul></div>'
        )
    thread_html = "\n".join(thread_parts)

    return (
        f'<section class="anchor" data-review-id="{escape_text(anchor_id)}" '
        f'data-heading-level="{section.anchor.level}">\n'
        f'  <div class="anchor-body">{body_html}</div>\n'
        f'  <div class="anchor-comments">\n'
        f'    {thread_html}\n'
        f'    <textarea data-anchor-id="{escape_text(anchor_id)}" '
        f'placeholder="写评论…(自动保存草稿)"></textarea>\n'
        f'  </div>\n'
        f"</section>"
    )


def render_review_html(*, doc_path: Path, doc_text: str, comments: dict | None) -> str:
    if comments is None:
        comments = {
            "schema_version": 1,
            "spec_file": str(doc_path),
            "review_version": 0,
            "anchors": {},
        }

    sections = split_sections(doc_text)
    anchors_map = comments.get("anchors") or {}

    body_parts: list[str] = []
    for section in sections:
        if section.anchor is None:
            html_body, _ = render_markdown_body(section.body_md)
            body_parts.append(f'<article class="prelude">{html_body}</article>')
        else:
            anchor_payload = anchors_map.get(section.anchor.id) or {}
            anchor_comments = anchor_payload.get("comments") or []
            body_parts.append(render_anchor_section(section, anchor_comments))
    body_html = "\n".join(body_parts)

    review_version = comments.get("review_version", 0)
    title = doc_path.name
    generated_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    embedded_json = (
        json.dumps(comments, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )

    return (
        "<!doctype html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Review: {escape_text(title)}</title>\n"
        f"<style>\n{STYLES}\n</style>\n"
        "</head>\n"
        "<body>\n"
        "<main>\n"
        '<header class="review-header">\n'
        '  <div class="review-header-text">\n'
        f"    <h1>Review: {escape_text(title)}</h1>\n"
        f'    <div class="meta">source: {escape_text(str(doc_path))} · review v{escape_text(str(review_version))} · generated {escape_text(generated_at)}</div>\n'
        "  </div>\n"
        '  <button id="export-btn" type="button">导出未提交评论 (<span id="draft-count">0</span>)</button>\n'
        "</header>\n"
        f"{body_html}\n"
        "</main>\n"
        f'<script type="application/json" id="comments-data">{embedded_json}</script>\n'
        f"<script>\n{SCRIPTS}\n</script>\n"
        "</body>\n"
        "</html>\n"
    )


STYLES = """
:root { color-scheme: light; --bg: #f8fafc; --panel: #ffffff; --text: #111827; --muted: #64748b; --border: #dbe3ef; --accent: #1f4b99; --agent-bg: #fef3c7; --user-bg: #e0ecff; --code-bg: #0f172a; --code-fg: #e5e7eb; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif; line-height: 1.55; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 20px 48px; }
header.review-header { position: sticky; top: 0; z-index: 10; background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 14px 20px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; gap: 16px; backdrop-filter: blur(4px); }
.review-header h1 { margin: 0; font-size: 1.15rem; }
.meta { color: var(--muted); font-size: 0.82rem; margin-top: 4px; }
#export-btn { background: var(--accent); color: white; border: none; border-radius: 8px; padding: 10px 16px; font-size: 0.92rem; cursor: pointer; white-space: nowrap; }
#export-btn:hover { filter: brightness(1.1); }
#export-btn[data-has-drafts="1"] { box-shadow: 0 0 0 3px rgba(31, 75, 153, 0.25); }
article.prelude { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-bottom: 18px; }
section.anchor { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-bottom: 18px; display: grid; grid-template-columns: 1fr 340px; gap: 24px; }
.anchor-body h1, .anchor-body h2, .anchor-body h3, .anchor-body h4, .anchor-body h5, .anchor-body h6 { margin: 0 0 12px; line-height: 1.25; }
.anchor-body p { margin: 0.7em 0; }
.anchor-body pre { background: var(--code-bg); color: var(--code-fg); padding: 12px; border-radius: 8px; overflow-x: auto; }
.anchor-body code { font-family: ui-monospace, SFMono-Regular, monospace; font-size: 0.9em; }
.anchor-body table { width: 100%; border-collapse: collapse; margin: 0.8em 0; }
.anchor-body th, .anchor-body td { border: 1px solid var(--border); padding: 6px 8px; text-align: left; vertical-align: top; }
.anchor-body th { background: #eef4ff; }
.anchor-body ul { padding-left: 1.4rem; }
.anchor-comments { border-left: 2px solid var(--border); padding-left: 16px; font-size: 0.92rem; min-width: 0; }
.thread-label { margin: 4px 0 8px; color: var(--muted); font-size: 0.82rem; font-weight: 500; }
ul.comments { list-style: none; padding: 0; margin: 0 0 12px; }
.comment { padding: 8px 10px; border-radius: 8px; margin-bottom: 8px; background: var(--user-bg); }
.comment.role-agent { background: var(--agent-bg); }
.comment-meta { color: var(--muted); font-size: 0.78rem; margin-bottom: 4px; }
.comment-text { white-space: pre-wrap; word-break: break-word; }
.comment-response { color: var(--muted); margin-top: 6px; padding-top: 6px; border-top: 1px dashed var(--border); white-space: pre-wrap; }
details.resolved-thread { margin-bottom: 10px; }
details.resolved-thread summary { cursor: pointer; color: var(--muted); font-size: 0.82rem; padding: 4px 0; }
.anchor-comments textarea { width: 100%; min-height: 80px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; font-family: inherit; font-size: 0.95rem; resize: vertical; background: #fcfcfd; }
.anchor-comments textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
@media (max-width: 960px) { section.anchor { grid-template-columns: 1fr; } .anchor-comments { border-left: none; border-top: 2px solid var(--border); padding-left: 0; padding-top: 16px; } }
"""

SCRIPTS = """
(function () {
  const dataNode = document.getElementById('comments-data');
  const COMMENTS = JSON.parse(dataNode.textContent);
  const sourceKey = (COMMENTS.spec_file || 'doc').replace(/[^a-zA-Z0-9_\\-]/g, '-');
  const storageKey = (anchor) => 'review:' + sourceKey + ':' + anchor;
  const textareas = document.querySelectorAll('textarea[data-anchor-id]');
  const draftCountNode = document.getElementById('draft-count');
  const exportBtn = document.getElementById('export-btn');

  function updateDraftCount() {
    let n = 0;
    textareas.forEach((t) => { if (t.value.trim()) n++; });
    draftCountNode.textContent = String(n);
    exportBtn.dataset.hasDrafts = n > 0 ? '1' : '0';
  }

  textareas.forEach((t) => {
    const id = t.dataset.anchorId;
    const saved = sessionStorage.getItem(storageKey(id));
    if (saved) t.value = saved;
    t.addEventListener('input', () => {
      const v = t.value;
      if (v.trim()) {
        sessionStorage.setItem(storageKey(id), v);
      } else {
        sessionStorage.removeItem(storageKey(id));
      }
      updateDraftCount();
    });
  });
  updateDraftCount();

  exportBtn.addEventListener('click', () => {
    const next = JSON.parse(JSON.stringify(COMMENTS));
    next.anchors = next.anchors || {};
    next.review_version = (next.review_version || 0) + 1;
    const now = new Date().toISOString();
    let added = 0;
    textareas.forEach((t) => {
      const text = t.value.trim();
      if (!text) return;
      const anchorId = t.dataset.anchorId;
      const section = t.closest('section.anchor');
      const headingNode = section ? section.querySelector('h1,h2,h3,h4,h5,h6') : null;
      const heading = headingNode ? headingNode.textContent.trim() : anchorId;
      const existing = next.anchors[anchorId] || { heading: heading, comments: [] };
      existing.heading = heading;
      existing.comments = existing.comments || [];
      existing.comments.push({
        id: 'c-' + now.replace(/[:.]/g, '-') + '-' + anchorId + '-' + added,
        role: 'user',
        status: 'open',
        text: text,
        created_in_version: next.review_version,
      });
      next.anchors[anchorId] = existing;
      added++;
    });
    const blob = new Blob([JSON.stringify(next, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const stem = (COMMENTS.spec_file || 'doc').split('/').pop().replace(/\\.md$/, '');
    a.download = stem + '.comments.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 0);
  });
})();
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render review HTML from a Markdown doc.")
    parser.add_argument("--doc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--comments", type=Path, help="Optional comments.json path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.doc.exists():
        sys.stderr.write(f"ERROR: missing doc: {args.doc}\n")
        return 2
    doc_text = args.doc.read_text(encoding="utf-8")
    comments = None
    if args.comments is not None:
        if not args.comments.exists():
            sys.stderr.write(f"ERROR: missing comments: {args.comments}\n")
            return 2
        comments = json.loads(args.comments.read_text(encoding="utf-8"))
    html = render_review_html(doc_path=args.doc, doc_text=doc_text, comments=comments)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    sys.stdout.write(f"wrote {args.output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from droid_observe import resolve_target_workspaces


MAX_TAIL_BYTES = 60000
STATUS_RE = re.compile(r"^- Status:\s*(\S+)\s*$", re.MULTILINE)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def redact_state(state: dict) -> dict:
    redacted = dict(state)
    if "workspace_token" in redacted:
        redacted["workspace_token"] = "<redacted>"
    return redacted


def read_tail(path: Path, max_bytes: int = MAX_TAIL_BYTES) -> str:
    if not path.exists():
        return ""
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
                handle.readline()
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def age_seconds(raw: str | None) -> int | None:
    value = parse_iso(raw)
    if value is None:
        return None
    return max(0, int((datetime.now(timezone.utc) - value).total_seconds()))


def human_age(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds < 60:
        return f"{seconds}s"
    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {rest}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def workspace_summary(workspace: Path) -> dict:
    state = read_json(workspace / "state.json")
    heartbeat_age = age_seconds(state.get("last_heartbeat_at"))
    return {
        "path": str(workspace),
        "name": workspace.name,
        "goal": state.get("goal") or workspace.name,
        "status": state.get("status") or "unknown",
        "current_item": state.get("current_item") or "none",
        "current_phase": state.get("current_phase") or "none",
        "heartbeat_age_sec": heartbeat_age,
        "heartbeat_age": human_age(heartbeat_age),
        "last_validation": state.get("last_validation"),
        "stop_reason": state.get("stop_reason"),
        "updated_at": state.get("updated_at"),
        "iterations": state.get("iterations"),
        "agent_pid": state.get("agent_pid"),
    }


def item_short_name(item: str) -> str:
    if not item or item == "none":
        return "No active item"
    return item.split(":", 1)[0].strip() if ":" in item else item


def fix_plan_statuses(workspace: Path) -> list[str]:
    text = read_tail(workspace / "fix_plan.md", max_bytes=200000)
    return STATUS_RE.findall(text)


def fix_plan_all_done(workspace: Path) -> bool:
    statuses = fix_plan_statuses(workspace)
    return bool(statuses) and all(status == "done" for status in statuses)


def explain_status(summary: dict) -> dict:
    status = summary["status"]
    item = summary["current_item"]
    phase = summary["current_phase"]
    stop_reason = summary.get("stop_reason")
    heartbeat_age = summary.get("heartbeat_age_sec")
    if status == "running" and heartbeat_age is not None and heartbeat_age > 300:
        return {
            "health": "stale",
            "headline": f"Possibly stuck during {item_short_name(item)}",
            "why": f"No heartbeat for {human_age(heartbeat_age)}.",
            "next_action": "Inspect runtime details or wait for the next heartbeat.",
            "needs_user": True,
            "last_validation_label": "Previous validation",
        }
    if status == "running":
        return {
            "health": "running",
            "headline": f"Running {item}",
            "why": f"Current phase: {phase}. Heartbeat age: {summary['heartbeat_age']}.",
            "next_action": "No action needed unless the heartbeat becomes stale.",
            "needs_user": False,
            "last_validation_label": "Previous validation",
        }
    if status == "stopped":
        reason = stop_reason or "stopped without a reason"
        return {
            "health": "needs_attention",
            "headline": f"Stopped during {item_short_name(item)}",
            "why": reason,
            "next_action": "Inspect P1 runtime; idle timeout means the agent produced no output before the watchdog stopped it." if "timeout" in reason else "Inspect logs before resuming.",
            "needs_user": True,
            "last_validation_label": "Last validation",
        }
    if status == "done" or status == "completed":
        return {
            "health": "done",
            "headline": "Long-run completed",
            "why": f"Last active item: {item}.",
            "next_action": "Review final logs and artifacts.",
            "needs_user": False,
            "last_validation_label": "Last validation",
        }
    return {
        "health": "unknown",
        "headline": f"Status: {status}",
        "why": "The workspace state is incomplete or not recognized.",
        "next_action": "Inspect state details.",
        "needs_user": True,
        "last_validation_label": "Last validation",
    }


def build_snapshot(*, repo: Path, workspace: Path | None = None, sessions_dir: Path | None = None) -> dict:
    workspaces = resolve_target_workspaces(str(repo), sessions_dir or Path.home() / ".factory" / "sessions")
    if workspace is not None:
        selected_workspace = workspace
        if selected_workspace not in workspaces:
            workspaces.insert(0, selected_workspace)
    elif workspaces:
        selected_workspace = workspaces[0]
    else:
        raise RuntimeError(f"no long-loop workspace found for: {repo}")
    summaries = [workspace_summary(path) for path in workspaces]
    selected_summary = workspace_summary(selected_workspace)
    if fix_plan_all_done(selected_workspace):
        explanation = {
            "health": "done",
            "headline": "Long-run completed",
            "why": "All fix_plan items are done; state.json may still contain an older watchdog stop reason.",
            "next_action": "Review final logs and artifacts.",
            "needs_user": False,
            "last_validation_label": "Last validation",
        }
    else:
        explanation = explain_status(selected_summary)
    selected = {
        **selected_summary,
        **explanation,
        "logs_tail": read_tail(selected_workspace / "logs.md"),
        "runtime_tail": read_tail(selected_workspace / "runtime.log"),
        "fix_plan": read_tail(selected_workspace / "fix_plan.md"),
        "state": redact_state(read_json(selected_workspace / "state.json")),
    }
    return {
        "repo": str(repo),
        "selected_workspace": str(selected_workspace),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "workspaces": summaries,
        "selected": selected,
    }


def render_index_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Longrun Dashboard</title>
<style>
:root {
  --bg: #f5f3ef;
  --surface: #fffdf8;
  --surface-2: #f0ece3;
  --fg: #1e1b16;
  --muted: #756f64;
  --border: #ded6c9;
  --accent: #2f6f4e;
  --warn: #9a6700;
  --danger: #a43f3f;
  --mono-bg: #181612;
  --mono-fg: #f4efe6;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-width: 320px;
  background: var(--bg);
  color: var(--fg);
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.45;
}
main { max-width: 1180px; margin: 0 auto; padding: 32px 24px 56px; }
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 24px; }
h1 { margin: 0; font-size: clamp(28px, 4vw, 48px); letter-spacing: -0.04em; }
.subtle { color: var(--muted); font-size: 14px; }
.badge { border: 1px solid var(--border); background: var(--surface); border-radius: 999px; padding: 8px 12px; font-weight: 700; }
.badge.running { color: var(--accent); border-color: color-mix(in oklch, var(--accent), white 65%); }
.badge.stale, .badge.needs_attention { color: var(--warn); border-color: color-mix(in oklch, var(--warn), white 65%); }
.badge.done { color: var(--accent); }
.hero { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.6fr); gap: 16px; align-items: stretch; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 20px; }
.status-title { font-size: clamp(22px, 3vw, 32px); font-weight: 780; letter-spacing: -0.03em; margin: 0 0 12px; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
.kv { background: var(--surface-2); border-radius: 14px; padding: 12px; min-width: 0; }
.kv .label { display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
.kv .value { overflow-wrap: anywhere; font-weight: 650; }
.section-title { margin: 0 0 12px; font-size: 18px; }
.workspace-list { display: grid; gap: 8px; }
.workspace-button { width: 100%; text-align: left; border: 1px solid var(--border); background: var(--surface); border-radius: 12px; padding: 10px 12px; color: var(--fg); cursor: pointer; }
.workspace-button.active { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
.details { margin-top: 16px; display: grid; gap: 12px; }
details { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 14px 16px; }
summary { cursor: pointer; font-weight: 750; }
pre { max-height: 420px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; background: var(--mono-bg); color: var(--mono-fg); border-radius: 12px; padding: 14px; font-size: 13px; }
@media (max-width: 840px) {
  main { padding: 24px 16px 40px; }
  .top, .hero { display: block; }
  .badge { display: inline-block; margin-top: 12px; }
  .grid { grid-template-columns: 1fr; }
  .card { margin-bottom: 16px; }
}
</style>
</head>
<body>
<main>
  <div class="top">
    <div>
      <h1>Longrun Dashboard</h1>
      <div class="subtle" id="repo">Loading workspace...</div>
    </div>
    <div class="badge" id="health">Loading</div>
  </div>
  <section class="hero">
    <article class="card">
      <h2 class="status-title" id="headline">Loading...</h2>
      <p id="why" class="subtle"></p>
      <h3 class="section-title">Now</h3>
      <div class="grid">
        <div class="kv"><span class="label">Current item</span><span class="value" id="item"></span></div>
        <div class="kv"><span class="label">Current phase</span><span class="value" id="phase"></span></div>
        <div class="kv"><span class="label">Heartbeat</span><span class="value" id="heartbeat"></span></div>
      </div>
      <h3 class="section-title" style="margin-top: 18px;">Needs attention</h3>
      <p id="next-action"></p>
    </article>
    <aside class="card">
      <h3 class="section-title">Workspaces</h3>
      <div class="workspace-list" id="workspaces"></div>
    </aside>
  </section>
  <section class="details">
    <details open>
      <summary>Curated logs</summary>
      <pre id="logs"></pre>
    </details>
    <details>
      <summary>Runtime details</summary>
      <pre id="runtime"></pre>
    </details>
    <details>
      <summary>Fix plan</summary>
      <pre id="fix-plan"></pre>
    </details>
    <details>
      <summary>State JSON</summary>
      <pre id="state-json"></pre>
    </details>
  </section>
</main>
<script>
let selectedWorkspace = new URLSearchParams(location.search).get('workspace') || '';
function text(id, value) { document.getElementById(id).textContent = value ?? ''; }
function healthLabel(value) {
  return {running: 'Running', stale: 'Possibly stuck', needs_attention: 'Needs attention', done: 'Done', unknown: 'Unknown'}[value] || value;
}
async function refresh() {
  const suffix = selectedWorkspace ? '?workspace=' + encodeURIComponent(selectedWorkspace) : '';
  const response = await fetch('/api/snapshot' + suffix);
  const data = await response.json();
  selectedWorkspace = data.selected_workspace;
  const selected = data.selected;
  text('repo', data.repo + ' · refreshed ' + data.generated_at);
  const badge = document.getElementById('health');
  badge.className = 'badge ' + selected.health;
  badge.textContent = healthLabel(selected.health);
  text('headline', selected.headline);
  text('why', selected.why);
  text('item', selected.current_item);
  text('phase', selected.current_phase);
  text('heartbeat', selected.heartbeat_age);
  text('next-action', selected.next_action);
  text('logs', selected.logs_tail || '(no logs yet)');
  text('runtime', selected.runtime_tail || '(no runtime output yet)');
  text('fix-plan', selected.fix_plan || '(no fix plan)');
  text('state-json', JSON.stringify(selected.state, null, 2));
  const list = document.getElementById('workspaces');
  list.innerHTML = '';
  data.workspaces.forEach((workspace) => {
    const button = document.createElement('button');
    button.className = 'workspace-button' + (workspace.path === selectedWorkspace ? ' active' : '');
    button.textContent = workspace.name + ' · ' + workspace.status + ' · ' + workspace.current_item;
    button.onclick = () => {
      selectedWorkspace = workspace.path;
      history.replaceState(null, '', '?workspace=' + encodeURIComponent(selectedWorkspace));
      refresh();
    };
    list.appendChild(button);
  });
}
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    repo: Path
    sessions_dir: Path
    workspace: Path | None

    def write_response(self, status: int, content_type: str, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.write_response(200, "text/html; charset=utf-8", render_index_html())
            return
        if parsed.path == "/api/snapshot":
            query = urllib.parse.parse_qs(parsed.query)
            raw_workspace = query.get("workspace", [""])[0]
            workspace = Path(raw_workspace) if raw_workspace else self.workspace
            try:
                snapshot = build_snapshot(repo=self.repo, workspace=workspace, sessions_dir=self.sessions_dir)
            except RuntimeError as exc:
                self.write_response(404, "application/json; charset=utf-8", json.dumps({"error": str(exc)}))
                return
            self.write_response(200, "application/json; charset=utf-8", json.dumps(snapshot, ensure_ascii=False))
            return
        self.write_response(404, "text/plain; charset=utf-8", "not found")

    def log_message(self, _format: str, *_args) -> None:
        return


def serve(*, repo: Path, workspace: Path | None, sessions_dir: Path, port: int, open_browser: bool) -> int:
    class Handler(DashboardHandler):
        pass

    Handler.repo = repo
    Handler.sessions_dir = sessions_dir
    Handler.workspace = workspace
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    if open_browser:
        subprocess.run(["open", url], check=False)
    sys.stdout.write(f"longrun dashboard: {url}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open a dynamic long-run dashboard.")
    parser.add_argument("repo", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--sessions-dir", type=Path, default=Path.home() / ".factory" / "sessions")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--snapshot", action="store_true", help="Print one JSON snapshot and exit.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = args.repo.expanduser().resolve()
    workspace = args.workspace.expanduser().resolve() if args.workspace else None
    try:
        if args.snapshot:
            snapshot = build_snapshot(repo=repo, workspace=workspace, sessions_dir=args.sessions_dir)
            sys.stdout.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
            return 0
        return serve(repo=repo, workspace=workspace, sessions_dir=args.sessions_dir, port=args.port, open_browser=not args.no_open)
    except RuntimeError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

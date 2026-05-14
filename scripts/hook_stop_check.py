#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


VALIDATION_RE = re.compile(
    r"(run-verify\.sh|pytest|python3 -m unittest|npm test|npm run test|npm run lint|npm run typecheck|"
    r"tsc\b|verify_skills\.py|cargo test|go test|## 验证结果|validated \d+ skills)",
    re.I,
)
VISUAL_RE = re.compile(r"(screenshot|ui-visual-capture|agent-browser|playwright|overflow|visual)", re.I)
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs", ".swift", ".kt"}
UI_SUFFIXES = {".tsx", ".jsx", ".css", ".scss", ".vue", ".svelte"}


def project_root() -> Path:
    return Path(os.environ.get("FACTORY_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def load_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def suppress() -> dict:
    return {"suppressOutput": True}


def changed_files(root: Path) -> list[str]:
    result = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            files.append(path)
    return files


def transcript_text(path: str | None) -> str:
    if not path:
        return ""
    transcript = Path(path).expanduser()
    if not transcript.exists():
        return ""
    return transcript.read_text(encoding="utf-8", errors="replace")[-120000:]


def is_code_file(path: str) -> bool:
    return Path(path).suffix.lower() in CODE_SUFFIXES


def is_ui_file(path: str) -> bool:
    return Path(path).suffix.lower() in UI_SUFFIXES


def stop_message(files: list[str], transcript: str) -> str | None:
    code_files = [path for path in files if is_code_file(path)]
    if not code_files:
        return None
    problems: list[str] = []
    if not VALIDATION_RE.search(transcript):
        problems.append("code changes exist but no validation evidence was found; run /guard-verify before claiming completion")
    if any(is_ui_file(path) for path in code_files) and not VISUAL_RE.search(transcript):
        problems.append("UI files changed but no visual/screenshot/overflow evidence was found")
    if not problems:
        return None
    return (
        "Stop check advisory: "
        + "; ".join(problems)
        + f". Changed files: {', '.join(code_files[:12])}."
    )


def main() -> int:
    root = project_root()
    hook_input = load_input()
    message = stop_message(changed_files(root), transcript_text(hook_input.get("transcript_path")))
    sys.stdout.write(json.dumps({"systemMessage": message} if message else suppress(), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""garden_check.py — 跨 agent harness 的漂移 / 死链统一检测（只读）。

把已碎成多个脚本的检测聚合成单一入口，并补 3 个盲区：
  ① submodule：index 的 gitlink ↔ .gitmodules 声明 双向对账（抓孤儿 / 缺失 gitlink）
  ② agent-assets 软链悬挂（CI 安全：全缺 = 未安装 skip，部分缺 / mismatch = 漂移 fail）
  ③ AGENTS.md 路由表里「全前缀 slug」→ 实际 skill / command 死路由

刻意不做 wshobson 式 generate-all：本仓库是 symlink 单源，无产物可生成，照搬即 cargo-cult。

退出码：发现任一 DRIFT 返回 1；干净返回 0；SKIP（neutral）不计 fail。
解析逻辑拆成纯函数（parse_* / find_dead_routes / classify_symlinks），由 scripts/tests 用 fixtures 锚定。
"""
from __future__ import annotations

import argparse
import json as _json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"

# import 复用 install_hooks 的软链定义与状态判定（单源，不 shell-out 重复实现）
sys.path.insert(0, str(SCRIPTS))
try:  # pragma: no cover - import 兜底
    from install_hooks import agent_asset_links, link_status
except Exception:
    agent_asset_links = None  # type: ignore[assignment]
    link_status = None  # type: ignore[assignment]

LEVEL_OK = "OK"
LEVEL_SKIP = "SKIP"
LEVEL_DRIFT = "DRIFT"

# AGENTS.md 里无歧义的「全前缀 slug」。只匹配带前缀的完整 slug，
# 不碰 survey/unstuck 这类裸别名 —— 宁可漏检也不误报死路由（见模块末 LIMITATIONS）。
SLUG_RE = re.compile(r"\b(?:think|dev|guard|readable|assist|fe|web|agent|write)-[a-z0-9-]+\b")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    evidence: str = ""


# ---------- 纯解析函数（fixtures 可锚定，无副作用） ----------
def parse_index_gitlinks(ls_files_s_output: str) -> set[str]:
    """从 `git ls-files -s` 输出抽 gitlink（mode 160000）的 path。"""
    paths: set[str] = set()
    for line in ls_files_s_output.splitlines():
        if not line or "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        if meta.split(" ", 1)[0] == "160000":
            paths.add(path.strip())
    return paths


def parse_gitmodules_paths(config_output: str) -> set[str]:
    """从 `git config -f .gitmodules --get-regexp '\\.path$'` 输出抽 path。"""
    paths: set[str] = set()
    for line in config_output.splitlines():
        if " " in line:
            paths.add(line.split(" ", 1)[1].strip())
    return paths


def find_dead_routes(agents_md_text: str, known: set[str]) -> dict[str, int]:
    """返回 {死路由 slug: 首次出现行号}。只看带前缀的完整 slug。

    跳过家族 glob 写法（如 `guard-write-*` / `think-*`）：紧跟 `*` 或 `-*` 的 slug 是
    家族通配而非字面 skill 名，否则会把 `guard-write-*` 误截成不存在的 `guard-write`。
    """
    dead: dict[str, int] = {}
    for lineno, line in enumerate(agents_md_text.splitlines(), 1):
        for match in SLUG_RE.finditer(line):
            slug = match.group(0)
            trailing = line[match.end():match.end() + 2]
            if trailing[:1] == "*" or trailing[:2] == "-*":
                continue  # 家族 glob，非字面 slug
            if slug not in known and slug not in dead:
                dead[slug] = lineno
    return dead


def classify_symlinks(statuses: list[tuple[str, str, str]]) -> tuple[list[tuple[str, str, str]], bool]:
    """输入 [(link, target, status)]，返回 (非 ok 的列表, 是否全部缺失)。

    全部缺失 → 视为「未安装」（CI 无 HOME 软链的正常态），调用方据此降级为 SKIP。
    """
    bad = [s for s in statuses if s[2] != "ok"]
    all_missing = bool(statuses) and all(s[2] == "missing" for s in statuses)
    return bad, all_missing


# ---------- 已知 slug 集合（skill / command / capsule / subagent） ----------
def known_slugs() -> set[str]:
    names: set[str] = set()
    for base in ("coding-skills", "writing-skills"):
        directory = REPO / base
        if directory.is_dir():
            for child in directory.iterdir():
                if child.is_dir() and not child.name.startswith("_"):
                    names.add(child.name)
    for base in ("commands",):
        directory = REPO / base
        if directory.is_dir():
            for child in directory.iterdir():
                if child.suffix == ".md":
                    names.add(child.stem)
    # capsule / subagent 名字也带前缀（如 agent-discipline / security-fp-judge），纳入避免误报
    capsules = REPO / "agents" / "context-capsules"
    if capsules.is_dir():
        names.update(p.stem for p in capsules.glob("*.md"))
    for agent_dir in (REPO / "coding-agents").glob("*"):
        if agent_dir.is_dir():
            names.update(p.stem for p in agent_dir.glob("*.md"))
    return names


# ---------- 三个盲区检测 ----------
def _git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return result.stdout


def check_submodules() -> list[Finding]:
    index_paths = parse_index_gitlinks(_git(["ls-files", "-s"]))
    config_paths = parse_gitmodules_paths(
        _git(["config", "-f", ".gitmodules", "--get-regexp", r"\.path$"])
    )
    out: list[Finding] = []
    for path in sorted(index_paths - config_paths):
        out.append(Finding(
            LEVEL_DRIFT, "ORPHAN-GITLINK",
            f"index 有 gitlink 但 .gitmodules 无声明: {path}",
            evidence=f"git ls-files -s :: {path}  (修复: git rm --cached {path})",
        ))
    for path in sorted(config_paths - index_paths):
        out.append(Finding(
            LEVEL_DRIFT, "MISSING-GITLINK",
            f".gitmodules 声明但 index 无 gitlink: {path}", evidence=".gitmodules",
        ))
    if not out:
        out.append(Finding(
            LEVEL_OK, "SUBMODULES",
            f"{len(index_paths)} gitlink ↔ {len(config_paths)} .gitmodules 一致",
        ))
    return out


def check_symlinks(skip: bool = False) -> list[Finding]:
    if skip or agent_asset_links is None or link_status is None:
        reason = "--skip-symlinks" if skip else "install_hooks 不可导入"
        return [Finding(LEVEL_SKIP, "SYMLINKS", f"跳过软链检测（{reason}）")]
    links = list(agent_asset_links())
    statuses = [(str(link), str(target), link_status(link, target)) for link, target in links]
    bad, all_missing = classify_symlinks(statuses)
    if all_missing:
        return [Finding(
            LEVEL_SKIP, "SYMLINKS-NOT-INSTALLED",
            f"全部 {len(statuses)} 条 agent-assets 软链缺失 → 判定为未安装（非漂移）",
            evidence="install_hooks.agent_asset_links",
        )]
    if not bad:
        return [Finding(LEVEL_OK, "SYMLINKS", f"{len(statuses)} 条 agent-assets 软链全部 ok")]
    return [
        Finding(LEVEL_DRIFT, f"SYMLINK-{status.upper()}", f"{status}: {link} -> {target}",
                evidence="python3 scripts/install_hooks.py --target agent-assets --check")
        for link, target, status in bad
    ]


def check_routing() -> list[Finding]:
    agents_md = REPO / "agents" / "AGENTS.md"
    if not agents_md.exists():
        return [Finding(LEVEL_SKIP, "ROUTING", "agents/AGENTS.md 不存在")]
    known = known_slugs()
    dead = find_dead_routes(agents_md.read_text(encoding="utf-8"), known)
    if not dead:
        return [Finding(
            LEVEL_OK, "ROUTING",
            f"AGENTS.md 全前缀 slug 全部命中已知条目（已知 {len(known)} 个）",
        )]
    return [
        Finding(LEVEL_DRIFT, "DEAD-ROUTE",
                f"AGENTS.md 引用了不存在的 skill/command: {slug}",
                evidence=f"agents/AGENTS.md:{lineno}")
        for slug, lineno in sorted(dead.items(), key=lambda kv: kv[1])
    ]


# ---------- 聚合既有校验器 ----------
def run_aggregated() -> list[Finding]:
    out: list[Finding] = []
    for name in ("verify_skills.py", "verify_agents.py"):
        script = SCRIPTS / name
        if not script.exists():
            continue
        result = subprocess.run([sys.executable, str(script)], cwd=REPO, capture_output=True, text=True)
        if result.returncode == 0:
            out.append(Finding(LEVEL_OK, name, "通过"))
        else:
            tail = (result.stdout + result.stderr).strip().splitlines()
            out.append(Finding(
                LEVEL_DRIFT, name, f"失败: {tail[-1] if tail else f'exit {result.returncode}'}",
                evidence=f"python3 scripts/{name}",
            ))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="跨 agent harness 漂移 / 死链统一检测（只读）")
    parser.add_argument("--skip-symlinks", action="store_true",
                        help="跳过 agent-assets 软链检测（CI / 无 HOME 软链时）")
    parser.add_argument("--no-aggregate", action="store_true",
                        help="只跑 3 个新盲区，不跑 verify_skills / verify_agents")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args(argv)

    sections: list[tuple[str, list[Finding]]] = [
        ("submodules", check_submodules()),
        ("symlinks", check_symlinks(skip=args.skip_symlinks)),
        ("routing", check_routing()),
    ]
    if not args.no_aggregate:
        sections.append(("aggregated", run_aggregated()))

    drift = [f for _, fs in sections for f in fs if f.level == LEVEL_DRIFT]

    if args.json:
        print(_json.dumps({
            "drift": len(drift),
            "findings": [
                {"section": section, "level": f.level, "code": f.code,
                 "message": f.message, "evidence": f.evidence}
                for section, fs in sections for f in fs
            ],
        }, ensure_ascii=False, indent=2))
        return 1 if drift else 0

    icon = {LEVEL_OK: "✓", LEVEL_SKIP: "–", LEVEL_DRIFT: "✗"}
    for section, fs in sections:
        print(f"\n[{section}]")
        for f in fs:
            print(f"  {icon.get(f.level, '?')} {f.code}: {f.message}")
            if f.evidence and f.level == LEVEL_DRIFT:
                print(f"      ↳ {f.evidence}")
    print()
    if drift:
        print(f"GARDEN: {len(drift)} drift finding(s) ✗")
        return 1
    print("GARDEN: clean ✓")
    return 0


# LIMITATIONS（v1，刻意保守，宁漏勿误报）：
# - 路由对账只查带前缀的完整 slug；AGENTS.md 里 survey/unstuck/review 这类裸别名暂不核（需 alias→family fixture，后续加）。
# - submodule 对账只做 config↔index（无网络），不校 SHA / 初始化状态：CI 浅克隆会误报，留给本地全克隆另跑。
if __name__ == "__main__":
    sys.exit(main())

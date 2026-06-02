#!/usr/bin/env python3
"""校验 writing-skills/ 体系：catalog 完整性、命名、触发前缀、孤儿目录、_shared 豁免。

与 scripts/verify_skills.py 平行，但只管 writing-skills/。写作 hook/skill 隔离，不进编程 agent。

用法：
    python3 writing-hooks/verify_writing.py [repo_root]

repo_root 默认为本脚本上一级（即 ~/.dotfiles）。校验 <repo_root>/writing-skills/catalog.json。
失败打印诊断并 exit 1；通过 exit 0。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ALLOWED_DOMAINS = {"write", "guard", "assist", "readable"}
ALLOWED_ROLES = {"canonical", "brand-exception"}
NAME_CASE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TRIGGER_PREFIXES = ("当", "用于", "Use when ", "Invoke when ")
# catalog 不登记、孤儿检查豁免的目录段（以 . 开头的隐藏目录天然豁免）
EXEMPT_TOP = {"_shared"}


class ValidationError(Exception):
    pass


def fail(msg: str) -> None:
    raise ValidationError(msg)


def skills_root(repo_root: Path) -> Path:
    return repo_root / "writing-skills"


def read_description(skill_md: Path) -> str:
    """从 SKILL.md frontmatter 读 description（简单逐行解析，够用）。"""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return ""
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return ""
    for line in lines[1:end]:
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def load_catalog(root: Path) -> list[dict]:
    catalog_path = root / "catalog.json"
    if not catalog_path.exists():
        fail(f"MISSING CATALOG: {catalog_path}")
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    skills = payload.get("skills")
    if not isinstance(skills, list) or not skills:
        fail("INVALID CATALOG: skills must be a non-empty list")
    return skills


def validate(repo_root: Path) -> int:
    root = skills_root(repo_root)
    skills = load_catalog(root)

    seen_names: set[str] = set()
    seen_paths: set[Path] = set()
    registered_dirs: set[Path] = set()

    for entry in skills:
        if not isinstance(entry, dict):
            fail("INVALID CATALOG: every entry must be an object")
        name = entry.get("name")
        raw_path = entry.get("path")
        domain = entry.get("domain")
        role = entry.get("role")

        if not isinstance(name, str) or not NAME_CASE.fullmatch(name):
            fail(f"NAME CASE: {name!r} 必须是 hyphen-case")
        if not isinstance(raw_path, str) or not raw_path:
            fail(f"INVALID CATALOG: {name} path 必须是非空字符串")
        if domain not in ALLOWED_DOMAINS:
            fail(f"INVALID DOMAIN: {name} domain={domain!r}（允许 {sorted(ALLOWED_DOMAINS)}）")
        if role not in ALLOWED_ROLES:
            fail(f"INVALID ROLE: {name} role={role!r}（允许 {sorted(ALLOWED_ROLES)}）")
        if role == "canonical" and not name.startswith(f"{domain}-"):
            fail(f"CANONICAL PREFIX MISMATCH: {name} 应以 {domain}- 开头")

        if name in seen_names:
            fail(f"DUPLICATE NAME: {name}")
        seen_names.add(name)

        path = repo_root / raw_path
        if path in seen_paths:
            fail(f"DUPLICATE PATH: {raw_path}")
        seen_paths.add(path)

        if path.is_symlink() and not path.resolve().is_relative_to(repo_root):
            fail(f"PATH ESCAPES REPO: {name} path={raw_path}")
        if not path.exists():
            fail(f"MISSING PATH: {raw_path}")
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            fail(f"MISSING SKILL FILE: {raw_path}/SKILL.md")
        registered_dirs.add(path.resolve())

        description = read_description(skill_md)
        if not description:
            fail(f"MISSING DESCRIPTION: {name} SKILL.md frontmatter 无 description")
        if not any(description.startswith(p) for p in TRIGGER_PREFIXES):
            allowed = " / ".join(repr(p) for p in TRIGGER_PREFIXES)
            fail(
                f"DESCRIPTION TRIGGER PREFIX VIOLATION: {name} description 须以 {allowed} 之一开头；"
                f"got: {description!r}"
            )

    # 反向对账：writing-skills 下任何 SKILL.md 都必须在 catalog 注册（_shared/ 与隐藏目录豁免）
    orphans: list[str] = []
    for skill_md in root.rglob("SKILL.md"):
        rel = skill_md.parent.relative_to(root)
        if rel.parts and (rel.parts[0] in EXEMPT_TOP or any(p.startswith(".") for p in rel.parts)):
            continue
        if skill_md.parent.resolve() not in registered_dirs:
            orphans.append(str(skill_md.parent.relative_to(repo_root)))
    if orphans:
        fail("ORPHAN SKILL: " + ", ".join(sorted(orphans)) + "（有 SKILL.md 但未在 catalog.json 注册）")

    print(f"validated {len(skills)} writing skills")
    return 0


def main() -> int:
    repo_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    try:
        return validate(repo_root)
    except ValidationError as exc:
        sys.stderr.write(f"WRITING SKILLS CHECK FAILED: {exc}\n")
        return 1
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"WRITING SKILLS CHECK FAILED: invalid catalog JSON: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

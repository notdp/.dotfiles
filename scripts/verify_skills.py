#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_DOMAINS = {"think", "dev", "guard", "assist", "readable", "fe", "web", "ui", "agent", "team"}
ALLOWED_ROLES = {"canonical", "legacy", "brand-exception"}
BRAND_EXCEPTIONS = {"hive", "agent-browser", "react-doctor"}
REFERENCE_PATTERN = re.compile(
    r"(?<![/.])\b(?:refs|references|examples|scripts|agents|templates)/[\w./-]+\b"
)
BOUNDARY_REFERENCE_PATTERN = re.compile(r"与\s*/?([a-z]+-[a-z0-9-]+)\s*(?:的)?区别")
WORKFLOW_QUALITY_TERMS = (
    "证据",
    "验收",
    "验证",
    "停止",
    "退出",
    "风险",
    "禁止",
    "Gotchas",
    "Evidence",
    "Acceptance",
    "Verification",
    "Stop",
    "Exit",
    "Risk",
    "Escalate",
)
WORKFLOW_QUALITY_LINE_THRESHOLD = 80
TRIGGER_PREFIXES = (
    "Use when ",
    "Invoke when ",
    "用于",
    "当",
)


class ValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillEntry:
    name: str
    path: Path
    domain: str
    role: str
    migration: dict[str, Any] | None
    trigger_exempt: bool


@dataclass(frozen=True)
class ValidationContext:
    repo_root: Path

    @property
    def skills_root(self) -> Path:
        return self.repo_root / "skills"

    @property
    def catalog_path(self) -> Path:
        return self.skills_root / "catalog.json"


def fail(message: str) -> None:
    raise ValidationError(message)


def load_catalog(context: ValidationContext) -> list[SkillEntry]:
    if not context.catalog_path.exists():
        fail(f"MISSING CATALOG: {context.catalog_path}")

    payload = json.loads(context.catalog_path.read_text())
    skills = payload.get("skills")
    if not isinstance(skills, list) or not skills:
        fail("INVALID CATALOG: skills must be a non-empty list")

    entries: list[SkillEntry] = []
    seen_names: set[str] = set()
    seen_paths: set[Path] = set()
    planned_canonicals: set[str] = set()
    roles_by_name: dict[str, str] = {}

    for raw_entry in skills:
        if not isinstance(raw_entry, dict):
            fail("INVALID CATALOG: every skill entry must be an object")

        name = raw_entry.get("name")
        raw_path = raw_entry.get("path")
        domain = raw_entry.get("domain")
        role = raw_entry.get("role")
        migration = raw_entry.get("migration")
        trigger_exempt = bool(raw_entry.get("trigger-exempt", False))

        if not isinstance(name, str) or not name:
            fail("INVALID CATALOG: skill name must be a non-empty string")
        if not isinstance(raw_path, str) or not raw_path:
            fail(f"INVALID CATALOG: {name} path must be a non-empty string")
        if not isinstance(domain, str) or domain not in ALLOWED_DOMAINS:
            fail(f"INVALID DOMAIN: {name} domain={domain!r}")
        if role not in ALLOWED_ROLES:
            fail(f"INVALID ROLE: {name} role={role!r}")

        path = context.repo_root / raw_path
        if name in seen_names:
            fail(f"DUPLICATE NAME: {name}")
        if path in seen_paths:
            fail(f"DUPLICATE PATH: {raw_path}")
        if path.is_symlink() and not path.resolve().is_relative_to(context.repo_root):
            fail(f"PATH ESCAPES REPO: {name} path={raw_path}")
        if not path.exists():
            fail(f"MISSING PATH: {raw_path}")
        if not (path / "SKILL.md").exists():
            fail(f"MISSING SKILL FILE: {raw_path}/SKILL.md")

        if role == "canonical":
            expected_prefix = f"{domain}-"
            if not name.startswith(expected_prefix):
                fail(f"CANONICAL PREFIX MISMATCH: {name} should start with {expected_prefix}")
            if migration is not None:
                fail(f"CANONICAL MIGRATION FORBIDDEN: {name}")
        elif role == "legacy":
            if not isinstance(migration, dict):
                fail(f"MISSING MIGRATION: {name}")
            state = migration.get("state")
            if state not in {"planned", "deferred"}:
                fail(f"INVALID MIGRATION STATE: {name} state={state!r}")
            canonical = migration.get("canonical")
            if state == "planned":
                if not isinstance(canonical, str) or not canonical:
                    fail(f"MISSING FUTURE CANONICAL: {name}")
                if not canonical.startswith(f"{domain}-"):
                    fail(f"FUTURE CANONICAL PREFIX MISMATCH: {name} -> {canonical}")
                if canonical in planned_canonicals:
                    fail(f"DUPLICATE FUTURE CANONICAL: {canonical}")
                planned_canonicals.add(canonical)
            elif canonical is not None:
                fail(f"DEFERRED MIGRATION MUST OMIT CANONICAL: {name}")
        else:
            if name not in BRAND_EXCEPTIONS:
                fail(f"UNKNOWN BRAND EXCEPTION: {name}")
            if migration is not None:
                fail(f"BRAND EXCEPTION MIGRATION FORBIDDEN: {name}")

        entries.append(
            SkillEntry(
                name=name,
                path=path,
                domain=domain,
                role=role,
                migration=migration,
                trigger_exempt=trigger_exempt,
            )
        )
        seen_names.add(name)
        seen_paths.add(path)
        roles_by_name[name] = role

    for entry in entries:
        if entry.role != "legacy" or not entry.migration or entry.migration.get("state") != "planned":
            continue
        canonical = entry.migration["canonical"]
        if canonical not in seen_names:
            fail(f"UNKNOWN FUTURE CANONICAL: {entry.name} -> {canonical}")
        if roles_by_name[canonical] != "canonical":
            fail(f"FUTURE CANONICAL ROLE MISMATCH: {entry.name} -> {canonical}")

    return entries


def parse_frontmatter(skill_file: Path) -> dict[str, str]:
    lines = skill_file.read_text().splitlines()
    if not lines or lines[0] != "---":
        fail(f"INVALID FRONTMATTER: {skill_file}")

    try:
        end_index = lines.index("---", 1)
    except ValueError as exc:
        raise ValidationError(f"MISSING FRONTMATTER END: {skill_file}") from exc

    fields: dict[str, str] = {}
    for line in lines[1:end_index]:
        if line.startswith("name:"):
            fields["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            fields["description"] = line.split(":", 1)[1].strip()

    if not fields.get("name"):
        fail(f"MISSING FRONTMATTER NAME: {skill_file}")
    if not fields.get("description"):
        fail(f"MISSING FRONTMATTER DESCRIPTION: {skill_file}")
    return fields


def collect_references(skill_file: Path) -> set[str]:
    content = skill_file.read_text()
    return set(REFERENCE_PATTERN.findall(content))


def collect_boundary_references(content: str) -> set[str]:
    return set(BOUNDARY_REFERENCE_PATTERN.findall(content))


def content_without_frontmatter(skill_file: Path) -> str:
    lines = skill_file.read_text().splitlines()
    if not lines or lines[0] != "---":
        fail(f"INVALID FRONTMATTER: {skill_file}")

    try:
        end_index = lines.index("---", 1)
    except ValueError as exc:
        raise ValidationError(f"MISSING FRONTMATTER END: {skill_file}") from exc

    return "\n".join(lines[end_index + 1 :])


def is_trigger_exempt(entry: SkillEntry) -> bool:
    # brand-exception skills 默认豁免，其它 skill 通过 trigger-exempt 显式豁免
    return entry.role == "brand-exception" or entry.trigger_exempt


def validate_trigger_prefix(entry: SkillEntry, description: str) -> None:
    if is_trigger_exempt(entry):
        return
    if not any(description.startswith(prefix) for prefix in TRIGGER_PREFIXES):
        allowed = "\n  - ".join(repr(p) for p in TRIGGER_PREFIXES)
        fail(
            f"DESCRIPTION TRIGGER PREFIX VIOLATION: {entry.name} description must start with one of:\n  - {allowed}\n"
            f"got: {description!r}"
        )


def validate_workflow_quality(entry: SkillEntry, skill_file: Path, content: str) -> None:
    if is_trigger_exempt(entry):
        return

    non_empty_lines = [line for line in content.splitlines() if line.strip()]
    if len(non_empty_lines) < WORKFLOW_QUALITY_LINE_THRESHOLD:
        return

    headings = [
        line.strip()
        for line in content.splitlines()
        if line.lstrip().startswith("#")
    ]
    if any(term in heading for heading in headings for term in WORKFLOW_QUALITY_TERMS):
        return

    fail(
        f"WORKFLOW QUALITY VIOLATION: {entry.name} has {len(non_empty_lines)} non-empty lines "
        f"but no quality gate heading in {skill_file}. Add evidence/acceptance/stop/risk/gotchas guidance "
        "or move mechanical detail into refs/."
    )


def validate_boundary_references(entry: SkillEntry, content: str, skill_names: set[str]) -> None:
    for reference in sorted(collect_boundary_references(content)):
        if reference not in skill_names:
            fail(f"UNKNOWN SKILL BOUNDARY: {entry.name} references {reference}")


def resolve_reference(entry: SkillEntry, context: ValidationContext, relative_path: str) -> Path | None:
    """尝试按 skill-local，再按 repo-root 解析引用；任一存在就返回该 Path。"""
    local = entry.path / relative_path
    if local.exists():
        return local
    repo_root_candidate = context.repo_root / relative_path
    if repo_root_candidate.exists():
        return repo_root_candidate
    return None


def validate_executable_bit(skill_file: Path, resolved: Path) -> None:
    # 仓库根的可执行脚本（scripts/*.sh、scripts/*.py）必须带执行位
    if resolved.suffix not in {".sh", ".py"}:
        return
    if not resolved.name:
        return
    # 仅对 repo-root scripts/ 下的脚本校验
    parts = resolved.parts
    if "scripts" not in parts:
        return
    if not resolved.stat().st_mode & 0o111:
        fail(
            f"SCRIPT NOT EXECUTABLE: {skill_file} -> {resolved} (chmod +x required)"
        )


def validate_skill_entry(context: ValidationContext, entry: SkillEntry, skill_names: set[str]) -> None:
    skill_file = entry.path / "SKILL.md"
    frontmatter = parse_frontmatter(skill_file)
    content = content_without_frontmatter(skill_file)
    if frontmatter["name"] != entry.name:
        fail(
            f"NAME MISMATCH: catalog={entry.name} frontmatter={frontmatter['name']} file={skill_file}"
        )

    validate_trigger_prefix(entry, frontmatter["description"])
    validate_workflow_quality(entry, skill_file, content)
    validate_boundary_references(entry, frontmatter["description"] + "\n" + content, skill_names)

    for relative_path in sorted(collect_references(skill_file)):
        resolved = resolve_reference(entry, context, relative_path)
        if resolved is None:
            fail(f"BROKEN REFERENCE: {skill_file} -> {relative_path}")
        validate_executable_bit(skill_file, resolved)


def main() -> int:
    try:
        repo_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
        context = ValidationContext(repo_root=repo_root)
        entries = load_catalog(context)
        skill_names = {entry.name for entry in entries}
        for entry in entries:
            validate_skill_entry(context, entry, skill_names)
            print(f"ok: {entry.name} -> {entry.path.relative_to(context.repo_root)}")
        print(f"validated {len(entries)} skills")
    except ValidationError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

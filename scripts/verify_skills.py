#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_DOMAINS = {"think", "dev", "guard", "assist", "readable", "fe", "web", "ui", "agent", "team", "workflow"}
ALLOWED_ROLES = {"canonical", "legacy", "brand-exception"}
BRAND_EXCEPTIONS = {"hive", "agent-browser", "react-doctor"}
REFERENCE_PATTERN = re.compile(
    r"(?<![/.])\b(?:refs|references|examples|scripts|agents|templates)/[\w./-]+\b"
)
BOUNDARY_REFERENCE_PATTERN = re.compile(r"与\s*/?([a-z]+-[a-z0-9-]+)\s*(?:的)?区别")
RISK_PATTERNS = {
    "secrets": re.compile(
        r"\b(?:read|collect|use|access|load|store|write)\b.{0,60}\b(?:api[-_ ]?keys?|secrets?|tokens?|env(?:ironment)?(?: vars?)?)\b"
        r"|\b(?:api[-_ ]?keys?|secrets?|tokens?)\b.{0,60}\b(?:from env|environment variables?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "network": re.compile(
        r"\b(?:call|query|fetch|request|send|download|upload|scrape|access)\b.{0,60}\b(?:https?|rest api|api|webhooks?)\b"
        r"|\b(?:curl|requests\.\w+|fetch\()\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "data-side-effects": re.compile(
        r"\b(?:write|modify|delete|migrate|backfill|apply|overwrite)\b.{0,60}\b(?:databases?|migrations?|files?|data|records?|results?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "medical-clinical-lab": re.compile(
        r"\b(?:generate|process|analyze|handle|write|create)\b.{0,60}\b(?:clinical|medical|patient|laboratory|lab automation|hipaa|treatment)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "offensive-dual-use": re.compile(
        r"\b(?:exploit|exploitation|c2|command[- ]and[- ]control|phishing|credential(?: dumping| theft| access)?|lateral movement|brute[- ]?force|red team|penetration test|pentest|scan external target)\b",
        re.IGNORECASE | re.DOTALL,
    ),
}
GUARDRAIL_ANCHOR_PATTERN = re.compile(
    r"(/guard-secure|/guard-gitops|guardrail|guardrails|risk|risks|authorization|authorized|scope|scope-bound|风险|授权|范围|护栏|边界)",
    re.IGNORECASE,
)
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
METHODOLOGY_DOMAINS = ALLOWED_DOMAINS
METHODOLOGY_HEADING_PATTERN = re.compile(r"(思维框架|方法论|评估模型|Ambiguity Score|核心循环)", re.IGNORECASE)
METHODOLOGY_HOW_TABLE_PATTERN = re.compile(r"\|.*核心动作.*\|")
METHODOLOGY_WHY_TERMS = (
    "为什么",
    "原因",
    "目的",
    "价值",
    "避免",
    "防止",
    "防什么",
    "偏差",
    "失败模式",
    "代价",
    "rationale",
    "Rationale",
    "Why",
    "why",
)
VAGUE_CONDITIONAL_WORDS: tuple[str, ...] = (
    "必要时",
    "适当",
    "如需",
    "如果需要",
    "视情况",
    "可能的话",
    "灵活",
)
CONCRETE_CONDITION_PATTERN = re.compile(
    r"/[a-z][-a-z0-9]+"           # skill reference
    r"|\d+\s*[%秒次个件条步层]"     # numeric threshold with unit
    r"|[<>≥≤=]\s*\d+"             # comparison operator with digits
    r"|\.\w{1,5}\b"              # file extension (.py, .sh, .md, .json)
    r"|当.{1,40}时"               # trigger clause 当...时
    r"|若.{1,40}则"               # trigger clause 若...则
    r"|超过"                      # threshold keyword
    r"|exit code"                 # exit code
    r"|`.+?`"                    # backtick-wrapped content
)


NAME_CASE_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# 机器特定的 user-home 绝对路径（非可移植）。匿名占位 /Users/.../ 因首字符为 '.' 不匹配。
MACHINE_PATH_PATTERN = re.compile(r"/(?:Users|home)/[A-Za-z0-9][\w.-]*/")
BODY_LENGTH_WARN_THRESHOLD = 400


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
        return self.repo_root / "coding-skills"

    @property
    def catalog_path(self) -> Path:
        return self.skills_root / "catalog.json"


@dataclass(frozen=True)
class MarkdownSection:
    heading: str
    line_number: int
    lines: list[str]


@dataclass(frozen=True)
class AssetValidationSummary:
    agents: int = 0
    commands: int = 0
    plugin_manifests: int = 0


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
        if not NAME_CASE_PATTERN.fullmatch(name):
            fail(f"NAME CASE: {name} 必须是 hyphen-case（小写字母/数字，连字符分隔）")
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


def parse_markdown_frontmatter(markdown_file: Path) -> dict[str, Any]:
    lines = markdown_file.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0] != "---":
        fail(f"INVALID FRONTMATTER: {markdown_file}")

    try:
        end_index = lines.index("---", 1)
    except ValueError as exc:
        raise ValidationError(f"MISSING FRONTMATTER END: {markdown_file}") from exc

    fields: dict[str, Any] = {}
    current_key: str | None = None
    for line in lines[1:end_index]:
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")) and ":" in line:
            key, raw_value = line.split(":", 1)
            key = key.strip()
            value = raw_value.strip()
            fields[key] = value if value else {}
            current_key = key
            continue
        if current_key and isinstance(fields.get(current_key), dict) and ":" in line:
            key, raw_value = line.split(":", 1)
            fields[current_key][key.strip()] = raw_value.strip()
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


def iter_top_level_sections(content: str) -> list[MarkdownSection]:
    sections: list[MarkdownSection] = []
    current_heading = "<root>"
    current_line_number = 1
    current_lines: list[str] = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        if line.startswith("## ") and not line.startswith("### "):
            if current_lines:
                sections.append(
                    MarkdownSection(
                        heading=current_heading,
                        line_number=current_line_number,
                        lines=current_lines,
                    )
                )
            current_heading = line.strip()
            current_line_number = line_number
            current_lines = [line]
            continue
        current_lines.append(line)

    if current_lines:
        sections.append(
            MarkdownSection(
                heading=current_heading,
                line_number=current_line_number,
                lines=current_lines,
            )
        )
    return sections


def has_why_rationale(lines: list[str]) -> bool:
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not stripped or stripped.startswith("|"):
            continue
        if any(term in stripped for term in METHODOLOGY_WHY_TERMS):
            return True
    return False


def validate_methodology_why(entry: SkillEntry, skill_file: Path, content: str) -> None:
    if is_trigger_exempt(entry) or entry.domain not in METHODOLOGY_DOMAINS:
        return

    for section in iter_top_level_sections(content):
        heading_matches = bool(METHODOLOGY_HEADING_PATTERN.search(section.heading))
        table_header_indexes = [
            index
            for index, line in enumerate(section.lines)
            if METHODOLOGY_HOW_TABLE_PATTERN.search(line)
        ]
        if not heading_matches and not table_header_indexes:
            continue

        for table_index in table_header_indexes:
            table_header = section.lines[table_index]
            if any(term in table_header for term in METHODOLOGY_WHY_TERMS):
                continue
            if has_why_rationale(section.lines[:table_index]):
                continue
            fail(
                f"METHODOLOGY WHY VIOLATION: {entry.name} section {section.heading!r} "
                f"in {skill_file}:{section.line_number} has a methodology table with '核心动作' "
                "but no why/rationale. Add a why paragraph before the table or a column such as "
                "'为什么 / 防什么偏差'."
            )

        if heading_matches and not table_header_indexes and not has_why_rationale(section.lines[:12]):
            fail(
                f"METHODOLOGY WHY VIOLATION: {entry.name} section {section.heading!r} "
                f"in {skill_file}:{section.line_number} describes a thinking model without why/rationale. "
                "Explain what failure mode, bias, or cost this model is meant to avoid."
            )


def _is_output_format_heading(heading: str) -> bool:
    return any(term in heading for term in ("输出格式", "Output Format", "输出"))


def collect_vague_conditional_warnings(entry: SkillEntry, skill_file: Path, content: str) -> list[str]:
    if is_trigger_exempt(entry):
        return []

    lines = content.splitlines()
    warnings: list[str] = []
    in_code_block = False
    in_output_section = False

    for line_number_0, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if stripped.startswith("## "):
            in_output_section = _is_output_format_heading(stripped)
            continue
        if in_output_section:
            continue

        for word in VAGUE_CONDITIONAL_WORDS:
            if word not in stripped:
                continue
            # "适当" preceded by "不" is fine ("不适当")
            if word == "适当":
                idx = stripped.find(word)
                if idx > 0 and stripped[idx - 1] == "不":
                    continue

            # Check same line for concrete condition
            if CONCRETE_CONDITION_PATTERN.search(stripped):
                continue

            # Check next non-empty, non-heading line
            found_concrete = False
            for next_line in lines[line_number_0 + 1 :]:
                next_stripped = next_line.strip()
                if not next_stripped:
                    continue
                if next_stripped.startswith("#"):
                    break
                if CONCRETE_CONDITION_PATTERN.search(next_stripped):
                    found_concrete = True
                break
            if found_concrete:
                continue

            # frontmatter occupies lines before content; approximate the file line number
            # by adding 1 (content starts after frontmatter end marker)
            warnings.append(
                f"VAGUE CONDITIONAL WARNING: {entry.name} uses '{word}' "
                f"at {skill_file}:{line_number_0 + 1} without adjacent concrete condition"
            )

    return warnings


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


def collect_high_risk_capability_warnings(entry: SkillEntry, text: str) -> list[str]:
    categories = [
        category
        for category, pattern in RISK_PATTERNS.items()
        if pattern.search(text)
    ]
    if not categories:
        return []
    warnings = [
        f"RISK WARNING: {entry.name} declares high-risk capability categories: "
        + ", ".join(categories)
    ]
    if not GUARDRAIL_ANCHOR_PATTERN.search(text):
        warnings.append(
            f"GUARDRAIL WARNING: {entry.name} declares high-risk capabilities without "
            "risk/authorization guardrails; add a Risk/Guardrails section or route through "
            "/guard-secure and /guard-gitops."
        )
    return warnings


def validate_skill_entry(context: ValidationContext, entry: SkillEntry, skill_names: set[str]) -> list[str]:
    skill_file = entry.path / "SKILL.md"
    frontmatter = parse_frontmatter(skill_file)
    content = content_without_frontmatter(skill_file)
    if frontmatter["name"] != entry.name:
        fail(
            f"NAME MISMATCH: catalog={entry.name} frontmatter={frontmatter['name']} file={skill_file}"
        )

    validate_trigger_prefix(entry, frontmatter["description"])
    validate_workflow_quality(entry, skill_file, content)
    validate_methodology_why(entry, skill_file, content)
    full_text = frontmatter["description"] + "\n" + content
    validate_boundary_references(entry, full_text, skill_names)
    validate_no_machine_paths(skill_file, full_text)

    for relative_path in sorted(collect_references(skill_file)):
        resolved = resolve_reference(entry, context, relative_path)
        if resolved is None:
            fail(f"BROKEN REFERENCE: {skill_file} -> {relative_path}")
        validate_executable_bit(skill_file, resolved)
    warnings = collect_high_risk_capability_warnings(entry, full_text)
    warnings.extend(collect_vague_conditional_warnings(entry, skill_file, content))
    warnings.extend(collect_body_length_warning(entry, skill_file))
    return warnings


def validate_no_machine_paths(skill_file: Path, text: str) -> None:
    """禁止机器特定 user-home 绝对路径（不可移植、泄漏作者机器名）。

    匿名占位写法 `/Users/.../` 或 `/Users/<you>/` 不匹配；用这些代替具体用户名。
    """
    match = MACHINE_PATH_PATTERN.search(text)
    if match:
        fail(
            f"MACHINE PATH: {skill_file} 含机器特定绝对路径 {match.group(0)!r}"
            "（改用 ~/ 或 /Users/<you>/ 等可移植写法）"
        )


def collect_body_length_warning(entry: SkillEntry, skill_file: Path) -> list[str]:
    """SKILL.md 过长会挤占上下文预算；超阈值给 warning，建议拆到 references/。

    brand-exception（如 agent-browser 这类 CLI 包装）天然较长，豁免。
    """
    if entry.role == "brand-exception":
        return []
    line_count = len(skill_file.read_text(encoding="utf-8").splitlines())
    if line_count > BODY_LENGTH_WARN_THRESHOLD:
        return [
            f"BODY LENGTH WARNING: {entry.name} SKILL.md {line_count} 行 "
            f"> {BODY_LENGTH_WARN_THRESHOLD}，考虑把机械细节拆到 references/"
        ]
    return []


def routing_cases_path(context: ValidationContext) -> Path:
    return context.repo_root / "scripts" / "fixtures" / "skill_routing_cases.json"


def deprecated_concepts_path(context: ValidationContext) -> Path:
    return context.repo_root / "scripts" / "fixtures" / "deprecated-concepts.json"


def validate_deprecated_concepts(context: ValidationContext, entries: list[SkillEntry]) -> int:
    path = deprecated_concepts_path(context)
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"INVALID DEPRECATED CONCEPTS JSON: {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise ValidationError(f"INVALID DEPRECATED CONCEPTS: {path} must contain a list")

    warning_count = 0
    for entry in entries:
        skill_file = entry.path / "SKILL.md"
        if not skill_file.exists():
            continue
        # Skip files under refs/ directory
        if "refs" in skill_file.parts:
            continue
        content_lines = skill_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for concept_entry in payload:
            concept = concept_entry.get("concept", "")
            replacement = concept_entry.get("replacement", "")
            scan_pattern = concept_entry.get("scan_pattern", "")
            if not scan_pattern:
                continue
            pattern_re = re.compile(r"(?<![a-zA-Z0-9_-])" + re.escape(scan_pattern) + r"(?![a-zA-Z0-9_])")
            for line_number, line in enumerate(content_lines, start=1):
                if pattern_re.search(line):
                    print(
                        f"DEPRECATED CONCEPT WARNING: {entry.name} references deprecated "
                        f"'{concept}' (replaced by {replacement}) in {skill_file}:{line_number}"
                    )
                    warning_count += 1
    return len(payload)


def validate_routing_cases(context: ValidationContext, entries: list[SkillEntry], skill_names: set[str]) -> int:
    path = routing_cases_path(context)
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"INVALID ROUTING CASES JSON: {path}: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        fail(f"INVALID ROUTING CASES: {path} must contain a non-empty list")

    skill_text_by_name = {
        entry.name: (entry.path / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        for entry in entries
    }
    seen_ids: set[str] = set()
    for index, case in enumerate(payload, start=1):
        if not isinstance(case, dict):
            fail(f"INVALID ROUTING CASE: index={index} must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            fail(f"INVALID ROUTING CASE: index={index} missing id")
        if case_id in seen_ids:
            fail(f"DUPLICATE ROUTING CASE: {case_id}")
        seen_ids.add(case_id)

        expected = case.get("expected_skills")
        rejected = case.get("reject_skills", [])
        terms = case.get("match_terms")
        if not isinstance(expected, list) or not expected:
            fail(f"INVALID ROUTING CASE: {case_id} expected_skills must be a non-empty list")
        if not isinstance(rejected, list):
            fail(f"INVALID ROUTING CASE: {case_id} reject_skills must be a list")
        if not isinstance(terms, list) or not all(isinstance(term, str) and term for term in terms):
            fail(f"INVALID ROUTING CASE: {case_id} match_terms must be non-empty strings")

        for skill in [*expected, *rejected]:
            if not isinstance(skill, str) or not skill:
                fail(f"INVALID ROUTING CASE: {case_id} skill names must be non-empty strings")
            if skill not in skill_names:
                fail(f"UNKNOWN ROUTING SKILL: {case_id} references {skill}")
        overlap = set(expected).intersection(rejected)
        if overlap:
            fail(f"ROUTING CASE CONFLICT: {case_id} both expects and rejects {', '.join(sorted(overlap))}")

        for skill in expected:
            text = skill_text_by_name[skill]
            if not any(term in text for term in terms):
                fail(f"ROUTING CASE UNCOVERED: {case_id} expected {skill} to mention one of match_terms")

        expected_text = "\n".join(skill_text_by_name[skill] for skill in expected)
        for rejected_skill in rejected:
            if rejected_skill not in expected_text:
                fail(
                    f"ROUTING CASE MISSING REJECT BOUNDARY: {case_id} rejects {rejected_skill} "
                    f"but no expected skill ({', '.join(expected)}) declares a boundary mentioning it. "
                    "Add an explicit boundary note (e.g. 与 <reject> 区别 / 不要用 <reject>) so the agent "
                    "knows why not to route there."
                )
    return len(payload)


def validate_command_asset(command_file: Path) -> None:
    frontmatter = parse_markdown_frontmatter(command_file)
    if not isinstance(frontmatter.get("description"), str) or not frontmatter["description"]:
        fail(f"COMMAND ASSET MISSING FIELD: {command_file} field=description")
    content = command_file.read_text(encoding="utf-8", errors="replace")
    if "$ARGUMENTS" in content and not frontmatter.get("argument-hint"):
        fail(f"COMMAND ASSET MISSING FIELD: {command_file} field=argument-hint")


def validate_agent_asset(agent_file: Path) -> None:
    frontmatter = parse_markdown_frontmatter(agent_file)
    for field in ("description", "mode", "model", "permission"):
        if not frontmatter.get(field):
            fail(f"AGENT ASSET MISSING FIELD: {agent_file} field={field}")
    permission = frontmatter.get("permission")
    if not isinstance(permission, dict) or not permission:
        fail(f"AGENT ASSET INVALID PERMISSION: {agent_file}")
    for tool, value in permission.items():
        if value not in {"allow", "deny", "ask"}:
            fail(f"AGENT ASSET INVALID PERMISSION: {agent_file} {tool}={value!r}")


def validate_relative_manifest_path(context: ValidationContext, manifest: Path, raw_path: Any, field: str) -> None:
    if raw_path in (None, ""):
        return
    if not isinstance(raw_path, str):
        fail(f"PLUGIN MANIFEST INVALID PATH: {manifest} field={field}")
    target = (manifest.parent / raw_path).resolve()
    if not target.is_relative_to(context.repo_root.resolve()):
        fail(f"PLUGIN MANIFEST PATH ESCAPES REPO: {manifest} field={field} path={raw_path}")


def validate_plugin_manifest(context: ValidationContext, manifest: Path) -> None:
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"PLUGIN MANIFEST INVALID JSON: {manifest}: {exc}") from exc
    if not isinstance(payload, dict):
        fail(f"PLUGIN MANIFEST INVALID JSON: {manifest} root must be an object")
    for field in ("name", "version"):
        if not isinstance(payload.get(field), str) or not payload[field]:
            fail(f"PLUGIN MANIFEST MISSING FIELD: {manifest} field={field}")
    for field in ("entry", "source", "main"):
        validate_relative_manifest_path(context, manifest, payload.get(field), field)


def iter_repo_plugin_manifests(context: ValidationContext) -> list[Path]:
    candidates = [
        context.repo_root / ".codex-plugin" / "plugin.json",
        context.repo_root / ".claude-plugin" / "plugin.json",
        context.repo_root / ".agents" / "plugins" / "marketplace.json",
    ]
    return [path for path in candidates if path.exists()]


def validate_agent_assets(context: ValidationContext) -> AssetValidationSummary:
    agent_files = sorted((context.repo_root / ".kilo" / "agent").glob("*.md")) if (context.repo_root / ".kilo" / "agent").exists() else []
    command_files = sorted((context.repo_root / "commands").glob("*.md")) if (context.repo_root / "commands").exists() else []
    manifests = iter_repo_plugin_manifests(context)
    for agent_file in agent_files:
        validate_agent_asset(agent_file)
    for command_file in command_files:
        validate_command_asset(command_file)
    for manifest in manifests:
        validate_plugin_manifest(context, manifest)
    return AssetValidationSummary(
        agents=len(agent_files),
        commands=len(command_files),
        plugin_manifests=len(manifests),
    )


def validate_catalog_coverage(context: ValidationContext, entries: list[SkillEntry]) -> None:
    """反向对账：skills/ 下任何带 SKILL.md 的目录都必须在 catalog.json 注册。

    catalog -> 目录方向已由 load_catalog 校验（MISSING PATH）；本函数补目录 -> catalog
    方向，抓"有 SKILL.md 但未注册"的孤儿目录（注册后才会进路由/校验，否则静默漏检）。
    隐藏目录（如 skills/.system/ 下的工具类 skill）故意不进 catalog，按段名以 '.' 开头豁免。
    """
    registered = {entry.path.resolve() for entry in entries}
    orphans: list[str] = []
    for skill_file in context.skills_root.rglob("SKILL.md"):
        skill_dir = skill_file.parent
        rel_parts = skill_dir.relative_to(context.skills_root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if skill_dir.resolve() not in registered:
            orphans.append(str(skill_dir.relative_to(context.repo_root)))
    if orphans:
        fail(
            "ORPHAN SKILL: "
            + ", ".join(sorted(orphans))
            + " (有 SKILL.md 但未在 catalog.json 注册)"
        )


def main() -> int:
    try:
        repo_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
        context = ValidationContext(repo_root=repo_root)
        entries = load_catalog(context)
        validate_catalog_coverage(context, entries)
        skill_names = {entry.name for entry in entries}
        warnings: list[str] = []
        for entry in entries:
            warnings.extend(validate_skill_entry(context, entry, skill_names))
            for warning in warnings:
                sys.stdout.write(f"{warning}\n")
            warnings.clear()
            print(f"ok: {entry.name} -> {entry.path.relative_to(context.repo_root)}")
        routing_case_count = validate_routing_cases(context, entries, skill_names)
        deprecated_count = validate_deprecated_concepts(context, entries)
        asset_summary = validate_agent_assets(context)
        print(f"validated {len(entries)} skills")
        print(f"validated {routing_case_count} skill routing cases")
        print(f"validated {deprecated_count} deprecated concepts")
        print(
            "validated agent assets: "
            f"agents={asset_summary.agents} commands={asset_summary.commands} "
            f"plugin_manifests={asset_summary.plugin_manifests}"
        )
    except ValidationError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

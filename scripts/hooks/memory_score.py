from __future__ import annotations

FRONTMATTER_WEIGHT = 3
PROBLEM_TYPE_WEIGHTS = {
    "decision": 1.35,
    "correction": 1.25,
    "preference": 1.15,
    "failure-mode": 1.1,
    "knowledge": 1.0,
    "pattern": 1.0,
    "bug": 1.0,
}


def split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text
    try:
        end = lines.index("---", 1)
    except ValueError:
        return "", text
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1 :])


def parse_frontmatter(frontmatter: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip().lower()] = normalize_value(value.strip().strip("'\""))
    return data


def normalize_value(value: str) -> str:
    if value.startswith("[") and value.endswith("]"):
        return ", ".join(item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip())
    return value


def frontmatter_summary(frontmatter: str) -> str:
    keep = ("title", "tags", "module", "component", "problem_type", "date")
    parts = []
    for line in frontmatter.splitlines():
        key = line.split(":", 1)[0].strip().lower()
        if key in keep and line.strip():
            parts.append(line.strip())
    return " | ".join(parts)


def score_note(frontmatter: str, body: str, terms: list[str]) -> int:
    fm = frontmatter.lower()
    bd = body.lower()
    score = 0
    for term in terms:
        if not term:
            continue
        score += fm.count(term) * FRONTMATTER_WEIGHT
        score += bd.count(term)
    return score


def problem_type_weight(problem_type: str) -> float:
    return PROBLEM_TYPE_WEIGHTS.get(problem_type.strip().lower(), 1.0)

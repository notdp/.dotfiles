#!/usr/bin/env python3
"""DESIGN.md token-graph 语义 linter（stdlib-only）。

吸收自 `refs/google-labs-code/design.md`（Apache-2.0）的 lint 子集，clean-room 重写，
非搬运。详见 docs/refs-details/google-labs-code/design.md.md 与
docs/refs-update-absorption-2026-06-25.md。

校验本仓库 `fe-ui-design-system` / `/design-md` 产出/消费的 DESIGN.md 视觉契约——
把"token 是规范值"从 prose 约定升级为可机器校验。与 scripts/scan_ui_artifact.py
（HTML/CSS 文本层 slop）正交：本脚本是 DESIGN.md token-graph 语义层。

规则（忠实复刻 upstream 语义，已用其 9 个 fixture + 规则单测用例做差分验证）：
- broken-ref (error)：component 引用 `{path.to.token}` 解析不到已定义 token
- unknown-sub-token (warning)：component 用了非法 sub-token（非 backgroundColor/textColor/…）
- section-order (warning)：8 个 canonical section 顺序颠倒
- orphaned-tokens (warning)：自定义 color token 定义了却无人引用（MD3 家族白名单豁免）
- contrast-ratio (warning)：component 的 bg/text 色对 WCAG AA 对比 < 4.5:1
- 解析层 (error)：非法 hex / 非法单位 / 重复 section / 无 YAML

边界与已知限制（见 docs/refs-update-absorption-2026-06-25.md B.2/Part A 风险）：
- **只硬化客观规则**：error 级（断引用/非法值/重复 section）才影响 exit code；
  warning（contrast/orphaned/section-order）为"候选需看上下文"，不进硬 gating。
- 无色调阶生成：`{colors.primary-60}` 只有显式定义才解析，否则判 broken-ref（同 upstream）。
- contrast 按正文阈值 4.5:1；大字号/装饰文本 WCAG 阈值不同（3:1），warning 仅供人工复核。
- orphaned-tokens 的 MD3 家族白名单见 MD3_STANDARD_FAMILIES，非 MD3 命名的自定义 token 才报。
- **手写最小 YAML 子集解析器**（无 PyYAML 依赖，遵循本仓库 stdlib-only 惯例）：
  只支持 DESIGN.md front-matter 语法（嵌套 map + 标量 + 引号 + 注释 + `---`/```yaml fence），
  不支持任意 YAML（list/anchor/多行/流式）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ── Spec 常量（来自 refs/google-labs-code/design.md spec-config.yaml）────────────

CANONICAL_ORDER = [
    "Overview",
    "Colors",
    "Typography",
    "Layout",
    "Elevation & Depth",
    "Shapes",
    "Components",
    "Do's and Don'ts",
]
SECTION_ALIASES = {
    "Brand & Style": "Overview",
    "Layout & Spacing": "Layout",
    "Elevation": "Elevation & Depth",
}
VALID_COMPONENT_SUB_TOKENS = [
    "backgroundColor",
    "textColor",
    "typography",
    "rounded",
    "padding",
    "size",
    "height",
    "width",
]
# MD3 baseline color families：属于这些家族的 token 永不报 orphan（即便无 component 引用）。
MD3_STANDARD_FAMILIES = {
    "primary",
    "secondary",
    "tertiary",
    "error",
    "surface",
    "background",
    "outline",
}
MAX_REFERENCE_DEPTH = 10

# ── 谓词（来自 model/spec.ts）───────────────────────────────────────────────────

_TOKEN_REF_RE = re.compile(r"^\{[a-zA-Z0-9._-]+\}$")
_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_DIM_RE = re.compile(r"^(-?\d*\.?\d+)([a-zA-Z%]+)$")
_UNITLESS_RE = re.compile(r"^\d*\.?\d+$")


def is_token_reference(raw: Any) -> bool:
    return isinstance(raw, str) and bool(_TOKEN_REF_RE.match(raw))


def is_valid_color(raw: Any) -> bool:
    return isinstance(raw, str) and bool(_COLOR_RE.match(raw))


def parse_dimension_parts(raw: Any) -> dict | None:
    if not isinstance(raw, str):
        return None
    m = _DIM_RE.match(raw)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    return {"value": value, "unit": m.group(2)}


def is_parseable_dimension(raw: Any) -> bool:
    return parse_dimension_parts(raw) is not None


def resolve_alias(heading: str) -> str:
    return SECTION_ALIASES.get(heading, heading)


# ── 值解析（来自 model/handler.ts）──────────────────────────────────────────────


def parse_color(raw: str) -> dict:
    """hex → {type:'color', hex, r, g, b, a, luminance}（WCAG 2.1 sRGB 相对亮度）。"""
    hex_v = raw
    if len(hex_v) == 4:  # #RGB → #RRGGBB
        hex_v = "#" + "".join(c * 2 for c in hex_v[1:])
    if len(hex_v) == 5:  # #RGBA → #RRGGBBAA
        hex_v = "#" + "".join(c * 2 for c in hex_v[1:])
    hex_v = hex_v.lower()
    r = int(hex_v[1:3], 16)
    g = int(hex_v[3:5], 16)
    b = int(hex_v[5:7], 16)
    a = int(hex_v[7:9], 16) / 255 if len(hex_v) == 9 else None
    return {"type": "color", "hex": hex_v, "r": r, "g": g, "b": b, "a": a,
            "luminance": _luminance(r, g, b)}


def _luminance(r: int, g: int, b: int) -> float:
    def lin(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(a: dict, b: dict) -> float:
    l1 = max(a["luminance"], b["luminance"])
    l2 = min(a["luminance"], b["luminance"])
    return (l1 + 0.05) / (l2 + 0.05)


def parse_dimension(raw: str) -> dict:
    parts = parse_dimension_parts(raw)
    if not parts:
        raise ValueError(f"Invalid dimension: {raw}")
    return {"type": "dimension", "value": parts["value"], "unit": parts["unit"]}


def _parse_typography(props: dict, path: str, findings: list) -> dict:
    result: dict = {"type": "typography"}
    ff = props.get("fontFamily")
    if isinstance(ff, str):
        if is_valid_color(ff):
            findings.append(_f("error", f"{path}.fontFamily",
                               f"'{ff}' appears to be a color, not a valid font family."))
        result["fontFamily"] = ff
    if "fontWeight" in props and props["fontWeight"] is not None:
        fw = props["fontWeight"]
        fw_val = None
        if isinstance(fw, (int, float)) and not isinstance(fw, bool):
            fw_val = fw
        elif isinstance(fw, str):
            try:
                fw_val = float(fw) if "." in fw else int(fw)
            except ValueError:
                fw_val = None
        if fw_val is None:
            findings.append(_f("error", f"{path}.fontWeight",
                               f"'{fw}' is not a valid font weight. Expected a number."))
        else:
            result["fontWeight"] = fw_val
    if isinstance(props.get("fontFeature"), str):
        result["fontFeature"] = props["fontFeature"]
    if isinstance(props.get("fontVariation"), str):
        result["fontVariation"] = props["fontVariation"]
    for prop in ("fontSize", "lineHeight", "letterSpacing"):
        raw = props.get(prop)
        if isinstance(raw, str):
            if is_parseable_dimension(raw):
                parsed = parse_dimension(raw)
                if parsed["unit"] not in ("px", "rem", "em"):
                    findings.append(_f("error", f"{path}.{prop}",
                                       f"'{raw}' has an invalid unit '{parsed['unit']}'. "
                                       "Only px, rem, and em are allowed."))
                result[prop] = parsed
            elif prop == "lineHeight" and _UNITLESS_RE.match(raw):
                result[prop] = {"type": "dimension", "value": float(raw), "unit": ""}
            elif not is_token_reference(raw):
                findings.append(_f("error", f"{path}.{prop}", f"'{raw}' is not a valid dimension."))
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool) and prop == "lineHeight":
            result[prop] = {"type": "dimension", "value": float(raw), "unit": ""}
    return result


def _resolve_reference(symbol_table: dict, path: str, visited: set, depth: int = 0):
    if depth > MAX_REFERENCE_DEPTH:
        return None
    if path in visited:
        return None
    visited.add(path)
    value = symbol_table.get(path)
    if value is None:
        return None
    if isinstance(value, str) and is_token_reference(value):
        return _resolve_reference(symbol_table, value[1:-1], visited, depth + 1)
    return value


def _f(severity: str, path: str | None, message: str) -> dict:
    return {"severity": severity, "path": path, "message": message}


# ── Model：从 parsed dict 构建 DesignSystemState（来自 model/handler.ts）──────────


def build_state(parsed: dict) -> dict:
    """复刻 ModelHandler.execute：返回 {designSystem, findings}。"""
    findings: list = []
    symbol_table: dict = {}
    colors: dict = {}
    typography: dict = {}
    rounded: dict = {}
    spacing: dict = {}

    # Phase 1：primitive token
    for name, raw in (parsed.get("colors") or {}).items():
        key = f"colors.{name}"
        if is_token_reference(raw):
            symbol_table[key] = raw
        elif is_valid_color(raw):
            resolved = parse_color(raw)
            colors[name] = resolved
            symbol_table[key] = resolved
        else:
            findings.append(_f("error", key,
                               f"'{raw}' is not a valid color. Expected a hex color code (e.g., #ffffff)."))
            symbol_table[key] = raw

    for name, props in (parsed.get("typography") or {}).items():
        if isinstance(props, dict):
            resolved = _parse_typography(props, f"typography.{name}", findings)
            typography[name] = resolved
            symbol_table[f"typography.{name}"] = resolved

    for name, raw in (parsed.get("rounded") or {}).items():
        key = f"rounded.{name}"
        if isinstance(raw, str):
            if is_parseable_dimension(raw):
                resolved = parse_dimension(raw)
                if resolved["unit"] not in ("px", "rem", "em"):
                    findings.append(_f("error", key,
                                       f"'{raw}' has an invalid unit '{resolved['unit']}'. "
                                       "Only px, rem, and em are allowed."))
                rounded[name] = resolved
                symbol_table[key] = resolved
            else:
                if not is_token_reference(raw):
                    findings.append(_f("error", key, f"'{raw}' is not a valid dimension."))
                symbol_table[key] = raw

    for name, raw in (parsed.get("spacing") or {}).items():
        key = f"spacing.{name}"
        if is_parseable_dimension(raw):
            spacing[name] = parse_dimension(raw)
            symbol_table[key] = spacing[name]
        else:
            symbol_table[key] = raw

    # Phase 2：链式引用解析（colors / rounded / spacing）
    for name, raw in (parsed.get("colors") or {}).items():
        if is_token_reference(raw):
            resolved = _resolve_reference(symbol_table, raw[1:-1], set())
            if isinstance(resolved, dict) and resolved.get("type") == "color":
                colors[name] = resolved
                symbol_table[f"colors.{name}"] = resolved
    for name, raw in (parsed.get("rounded") or {}).items():
        if isinstance(raw, str) and is_token_reference(raw):
            resolved = _resolve_reference(symbol_table, raw[1:-1], set())
            if isinstance(resolved, dict) and resolved.get("type") == "dimension":
                rounded[name] = resolved
                symbol_table[f"rounded.{name}"] = resolved
    for name, raw in (parsed.get("spacing") or {}).items():
        if isinstance(raw, str) and is_token_reference(raw):
            resolved = _resolve_reference(symbol_table, raw[1:-1], set())
            if isinstance(resolved, dict) and resolved.get("type") == "dimension":
                spacing[name] = resolved
                symbol_table[f"spacing.{name}"] = resolved

    # Phase 3：components
    components: dict = {}
    for comp_name, props in (parsed.get("components") or {}).items():
        if not isinstance(props, dict):
            continue
        properties: dict = {}
        unresolved_refs: list = []
        for prop_name, raw_value in props.items():
            if isinstance(raw_value, bool):
                properties[prop_name] = raw_value
            elif isinstance(raw_value, (int, float)):
                properties[prop_name] = raw_value
            elif is_token_reference(raw_value):
                resolved = _resolve_reference(symbol_table, raw_value[1:-1], set())
                if resolved is not None:
                    properties[prop_name] = resolved
                else:
                    unresolved_refs.append(raw_value)
                    properties[prop_name] = raw_value
            elif is_valid_color(raw_value):
                properties[prop_name] = parse_color(raw_value)
            elif is_parseable_dimension(raw_value):
                properties[prop_name] = parse_dimension(raw_value)
            else:
                properties[prop_name] = raw_value
        components[comp_name] = {"properties": properties, "unresolvedRefs": unresolved_refs}

    return {
        "designSystem": {
            "name": parsed.get("name"),
            "description": parsed.get("description"),
            "colors": colors,
            "typography": typography,
            "rounded": rounded,
            "spacing": spacing,
            "components": components,
            "symbolTable": symbol_table,
            "sections": parsed.get("sections"),
        },
        "findings": findings,
    }


# ── 规则（来自 linter/rules/*.ts）──────────────────────────────────────────────


def rule_broken_ref(state: dict) -> list:
    findings = []
    for comp_name, comp in state["components"].items():
        for ref in comp["unresolvedRefs"]:
            findings.append(_f("error", f"components.{comp_name}",
                               f"Reference {ref} does not resolve to any defined token."))
        for prop_name in comp["properties"]:
            if prop_name not in VALID_COMPONENT_SUB_TOKENS:
                findings.append(_f("warning", f"components.{comp_name}.{prop_name}",
                                   f"'{prop_name}' is not a recognized component sub-token. "
                                   f"Valid sub-tokens: {', '.join(VALID_COMPONENT_SUB_TOKENS)}."))
    return findings


_ORDER_MAP = {s: i for i, s in enumerate(CANONICAL_ORDER)}


def rule_section_order(state: dict) -> list:
    findings = []
    sections = state.get("sections") or []
    if not sections:
        return findings
    known = [resolve_alias(s) for s in sections]
    known = [s for s in known if s in _ORDER_MAP]
    for i in range(len(known) - 1):
        cur, nxt = known[i], known[i + 1]
        if _ORDER_MAP[cur] > _ORDER_MAP[nxt]:
            findings.append(_f("warning", None,
                               f"Section '{cur}' appears before '{nxt}', which is out of order. "
                               f"Expected order: {', '.join(CANONICAL_ORDER)}"))
            break
    return findings


def _color_family(name: str) -> str:
    n = name
    n = re.sub(r"^on-", "", n)
    n = re.sub(r"^inverse-", "", n)
    n = re.sub(r"^on-", "", n)
    n = re.sub(r"-container.*$", "", n)
    n = re.sub(r"-fixed.*$", "", n)
    n = re.sub(r"-(dim|bright|tint|variant)$", "", n)
    return n


def rule_orphaned_tokens(state: dict) -> list:
    if not state["components"]:
        return []
    symbol_table = state["symbolTable"]
    referenced_paths: set = set()
    for comp in state["components"].values():
        for value in comp["properties"].values():
            if isinstance(value, dict) and "type" in value:
                for key, sym_value in symbol_table.items():
                    if sym_value is value:  # 对象 identity（同 upstream symValue === value）
                        referenced_paths.add(key)
    referenced_families: set = set()
    for path in referenced_paths:
        if path.startswith("colors."):
            referenced_families.add(_color_family(path[len("colors."):]))
    findings = []
    for name in state["colors"]:
        path = f"colors.{name}"
        if path in referenced_paths:
            continue
        family = _color_family(name)
        if family in referenced_families:
            continue
        if family in MD3_STANDARD_FAMILIES:
            continue
        findings.append(_f("warning", path,
                           f"'{name}' is defined but never referenced by any component."))
    return findings


_WCAG_AA_MIN = 4.5


def rule_contrast_ratio(state: dict) -> list:
    findings = []
    for comp_name, comp in state["components"].items():
        bg = comp["properties"].get("backgroundColor")
        text = comp["properties"].get("textColor")
        if not _is_color(bg) or not _is_color(text):
            continue
        ratio = contrast_ratio(bg, text)
        if ratio < _WCAG_AA_MIN:
            findings.append(_f("warning", f"components.{comp_name}",
                               f"textColor ({text['hex']}) on backgroundColor ({bg['hex']}) has "
                               f"contrast ratio {ratio:.2f}:1, below WCAG AA minimum of {_WCAG_AA_MIN}:1."))
    return findings


def _is_color(v: Any) -> bool:
    return isinstance(v, dict) and v.get("type") == "color"


ALL_RULES = [rule_broken_ref, rule_section_order, rule_orphaned_tokens, rule_contrast_ratio]


# ── 最小 YAML 子集解析器（无 PyYAML 依赖）──────────────────────────────────────


class DesignMdError(Exception):
    """解析层不可恢复错误（无 YAML / 重复 section / YAML 语法）。"""


def _parse_scalar(raw: str):
    v = raw.strip()
    if not v:
        return None
    if v[0] in ('"', "'"):
        quote = v[0]
        end = v.find(quote, 1)
        if end == -1:
            return v[1:]  # 未闭合，宽松取剩余
        return v[1:end]
    # 裸值：注释处理。`: #...`（值以 # 开头）→ YAML 视为 comment → null
    if v.startswith("#"):
        return None
    # 行内注释 ` #`（空格+井号）截断
    m = re.search(r"\s#", v)
    if m:
        v = v[: m.start()].strip()
    if v == "":
        return None
    if v in ("null", "~"):
        return None
    if v == "true":
        return True
    if v == "false":
        return False
    if re.match(r"^-?\d+$", v):
        return int(v)
    if re.match(r"^-?\d*\.\d+$", v):
        return float(v)
    return v


def parse_yaml_block(text: str) -> dict:
    """解析受限 YAML 子集：嵌套 map + 标量。不支持 list/anchor/多行。

    map-opener vs null 标量靠前瞻下一行缩进区分：`key:`（或 `key: # 注释`）后若下一行
    更深缩进 → 开 map；否则 → null 标量（含 `key: #hex` 这种 YAML 注释→null 的情况）。
    """
    root: dict = {}
    stack: list = [(-1, root)]  # [(indent, container_dict)]，root 用 indent=-1

    entries: list = []  # [(indent, key, value_part)]，仅含含 key 的有效行
    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped in ("---", "..."):
            continue
        if ":" not in raw_line:
            continue  # 忽略不含 key 的行（受限语法）
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key_part, _, value_part = stripped.partition(":")
        key = key_part.strip()
        if len(key) > 1 and key[0] in ('"', "'") and key[-1] == key[0]:
            key = key[1:-1]
        entries.append((indent, key, value_part))

    for i, (indent, key, value_part) in enumerate(entries):
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            stack = [(-1, root)]
        parent = stack[-1][1]
        scalar = _parse_scalar(value_part)
        next_deeper = i + 1 < len(entries) and entries[i + 1][0] > indent
        if scalar is None and next_deeper:
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = scalar
    return root


_FENCE_RE = re.compile(r"^```(\w*)\s*$")
_H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def parse_design_md(content: str) -> dict:
    """从 DESIGN.md 抽 token（front matter + ```yaml fence）+ H2 sections。

    返回 parsed dict（含 name/description/colors/typography/rounded/spacing/components/sections）。
    重复顶层 key、无 YAML 时抛 DesignMdError。
    """
    lines = content.split("\n")
    blocks: list = []  # [(label, yaml_text)]
    body_start = 0

    # 1. front matter：文件起始的 --- ... ---
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines) and lines[i].strip() == "---":
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == "---":
                blocks.append(("frontmatter", "\n".join(lines[i + 1:j])))
                body_start = j + 1
                break

    # 2. body：```yaml fence + H2 sections（fence 内的 ## 不算 heading）
    sections: list = []
    in_fence = False
    fence_lang = ""
    fence_buf: list = []
    fence_idx = 0
    for line in lines[body_start:]:
        m = _FENCE_RE.match(line.strip())
        if m:
            if not in_fence:
                in_fence = True
                fence_lang = m.group(1).lower()
                fence_buf = []
            else:
                if fence_lang in ("yaml", "yml"):
                    blocks.append((f"code block {fence_idx + 1}", "\n".join(fence_buf)))
                    fence_idx += 1
                in_fence = False
                fence_lang = ""
            continue
        if in_fence:
            fence_buf.append(line)
            continue
        hm = _H2_RE.match(line)
        if hm:
            sections.append(hm.group(1).strip())

    if not blocks:
        raise DesignMdError("No YAML content found. Expected frontmatter (---) or fenced yaml code blocks.")

    # 3. merge blocks + 重复 key 检测
    merged: dict = {}
    seen: dict = {}
    for label, text in blocks:
        try:
            parsed = parse_yaml_block(text)
        except Exception as exc:  # pragma: no cover - 防御
            raise DesignMdError(f"YAML parse error in {label}: {exc}") from exc
        for key in parsed:
            if key in seen:
                raise DesignMdError(f"Section '{key}' is defined in both {seen[key]} and {label}.")
            seen[key] = label
        merged.update(parsed)

    merged["sections"] = sections
    return merged


# ── 顶层 lint API ──────────────────────────────────────────────────────────────

_SEV_TO_P = {"error": "P0", "warning": "P1", "info": "P2"}


def lint_content(content: str) -> list:
    """lint 一段 DESIGN.md 文本，返回 findings 列表。"""
    try:
        parsed = parse_design_md(content)
    except DesignMdError as exc:
        return [_f("error", None, str(exc))]
    result = build_state(parsed)
    findings = list(result["findings"])
    state = result["designSystem"]
    for rule in ALL_RULES:
        findings.extend(rule(state))
    return findings


def lint_file(path: Path) -> list:
    return lint_content(path.read_text(encoding="utf-8"))


# ── CLI / 输出 ─────────────────────────────────────────────────────────────────


def _render_table(per_file: list) -> str:
    out = []
    total = {"error": 0, "warning": 0, "info": 0}
    for path, findings in per_file:
        out.append(f"\n## {path}")
        if not findings:
            out.append("  ✓ no findings")
            continue
        out.append("| sev | P | path | message |")
        out.append("|---|---|---|---|")
        for f in findings:
            total[f["severity"]] = total.get(f["severity"], 0) + 1
            p = _SEV_TO_P.get(f["severity"], "P?")
            out.append(f"| {f['severity']} | {p} | {f['path'] or '-'} | {f['message']} |")
    out.append(f"\nsummary: errors={total['error']} warnings={total['warning']} infos={total['info']}")
    return "\n".join(out)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="DESIGN.md token-graph 语义 linter")
    parser.add_argument("files", nargs="+", help="DESIGN.md 文件路径")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = parser.parse_args(argv)

    per_file = []
    had_error = False
    for f in args.files:
        path = Path(f)
        if not path.is_file():
            findings = [_f("error", None, f"file not found: {f}")]
        else:
            findings = lint_file(path)
        if any(d["severity"] == "error" for d in findings):
            had_error = True
        per_file.append((str(path), findings))

    if args.json:
        payload = {
            "files": [
                {"path": p, "findings": [{**d, "p": _SEV_TO_P.get(d["severity"], "P?")} for d in fs]}
                for p, fs in per_file
            ],
            "summary": {
                "errors": sum(1 for _, fs in per_file for d in fs if d["severity"] == "error"),
                "warnings": sum(1 for _, fs in per_file for d in fs if d["severity"] == "warning"),
                "infos": sum(1 for _, fs in per_file for d in fs if d["severity"] == "info"),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_render_table(per_file))

    # exit 1 仅当有 error 级（客观结构错误）；warning 不进 gating（见模块 docstring 边界）
    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())

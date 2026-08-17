#!/usr/bin/env python3
"""Extract Claude Code Desktop keyboard shortcuts from the app bundle and diff
against the last snapshot. Silent (exit 0, no output) when nothing changed.

Sources inside Contents/Resources/ion-dist/assets/v1/*.js (hashed filenames, so
everything is located by content, never by name):
  1. pane/composer table   -- array of {command,key,code,when}
  2. command registry      -- {name:{description,...,shortcut:{bindings:[...]}}}
  3. shortcuts modal       -- rows rendered in the Cmd+/ dialog
"""

import json
import plistlib
import re
import sys
from pathlib import Path

APP = Path("/Applications/Claude.app")
ASSETS = APP / "Contents/Resources/ion-dist/assets/v1"
SNAPSHOT = Path(__file__).with_name("snapshot.json")


def app_version() -> str:
    try:
        info = plistlib.loads((APP / "Contents/Info.plist").read_bytes())
        return info.get("CFBundleShortVersionString", "?")
    except Exception:
        return "?"


def chunks():
    """(name, source) for every JS chunk, largest first (hot ones are big)."""
    files = sorted(ASSETS.glob("*.js"), key=lambda p: -p.stat().st_size)
    for p in files:
        yield p.name, p.read_text(errors="ignore")


# --- 1. pane / composer table -------------------------------------------------

PANE_RE = re.compile(
    r'\{command:"(\w+)",key:"([^"]+)"(?:,code:"[^"]*")?'
    r'(?:,when:"([^"]*)")?(?:,mac:(![01]))?(?:,gate:"([^"]*)")?\}'
)


def pane_table(src):
    out = []
    for cmd, key, when, mac, gate in PANE_RE.findall(src):
        e = {"command": cmd, "key": key}
        if when:
            e["when"] = when
        if mac:
            e["mac"] = mac == "!0"
        if gate:
            e["gate"] = gate
        out.append(e)
    return out


# --- 2. command registry ------------------------------------------------------

# Entries without a `shortcut` must NOT swallow the next entry's bindings, so the
# skipped span may not cross another `description:` — each entry has exactly one.
REG_RE = re.compile(
    r'(\w+):\{description:([\w$]+)\.description,(?:(?!description:)[\s\S]){0,400}?'
    r'shortcut:\{bindings:\[(.*?)\]\}'
)
BIND_RE = re.compile(
    r'key:"([^"]+)"(?:,code:"[^"]*")?,modifiers:\[([^\]]*)\](?:,platform:"([^"]*)")?'
)
# Labels live in separate minified consts: vS=$a({description:{defaultMessage:"..."
DESC_RE = re.compile(r'([\w$]+)=\$?\w*\(\{description:\{defaultMessage:"([^"]*)"')


def registry(src):
    labels = dict(DESC_RE.findall(src))
    out = {}
    for name, dvar, binds in REG_RE.findall(src):
        keys = []
        for key, mods, platform in BIND_RE.findall(binds):
            if platform == "non-mac":
                continue
            mods = [m.strip('"') for m in mods.split(",") if m.strip()]
            combo = "+".join(mods + [key])
            if combo not in keys:
                keys.append(combo)
        if keys:
            out[name] = {"keys": keys, "label": labels.get(dvar, name)}
    return out


# --- 3. Cmd+/ modal -----------------------------------------------------------

ROW_RE = re.compile(
    # The array form is scanned string-by-string: a key can itself contain `]`
    # (`["cmd+shift+]","ctrl+tab"]`), so a naive [^\]]* truncates it.
    r'(?:shortcut:(\[(?:"[^"]*",?)*\]|"[^"]*"|[A-Za-z_$][^,]{0,70}?)|shortcutId:"(\w+)")'
    r',children:[\s\S]{0,120}?defaultMessage:"([^"]*)"'
)


def modal_rows(src):
    # Anchor on the modal's own row, not on the label "Keyboard shortcuts" — that
    # string also appears as a help-menu item in a different (larger) chunk, and
    # chunks are scanned largest-first.
    anchors = [m.start() for m in re.finditer(r'shortcutId:"shortcuts_modal"', src)]
    if not anchors:
        return []
    seg = src[max(0, anchors[0] - 20000): anchors[-1] + 20000]
    out = []
    for shortcut, sid, label in ROW_RE.findall(seg):
        label = label.encode().decode("unicode_escape")
        key = shortcut.strip('"') if shortcut else f"@{sid}"
        # A bare identifier is a hoisted array of alternatives (var Ig=["a","b"]).
        if re.fullmatch(r"[A-Za-z_$]\w*", key):
            arr = re.search(rf'\b{re.escape(key)}=\[("[^\]]*")\]', src)
            if arr:
                key = "[" + arr.group(1) + "]"
        out.append({"label": label, "key": key})
    return out


# --- collect ------------------------------------------------------------------

# Modal rows are JSX props, so a key can be an array, a platform ternary, or a
# `shortcutId` pointing into the registry. Normalise to a plain key string.
TERNARY_RE = re.compile(r'^\w+\?(?:\w+\?)?"([^"]+)"')
QUOTED_RE = re.compile(r'"([^"]+)"')


def resolve_key(key, reg):
    if "\\u" in key:
        key = key.encode().decode("unicode_escape")
    if key.startswith("@"):
        entry = reg.get(key[1:])
        if isinstance(entry, dict):
            return " / ".join(entry["keys"])
        return " / ".join(entry) if isinstance(entry, list) else key
    if key.startswith("["):
        return " / ".join(QUOTED_RE.findall(key))
    m = TERNARY_RE.match(key)  # desktop branch is always the first string
    return m.group(1) if m else key


def collect():
    data = {"version": app_version(), "pane": [], "registry": {}, "modal": []}
    for _, src in chunks():
        if not data["pane"]:
            data["pane"] = pane_table(src)
        if not data["registry"]:
            data["registry"] = registry(src)
        if not data["modal"]:
            data["modal"] = modal_rows(src)
        if data["pane"] and data["registry"] and data["modal"]:
            break
    for row in data["modal"]:
        row["key"] = resolve_key(row["key"], data["registry"])
    return data


SECTIONS = ("pane", "registry", "modal")


def flatten(snap):
    """{section: {stable_id: (display_label, key_string)}} — the diff/render unit."""
    out = {s: {} for s in SECTIONS}

    for e in snap.get("pane", []):
        # Same command binds different keys per platform/context, so `when`/`mac`
        # are part of the identity — otherwise the variants overwrite each other.
        ident = e["command"]
        for extra in ("when", "mac", "gate"):
            if extra in e:
                ident += f"@{e[extra]}"
        out["pane"][ident] = (e["command"], e["key"])

    for name, v in snap.get("registry", {}).items():
        # Older snapshots stored a bare key list; tolerate both shapes.
        keys, label = (v["keys"], v.get("label", name)) if isinstance(v, dict) else (v, name)
        out["registry"][name] = (label, " / ".join(keys))

    for e in snap.get("modal", []):
        out["modal"][f'{e["label"]}|{e["key"]}'] = (e["label"], e["key"])

    return out


def diff(old, new):
    """(lines, marks) — marks is {section: {id: 'added'|old_key}} for rendering."""
    lines, marks = [], {s: {} for s in SECTIONS}
    if old.get("version") != new["version"]:
        lines.append(f"CCD version: {old.get('version')} -> {new['version']}")

    fo, fn = flatten(old), flatten(new)
    for s in SECTIONS:
        o, n = fo[s], fn[s]
        for k in sorted(n.keys() - o.keys()):
            marks[s][k] = "added"
            lines.append(f"+ [{s}] {n[k][0]}: {n[k][1]}")
        for k in sorted(o.keys() - n.keys()):
            lines.append(f"- [{s}] {o[k][0]}: {o[k][1]} (removed)")
        for k in sorted(o.keys() & n.keys()):
            if o[k][1] != n[k][1]:
                marks[s][k] = o[k][1]
                lines.append(f"~ [{s}] {n[k][0]}: {o[k][1]} -> {n[k][1]}")
    return lines, marks


PRETTY = {"cmd": "⌘", "ctrl": "⌃", "shift": "⇧", "alt": "⌥",
          "arrowleft": "←", "arrowright": "→", "arrowup": "↑", "arrowdown": "↓",
          "left": "←", "right": "→", "up": "↑", "down": "↓",
          "enter": "↩", "backspace": "⌫", "tab": "⇥"}
# Anything outside this alphabet is a raw JS expression (`t?"cmd+n":"cmd+shift+o"`)
# or a variable reference — pass it through untouched rather than mangling it.
PLAIN_KEY = re.compile(r"[\w+`\\/.,;'…\[\]-]+")
TITLES = {
    "pane": "面板 / 输入框键位表（硬编码，部分不出现在 ⌘/ 弹窗里）",
    "registry": "全局命令注册表",
    "modal": "⌘/ 内置弹窗实际渲染的行",
}

def pretty(key):
    def one(k):
        if not k or k.startswith("@") or not PLAIN_KEY.fullmatch(k):
            return k
        return "".join(PRETTY.get(p, p.upper() if len(p) == 1 else p)
                       for p in k.split("+"))

    out = " / ".join(one(k) for k in key.split(" / "))
    # ⌃` would terminate a single-backtick span, so widen the fence when needed.
    return f"`` {out} ``" if "`" in out else f"`{out}`"


def render(new, marks, removed_lines):
    """Full table every run; changed rows carry a marker."""
    md = [f"# CCD 快捷键全量表 — 版本 {new['version']}", ""]
    total_marked = sum(len(m) for m in marks.values())
    md.append(f"标记说明：**🆕 新增** · **✏️ 改键（括号内为旧键）** · 本次共 {total_marked} 处变动")
    md.append("")

    for s in SECTIONS:
        rows = flatten(new)[s]
        md += [f"## {TITLES[s]}", "", "| 快捷键 | 命令 / 说明 | |", "|---|---|---|"]
        for ident, (label, key) in sorted(rows.items(), key=lambda kv: kv[1][0].lower()):
            mark = marks[s].get(ident)
            note = "🆕" if mark == "added" else (f"✏️ 旧: `{mark}`" if mark else "")
            md.append(f"| {pretty(key)} | {label} | {note} |")
        md.append("")

    if removed_lines:
        md += ["## 本次移除", ""] + [f"- {l.lstrip('- ')}" for l in removed_lines] + [""]
    return "\n".join(md)


def main():
    if not ASSETS.is_dir():
        print(f"ERROR: {ASSETS} not found — is Claude.app installed?", file=sys.stderr)
        return 2

    new = collect()
    # A handful of rows means the regex latched onto the wrong chunk, which reads
    # as "everything was removed" — treat it as missing so the WARN path kicks in.
    MIN_ROWS = {"pane": 5, "registry": 10, "modal": 10}
    missing = [k for k, n in MIN_ROWS.items() if len(new[k]) < n]
    if len(missing) == 3:
        print("ERROR: extracted nothing — bundle layout changed, extract.py needs "
              "updating. Do NOT report shortcuts as removed.", file=sys.stderr)
        return 3

    if SNAPSHOT.exists():
        old = json.loads(SNAPSHOT.read_text())
        # A section that vanished means the regex broke, not that Anthropic deleted
        # every shortcut. Carry the old data forward and say so.
        for k in missing:
            if old.get(k):
                new[k] = old[k]
                print(f"WARN: section '{k}' no longer parses; kept previous data. "
                      "extract.py likely needs updating.", file=sys.stderr)
        changes, marks = diff(old, new)
    else:
        changes, marks = [], {s: {} for s in SECTIONS}

    SNAPSHOT.write_text(json.dumps(new, indent=2, ensure_ascii=False))
    print(render(new, marks, [l for l in changes if l.startswith("- ")]))
    if changes:
        print("\n<!-- CHANGELOG\n" + "\n".join(changes) + "\n-->")
    return 0


def demo():
    """Self-check: diff stays quiet on identity and catches each kind of change."""
    base = {"version": "1.0", "pane": [{"command": "a", "key": "ctrl+o"}],
            "registry": {"r": {"keys": ["cmd+/"], "label": "R"}},
            "modal": [{"label": "L", "key": "esc"}]}
    assert diff(base, base)[0] == [], "identical snapshots must produce no diff"

    def mutate(fn):
        c = json.loads(json.dumps(base))
        fn(c)
        return diff(base, c)

    lines, marks = mutate(lambda c: c["pane"][0].__setitem__("key", "ctrl+p"))
    assert "~ [pane] a: ctrl+o -> ctrl+p" in lines, lines
    assert marks["pane"]["a"] == "ctrl+o", marks

    lines, marks = mutate(lambda c: c["registry"].__setitem__(
        "new", {"keys": ["cmd+j"], "label": "N"}))
    assert any(l.startswith("+ [registry] N") for l in lines), lines
    assert marks["registry"]["new"] == "added"

    lines, _ = mutate(lambda c: c.__setitem__("modal", []))
    assert any(l.startswith("- [modal] L") for l in lines), lines

    lines, _ = mutate(lambda c: c.__setitem__("version", "1.1"))
    assert lines == ["CCD version: 1.0 -> 1.1"], lines

    # A pre-label snapshot must still diff cleanly against the new shape.
    legacy = json.loads(json.dumps(base))
    legacy["registry"] = {"r": ["cmd+/"]}
    assert not [l for l in diff(legacy, base)[0] if "[registry]" in l], "legacy shape broke"

    live = collect()
    assert live["pane"] and live["registry"] and live["modal"], \
        f"live extraction empty: { {k: len(v) for k, v in live.items() if k != 'version'} }"
    assert sum(1 for v in live["registry"].values() if v["label"] != "?") > 15, \
        "registry labels failed to resolve"
    probe = {s: {} for s in SECTIONS}
    probe["modal"][next(iter(flatten(live)["modal"]))] = "added"
    assert "🆕" in render(live, probe, []), "render dropped the change marker"
    print("ok — diff + render + live extraction pass;",
          {k: len(v) for k, v in live.items() if k != "version"})


if __name__ == "__main__":
    sys.exit(demo() if "--demo" in sys.argv else main())

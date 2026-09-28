#!/usr/bin/env python3
"""Extract Claude Code Desktop keyboard shortcuts from the app bundle and diff
against the last snapshot. Silent (exit 0, no output) when nothing changed.

Sources inside Contents/Resources/ion-dist/assets/v1/*.js (hashed filenames, so
everything is located by content, never by name):
  1. pane/composer table   -- array of {command,key,code,when,mac,gate,matchBy}
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


def unescape(s):
    """JS string escapes survive the regex: `cmd+shift+\\\\`, `cmd+1\\u20269`."""
    if "\\" not in s:
        return s
    try:
        return s.encode().decode("unicode_escape")
    except UnicodeDecodeError:  # already decoded (a lone trailing `\\`)
        return s


_CHUNKS = []


def bundle_search(pattern):
    """First match of `pattern` anywhere in the bundle — labels for a row can live
    in a different chunk than the modal that renders it."""
    if not _CHUNKS:
        _CHUNKS.extend(src for _, src in chunks())
    for src in _CHUNKS:
        m = re.search(pattern, src)
        if m:
            return m
    return None


def chunks():
    """(name, source) for every JS chunk, largest first (hot ones are big)."""
    files = sorted(ASSETS.glob("*.js"), key=lambda p: -p.stat().st_size)
    for p in files:
        yield p.name, p.read_text(errors="ignore")


# --- 1. pane / composer table -------------------------------------------------

# Entries are parsed in two steps instead of one order-sensitive pattern: an
# earlier version spelled out `code?,when?,mac?,gate?` in order and silently
# dropped every entry carrying an unlisted field (`matchBy:"key"` on
# backgroundTasks / attachTerminalOutput). Anchor on `{command:"…"` , swallow the
# whole object, then read fields by name — new fields can appear in any order.
PANE_ENTRY_RE = re.compile(r'\{(command:"\w+"(?:,\w+:(?:"[^"]*"|!\d|\w+))*)\}')
PANE_ATTR_RE = re.compile(r'(\w+):(?:"([^"]*)"|(!\d)|(\w+))')
# Every real keybinding has command+key adjacent; used to detect silent drops.
PANE_ANCHOR_RE = re.compile(r'\{command:"\w+",key:"')
# Digit families are generated, not written out, so their keys are template
# literals the static table cannot see:
#   `nR.map(e=>({command:`selectBrowserTab${e}`,key:`cmd+${e}`,…}))`
#   `[...nR,"0"].flatMap(e=>{let t=e==="0"?"newPreset":`selectPreset${e}`;…})`
# They are expanded over the digit list and tagged `tpl` — hidden from the rendered
# table (⌘1…9 as nine rows is noise) but still found by the modal rows that look
# them up through the pane-table helpers ("Select preset", "Jump to Browser tab").
PANE_TPL_RE = re.compile(
    r'\{command:(?:`([^`]*)`|(\w+)),key:`([^`]*)`'
    r'((?:,\w+:(?:"[^"]*"|`[^`]*`|!\d|\w+))*)\}')
PANE_MAP_RE = re.compile(
    r'(?:\[\.\.\.(\w+)(?:,"([^"]*)")?\]|(?<![\w$])(\w+))\.(?:flatMap|map)\(')
PANE_ALT_RE = re.compile(r'let \w+=\w+==="([^"]*)"\?"(\w+)":`([^`]*)`')
PLACEHOLDER_RE = re.compile(r'\$\{\w+\}')
PANE_KEEP = ("when", "gate", "matchBy")


def pane_table(src):
    out = []
    for body in PANE_ENTRY_RE.findall(src):
        attrs = {}
        for name, quoted, bang, bare in PANE_ATTR_RE.findall(body):
            attrs[name] = quoted if quoted else (bang or bare)
        if "key" not in attrs:
            continue
        e = {"command": attrs["command"], "key": unescape(attrs["key"])}
        if "mac" in attrs:
            e["mac"] = attrs["mac"] == "!0"
        for k in PANE_KEEP:
            if attrs.get(k):
                e[k] = attrs[k]
        out.append(e)

    out += pane_families(src)

    anchors = len(PANE_ANCHOR_RE.findall(src))
    if out and len(out) < anchors:
        print(f"WARN: pane table parsed {len(out)} of {anchors} keybinding entries "
              "— an entry shape changed; extract.py needs updating. The missing "
              "rows are NOT removed shortcuts.", file=sys.stderr)
    return out


def pane_families(src):
    """Expand the generated digit families into concrete `tpl` entries."""
    out = []
    for m in PANE_TPL_RE.finditer(src):
        cmd_tpl, cmd_var, key_tpl, tail = m.groups()
        head = src[max(0, m.start() - 600):m.start()]
        anchor = None
        for a in PANE_MAP_RE.finditer(head):
            anchor = a
        if anchor is None:
            continue
        listvar = anchor.group(1) or anchor.group(3)
        lit = re.search(r'(?<![\w$])' + re.escape(listvar) + r'=\[((?:"[^"]*",?)+)\]', src)
        if not lit:
            continue
        values = QUOTED_RE.findall(lit.group(1))
        if anchor.group(2):  # `[...nR,"0"]`
            values.append(anchor.group(2))
        alt = PANE_ALT_RE.search(head) if cmd_var else None
        if cmd_var and alt is None:
            continue
        if alt:
            cmd_tpl = alt.group(3)
        attrs = {}
        for name, quoted, bang, bare in PANE_ATTR_RE.findall(tail):
            attrs[name] = quoted if quoted else (bang or bare)
        for v in values:
            command = (alt.group(2) if alt and v == alt.group(1)
                       else PLACEHOLDER_RE.sub(v, cmd_tpl))
            e = {"command": command, "key": PLACEHOLDER_RE.sub(v, key_tpl), "tpl": True}
            if "mac" in attrs:
                e["mac"] = attrs["mac"] == "!0"
            for k in PANE_KEEP:
                if attrs.get(k):
                    e[k] = attrs[k]
            out.append(e)
    return out


# --- 2. command registry ------------------------------------------------------

# Entries without a `shortcut` must NOT swallow the next entry's bindings, so the
# skipped span may not cross another `description:` — each entry has exactly one.
# Both halves ship in several shapes and an unhandled one drops a whole command
# (1.52386.6 moved the copy-link entries to a hoisted array, and the palette /
# sidebar entries to a default-table helper):
#   description: `NP.description` or `Xz.show`  -- hoisted message object, any field
#                `{defaultMessage:"Ant tools"…}` -- inline
#   bindings:    `[{key:"j",…}]`      -- inline array
#                `lB`                 -- hoisted array, shared by several commands
#                `dh("command_palette")` -- built from the default-shortcut table
REG_RE = re.compile(
    r'(\w+):\{description:(?:([\w$]+)\.(\w+)|\{defaultMessage:"([^"]*)")'
    r',(?:(?!description:)[\s\S]){0,400}?'
    r'shortcut:\{bindings:(?:\[(.*?)\]\}|([\w$]+)\}|(\w+)\("(\w+)"\)\})'
)
# Every command that declares a shortcut, used to detect silent drops.
REG_ANCHOR_RE = re.compile(r'shortcut:\{bindings:')
# `app:"web"` bindings never fire in the desktop app, so they must be dropped the
# same way `platform:"non-mac"` is — otherwise one command lists two keys and the
# web-only one looks like a real desktop shortcut.
BIND_RE = re.compile(
    r'key:"([^"]+)"(?:,code:"[^"]*")?,modifiers:\[([^\]]*)\]'
    r'(?:,platform:"([^"]*)")?(?:,app:"([^"]*)")?'
)
# `function dh(e){let{key:t,shift:n}=uh[e]…}` over
# `var uh={command_palette:{key:"k"},search_palette:{key:"k",shift:!0}…}` — the
# palette and sidebar keys live in that table instead of in a binding array.
DEFAULT_FN_RE = re.compile(r'function (\w+)\(\w\)\{let\{key:\w+,shift:\w+\}=(\w+)\[\w\]')
DEFAULT_ENTRY_RE = re.compile(r'(\w+):\{key:"([^"]+)"(,shift:!0)?\}')


def hoisted(src, name):
    """`lB=[{…},{…}]` — the array body; one level of nesting (modifiers:[…])."""
    m = re.search(r'(?<![\w$])' + re.escape(name)
                  + r'=(\[(?:[^\[\]]|\[[^\[\]]*\])*\])', src)
    return m.group(1) if m else None


def default_tables(src):
    """{helper: {command id: (key, shift)}} for `bindings:dh("id")`."""
    out = {}
    for fn, table in DEFAULT_FN_RE.findall(src):
        body = re.search(r'(?<![\w$])' + re.escape(table)
                         + r'=(\{(?:[^{}]|\{[^{}]*\})*\})', src)
        if body:
            out[fn] = {i: (k, bool(sh))
                       for i, k, sh in DEFAULT_ENTRY_RE.findall(body.group(1))}
    return out


def label_for(src, var, field):
    """`Xz=Ql({show:{defaultMessage:"Show terminal"…` — labels are hoisted consts."""
    if not var:
        return None
    m = re.search(r'(?<![\w$])' + re.escape(var) + r'=[\w$]*\(\{[\s\S]{0,500}?'
                  r'(?<![\w$])' + re.escape(field) + r':\{defaultMessage:"([^"]*)"', src)
    return m.group(1) if m else None


def registry(src):
    defaults = default_tables(src)
    out, parsed = {}, 0
    for m in REG_RE.finditer(src):
        name, lvar, lfield, linline, inline, var, helper, arg = m.groups()
        parsed += 1
        keys = []
        if helper:
            entry = defaults.get(helper, {}).get(arg)
            if entry:
                key, shift = entry
                keys = ["+".join(["cmd"] + (["shift"] if shift else []) + [key])]
        else:
            binds = inline if inline is not None else hoisted(src, var)
            if binds is None:  # a hoisted array the regex could not follow
                parsed -= 1
                continue
            for key, mods, platform, app in BIND_RE.findall(binds):
                if platform == "non-mac" or app == "web":
                    continue
                mods = [x.strip('"') for x in mods.split(",") if x.strip()]
                combo = "+".join(mods + [unescape(key)])
                if combo not in keys:
                    keys.append(combo)
        if keys:
            label = linline if linline is not None else label_for(src, lvar, lfield)
            out[name] = {"keys": keys, "label": label or name}

    anchors = len(REG_ANCHOR_RE.findall(src))
    if out and parsed < anchors:
        print(f"WARN: registry parsed {parsed} of {anchors} commands that declare a "
              "shortcut — an entry shape changed; extract.py needs updating. The "
              "missing rows are NOT removed shortcuts.", file=sys.stderr)
    return out


# --- 3. Cmd+/ modal -----------------------------------------------------------

# Anchor on the `{` that opens the row's props so a row can never start mid-object,
# then take everything up to `,children:` as the key expression -- it may be a
# string, an array (whose members can contain `]`), a ternary, or a helper call
# like `RP("toggleTerminal",c)` / `LP("jumpNextPrompt",c,{promptJump:t})??[]`.
# The gap before the label must not cross another shortcut anchor, otherwise a row
# whose label is a variable (`children:t`) swallows the NEXT row's key.
# The key expression must not run past its own `,children:` either. A row whose
# label is a spread (`children:b(Y,{...UP.close})`) has no inline defaultMessage,
# and without that guard the key group backtracks across the whole row and steals
# the NEXT row's key + label.
# Three label shapes: an inline defaultMessage, a spread of a hoisted message
# object (`...UP.close`), or a remote string looked up by id (`b(wr,{id:"f6dc44"})`).
ROW_RE = re.compile(
    r'\{(?:shortcut:((?:(?!,children:|shortcut(?:Id)?:)[\s\S]){0,120}?)|shortcutId:"(\w+)")'
    r',children:((?:(?!shortcut(?:Id)?:)[\s\S]){0,120}?)'
    r'(?:defaultMessage:"([^"]*)"|\.\.\.([\w$]+)\.(\w+)\}|\bid:"([0-9a-z]{6})"\})'
)
# `UP=Ql({close:{defaultMessage:"Close split view"…})` — the spread label's source.
SPREAD_LABEL_RE = r'\b{}=\w+\(\{{[\s\S]{{0,400}}?\b{}:\{{defaultMessage:"([^"]*)"'
# `{shortcutString:_}=_n("amber_tributary_lantern_overview_toggle")` — the key of a
# feature-gated row is a local bound to a registry id, not a literal.
SHORTCUT_STR_RE = re.compile(r'\{shortcutString:(\w+)\}=\w+\("(\w+)"\)')
# `b=Bz("reopenClosed",c)` — a pane-table helper call hoisted into a local that
# several rows then use as `shortcut:b`. Matched by shape because the helper names
# are mangled and reshuffle every release; resolved through find_helpers().
HELPER_VAR_RE = re.compile(r'(?<![\w$])(\w+)=(\w+)\("(\w+)",\w+(?:,[^)]*)?\)')
# `{shortcutString:t,description:n}=d_()` — both halves of the row come from a hook
# imported from another chunk, so neither the key nor the label is in this file.
HOOK_ROW_RE = re.compile(r'\{shortcutString:(\w+),description:(\w+)\}=(\w+)\(\)')
# `e=Mn("new_session_pane_right")` then `{shortcut:e.shortcutString,children:
# e.description}` — both halves of the row come straight from the registry entry.
REGVAR_RE = re.compile(r'(?<![\w$])(\w+)=\w+\("(\w+)"\)')
FIELD_ROW_RE = re.compile(r'\{shortcut:(\w+)\.shortcutString,children:\1\.description\}')
# `` shortcut:`${n}+q` `` with `function ER(){return kr()?"alt":"ctrl"}` — the
# modifier is picked at runtime; the mac branch is the first string, as everywhere.
MODFN_RE = re.compile(r'function (\w+)\(\)\{return \w+\(\)\?"([^"]+)":"[^"]+"\}')
MODVAR_RE = re.compile(r'(?<![\w$])(\w+)=(\w+)\(\)[,;]')
# `var RR="cmd+b"` / `let t=Yi(),n="cmd+r"` — a key written straight into a local
# instead of into the row. Without this the row renders the identifier (`RR`).
# The value guard keeps the pattern from picking up every `x.title="…"` assignment
# in the segment: only a key-shaped string can be a shortcut.
LOCAL_STR_RE = re.compile(r'(?<![\w$])(\w+)=("[a-z0-9+]+")[,;)]')
KEYISH_RE = re.compile(r'[a-z0-9]+(?:\+[a-z0-9]+)*$')
TEMPLATE_RE = re.compile(r'^`\$\{(\w+)\}([^`]*)`$')
# `{shortcut:`${n}+q`,children:A(dr,{id:r})}` with `r="1eodd8i"` — a remote label
# looked up through a local, which the inline-id branch of ROW_RE cannot see.
REMOTE_ROW_RE = re.compile(
    r'\{shortcut:(`[^`]*`|"[^"]*"|\w+),children:\w+\(\w+,\{id:(\w+)\}\)\}')
IDVAR_RE = re.compile(r'(?<![\w$])(\w+)="([0-9a-z]{6,8})"[,;]')
# `n.replace(/1$/,"1\u20269")` — the preset/tab rows widen a single key to a range.
REPLACE_RE = re.compile(r'^(.*)\.replace\(/1\$/,"([^"]*)"\)$')
# `import{vr as d_}from"./shared-12-BzDv77xE.js"` — followed to find that hook.
IMPORT_RE = re.compile(r'import\{([^}]*)\}from"\./([\w.\-]+\.js)"')


def hook_registry_id(src, hook):
    """Follow `import{X as hook}from"./chunk.js"` -> that chunk's `Y as X` export ->
    the registry id the hook wraps (`return $e("toggle_dictation",…)`)."""
    for names, fname in IMPORT_RE.findall(src):
        m = re.search(r'(?<![\w$])(\w+) as ' + re.escape(hook) + r'(?![\w$])', names)
        if not m:
            continue
        path = ASSETS / fname
        if not path.is_file():
            return None
        other = path.read_text(errors="ignore")
        # The import name is the export alias; the export list sits at the end.
        exp = re.findall(r'(?<![\w$])(\w+) as ' + re.escape(m.group(1)) + r'(?![\w$])', other)
        if not exp:
            return None
        fn = re.search(r'function ' + re.escape(exp[-1]) + r'\(', other)
        if not fn:
            return None
        ids = re.findall(r'\("([a-z][a-z0-9_]{3,})"', other[fn.start():fn.start() + 2000])
        return ids[0] if ids else None
    return None
# Count of rows the modal actually renders, used to detect silent drops.
ROW_ANCHOR_RE = re.compile(r'\{shortcut(?:Id)?:')
# A row whose label was hoisted into a local (`let t=j(Z,{defaultMessage:"Settings"…});
# return e?$({shortcut:"cmd+,",children:t}):$({shortcutId:"settings",children:t})`).
# Both branches are the same row, so the first (desktop) one wins.
VAR_ROW_RE = re.compile(
    r'\{(?:shortcut:([\s\S]{0,120}?)|shortcutId:"(\w+)"),children:(\w+)\}'
)
VAR_LABEL_RE = r'\b{}=[^;]{{0,80}}?defaultMessage:"([^"]*)"'


def groups(m):
    """`m.groups()` with None replaced by "" — the row parsers test group emptiness
    and `findall()` (which these loops used before they needed match offsets) never
    handed them None."""
    return tuple(g or "" for g in m.groups())


def modal_rows(src, reg=None):
    # Anchor on the modal's own row, not on the label "Keyboard shortcuts" — that
    # string also appears as a help-menu item in a different (larger) chunk, and
    # chunks are scanned largest-first.
    anchors = [m.start() for m in re.finditer(r'shortcutId:"shortcuts_modal"', src)]
    if not anchors:
        return []
    seg = src[max(0, anchors[0] - 20000): anchors[-1] + 20000]
    # The segment spans every component that renders part of the modal, and they all
    # use the same mangled single letters, so a name is not unique within it: `n` is
    # `CR("selectPreset1",…)` in one component and the literal `"cmd+r"` in the next.
    # Bindings are therefore recorded WITH their offset and resolved against the
    # row's own offset — nearest binding before the row wins. A flat dict here made
    # "Reload page in Browser" come out as ⌘⌥1 (selectPreset1) instead of ⌘R.
    binds = {}

    def bind(name, pos, value):
        binds.setdefault(name, []).append((pos, value))

    for m in SHORTCUT_STR_RE.finditer(seg):
        bind(m.group(1), m.start(), f"@{m.group(2)}")
    for m in HELPER_VAR_RE.finditer(seg):
        bind(m.group(1), m.start(), f'{m.group(2)}("{m.group(3)}")')
    for m in LOCAL_STR_RE.finditer(seg):
        value = m.group(2).strip('"')
        if KEYISH_RE.fullmatch(value):
            bind(m.group(1), m.start(), value)
    # A hook row carries both halves: its key resolves through the registry id and
    # its label is the registry's own description.
    hooklabels = {}
    for m in HOOK_ROW_RE.finditer(seg):
        kvar, lvar, hook = m.groups()
        rid = hook_registry_id(src, hook)
        if rid is None:
            continue
        bind(kvar, m.start(), f"@{rid}")
        hooklabels[lvar] = (reg or {}).get(rid, {}).get("label", rid)
    for cands in binds.values():
        cands.sort()

    def nearest(name, at):
        """The binding of `name` closest above `at`; a module-level const declared
        below its use (hoisted `var`) falls back to the first one."""
        cands = binds.get(name)
        if not cands:
            return None
        before = [v for pos, v in cands if pos < at]
        return before[-1] if before else cands[0][1]
    # Locals holding a registry entry, and locals holding a platform modifier.
    regvars = {loc: rid for loc, rid in REGVAR_RE.findall(seg) if rid in (reg or {})}
    modfns = dict(MODFN_RE.findall(src))
    modvars = {loc: modfns[fn] for loc, fn in MODVAR_RE.findall(seg) if fn in modfns}

    def local(key, at):
        """`b` / `_??[]` -> the key, registry id, helper call or array it was bound
        to at offset `at` (the row's own position; see `binds` above)."""
        m = TEMPLATE_RE.match(key)  # `${n}+q` -> "alt+q"
        if m and m.group(1) in modvars:
            return modvars[m.group(1)] + m.group(2)
        m = re.fullmatch(r"(\w+)(\..+)", key)  # `n.replace(/1$/,…)`
        if m:
            head = local(m.group(1), at)
            return head + m.group(2) if head != m.group(1) else key
        bare = key[:-4] if key.endswith("??[]") else key
        found = nearest(bare, at)
        if found is not None:
            return found
        # A bare identifier can also be a hoisted array of alternatives (Ig=["a","b"]).
        if re.fullmatch(r"[A-Za-z_$]\w*", bare):
            arr = re.search(rf'\b{re.escape(bare)}=\[("[^\]]*")\]', src)
            if arr:
                return "[" + arr.group(1) + "]"
        return key

    out = []
    for row in ROW_RE.finditer(seg):
        # `groups()` yields None for a group that did not participate, where
        # `findall()` used to yield "" — every branch below tests emptiness.
        shortcut, sid, _gap, label, sp_var, sp_key, remote = groups(row)
        if not label and sp_var:
            # `_n.description` where `_n=Mn("<registry id>")`. Only `description`:
            # any other field is a message object's own key, and single-letter
            # locals collide across components.
            if sp_key == "description" and sp_var in regvars:
                label = (reg or {})[regvars[sp_var]]["label"]
            else:
                m = re.search(SPREAD_LABEL_RE.format(re.escape(sp_var), re.escape(sp_key)), src)
                # The object may be a local (a prop), so fall back to the field
                # name — but only a distinctive one; `description` matches anything.
                if not m and sp_key != "description":
                    m = bundle_search(r'(?<![\w$])' + re.escape(sp_key)
                                      + r':\{defaultMessage:"([^"]*)"')
                label = m.group(1) if m else f"{sp_var}.{sp_key}"
        label = label.encode().decode("unicode_escape")
        if not label and remote:
            # Label ships from the server, not the bundle; keep the id so the row
            # still shows up instead of silently vanishing. Applied after the
            # escape decode — running non-ASCII text through it mangles it.
            label = f"[远程文案 {remote}]"
        if sid and label == f"{sp_var}.{sp_key}" and sid in (reg or {}):
            # `{shortcutId:"new_code_session_from_current",children:{..._n.description}}`
            # — the label object is a local, but the row names its registry entry.
            label = reg[sid]["label"]
        key = shortcut.strip('"') if shortcut else f"@{sid}"
        out.append({"label": label, "key": local(key, row.start())})

    # A remote label addressed through a local (`{id:r}` with `r="1eodd8i"`).
    idvars = dict(IDVAR_RE.findall(seg))
    for row in REMOTE_ROW_RE.finditer(seg):
        shortcut, var = groups(row)
        if var not in idvars:
            continue
        out.append({"label": f"[远程文案 {idvars[var]}]",
                    "key": local(shortcut.strip('"'), row.start())})

    # `{shortcut:e.shortcutString,children:e.description}` — key and label both
    # come from the registry entry the local was bound to.
    for var in FIELD_ROW_RE.findall(seg):
        rid = regvars.get(var)
        if rid is None:
            continue
        out.append({"label": (reg or {})[rid]["label"], "key": f"@{rid}"})

    seen, dupes = {r["label"] for r in out}, 0
    for row in VAR_ROW_RE.finditer(seg):
        shortcut, sid, var = groups(row)
        label = hooklabels.get(var)
        if label is None:
            lab = re.search(VAR_LABEL_RE.format(re.escape(var)), seg)
            if not lab:
                continue
            label = lab.group(1).encode().decode("unicode_escape")
        if label in seen:  # the other branch of the same platform ternary
            dupes += 1
            continue
        seen.add(label)
        key = shortcut.strip('"') if shortcut else f"@{sid}"
        out.append({"label": label, "key": local(key, row.start())})

    rendered = len(ROW_ANCHOR_RE.findall(seg))
    if out and len(out) + dupes < rendered:
        print(f"WARN: modal parsed {len(out)} of {rendered} rendered rows — a row "
              "shape changed; extract.py needs updating. The missing rows are NOT "
              "removed shortcuts.", file=sys.stderr)
    return out


# --- collect ------------------------------------------------------------------

# Modal rows are JSX props, so a key can be an array, a platform ternary, or a
# `shortcutId` pointing into the registry. Normalise to a plain key string.
TERNARY_RE = re.compile(r'^\w+(?:\(\))?\?(?:\w+(?:\(\))?\?)?"([^"]+)"')
# The desktop branch of a ternary may itself be an array: n?["a","b"]:"b".
TERNARY_ARR_RE = re.compile(r'^\w+(?:\(\))?\?(\[(?:"[^"]*",?)+\])')
QUOTED_RE = re.compile(r'"([^"]+)"')
# Two minified helpers look a command up in the pane table at runtime; one takes
# the first hit, the other keeps them all. Their names are mangled and get
# reshuffled on every release (LP/RP -> VP/HP in 1.46388.4), so find them by body.
HELPER_RE = re.compile(r'^(\w+)\("(\w+)"')
HELPER_DEF_RE = re.compile(
    r'function (\w+)\((\w),(\w),(\w)\)\{return (\w+)\(\2,\3,\4\)\[0\]\}'
    r'function \5\([\s\S]{0,400}?\.command===[\s\S]{0,200}?\.push\(\w+\.key\)'
)


def find_helpers(src):
    """{minified name: 'first'|'all'} for the pane-table lookup helpers."""
    m = HELPER_DEF_RE.search(src)
    if not m:
        print("WARN: could not locate the pane-table lookup helpers — modal rows "
              "that call them will show a raw JS expression; extract.py needs "
              "updating. Those rows are NOT removed shortcuts.", file=sys.stderr)
        return {}
    return {m.group(1): "first", m.group(5): "all"}


def pane_keys(command, pane):
    """Replay RP(): desktop is isClaudeApp+mac, gates are always shown."""
    keys = []
    for e in pane:
        if e["command"] != command:
            continue
        when = e.get("when")
        if when == "!isClaudeApp" or (when and when != "isClaudeApp"):
            continue
        if e.get("mac") is False:
            continue
        if e["key"] not in keys:
            keys.append(e["key"])
    return keys


def resolve_key(key, reg, pane=(), helpers=None):
    key = unescape(key)
    m = REPLACE_RE.match(key)
    if m:
        widened = unescape(m.group(2))
        resolved = resolve_key(m.group(1), reg, pane, helpers)
        return " / ".join(k[:-1] + widened if k.endswith("1") else k
                          for k in resolved.split(" / "))
    if key.startswith("@"):
        entry = reg.get(key[1:])
        if isinstance(entry, dict):
            return " / ".join(entry["keys"])
        return " / ".join(entry) if isinstance(entry, list) else key
    if key.startswith("["):
        return " / ".join(QUOTED_RE.findall(key))
    m = HELPER_RE.match(key)
    if m and m.group(1) in (helpers or {}):
        found = pane_keys(m.group(2), pane)
        first = helpers[m.group(1)] == "first"
        return found[0] if (first and found) else (" / ".join(found) or key)
    m = TERNARY_ARR_RE.match(key)
    if m:
        return " / ".join(QUOTED_RE.findall(m.group(1)))
    m = TERNARY_RE.match(key)  # desktop branch is always the first string
    return m.group(1) if m else key


MODAL_ANCHOR_RE = re.compile(r'shortcutId:"shortcuts_modal"')


def collect():
    data = {"version": app_version(), "pane": [], "registry": {}, "modal": []}
    helpers, modal_src = {}, None
    for _, src in chunks():
        if not data["pane"]:
            data["pane"] = pane_table(src)
        if not data["registry"]:
            data["registry"] = registry(src)
        if modal_src is None and MODAL_ANCHOR_RE.search(src):
            modal_src = src
        if data["pane"] and data["registry"] and modal_src is not None:
            break
    # The modal is parsed after the loop: a hook row resolves its key AND its label
    # through the registry, which lives in a different chunk than the modal.
    if modal_src is not None:
        data["modal"] = modal_rows(modal_src, data["registry"])
        helpers = find_helpers(modal_src)
    for row in data["modal"]:
        row["key"] = resolve_key(row["key"], data["registry"], data["pane"], helpers)
    return data


SECTIONS = ("pane", "registry", "modal")


def flatten(snap):
    """{section: {stable_id: (display_label, key_string)}} — the diff/render unit."""
    out = {s: {} for s in SECTIONS}

    for e in snap.get("pane", []):
        if e.get("tpl"):  # generated digit family: lookup-only, never rendered
            continue
        # Same command binds different keys per platform/context, so `when`/`mac`
        # are part of the identity — otherwise the variants overwrite each other.
        ident = e["command"]
        for extra in ("when", "mac", "gate"):
            if extra in e:
                ident += f"@{e[extra]}"
        # `when:"!isClaudeApp"` fires only in the web app and `mac:false` only off
        # macOS — without the tag they read as live desktop keys on this machine.
        tag = ""
        if e.get("when") == "!isClaudeApp":
            tag = "（仅网页版）"
        elif e.get("mac") is False:
            tag = "（仅非 mac）"
        # One command can bind several keys in the same context (⌫ and delete
        # for sketchDeleteSelection), and they share an identity — aggregate them
        # instead of letting the last one win, so a key change still reads as ✏️
        # rather than as an addition plus a removal.
        prev = out["pane"].get(ident)
        keys = prev[1].split(" / ") if prev else []
        key = unescape(e["key"])  # older snapshots stored the escaped form
        if key not in keys:
            keys.append(key)
        out["pane"][ident] = (e["command"] + tag, " / ".join(keys))

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
    # Bindings behind a hoisted array (`bindings:lB`) or the default-shortcut table
    # (`bindings:dh("command_palette")`) must resolve, not vanish.
    assert any(k.startswith("copy_") for k in live["registry"]), \
        "hoisted binding arrays no longer resolve"
    assert live["registry"].get("command_palette", {}).get("keys") == ["cmd+k"], \
        "default-table bindings no longer resolve"
    # A modal key left as a bare identifier means a local was never followed —
    # single-word key literals (enter, esc, …) are not identifiers in that sense.
    LITERAL = set(PRETTY) | {"enter", "esc", "escape", "space", "delete", "tab",
                             "backspace", "esc esc"}
    stray = [r for r in live["modal"]
             if re.fullmatch(r"[A-Za-z_$]\w*", r["key"]) and r["key"] not in LITERAL]
    assert not stray, f"unresolved modal locals: {stray}"
    probe = {s: {} for s in SECTIONS}
    probe["modal"][next(iter(flatten(live)["modal"]))] = "added"
    assert "🆕" in render(live, probe, []), "render dropped the change marker"
    print("ok — diff + render + live extraction pass;",
          {k: len(v) for k, v in live.items() if k != "version"})


if __name__ == "__main__":
    sys.exit(demo() if "--demo" in sys.argv else main())

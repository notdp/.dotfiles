#!/usr/bin/env python3
"""Extract Claude Code Desktop keyboard shortcuts and diff against the last
snapshot. Silent (exit 0, no output) when nothing changed.

The app stopped shipping its UI locally in 6.x: Contents/Resources/ion-dist is
now a one-page "Claude was updated" placeholder, and the packed
main_window/index.html says in so many words that "everything else gets loaded
from claude.ai". The renderer bundle is fetched from assets-proxy.anthropic.com
and lands in Electron's HTTP cache, so that cache is the source now.

Cache entries are Chromium "simple cache" files: a 24-byte header, the request
URL as the key, then the response body exactly as served — zstd, in practice.

The catch worth remembering: this corpus is "every chunk this Mac loaded
recently", not a complete bundle. A screen nobody opened can be missing
entirely, and `--sources` prints which chunk each section came from and how old
it is so that case is visible rather than silent.

Sources (located by content, never by file name — names carry a build hash):
  1. pane/composer table   -- array of {command,key,code,when,mac,gate,matchBy}
  2. command registry      -- {name:{description,...,shortcut:{bindings:[...]}}}
  3. shortcuts modal       -- rows rendered in the Cmd+/ dialog
"""

import json
import os
import plistlib
import re
import struct
import sys
import time
import zlib
from compression import zstd  # stdlib, Python 3.14+
from pathlib import Path

APP = Path("/Applications/Claude.app")
CACHE = Path.home() / "Library/Application Support/Claude/Cache/Cache_Data"
ASSET_PREFIX = "https://assets-proxy.anthropic.com/claude-ai/"
SNAPSHOT = Path(__file__).with_name("snapshot.json")

# Sections whose parse came out incomplete this run. A row this script
# failed to read is not a shortcut that was taken away, so a section in
# here never contributes removals: the previous snapshot's rows are kept.
DRIFT = set()

# How far back to take cached chunks; 0 means no limit, which is the default.
# A window looks tempting and is a trap: reading an entry does not rewrite its
# file, so a chunk that is still current but was first fetched months ago keeps
# its old mtime, and any window quietly drops it (a 30-day one cost three of the
# modal chunk's imports). mtime says when a copy was written, never whether it
# is still part of the deployed build.
WINDOW_DAYS = float(os.environ.get("CCD_SHORTCUTS_CACHE_DAYS", "0"))

SIMPLE_CACHE_MAGIC = struct.pack("<Q", 0xFCFB6D1BA7725C30)
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GZIP_MAGIC = b"\x1f\x8b\x08"


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


def cache_key(head):
    """Request URL of a Chromium simple-cache entry, or None if the file is not
    one. Layout: magic u64, version u32, key_length u32, key_hash u32, four bytes
    of padding, then the key. An isolated entry prefixes the key with its cache
    partition (`1/0/https://…`), hence the search for the scheme rather than a
    fixed offset."""
    if not head.startswith(SIMPLE_CACHE_MAGIC):
        return None
    klen = struct.unpack_from("<I", head, 12)[0]
    if not 0 < klen <= 1000 or 24 + klen > len(head):
        return None
    key = head[24:24 + klen].decode("utf-8", "replace")
    i = key.find("https://")
    return key[i:] if i >= 0 else None


def decompress(blob):
    """Entry body as text. The body is stored as served, so it carries the
    response's content-encoding; zstd and gzip cover everything the asset host
    sends. The compressed stream is found by magic instead of by walking the
    stream layout — a magic that lands inside the header stream simply fails to
    decompress, so a few candidate offsets are tried before giving up."""
    for magic, expand in (
        (ZSTD_MAGIC, lambda b: zstd.ZstdDecompressor().decompress(b)),
        (GZIP_MAGIC, lambda b: zlib.decompress(b, 16 + zlib.MAX_WBITS)),
    ):
        at = blob.find(magic)
        for _ in range(4):
            if at < 0:
                break
            try:
                out = expand(blob[at:])
                if out:
                    return out.decode("utf-8", "replace")
            except Exception:
                pass
            at = blob.find(magic, at + 4)
    return blob.decode("utf-8", "replace")  # identity-encoded


# `shared-1-Br76wQvv.js` -> `shared-1`. The build hash is eight characters and
# may itself contain a dash (`shared-39-nl-1lpZw.js`, `shared-frame-CJfW4IE-.js`),
# so it is cut by length from the end rather than at the last dash.
HASHED_NAME_RE = re.compile(r"^(.*)-[A-Za-z0-9_-]{8}\.js$")


def logical_name(fname):
    m = HASHED_NAME_RE.match(fname)
    return m.group(1) if m else fname.removesuffix(".js")


_INDEX = None   # logical chunk name -> (path, mtime, file name)
_BY_FILE = {}   # "name-BUILDHASH.js" -> logical chunk name
_SRC = {}       # logical chunk name -> decompressed source


def index():
    """Newest cached copy of every asset chunk. The same logical chunk is cached
    once per build it was served from, so entries are collapsed by the name with
    the build hash stripped (`shared-1-Br76wQvv.js` -> `shared-1`) and the newest
    mtime wins."""
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    _INDEX = {}
    floor = time.time() - WINDOW_DAYS * 86400 if WINDOW_DAYS > 0 else 0
    if not CACHE.is_dir():
        return _INDEX
    for path in CACHE.iterdir():
        try:
            st = path.stat()
        except OSError:
            continue
        if not path.is_file() or st.st_mtime < floor:
            continue
        try:
            with open(path, "rb") as f:
                url = cache_key(f.read(1024))
        except OSError:
            continue
        if not url or not url.startswith(ASSET_PREFIX) or not url.endswith(".js"):
            continue
        fname = url.rsplit("/", 1)[-1]
        logical = logical_name(fname)
        _BY_FILE[fname] = logical
        prev = _INDEX.get(logical)
        if prev is None or st.st_mtime > prev[1]:
            _INDEX[logical] = (path, st.st_mtime, fname)
    return _INDEX


def chunk_mtime(fname):
    entry = index().get(_BY_FILE.get(fname) or logical_name(fname))
    return entry[1] if entry else None


def chunk_src(fname):
    """Source of one chunk by the file name an import spells it with, read once
    and kept. The build hash in that name may not be the copy the cache holds;
    another build of the same logical chunk is accepted, because what this
    resolves — an export list, a message object — survives a rebuild far better
    than it survives being absent."""
    logical = _BY_FILE.get(fname) or logical_name(fname)
    entry = index().get(logical)
    if entry is None:
        return None
    if logical not in _SRC:
        _SRC[logical] = decompress(entry[0].read_bytes())
    return _SRC[logical]


def bundle_search(pattern, literal=None):
    """First match of `pattern` anywhere in the cached bundle — labels for a row
    can live in a different chunk than the modal that renders it. `literal` is a
    plain substring every match must contain; it skips the regex on the chunks
    that cannot match, which is nearly all of them."""
    for _, src in chunks():
        if literal is not None and literal not in src:
            continue
        m = re.search(pattern, src)
        if m:
            return m
    return None


def chunks():
    """(file name, source) for every cached chunk, most recently fetched first.
    Ordering by recency rather than by size is what keeps a module that was
    dropped from the build months ago from answering before the chunk the app
    loaded this morning."""
    for logical, (path, _mtime, fname) in sorted(
            index().items(), key=lambda kv: -kv[1][1]):
        if logical not in _SRC:
            _SRC[logical] = decompress(path.read_bytes())
        yield fname, _SRC[logical]


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
        DRIFT.add("pane")
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
    # Minified names can contain `$` (`v$("command_palette")`), so every name
    # group here takes `[\w$]`, not `\w`.
    r'shortcut:\{bindings:(?:\[(.*?)\]\}|([\w$]+)\}|([\w$]+)\("([\w$]+)"\)\})'
)
# Every command that declares a shortcut, used to detect silent drops.
REG_ANCHOR_RE = re.compile(r'shortcut:\{bindings:')
# `app:"web"` bindings never fire in the desktop app, so they must be dropped the
# same way `platform:"non-mac"` is — otherwise one command lists two keys and the
# web-only one looks like a real desktop shortcut.
# One binding object, taken whole and read by field name. Spelling the fields
# out in order is what broke in 6.x: `matchBy:"char"` appeared between `code` and
# `modifiers`, the ordered pattern stopped matching, and sixteen commands —
# pin/rename/fork/archive_code_session and friends — silently lost their keys,
# which in turn left every modal row that looks them up unresolved.
BIND_OBJ_RE = re.compile(r'\{(key:"[^"]*"[^{}]*)\}')
BIND_FIELD_RE = re.compile(r'(\w+):(?:"([^"]*)"|\[([^\]]*)\])')


def bindings_of(text):
    """(key, modifiers, platform, app) for every binding object in `text`."""
    for body in BIND_OBJ_RE.findall(text):
        fields = {}
        for m in BIND_FIELD_RE.finditer(body):
            fields[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
        if "key" in fields:
            yield (fields["key"], fields.get("modifiers", ""),
                   fields.get("platform", ""), fields.get("app", ""))
# `function dh(e){let{key:t,shift:n}=uh[e]…}` over
# `var uh={command_palette:{key:"k"},search_palette:{key:"k",shift:!0}…}` — the
# palette and sidebar keys live in that table instead of in a binding array.
# The helper is sometimes a declaration and sometimes an assigned function
# expression (`v$=(function(e){let{key:t,shift:n}=TG[e]…` in 6.x), so both the
# name before `=` and the name after `function` are tried.
DEFAULT_FN_RE = re.compile(
    r'(?:function ([\w$]+)|([\w$]+)=\(?function\s*)\(\w\)\{'
    r'let\{key:\w+,shift:\w+\}=([\w$]+)\[\w\]')
DEFAULT_ENTRY_RE = re.compile(r'(\w+):\{key:"([^"]+)"(,shift:!0)?\}')


def hoisted(src, name):
    """`lB=[{…},{…}]` — the array body; one level of nesting (modifiers:[…])."""
    m = re.search(r'(?<![\w$])' + re.escape(name)
                  + r'=(\[(?:[^\[\]]|\[[^\[\]]*\])*\])', src)
    return m.group(1) if m else None


def default_tables(src):
    """{helper: {command id: (key, shift)}} for `bindings:dh("id")`."""
    out = {}
    for declared, assigned, table in DEFAULT_FN_RE.findall(src):
        fn = declared or assigned
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
            for key, mods, platform, app in bindings_of(binds):
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
        DRIFT.add("registry")
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
    r',children:((?:(?!shortcut(?:Id)?:|\}\)\s*,)[\s\S]){0,120}?)'
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
FIELD_ROW_RE = re.compile(
    r'\{shortcut:(\w+)\.shortcutString,children:(?:\w+\?[\s\S]{0,200}?:)?\1\.description\}')
# `let o=a()==="rtl"` — a row key or label picked by text direction. The LTR
# branch is the `else` one, the opposite of the platform ternaries.
RTL_VAR_RE = re.compile(r'(?<![\w$])(\w+)=\w+\(\)==="rtl"')
# The row's own `strip('"')` has already eaten the closing quote by the time
# the key gets here, hence the optional one.
RTL_TERNARY_RE = re.compile(r'^(\w+)\?"([^"]+)":"([^"]+)"?$')
FIELD_KEY_RE = re.compile(r'^(\w+)\.shortcutString$')
# `` shortcut:`${n}+q` `` with `function ER(){return kr()?"alt":"ctrl"}` — the
# modifier is picked at runtime; the mac branch is the first string, as everywhere.
MODFN_RE = re.compile(r'function (\w+)\(\)\{return \w+\(\)\?"([^"]+)":"[^"]+"\}')
MODVAR_RE = re.compile(r'(?<![\w$])(\w+)=(\w+)\(\)[,;]')
# `var RR="cmd+b"` / `let t=Yi(),n="cmd+r"` — a key written straight into a local
# instead of into the row. Without this the row renders the identifier (`RR`).
# The value guard keeps the pattern from picking up every `x.title="…"` assignment
# in the segment: only a key-shaped string can be a shortcut.
LOCAL_STR_RE = re.compile(r'(?<![\w$])(\w+)=("[a-z0-9+]+")[,;)\s]')
# `a=e?"cmd+alt+left":"cmd+alt+right"` — a ternary hoisted into a local, which
# the row then uses as `shortcut:a`. Resolved like an inline one.
_BRANCH = r'(?:\w+\?"[^"]*":"[^"]*"|"[^"]*")'
TERNARY_VAR_RE = re.compile(
    r'(?<![\w$])(\w+)=(\w+\?' + _BRANCH + r':' + _BRANCH + r')(?=[,;)\s])')
# `let t=/1$/,c=e.replace(t,"1…9")` — the regex literal is its own local now,
# so the widening call no longer carries it inline.
REPLACE_VAR_RE = re.compile(r'(?<![\w$])(\w+)=(\w+\.replace\(\w+,"[^"]*"\))')
# `u=["cmd+shift+]",...c,...l]` with `c=o?[]:["ctrl+tab"]` — the alternatives
# are spread in from locals instead of being written out in the array.
ARRAY_VAR_RE = re.compile(r'(?<![\w$])(\w+)=(?=\[)')
# `c=o?[]:["ctrl+tab"]` — one branch is empty, so the other is the live set.
ARRAY_TERNARY_VAR_RE = re.compile(
    r'(?<![\w$])(\w+)=(\w+\?\[[^\]]*\]:\[[^\]]*\])(?=[,;)\s])')
SPREAD_RE = re.compile(r'\.\.\.(\w+)')
# `` `${n}+q` `` reached through a ternary whose other branch is an array.
TEMPLATE_ANY_RE = re.compile(r'`\$\{(\w+)\}([^`]*)`')
# `i=r?["ctrl+tab",…,`${n}+q`]:`${n}+q`` — branches that are an array and a
# template, so neither the plain nor the array ternary binding sees it.
MIXED_TERNARY_VAR_RE = re.compile(r'(?<![\w$])(\w+)=(\w+\?\[[^\]]*\]:`[^`]*`)')
# `a=t(ie,{id:"1eodd8i"})` — a label the server ships, hoisted into a local.
REMOTE_VAR_RE = re.compile(r'(?<![\w$])(\w+)=\w+\(\w+,\{id:"([0-9a-z]{6,8})"\}\)')
KEYISH_RE = re.compile(r'[a-z0-9]+(?:\+[a-z0-9]+)*$')
TEMPLATE_RE = re.compile(r'^`\$\{(\w+)\}([^`]*)`$')
# `{shortcut:`${n}+q`,children:A(dr,{id:r})}` with `r="1eodd8i"` — a remote label
# looked up through a local, which the inline-id branch of ROW_RE cannot see.
REMOTE_ROW_RE = re.compile(
    r'\{shortcut:(`[^`]*`|"[^"]*"|\w+),children:\w+\(\w+,\{id:(\w+)\}\)\}')
IDVAR_RE = re.compile(r'(?<![\w$])(\w+)="([0-9a-z]{6,8})"[,;]')
# `n.replace(/1$/,"1\u20269")` — the preset/tab rows widen a single key to a range.
REPLACE_RE = re.compile(r'^(.*)\.replace\((?:/1\$/|\w+),"([^"]*)"\)$')
# `import{vr as d_}from"./shared-12-BzDv77xE.js"` — followed to find that hook.
IMPORT_RE = re.compile(r'import\{([^}]*)\}from"\./([\w.\-]+\.js)"')


def hook_registry_id(src, hook):
    """Follow `import{X as hook}from"./chunk.js"` -> that chunk's `Y as X` export ->
    the registry id the hook wraps (`return $e("toggle_dictation",…)`)."""
    for names, fname in IMPORT_RE.findall(src):
        m = re.search(r'(?<![\w$])([\w$]+) as ' + re.escape(hook) + r'(?![\w$])', names)
        if not m:
            continue
        other = chunk_src(fname)
        if other is None:
            return None
        # The import name is the export alias; the export list sits at the end.
        exp = re.findall(r'(?<![\w$])([\w$]+) as ' + re.escape(m.group(1)) + r'(?![\w$])', other)
        if not exp:
            return None
        fn = re.search(r'function ' + re.escape(exp[-1]) + r'\(', other)
        if not fn:
            return None
        ids = re.findall(r'\("([a-z][a-z0-9_]{3,})"', other[fn.start():fn.start() + 2000])
        return ids[0] if ids else None
    return None
def import_pairs(names):
    """`"Ha as e,aa as t,plain"` -> (exported name, local name) per binding."""
    for part in names.split(","):
        part = part.strip()
        m = re.fullmatch(r"([\w$]+) as ([\w$]+)", part)
        if m:
            yield m.group(1), m.group(2)
        elif re.fullmatch(r"[\w$]+", part):
            yield part, part


def internals_for(other, exported):
    """f.js's `internal as exported` export list -> the internal names. One export
    name can be re-exported from several internals (`ju as nt`, `q7 as nt`), so
    every candidate comes back and the caller picks the one that fits."""
    return re.findall(r"(?<![\w$])([\w$]+) as " + re.escape(exported) + r"(?![\w$])", other)


def imported_from(src, local):
    """`local` -> (defining chunk's source, [its internal names]) by following
    `import{X as local}from"./f.js"` into f.js's export list."""
    for names, fname in IMPORT_RE.findall(src):
        for exported, name in import_pairs(names):
            if name != local:
                continue
            other = chunk_src(fname)
            return (other, internals_for(other, exported)) if other else None
    return None


def spread_label(src, var, key):
    """`{...re.close}` -> the `defaultMessage` of `close` in the object `var` holds.
    The object may be declared in this chunk or imported from another one; in
    2.31226.1 the split-view labels moved out, and without the import hop the
    generic fallback picked up an unrelated "Close" from the biggest chunk."""
    m = re.search(SPREAD_LABEL_RE.format(re.escape(var), re.escape(key)), src)
    if m:
        return m.group(1)
    found = imported_from(src, var)
    if not found:
        return None
    other, internals = found
    for internal in internals:
        m = re.search(SPREAD_LABEL_RE.format(re.escape(internal), re.escape(key)), other)
        if m:
            return m.group(1)
    return None


def modifier_fns(src):
    """{name in `src`: the mac modifier it returns} for `function X(){return
    isSomething()?"alt":"ctrl"}`, declared here or imported."""
    out = dict(MODFN_RE.findall(src))
    for names, fname in IMPORT_RE.findall(src):
        other = chunk_src(fname)
        if other is None:
            continue
        defs = dict(MODFN_RE.findall(other))
        if not defs:
            continue
        for exported, local in import_pairs(names):
            for internal in internals_for(other, exported):
                if internal in defs:
                    out[local] = defs[internal]
    return out


# Count of rows the modal actually renders, used to detect silent drops.
ROW_ANCHOR_RE = re.compile(r'\{shortcut(?:Id)?:')
# A row whose label was hoisted into a local (`let t=j(Z,{defaultMessage:"Settings"…});
# return e?$({shortcut:"cmd+,",children:t}):$({shortcutId:"settings",children:t})`).
# Both branches are the same row, so the first (desktop) one wins.
VAR_ROW_RE = re.compile(
    r'\{(?:shortcut:([\s\S]{0,120}?)|shortcutId:"(\w+)"),children:(\w+)\}'
)
VAR_LABEL_RE = r'\b{}=[^;]{{0,80}}?defaultMessage:"([^"]*)"'
# After the memo unwrap a label is its own local too (`o=t(A,{defaultMessage:
# "Next sidebar tab",…})`), so it resolves by position like a key does rather
# than through the first match anywhere in the chunk.
LABEL_VAR_RE = re.compile(
    r'(?<![\w$])(\w+)=(?:\w+\?)?\w+\(\w+,\{(?:defaultMessage:"((?:[^"\\]|\\.)*)"|\.\.\.([\w$]+)\.(\w+)\})')


def groups(m):
    """`m.groups()` with None replaced by "" — the row parsers test group emptiness
    and `findall()` (which these loops used before they needed match offsets) never
    handed them None."""
    return tuple(g or "" for g in m.groups())


# 3.1623.0 compiled the modal through the React Compiler: every key and label is
# parked in a memo slot (`x=J1($,7,dep)?K1($,7,dep,<value>):$[8]`), so no binding
# regex below can see the value any more. These three unwrap that back into
# `x=<value>`, padded with spaces so every offset — and therefore `nearest()` —
# still lines up with the original source.
WRAP_RE = re.compile(r'(?<![\w$])([KIZ])(\d+)\(\$,\d+')
MEMO_COND = r'(?:J\d+\((?:[^()]|\([^()]*\))*\)(?:\s*(?:\|\||&&)\s*)?)+'
MEMO_ASSIGN_RE = re.compile(r'(?<![\w$])([\w$]+)=(' + MEMO_COND + r')$')
MEMO_SLOT_RE = re.compile(r':\$\[\d+\]')
CLOSERS = {')': '(', ']': '[', '}': '{'}


def call_args(src, open_paren):
    """Top-level argument spans of the call whose `(` sits at `open_paren`."""
    depth, i, start, out, n = 0, open_paren, open_paren + 1, [], len(src)
    while i < n:
        c = src[i]
        if c in '"\'`':
            q, i = c, i + 1
            while i < n and src[i] != q:
                i += 2 if src[i] == '\\' else 1
        elif c in '([{':
            depth += 1
        elif c in CLOSERS:
            depth -= 1
            if depth == 0:
                out.append(src[start:i])
                return out, i + 1
        elif c == ',' and depth == 1:
            out.append(src[start:i])
            start = i + 1
        i += 1
    return None, None


def unwrap_pass(src):
    """`K<n>($,slot,deps…,value)` -> value (it comes last); `I<n>`/`Z<n>` put the
    value third instead. A wrapper reached through `cond?…:$[n]` takes the whole
    conditional with it; a nested one (passed as an argument) collapses alone."""
    out, pos, changed = [], 0, False
    for m in WRAP_RE.finditer(src):
        if m.start() < pos:
            continue
        args, end = call_args(src, src.index('(', m.start()))
        if args is None or len(args) < 3:
            continue
        value = args[-1] if m.group(1) == 'K' else args[2]
        start, prefix = m.start(), ''
        if start and src[start - 1] == '?':
            a = MEMO_ASSIGN_RE.search(src, max(0, start - 600), start - 1)
            tail = MEMO_SLOT_RE.match(src, end)
            if a and tail:
                start, end, prefix = a.start(), tail.end(), a.group(1) + '='
        out.append(src[pos:start])
        out.append((prefix + value).ljust(end - start))
        pos, changed = end, True
    out.append(src[pos:])
    return ''.join(out), changed


def unwrap_memo(src):
    for _ in range(8):
        src, changed = unwrap_pass(src)
        if not changed:
            return src
    return src


def modal_rows(src, reg=None):
    # Anchor on the modal's own row, not on the label "Keyboard shortcuts" — that
    # string also appears as a help-menu item in a different (larger) chunk, and
    # chunks are scanned largest-first.
    anchors = [m.start() for m in re.finditer(r'shortcutId:"shortcuts_modal"', src)]
    if not anchors:
        return []
    # Padding keeps offsets identical, so the anchors above still point at the
    # same rows and `src` can be dropped in favour of the unwrapped text.
    src = unwrap_memo(src)
    seg = src[max(0, anchors[0] - 20000): anchors[-1] + 20000]
    # Every compiled component opens with `let $=J9(n)`. A binding only counts for
    # rows in its own component: the single-letter names repeat across components,
    # and a stale one handed "Next sidebar tab" the ⌘R of a later component.
    starts = [m.start() for m in re.finditer(r'J9\(', seg)]

    def component(at):
        prev = [p for p in starts if p <= at]
        return prev[-1] if prev else 0
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
    for m in TERNARY_VAR_RE.finditer(seg):
        bind(m.group(1), m.start(), m.group(2))
    for m in REPLACE_VAR_RE.finditer(seg):
        bind(m.group(1), m.start(), m.group(2))
    for m in MIXED_TERNARY_VAR_RE.finditer(seg):
        bind(m.group(1), m.start(), m.group(2))
    for m in ARRAY_TERNARY_VAR_RE.finditer(seg):
        bind(m.group(1), m.start(), m.group(2))
    for m in ARRAY_VAR_RE.finditer(seg):
        span, _end = call_args(seg, m.end())
        if span is not None:
            bind(m.group(1), m.start(), "[" + ",".join(span) + "]")
    labelbinds = {}
    for m in LABEL_VAR_RE.finditer(seg):
        name, msg, sp_var, sp_key = m.group(1), m.group(2), m.group(3), m.group(4)
        value = msg if msg is not None else f"...{sp_var}.{sp_key}"
        labelbinds.setdefault(name, []).append((m.start(), value))
    for m in REMOTE_VAR_RE.finditer(seg):
        labelbinds.setdefault(m.group(1), []).append(
            (m.start(), f"!{m.group(2)}"))  # `!` marks a label needing no decode
    for cands in labelbinds.values():
        cands.sort()
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
        """The binding of `name` closest above `at`, preferring one declared in the
        row's own component; a module-level const declared below its use (hoisted
        `var`) falls back to the first one."""
        cands = binds.get(name)
        if not cands:
            return None
        top = component(at)
        own = [v for pos, v in cands if top <= pos < at]
        if own:
            return own[-1]
        before = [v for pos, v in cands if pos < at]
        return before[-1] if before else cands[0][1]
    # Locals holding a registry entry, and locals holding a platform modifier.
    regvars = {loc: rid for loc, rid in REGVAR_RE.findall(seg) if rid in (reg or {})}
    rtlvars = [(m.start(), m.group(1)) for m in RTL_VAR_RE.finditer(seg)]

    def is_rtl(var, at):
        """`var` is the text-direction flag of the component that renders the row
        at `at`, so the declaration sits inside that same component."""
        top = component(at)
        return any(var == name and top <= pos < at for pos, name in rtlvars)
    modfns = modifier_fns(src)
    modvars = {loc: modfns[fn] for loc, fn in MODVAR_RE.findall(seg) if fn in modfns}

    def nearest_label(name, at):
        """The label local `name` held where the row sits. `...var.key` spreads go
        back through the registry/message-object lookups the inline rows use."""
        cands = labelbinds.get(name)
        if not cands:
            return None
        top = component(at)
        own = [v for pos, v in cands if top <= pos < at]
        if not own:
            # No cross-component fallback: a label is local to the component that
            # renders it, and reaching outside handed rows the wrong text.
            return None
        value = own[-1]
        if value.startswith("!"):
            return f"[远程文案 {value[1:]}]"
        if not value.startswith("..."):
            return value.encode().decode("unicode_escape")
        sp_var, sp_key = value[3:].split(".", 1)
        if sp_key == "description" and sp_var in regvars:
            return (reg or {})[regvars[sp_var]]["label"]
        found = spread_label(src, sp_var, sp_key)
        if found is None and sp_key != "description":
            m = bundle_search(r'(?<![\w$])' + re.escape(sp_key)
                              + r':\{defaultMessage:"([^"]*)"',
                              literal=sp_key + ':{defaultMessage:"')
            found = m.group(1) if m else None
        return found

    def expand(value, at, depth=0):
        """`["cmd+shift+]",...c,...l]` -> every alternative written out, following
        each spread into the local it names (`c=o?[]:["ctrl+tab"]`: a branch that
        is empty carries nothing, so the other one is the live set)."""
        if depth > 3 or not value.startswith("["):
            return value
        parts = []
        for item in value[1:-1].split(","):
            item = item.strip()
            m = SPREAD_RE.fullmatch(item)
            if not m:
                if item:
                    parts.append(item)
                continue
            inner = nearest(m.group(1), at)
            if inner is None:
                continue
            for branch in re.split(r'[?:]', inner):
                branch = branch.strip()
                if branch.startswith("[") and branch != "[]":
                    parts.extend(expand(branch, at, depth + 1)[1:-1].split(","))
        return "[" + ",".join(p for p in parts if p) + "]"

    def resolve_local(key, at):
        """`local()` plus the direction ternary a resolved local can turn out to be;
        the platform ternaries keep their first branch, an RTL one its `else`."""
        for _ in range(3):  # `c=e.replace(…)` with `e=y("selectPreset1",…)`: a
            widened = local(key, at)  # binding can name another binding
            if widened == key:
                break
            key = widened
        key = expand(key, at)
        m = RTL_TERNARY_RE.match(key)
        if m and is_rtl(m.group(1), at):
            return m.group(3)
        if not key.startswith("[") and "`" in key:
            # A ternary with a template in one branch: the modifier is picked at
            # runtime and the mac branch is the first string, as everywhere else.
            m = TEMPLATE_ANY_RE.search(key)
            if m and m.group(1) in modvars:
                return modvars[m.group(1)] + m.group(2)
        return key

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
            arr = re.search(rf'\b{re.escape(bare)}=\[("[^\]]*")\]', seg)
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
                found = spread_label(src, sp_var, sp_key)
                # The object may be a local (a prop), so fall back to the field
                # name — but only a distinctive one; `description` matches anything.
                if found is None and sp_key != "description":
                    m = bundle_search(r'(?<![\w$])' + re.escape(sp_key)
                                      + r':\{defaultMessage:"([^"]*)"',
                                      literal=sp_key + ':{defaultMessage:"')
                    found = m.group(1) if m else None
                label = found if found is not None else f"{sp_var}.{sp_key}"
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
        if FIELD_KEY_RE.match(key) and FIELD_KEY_RE.match(key).group(1) in regvars:
            # `{shortcut:t.shortcutString,children:<rtl>?"…":t.description}` — the
            # FIELD_ROW_RE pass below renders this row from its registry entry;
            # here only the RTL label is in reach.
            continue
        out.append({"label": label, "key": resolve_local(key, row.start())})

    # A remote label addressed through a local (`{id:r}` with `r="1eodd8i"`).
    idvars = dict(IDVAR_RE.findall(seg))
    for row in REMOTE_ROW_RE.finditer(seg):
        shortcut, var = groups(row)
        if var not in idvars:
            continue
        out.append({"label": f"[远程文案 {idvars[var]}]",
                    "key": resolve_local(shortcut.strip('"'), row.start())})

    # `{shortcut:e.shortcutString,children:e.description}` — key and label both
    # come from the registry entry the local was bound to.
    for var in FIELD_ROW_RE.findall(seg):
        rid = regvars.get(var)
        if rid is None:
            continue
        out.append({"label": (reg or {})[rid]["label"], "key": f"@{rid}"})

    seen, dupes, unlabelled = {r["label"] for r in out}, 0, []
    for row in VAR_ROW_RE.finditer(seg):
        shortcut, sid, var = groups(row)
        label = hooklabels.get(var)
        if label is None:
            label = nearest_label(var, row.start())
        if label is None:
            # Scoped to the row's own component: the single-letter names repeat,
            # and a chunk-wide search handed one row another component's label.
            top = component(row.start())
            lab = re.search(VAR_LABEL_RE.format(re.escape(var)), seg[top:])
            if not lab or top + lab.start() > row.start():
                unlabelled.append(resolve_local(shortcut.strip('"'), row.start())
                                  if shortcut else f"@{sid}")
                continue
            label = lab.group(1).encode().decode("unicode_escape")
        key = shortcut.strip('"') if shortcut else f"@{sid}"
        m = FIELD_KEY_RE.match(key)
        if m and m.group(1) in regvars:
            # `{shortcut:e.shortcutString,children:<rtl label>}` — key and label
            # both belong to the registry entry `e` was bound to.
            rid = regvars[m.group(1)]
            label, key = (reg or {})[rid]["label"], f"@{rid}"
        if label in seen:  # the other branch of the same platform ternary
            dupes += 1
            continue
        seen.add(label)
        out.append({"label": label, "key": resolve_local(key, row.start())})

    if unlabelled:
        DRIFT.add("modal")
        print(f"WARN: modal rows whose label did not resolve ({len(unlabelled)}), "
              "keys: " + ", ".join(unlabelled)
              + " — their label is passed in as a prop and extract.py cannot follow "
                "it yet. Those rows are NOT removed shortcuts.", file=sys.stderr)
    stray = [r["label"] for r in out
             if BARE_IDENT_RE.fullmatch(r["key"]) and r["key"] not in LITERAL_KEYS]
    if stray:
        DRIFT.add("modal")
        print(f"WARN: modal rows whose key stayed an identifier ({len(stray)}): "
              + ", ".join(stray[:8])
              + " — a binding shape changed; extract.py needs updating. Those rows "
                "are NOT removed shortcuts.", file=sys.stderr)
    rendered = len(ROW_ANCHOR_RE.findall(seg))
    if out and len(out) + dupes < rendered:
        DRIFT.add("modal")
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
# The "all" helper walks the pane table and collects every key bound to a
# command; the "first" helper is a one-liner that takes its first hit. They are
# matched apart and by name reference, because 6.x turned both into assigned
# function expressions, stopped keeping them adjacent, and put the "all" one
# first — the single pattern that spelled out `function FIRST…function ALL`
# matched none of that, which left every modal row that calls them unresolved.
HELPER_ALL_RE = re.compile(
    r'(?:function ([\w$]+)|([\w$]+)=\(?function\s*)\(\w+,\w+,\w+\)\{'
    r'[\s\S]{0,800}?\.command===[\s\S]{0,400}?\.push\(\w+\.key\)')
HELPER_FIRST_TPL = (r'(?:function ([\w$]+)|([\w$]+)=\(?function\s*)'
                    r'\(\w+,\w+,\w+\)\{return %s\(\w+,\w+,\w+\)\[0\]\}')


def helper_names(text):
    """{name: 'first'|'all'} for the two pane-table lookup helpers in `text`."""
    m = HELPER_ALL_RE.search(text)
    if not m:
        return {}
    every = m.group(1) or m.group(2)
    out = {every: "all"}
    first = re.search(HELPER_FIRST_TPL % re.escape(every), text)
    if first:
        out[first.group(1) or first.group(2)] = "first"
    return out


def find_helpers(src):
    """{name as `src` calls it: 'first'|'all'} for the pane-table lookup helpers.

    They used to be declared in the modal's own chunk. In 2.31226.1 they moved to
    a shared chunk and reach the modal through an import, so they are looked for
    here and in every chunk the modal imports from, then mapped back through the
    import alias (`C6` -> exported `R` -> local `g`)."""
    out = dict(helper_names(src))
    for names, fname in IMPORT_RE.findall(src):
        other = chunk_src(fname)
        if other is None:
            continue
        kinds = helper_names(other)
        if not kinds:
            continue
        for exported, local in import_pairs(names):
            for internal in internals_for(other, exported):
                if internal in kinds:
                    out[local] = kinds[internal]
    if not out:
        DRIFT.add("modal")
        print("WARN: could not locate the pane-table lookup helpers — modal rows "
              "that call them will show a raw JS expression; extract.py needs "
              "updating. Those rows are NOT removed shortcuts.", file=sys.stderr)
    return out


# The flags a pane entry's `when` is tested against here: the Claude desktop app
# on macOS. An unknown flag counts as off.
WHEN_ENV = {"isClaudeApp": True, "isMac": True,
            "isLinux": False, "isWindows": False, "isWeb": False}
WHEN_SAFE = re.compile(r"[\sTrueFalsandot()]+")


def when_true(expr):
    """`!isLinux` / `isClaudeApp || !isLinux` -> is this binding live on this
    machine. Whitelisting only `isClaudeApp` dropped the ⌥f5 diff-navigation keys."""
    if not expr:
        return True
    py = re.sub(r"[A-Za-z_]\w*", lambda m: str(WHEN_ENV.get(m.group(0), False)), expr)
    py = py.replace("||", " or ").replace("&&", " and ").replace("!", " not ")
    if not WHEN_SAFE.fullmatch(py):
        return True  # an unfamiliar shape: show the key rather than drop it
    try:
        return bool(eval(py, {"__builtins__": {}}, {}))
    except SyntaxError:
        return True


def pane_keys(command, pane):
    """Replay RP(): desktop is isClaudeApp+mac, gates are always shown."""
    keys = []
    for e in pane:
        if e["command"] != command:
            continue
        if not when_true(e.get("when")):
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
    if m:
        kind = (helpers or {}).get(m.group(1))
        found = pane_keys(m.group(2), pane)
        # An unrecognised helper name is still a pane-table lookup: every one of
        # them turns a command into the keys bound to it, and they differ only
        # in whether they keep the first hit. The names are minified locals that
        # get reshuffled every release, so when the alias is unknown but the
        # argument is a real pane command, go by the command. A call whose
        # argument is not one falls through untouched, as before.
        if kind is not None or found:
            return found[0] if (kind == "first" and found) else (" / ".join(found) or key)
    m = TERNARY_ARR_RE.match(key)
    if m:
        return " / ".join(QUOTED_RE.findall(m.group(1)))
    m = TERNARY_RE.match(key)  # desktop branch is always the first string
    return m.group(1) if m else key


# A key that came out as a bare name is an unresolved binding, not a shortcut —
# except for the handful of keys that really are spelled as a bare word.
BARE_IDENT_RE = re.compile(r'[A-Za-z_$][\w$]*')
LITERAL_KEYS = {"esc", "enter", "tab", "space", "delete", "backspace", "click",
                "up", "down", "left", "right", "home", "end", "pageup", "pagedown"}
LITERAL_KEYS |= {f"f{n}" for n in range(1, 13)}
MODAL_ANCHOR_RE = re.compile(r'shortcutId:"shortcuts_modal"')
# Characters no real key contains, so their presence means the row kept a scrap
# of JS: a helper call (`y("toggleExpandPane")??[]`), a registry id that nothing
# resolved (`@archive_code_session_chord`), a ternary. `.` and `]` are NOT here —
# ⌘. and ⌘⇧] are real keys.
UNRESOLVED_CHARS = '()"@{}'


def key_resolved(key):
    """Whether a modal key came out as a key and not as leftover source."""
    if not key:
        return False
    if any(c in key for c in UNRESOLVED_CHARS):
        return False
    return not (BARE_IDENT_RE.fullmatch(key) and key.lower() not in LITERAL_KEYS)


# Which cached chunk each section was read from, for --sources and the staleness
# check. Filled by collect(); a section missing here was never found at all.
SOURCES = {}


def collect():
    data = {"version": app_version(), "pane": [], "registry": {}, "modal": []}
    helpers, modal_src = {}, None
    SOURCES.clear()
    # The cached corpus is thousands of chunks and a few hundred MB of text, and
    # the section parsers are expensive enough that running them on every chunk
    # costs minutes. A plain substring that every real hit must contain settles
    # it first; only a chunk that passes gets parsed.
    for fname, src in chunks():
        if not data["pane"] and '{command:"' in src:
            data["pane"] = pane_table(src)
            if data["pane"]:
                SOURCES["pane"] = fname
        if not data["registry"] and "shortcut:{bindings:" in src:
            data["registry"] = registry(src)
            if data["registry"]:
                SOURCES["registry"] = fname
        if (modal_src is None and 'shortcuts_modal' in src
                and MODAL_ANCHOR_RE.search(src)):
            modal_src = src
            SOURCES["modal"] = fname
        if data["pane"] and data["registry"] and modal_src is not None:
            break
    # The modal is parsed after the loop: a hook row resolves its key AND its label
    # through the registry, which lives in a different chunk than the modal.
    if modal_src is not None:
        data["modal"] = modal_rows(modal_src, data["registry"])
        helpers = find_helpers(modal_src)
    for row in data["modal"]:
        row["key"] = resolve_key(row["key"], data["registry"], data["pane"], helpers)
    # A row that still carries JS where its key should be would otherwise enter
    # the table as a brand-new shortcut called `y("toggleExpandPane")??[]`, and
    # push the real row out as removed. Drop it and let carry_forward put the
    # last known good row back.
    unresolved = [r for r in data["modal"] if not key_resolved(r["key"])]
    if unresolved:
        DRIFT.add("modal")
        data["modal"] = [r for r in data["modal"] if key_resolved(r["key"])]
        shown = ", ".join(f'{r["label"]}={r["key"]}' for r in unresolved[:4])
        print(f"WARN: dropped {len(unresolved)} modal row(s) whose key never "
              f"resolved ({shown}{', …' if len(unresolved) > 4 else ''}) — a key "
              "shape changed; extract.py needs updating. Those rows are NOT "
              "removed shortcuts.", file=sys.stderr)
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


def carry_forward(old, new, section):
    """Put back the rows the previous snapshot had and this run did not read.

    Called only for a section that reported drift. Without it an entry whose
    shape changed leaves the table as a removal, which is exactly the wrong
    story: the shortcut is still in the app, this script just stopped being able
    to see it. A shortcut that was genuinely dropped lingers one extra run as the
    price, and the WARN above says which section to trust less.
    """
    have = set(flatten(new)[section])
    kept = 0
    if section == "registry":
        for name, value in old.get("registry", {}).items():
            if name not in have:
                new["registry"][name] = value
                kept += 1
        return kept
    for entry in old.get(section, []):
        # Don't bring back a row that was already unreadable last time: an old
        # `b("newTerminal")` would sit in the table next to the real row the
        # moment this run learns to read it.
        if section == "modal" and not key_resolved(entry.get("key", "")):
            continue
        probe = {s: {} if s == "registry" else [] for s in SECTIONS}
        probe[section] = [entry]
        ids = set(flatten(probe)[section])
        if ids and not ids & have:
            new[section].append(entry)
            have |= ids
            kept += 1
    return kept


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
            # A row whose old "key" was a scrap of JS was never a shortcut, so
            # it leaving is this script getting better, not Anthropic removing
            # anything. Announcing it reads as a removal and it is not one.
            if not key_resolved(o[k][1]):
                continue
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


def report_sources(stream=sys.stderr):
    """One line per section naming the chunk it was read from. The date is when
    that copy was written to the cache, which is not the same as how current it
    is — a chunk unchanged across deploys is never rewritten. It is here to show
    which file a surprising row came out of, not to date the build."""
    for section in SECTIONS:
        fname = SOURCES.get(section)
        if not fname:
            print(f"source: {section:<8} NOT FOUND in the cached bundle", file=stream)
            continue
        mtime = chunk_mtime(fname)
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)) if mtime else "?"
        print(f"source: {section:<8} {fname}  cached {when}", file=stream)


def grep(pattern, context=240, limit=20):
    """Print matches of `pattern` across the cached bundle, with the chunk they
    came from. The weekly write-up has to look up what a command actually does,
    and the bundle is now zstd blobs in a cache directory, so hand-rolled greps
    find nothing — this is the way in."""
    rx = re.compile(pattern)
    found = 0
    for fname, src in chunks():
        for m in rx.finditer(src):
            lo, hi = max(0, m.start() - context), m.end() + context
            print(f"--- {fname} @{m.start()}\n{src[lo:hi]}\n")
            found += 1
            if found >= limit:
                print(f"[stopped at {limit} matches]")
                return 0
    if not found:
        print(f"no match for {pattern!r} in {len(index())} cached chunks")
    return 0


def main():
    if "--grep" in sys.argv:
        at = sys.argv.index("--grep")
        if at + 1 >= len(sys.argv):
            print("usage: extract.py --grep PATTERN", file=sys.stderr)
            return 2
        return grep(sys.argv[at + 1])

    if "--sources" in sys.argv:
        collect()
        report_sources(sys.stdout)
        return 0

    if not CACHE.is_dir():
        print(f"ERROR: {CACHE} not found — the app's HTTP cache is where the UI "
              "bundle lives now; has Claude.app ever run on this Mac?",
              file=sys.stderr)
        return 2
    if not index():
        print(f"ERROR: no claude-ai asset chunk cached in the last {WINDOW_DAYS:g} "
              f"days under {CACHE}. Use Claude for a minute and run this again, or "
              "widen CCD_SHORTCUTS_CACHE_DAYS. This is NOT shortcuts being removed.",
              file=sys.stderr)
        return 2

    new = collect()
    report_sources()
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
                DRIFT.discard(k)
                print(f"WARN: section '{k}' no longer parses; kept previous data. "
                      "extract.py likely needs updating.", file=sys.stderr)
        # A partially parsed section would otherwise report every row it failed
        # to read as a removed shortcut.
        for k in sorted(DRIFT):
            kept = carry_forward(old, new, k)
            if kept:
                print(f"WARN: carried {kept} previously known '{k}' row(s) forward "
                      "because this run could not parse them. They are NOT new and "
                      "NOT removed; extract.py needs updating.", file=sys.stderr)
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
    # Same alphabet collect() filters on, so the self-check and the run agree on
    # what counts as a key spelled as a bare word (f6, esc, enter).
    LITERAL = set(PRETTY) | LITERAL_KEYS | {"escape", "esc esc"}
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

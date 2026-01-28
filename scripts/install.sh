#!/bin/bash

set -euo pipefail

expand_path() {
    case "$1" in
        "~") echo "$HOME" ;;
        "~/"*) echo "$HOME/${1:2}" ;;
        *)    echo "$1" ;;
    esac
}

# 通过参数或环境变量指定安装目录，默认 ~/.dotfiles
if [ "${1:-}" != "" ]; then
    DOTFILES_DIR="$(expand_path "$1")"
else
    DOTFILES_DIR="$(expand_path "${DOTFILES_DIR:-$HOME/.dotfiles}")"
fi
COMMANDS_DIR="$DOTFILES_DIR/commands"
SKILLS_DIR="$DOTFILES_DIR/skills"
DROIDS_DIR="$DOTFILES_DIR/droids"
AGENTS_FILE="$DOTFILES_DIR/agents/AGENTS.md"

CONFIG_URL="${CONFIG_URL:-https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/config.json}"

DEFAULT_LINK_TARGETS=(
    "~/.claude/commands"
    "~/.codex/prompts"
    "~/.factory/commands"
    "~/.gemini/antigravity/global_workflows"
)

DEFAULT_SKILL_TARGETS=(
    "~/.claude/skills"
    "~/.codex/skills"
    "~/.factory/skills"
)

DEFAULT_AGENT_TARGETS=(
    "~/.claude/CLAUDE.md"
    "~/.factory/AGENTS.md"
    "~/.codex/AGENTS.md"
)

DEFAULT_DROID_TARGETS=(
    "~/.factory/droids"
)

log() { echo "[info] $*"; }
warn() { echo "[warn] $*" >&2; }
LINK_TARGETS=()
SKILL_TARGETS=()
DROID_TARGETS=()
AGENT_TARGETS=()

ensure_description() {
    local file="$1"
    local tmp desc end_line body

    # 无 front-matter，直接补齐三行规范格式
    if [ "$(head -n1 "$file" 2>/dev/null)" != "---" ]; then
        tmp="$(mktemp)"
        {
            echo "---"
            echo "description:"
            echo "---"
            echo ""
            cat "$file"
        } >"$tmp"
        mv "$tmp" "$file"
        log "补齐 front-matter（仅 description）: $file"
        return
    fi

    # 已有 front-matter，跳过不处理
    return
}

ensure_description_all() {
    shopt -s nullglob
    for file in "$COMMANDS_DIR"/*.md; do
        ensure_description "$file"
    done
    shopt -u nullglob
}

if command -v curl >/dev/null 2>&1; then
    REMOTE_CONFIG=$(curl -fsSL "$CONFIG_URL" 2>/dev/null || echo "")
    if [ -n "$REMOTE_CONFIG" ]; then
        if command -v jq >/dev/null 2>&1; then
            while IFS= read -r line; do
                [ -n "$line" ] && LINK_TARGETS+=("$line")
            done < <(echo "$REMOTE_CONFIG" | jq -r '.commands[]')
            while IFS= read -r line; do
                [ -n "$line" ] && SKILL_TARGETS+=("$line")
            done < <(echo "$REMOTE_CONFIG" | jq -r '.skills[]' 2>/dev/null)
            while IFS= read -r line; do
                [ -n "$line" ] && AGENT_TARGETS+=("$line")
            done < <(echo "$REMOTE_CONFIG" | jq -r '.agents[]' 2>/dev/null)
            while IFS= read -r line; do
                [ -n "$line" ] && DROID_TARGETS+=("$line")
            done < <(echo "$REMOTE_CONFIG" | jq -r '.droids[]' 2>/dev/null)
            if [ "${#LINK_TARGETS[@]}" -eq 0 ]; then
                warn "远端配置缺少 commands 或为空，使用默认链接目标"
            fi
        else
            warn "未找到 jq，无法解析远端配置，使用默认链接目标"
        fi
    else
        warn "获取远端配置失败，使用默认链接目标"
    fi
else
    warn "未找到 curl，无法获取远端配置，使用默认链接目标"
fi

if [ "${#LINK_TARGETS[@]}" -eq 0 ]; then
    LINK_TARGETS=("${DEFAULT_LINK_TARGETS[@]}")
fi

if [ "${#SKILL_TARGETS[@]}" -eq 0 ]; then
    SKILL_TARGETS=("${DEFAULT_SKILL_TARGETS[@]}")
fi

if [ "${#AGENT_TARGETS[@]}" -eq 0 ]; then
    AGENT_TARGETS=("${DEFAULT_AGENT_TARGETS[@]}")
fi

if [ "${#DROID_TARGETS[@]}" -eq 0 ]; then
    DROID_TARGETS=("${DEFAULT_DROID_TARGETS[@]}")
fi

mkdir -p "$DOTFILES_DIR" "$COMMANDS_DIR" "$SKILLS_DIR" "$DROIDS_DIR" "$(dirname "$AGENTS_FILE")"

# 如果源文件不存在，合并所有现有 agents 文件内容
if [ ! -f "$AGENTS_FILE" ]; then
    log "首次安装，合并现有 agents 文件内容..."
    touch "$AGENTS_FILE"
    for raw_file in "${AGENT_TARGETS[@]}"; do
        file="$(expand_path "$raw_file")"
        if [ -f "$file" ] && [ ! -L "$file" ]; then
            echo "" >> "$AGENTS_FILE"
            echo "# === 来自 $raw_file ===" >> "$AGENTS_FILE"
            cat "$file" >> "$AGENTS_FILE"
            log "合并内容: $file"
        fi
    done
fi

for raw_dir in "${LINK_TARGETS[@]}"; do
    dir="$(expand_path "$raw_dir")"

    # 已存在且已正确链接，跳过
    if [ -L "$dir" ]; then
        target="$(readlink "$dir")"
        if [ "$target" = "$COMMANDS_DIR" ]; then
            log "已存在软链: $dir -> $target"
            continue
        fi
        rm "$dir"
    elif [ -f "$dir" ]; then
        warn "跳过：$dir 是普通文件"
        continue
    elif [ -d "$dir" ]; then
        backup="${dir}.bak-$(date +%Y%m%d%H%M%S)"
        mv "$dir" "$backup"
        log "备份原目录 -> $backup"
        if command -v rsync >/dev/null 2>&1; then
            rsync -a --ignore-existing "$backup"/ "$COMMANDS_DIR"/ || warn "复制 $backup 时出错"
        else
            warn "未找到 rsync，使用 cp -an 复制，可能覆盖同名文件"
            cp -an "$backup"/. "$COMMANDS_DIR"/ || warn "复制 $backup 时出错"
        fi
    fi

    mkdir -p "$(dirname "$dir")"

    ln -s "$COMMANDS_DIR" "$dir"
    log "创建软链: $dir -> $COMMANDS_DIR"
done

for raw_dir in "${SKILL_TARGETS[@]}"; do
    dir="$(expand_path "$raw_dir")"

    if [ -L "$dir" ]; then
        target="$(readlink "$dir")"
        if [ "$target" = "$SKILLS_DIR" ]; then
            log "已存在软链: $dir -> $target"
            continue
        fi
        rm "$dir"
    elif [ -f "$dir" ]; then
        warn "跳过：$dir 是普通文件"
        continue
    elif [ -d "$dir" ]; then
        backup="${dir}.bak-$(date +%Y%m%d%H%M%S)"
        mv "$dir" "$backup"
        log "备份原目录 -> $backup"
        if command -v rsync >/dev/null 2>&1; then
            rsync -a --ignore-existing "$backup"/ "$SKILLS_DIR"/ || warn "复制 $backup 时出错"
        else
            warn "未找到 rsync，使用 cp -an 复制，可能覆盖同名文件"
            cp -an "$backup"/. "$SKILLS_DIR"/ || warn "复制 $backup 时出错"
        fi
    fi

    mkdir -p "$(dirname "$dir")"

    ln -s "$SKILLS_DIR" "$dir"
    log "创建软链: $dir -> $SKILLS_DIR"
done

# 处理 droids 目录软链接
for raw_dir in "${DROID_TARGETS[@]}"; do
    dir="$(expand_path "$raw_dir")"

    if [ -L "$dir" ]; then
        target="$(readlink "$dir")"
        if [ "$target" = "$DROIDS_DIR" ]; then
            log "已存在软链: $dir -> $target"
            continue
        fi
        rm "$dir"
    elif [ -f "$dir" ]; then
        warn "跳过：$dir 是普通文件"
        continue
    elif [ -d "$dir" ]; then
        backup="${dir}.bak-$(date +%Y%m%d%H%M%S)"
        mv "$dir" "$backup"
        log "备份原目录 -> $backup"
        if command -v rsync >/dev/null 2>&1; then
            rsync -a --ignore-existing "$backup"/ "$DROIDS_DIR"/ || warn "复制 $backup 时出错"
        else
            warn "未找到 rsync，使用 cp -an 复制，可能覆盖同名文件"
            cp -an "$backup"/. "$DROIDS_DIR"/ || warn "复制 $backup 时出错"
        fi
    fi

    mkdir -p "$(dirname "$dir")"

    ln -s "$DROIDS_DIR" "$dir"
    log "创建软链: $dir -> $DROIDS_DIR"
done

# 处理 agents 文件软链接（文件级别，非目录）
for raw_file in "${AGENT_TARGETS[@]}"; do
    file="$(expand_path "$raw_file")"

    if [ -L "$file" ]; then
        target="$(readlink "$file")"
        if [ "$target" = "$AGENTS_FILE" ]; then
            log "已存在软链: $file -> $target"
            continue
        fi
        rm "$file"
    elif [ -d "$file" ]; then
        warn "跳过：$file 是目录"
        continue
    elif [ -f "$file" ]; then
        backup="${file}.bak-$(date +%Y%m%d%H%M%S)"
        mv "$file" "$backup"
        log "备份原文件 -> $backup"
    fi

    mkdir -p "$(dirname "$file")"

    ln -s "$AGENTS_FILE" "$file"
    log "创建软链: $file -> $AGENTS_FILE"
done

ensure_description_all

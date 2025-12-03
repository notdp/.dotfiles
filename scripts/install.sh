#!/bin/bash

set -euo pipefail

expand_path() {
    case "$1" in
        "~") echo "$HOME" ;;
        ~/*)  echo "$HOME/${1#~/}" ;;
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

CONFIG_URL="${CONFIG_URL:-https://raw.githubusercontent.com/notdp/.dotfiles/main/scripts/config.json}"

DEFAULT_LINK_TARGETS=(
    "~/.claude/commands"
    "~/.codex/prompts"
    "~/.factory/commands"
    "~/.gemini/antigravity/global_workflows"
)

log() { echo "[info] $*"; }
warn() { echo "[warn] $*" >&2; }
LINK_TARGETS=()

if command -v curl >/dev/null 2>&1; then
    REMOTE_CONFIG=$(curl -fsSL "$CONFIG_URL" 2>/dev/null || echo "")
    if [ -n "$REMOTE_CONFIG" ]; then
        if command -v jq >/dev/null 2>&1; then
            while IFS= read -r line; do
                [ -n "$line" ] && LINK_TARGETS+=("$line")
            done < <(echo "$REMOTE_CONFIG" | jq -r '.link_targets[]')
            if [ "${#LINK_TARGETS[@]}" -eq 0 ]; then
                warn "远端配置缺少 link_targets 或为空，使用默认链接目标"
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

mkdir -p "$DOTFILES_DIR" "$COMMANDS_DIR"

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

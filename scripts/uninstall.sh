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

for raw_dir in "${LINK_TARGETS[@]}"; do
    dir="$(expand_path "$raw_dir")"

    if [ -L "$dir" ]; then
        target="$(readlink "$dir")"
        if [ "$target" = "$COMMANDS_DIR" ]; then
            rm "$dir"
            log "移除软链: $dir"
        else
            warn "跳过：$dir 指向其他位置 ($target)"
            continue
        fi
    elif [ -e "$dir" ]; then
        warn "跳过：$dir 存在但非软链"
        continue
    else
        log "未找到软链: $dir"
    fi

    latest_backup=$(ls -1dt "${dir}.bak-"* 2>/dev/null | head -n 1 || true)
    if [ -n "${latest_backup:-}" ]; then
        mv "$latest_backup" "$dir"
        log "已恢复备份: $latest_backup -> $dir"
    else
        log "无可用备份，未恢复: $dir"
    fi
done

log "卸载完成"

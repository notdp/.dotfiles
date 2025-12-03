#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOTFILES_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$DOTFILES_DIR/config.json"
COMMANDS_DIR="$DOTFILES_DIR/commands"

mkdir -p "$COMMANDS_DIR"

jq -r '.link_targets[]' "$CONFIG_FILE" | while read -r dir; do
    dir="${dir/#\~/$HOME}"
    if [ -d "$dir" ] && [ ! -L "$dir" ]; then
        cp -n "$dir"/* "$COMMANDS_DIR"/ 2>/dev/null
        rm -rf "$dir"
    fi
    mkdir -p "$(dirname "$dir")"
    [ -L "$dir" ] && rm "$dir"
    ln -s "$COMMANDS_DIR" "$dir"
done

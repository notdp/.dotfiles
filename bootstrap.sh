#!/bin/bash
COMMANDS_DIR=~/.dotfiles/commands

LINK_TARGETS=(
    ~/.claude/commands
    ~/.codex/prompts
    ~/.factory/commands
)

mkdir -p "$COMMANDS_DIR"

for dir in "${LINK_TARGETS[@]}"; do
    if [ -d "$dir" ] && [ ! -L "$dir" ]; then
        cp -n "$dir"/* "$COMMANDS_DIR"/ 2>/dev/null
        rm -rf "$dir"
    fi
    mkdir -p "$(dirname "$dir")"
    [ -L "$dir" ] && rm "$dir"
    ln -s "$COMMANDS_DIR" "$dir"
done

echo "Done. Commands directory: $COMMANDS_DIR"

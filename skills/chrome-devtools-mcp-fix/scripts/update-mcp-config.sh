#!/bin/bash
# 自动获取 Chrome DevTools WebSocket endpoint 并更新 mcp.json

set -e

MCP_JSON="$HOME/.factory/mcp.json"

# 检测 Chrome 配置文件路径
detect_chrome_path() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        local paths=(
            "$HOME/Library/Application Support/Google/Chrome"
            "$HOME/Library/Application Support/Google/Chrome Beta"
            "$HOME/Library/Application Support/Google/Chrome Canary"
        )
    else
        # Linux
        local paths=(
            "$HOME/.config/google-chrome"
            "$HOME/.config/google-chrome-beta"
        )
    fi

    for path in "${paths[@]}"; do
        if [[ -f "$path/DevToolsActivePort" ]]; then
            echo "$path"
            return 0
        fi
    done

    return 1
}

# 获取 WebSocket endpoint
get_ws_endpoint() {
    local chrome_path="$1"
    local port_file="$chrome_path/DevToolsActivePort"

    if [[ ! -f "$port_file" ]]; then
        echo "错误: DevToolsActivePort 文件不存在" >&2
        echo "请确保 Chrome 已启动并在 chrome://inspect/#remote-debugging 启用了远程调试" >&2
        return 1
    fi

    local port=$(sed -n '1p' "$port_file")
    local path=$(sed -n '2p' "$port_file")

    if [[ -z "$port" || -z "$path" ]]; then
        echo "错误: DevToolsActivePort 文件格式不正确" >&2
        return 1
    fi

    echo "ws://127.0.0.1:${port}${path}"
}

# 更新 mcp.json
update_mcp_json() {
    local ws_endpoint="$1"

    if [[ ! -f "$MCP_JSON" ]]; then
        echo "错误: $MCP_JSON 不存在" >&2
        return 1
    fi

    # 使用 Python 更新 JSON（比 jq 更可靠处理复杂 JSON）
    python3 << EOF
import json
import sys

mcp_json_path = "$MCP_JSON"
ws_endpoint = "$ws_endpoint"

with open(mcp_json_path, 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['chrome-devtools'] = {
    "type": "stdio",
    "command": "npx",
    "args": [
        "-y",
        "chrome-devtools-mcp@latest",
        f"--wsEndpoint={ws_endpoint}"
    ],
    "disabled": False
}

with open(mcp_json_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"已更新 chrome-devtools 配置:")
print(f"  wsEndpoint: {ws_endpoint}")
EOF
}

# 主流程
main() {
    echo "=== Chrome DevTools MCP 配置更新工具 ==="
    echo

    # 检测 Chrome 路径
    echo "检测 Chrome 配置文件..."
    local chrome_path
    if ! chrome_path=$(detect_chrome_path); then
        echo "错误: 未找到任何 Chrome 的 DevToolsActivePort 文件" >&2
        echo "请确保:" >&2
        echo "  1. Chrome 正在运行" >&2
        echo "  2. 已在 chrome://inspect/#remote-debugging 启用远程调试" >&2
        exit 1
    fi
    echo "  找到: $chrome_path"
    echo

    # 获取 WebSocket endpoint
    echo "获取 WebSocket endpoint..."
    local ws_endpoint
    if ! ws_endpoint=$(get_ws_endpoint "$chrome_path"); then
        exit 1
    fi
    echo "  endpoint: $ws_endpoint"
    echo

    # 更新配置
    echo "更新 $MCP_JSON..."
    if ! update_mcp_json "$ws_endpoint"; then
        exit 1
    fi
    echo

    echo "=== 完成 ==="
    echo
    echo "请重启 Droid 以应用新配置。"
    echo
    echo "注意: Chrome 重启后 browser ID 会变，需要重新运行此脚本。"
}

main "$@"

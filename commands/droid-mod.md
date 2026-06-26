---
description: 修改/检查/恢复 droid 二进制
argument-hint: <status | apply | apply 1,3 | restore>
---

对 `~/.local/bin/droid` 二进制执行修改、状态检查或恢复。

脚本位置: `scripts/droid-mod/`

## 适用场景

- 检查当前 droid 是否已应用本仓库维护的二进制 mod
- 需要批量应用指定 mod，或从备份恢复原版 droid
- 排查 mod 是否生效、是否被新版本 droid 覆盖

## 子命令

| 命令 | 说明 |
|------|------|
| `status` | 检查当前 droid 各 mod 的应用状态和 settings.json 配置 |
| `apply` | 应用全部 mod（自动备份 → 移除签名 → 逐个应用 → 补偿 → 签名） |
| `apply 1,3` | 只应用指定编号的 mod |
| `restore` | 从备份恢复原版 droid |
| `restore 0.90.0` | 恢复指定版本的备份 |
| `restore --list` | 列出所有可用备份 |

## 执行方式

脚本目录通过当前命令文件位置推算: `$(dirname $THIS_COMMAND)/../scripts/droid-mod/`，
即 `~/.dotfiles/scripts/droid-mod/`。

根据 `$ARGUMENTS` 决定子命令，默认为 `status`。

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")/../scripts/droid-mod" 2>/dev/null && pwd || echo "$HOME/.dotfiles/scripts/droid-mod")"

# status
python3 "$SCRIPT_DIR/status.py"

# apply (全部)
python3 "$SCRIPT_DIR/apply.py"

# apply (指定 mod)
python3 "$SCRIPT_DIR/apply.py" 1,3

# restore
python3 "$SCRIPT_DIR/restore.py"
python3 "$SCRIPT_DIR/restore.py" 0.90.0
python3 "$SCRIPT_DIR/restore.py" --list
```

## 可用 mod

| # | key | 说明 |
|---|-----|------|
| 1 | mod-cycle-custom-model | Ctrl+N 直接切换 custom model |
| 2 | mod-fix-multiline-history-down | 修复多行历史按 ↓ 无法回到空输入框 |
| 3 | mod-highlight-welcome-modified | Welcome/Header 高亮 Modified 标记 |
| 5 | mod-extend-kitty-timeout | 将 kitty 检测超时扩到 999ms |

> 此表由 `scripts/droid-mod/apply.py` 的 `MODS` 派生，编号即 `id` 字段（非连续）。
> 已归档（不再列出、不参与补偿）：`mod-hide-command-truncation`、`mod-expand-diff-lines`、`mod-unlock-max-custom-effort`（见 `scripts/droid-mod/mods/_archive/`）。

## 规则

1. **改动仓库外二进制**：`apply` / `restore` 会修改 `~/.local/bin/droid`（仓库外）。按 AGENTS.md 边界纪律，执行前应先过 `/guard-gitops` 评估并取得用户**明确确认**；`status`（只读）不需要。
2. 先执行 `status` 确认当前状态再决定下一步
3. `apply` 会自动处理备份、签名、字节补偿，补偿失败会自动恢复
4. 修改后提示用户「新开一个 droid 窗口验证」
5. 不要在 droid 正在运行修改操作时中断

## Gotchas

- `status` 是入口，不要直接假设当前二进制状态
- 新版本 droid 可能导致某些 mod 偏移失效；异常时先看 `status` 和脚本输出，不要盲目重试
- 这类修改只影响本机二进制，不适合当成仓库级通用配置能力

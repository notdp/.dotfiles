# dotfiles

[English](./README.md)

让 Claude CLI、Codex CLI、Factory CLI 共享同一个 commands 目录。

## 快速安装

```bash
curl -fsSL https://raw.githubusercontent.com/notdp/.dotfiles/main/bootstrap.sh | bash
```

## 进阶安装（版本管理）

**1. Fork 并 Clone**

```bash
git clone https://github.com/<your-username>/.dotfiles.git <target-dir>
```

`<target-dir>` 是你想进行版本管理的目录（如 `~/.dotfiles`）。

**2. 创建软链**

```bash
cd <target-dir>
./scripts/install.sh
```

## 做了什么

```
~/.claude/commands   → <target-dir>/commands (软链)
~/.codex/prompts     → <target-dir>/commands (软链)
~/.factory/commands  → <target-dir>/commands (软链)
```

三个工具共享同一个目录，改一处全生效。

## 配置（进阶）

编辑 `config.json`：

```json
{
  "link_targets": [
    "~/.claude/commands",
    "~/.codex/prompts",
    "~/.factory/commands"
  ]
}
```

- `link_targets`：要创建软链的目录列表

修改配置后需重新运行 `./scripts/install.sh`。

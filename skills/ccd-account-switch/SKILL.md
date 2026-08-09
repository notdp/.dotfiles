---
name: ccd-account-switch
description: 切换 Claude 账号后恢复 Claude Code 桌面版的 session 列表和 scheduled task（routine）。当用户说切了账号、session 不见了、会话列表空了、历史会话没了、routine 消失、定时任务不跑了时使用。
---

# 切账号后恢复 session 和 routine

CCD 的 session 面板索引和 routine 注册表都按账号隔离，存在
`~/Library/Application Support/Claude/claude-code-sessions/<accountUuid>/<orgUuid>/`。
切账号 = 换目录，所以新账号下什么都看不见。

丢的只是索引和注册：

- transcript 在 `~/.claude/projects/<项目>/*.jsonl`，不分账号
- routine 本体在 `~/.claude/scheduled-tasks/<taskId>/SKILL.md`，不分账号
- `local_*.json` 索引文件里没有账号字段，所属账号完全由目录路径决定，所以能直接复制

## 步骤

当前账号：

```bash
python3 -c "import json;print(json.load(open('$HOME/.claude.json'))['oauthAccount'])"
```

找旧账号目录，按 session 数和最后修改时间挑最近在用的那个（一个 accountUuid 下可能有多个 orgUuid，只有一个是真在用的）：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && for d in */*/; do echo "$(ls "$d" | grep -c '^local_')	$(ls -lt "$d" | sed -n 2p | awk '{print $6,$7,$8}')	$d"; done
```

复制索引（`SRC`/`DST` 换成上面查到的 `<accountUuid>/<orgUuid>`）。`deleted_*` 是删除标记，一起带上，否则删掉的会话会复活：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && cp -n "$SRC"/local_*.json "$SRC"/deleted_* "$DST"/
```

`cp -n` 不覆盖已有文件。旧账号有好几个的话，从最近的开始按顺序跑，先复制的版本优先。

routine 注册表直接覆盖，不用合并：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && cp "$SRC/scheduled-tasks.json" "$DST/scheduled-tasks.json"
```

任务每天都在跑，旧目录里的那份就是最新的；新账号目录基本是空数组，没有值得保的东西。

最后重启 CCD 才会读到新索引。

## 之后

- 工具授权按账号存，恢复的 routine 建议各 Run now 一次重新批权限
- 旧账号目录里的残留注册无害，切回去仍然生效，不用清

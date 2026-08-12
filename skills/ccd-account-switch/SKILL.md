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

当前账号。`~/.claude.json` 的 oauthAccount 是 CLI 状态，CCD 切号后可能还停在旧账号（实测踩过，差点把方向搞反），只能当邮箱↔uuid 的参考映射。当前账号以桌面版自己的存储为准：

```bash
strings -a "$HOME/Library/Application Support/Claude/Local Storage/leveldb/"* 2>/dev/null | grep -oE '"account_uuid":"[a-f0-9-]{36}","organization_uuid":"[a-f0-9-]{36}"' | sort | uniq -c | sort -rn
```

列出所有账号目录，按 session 数和最后修改时间判断（一个 accountUuid 下可能有多个 orgUuid，只有一个是真在用的）：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && for d in */*/; do echo "$(ls "$d" | grep -c '^local_')	$(ls -lt "$d" | sed -n 2p | awk '{print $6,$7,$8}')	$d"; done
```

切号后 CCD 一启动就写新账号目录，所以 mtime 最新的通常是当前账号（DST），次新且 session 多的才是要恢复的旧账号（SRC）。两步结果要互相印证；邮箱和 uuid 对不上号就直接问用户当前登录的邮箱，别猜。

复制索引（`SRC`/`DST` 换成上面查到的 `<accountUuid>/<orgUuid>`）。`deleted_*` 是删除标记，一起带上，否则删掉的会话会复活：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/"
cp -n "$SRC"/local_*.json "$DST"/
cp -n "$SRC"/deleted_* "$DST"/
```

`cp -n` 不覆盖已有文件。两个坑：macOS 的 `cp -n` 跳过已存在文件时退出码非零，放 `&&` 链里会把后面的命令全吞掉，一条条跑；zsh 下 glob 没匹配会让整条 cp 失败，所以两类文件分开复制。旧账号有好几个的话，从最近的开始按顺序跑，先复制的版本优先。

routine 注册表直接覆盖，不用合并：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && cp "$SRC/scheduled-tasks.json" "$DST/scheduled-tasks.json"
```

一律以旧账号的为准。新账号目录里的注册表不一定是空数组——可能已有同一批任务，时间戳更新、配置还会漂移（实测 cron 被改过），这些都不值得保，直接覆盖。覆盖前 diff 一眼确认任务列表没有新账号独有的任务即可。

最后重启 CCD 才会读到新索引。

## 之后

- 工具授权按账号存，恢复的 routine 建议各 Run now 一次重新批权限
- 旧账号目录里的残留注册无害，切回去仍然生效，不用清

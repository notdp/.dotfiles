---
name: ccd-account-switch
description: 切 Claude 账号后，把上一个账号的 session 列表和 routine（scheduled task）传到新账号。当用户说切了账号、换号了、session 不见了、会话列表空了、历史会话没了、pin 的会话没了、会话内容停在过去、轮数变少、routine 消失、定时任务不跑了、想看某个账号下有哪些会话、或者要在账号之间搬会话记录时，都用这个 skill——哪怕用户只是问"我另一个号的会话还在吗"也该用。
---

# 切账号后传火

CCD 的 session 面板索引和 routine 注册表按账号隔离，存在
`~/Library/Application Support/Claude/claude-code-sessions/<accountUuid>/<orgUuid>/`。
切账号 = 换目录，所以新账号下什么都看不见。

丢的只是索引和注册，内容都还在：

- transcript 在 `~/.claude/projects/<项目>/*.jsonl`，不分账号
- routine 本体在 `~/.claude/scheduled-tasks/<taskId>/SKILL.md`，不分账号
- `local_*.json` 索引里没有账号字段，所属账号完全由目录路径决定，所以能直接复制

## 心智模型：传火，不是合并

用户每次登录新账号都会跑这个 skill，所以这是一条**传火链**：上一棒的目录就是完整火种，整个传给下一位，新账号成为新火种。不是在几个目录之间做双向合并。

**推论：旧目录里"独有"的会话不是丢失的，是用户删掉的。** 实测当前账号缺的 132 条，在当前账号 100% 都有 `deleted_<id>` 墓碑，零例外。所以：

- 不要按"哪个目录 session 多"判断该恢复谁
- 不要把"SRC 独有 N 条"当成"能找回 N 条"报给用户——捞回来就是把人家删掉的会话复活
- 不需要把几个旧目录两两交叉比。传火链上最近的一棒就是全集，更早的只会更少

真正要防的三件事全在 `scripts/pass_fire.py` 里，不用事前比对：不复活已删的、不把新状态盖回旧的、不误杀在用的。

下面的命令用 `$SKILL_DIR` 指本 skill 目录（skill 加载时系统会告诉你它的路径），先 export 一次省事：

```bash
export SKILL_DIR="$HOME/.claude/skills/ccd-account-switch"
```

脚本单独放在 `scripts/` 而不是内联在这份文档里，是两次翻车换来的：markdown 里的 `$` 加数字会在 skill 正文注入 agent context 时被吃掉（`awk '{print $6}'` 读到手上变成残缺命令，跑出来是空白列）；而把代码块抠出来批量跑又容易抠错块（实测抠错一次，误覆盖了 routine 注册表，cron 被打回旧值、lastRunAt 回拨一天）。独立文件两个问题都没有。

## 一、认账号

`~/.claude.json` 的 oauthAccount 是 CLI 状态，CCD 切号后可能还停在旧账号（实测踩过，差点把方向搞反），**不能用它判断当前是谁**。当前账号以桌面版自己的存储为准：

```bash
strings -a "$HOME/Library/Application Support/Claude/Local Storage/leveldb/"* 2>/dev/null | grep -oE '"account_uuid":"[a-f0-9-]{36}","organization_uuid":"[a-f0-9-]{36}"' | sort | uniq -c | sort -rn
```

然后列目录。这一步顺手把能捞到的 `accountUuid → 邮箱` 记进 `~/.claude/ccd-account-emails.json`——CCD 只保留当前登录账号的 profile，切号即覆盖，旧账号的邮箱不提前记就永远拿不到了：

```bash
python3 "$SKILL_DIR"/scripts/accounts.py
```

- **DST** = 上一步 leveldb 查出的 accountUuid。别靠 mtime 猜，CCD 一启动就写当前账号目录，mtime 最新只是佐证。一个 accountUuid 下可能有多个 orgUuid，取有会话的那个。
- **SRC** = 上一棒，即除 DST 外最后活动最近的那个。更早的不用管。
- 邮箱对不上号就直接问用户当前登录的邮箱，别猜。

**按可见会话数看，不是按文件数**：routine 每次执行都占一个 `local_*.json`（实测 148 个文件里 99 个是 routine），归档的侧栏也不显示，混进计数会让判断跑偏。

## 二、把目录摊成表格

确认 SRC 是不是用户要的那份数据，以及用户问"现在有什么""看一下"时，都用这个：

```bash
python3 "$SKILL_DIR"/scripts/table.py "$SRC"
```

输出是 `<accountUuid>/<orgUuid>` + 邮箱 + 汇总行，然后 Routines / Pinned / 各项目分组表格，对着 CCD 侧栏的分组来，用户能逐条核对。**邮箱查不到就靠项目分布和会话标题认**——后者其实更管用，同一个邮箱下也可能有好几棒。

归档的不进表：侧栏看不见，列出来只会让用户对不上号，末尾报个数就够了。

## 三、传火

**别纠结该不该传、是不是已经传过了。直接传。** 脚本是幂等的，火已经传过就传入 0 条。

先备份 DST，这步不可逆：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && rm -rf ../claude-code-sessions-backup && cp -R "$DST" ../claude-code-sessions-backup
```

传火和 routine 注册表，都是先看数字再加 `--go` 真写：

```bash
python3 "$SKILL_DIR"/scripts/pass_fire.py "$SRC" "$DST"          # 看数字
python3 "$SKILL_DIR"/scripts/pass_fire.py "$SRC" "$DST" --go     # 真写
python3 "$SKILL_DIR"/scripts/merge_routines.py "$SRC" "$DST" --go
```

DST 独有的文件不受影响，当前正在跑的会话就在里面，所以别图省事 `rm -rf "$DST"` 再整个拷。

## 四、校验

```bash
python3 "$SKILL_DIR"/scripts/verify.py "$DST"
```

漏传 0 就是传火链完整。最后重启 CCD 才会读到新索引，重启后随手开一个轮数多的会话，确认内容是最新的而不是停在过去。

## 之后

- 工具授权按账号存，恢复的 routine 建议各 Run now 一次重新批权限
- 旧账号目录里的残留注册无害，切回去仍然生效，不用清

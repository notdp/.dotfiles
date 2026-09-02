# 切账号后传火（设计与踩坑记录）

> 日常只需要跑 SKILL.md 里那一行 `passfire.py --go`；本文是脚本背后的心智模型与历史，改脚本前读。

CCD 的 session 面板索引和 routine 注册表按账号隔离，存在
`~/Library/Application Support/Claude/claude-code-sessions/<accountUuid>/<orgUuid>/`。
切账号 = 换目录，所以新账号下什么都看不见。

丢的只是索引和注册，内容都还在：

- transcript 在 `~/.claude/projects/<项目>/*.jsonl`，不分账号
- routine 本体在 `~/.claude/scheduled-tasks/<taskId>/SKILL.md`，不分账号
- `local_*.json` 索引里没有账号字段，所属账号完全由目录路径决定，所以能直接复制

## 心智模型：传火，不是合并

用户每次登录新账号都会跑这个 skill，所以这是一条**传火链**：上一棒的目录就是完整火种，整个传给下一位，新账号成为新火种。不是在几个目录之间做双向合并。

**传完 DST 看到的就该跟 SRC 一样**——不只是"SRC 有的传过去"，还包括"**SRC 已经删掉的，DST 也要删掉**"。只加不减是这个 skill 栽过最大的跟头，见下。

**CCD 侧栏只认 `local_<id>.json` 在不在，完全不看 `deleted_` 墓碑。** 实测：CCD 列出 302 条，DST 的 local 文件 306 减 3 归档减 1 当前会话，精确吻合。所以墓碑一个都不用搬，只拿来当"SRC 见过这个 id"的证据：

| SRC 那边 | 含义 | 怎么办 |
|---|---|---|
| 有 local、无墓碑 | SRC 侧栏显示中 | 拷给 DST |
| 有墓碑 | 用户删过 | DST 留着的话也移走 |
| 从没见过这个 id | DST 切号后新建的 | 原样留着 |

不需要把几个旧目录两两交叉比，传火链上最近的一棒就是全集。

### 栽过的跟头：只加不减

2026-08-21 用户切号、跑完传火、重启，ordo_ai 下冒出 51 条早就删掉的会话。

根因不是传火拷错了，是**删除动作从不跨账号同步**：新账号目录 08-16 被灌了一份全量索引，用户 08-18~19 又在旧账号手动删了 500 多条（墓碑 mtime 逐条散开，人删的特征），新账号一无所知。切过去 = 换了一个停在 08-16 的目录，删掉的全在。

当时的 `pass_fire` 只加不减，传完还是脏的。`verify.py` 更糟：它把"local 和墓碑并存"当正常现象打印，只在数量比上次多时才警告——而并存本身就等于"已删会话正挂在侧栏"，雷埋了五天，每次都是绿的。

下面的命令用 `$SKILL_DIR` 指本 skill 目录（skill 加载时系统会告诉你它的路径），先 export 一次省事：

```bash
export SKILL_DIR="$HOME/.claude/skills/ccd-account-switch"
```

脚本单独放在 `scripts/` 而不是内联在这份文档里，是两次翻车换来的：markdown 里的 `$` 加数字会在 skill 正文注入 agent context 时被吃掉（`awk '{print $6}'` 读到手上变成残缺命令，跑出来是空白列）；而把代码块抠出来批量跑又容易抠错块（实测抠错一次，误覆盖了 routine 注册表，cron 被打回旧值、lastRunAt 回拨一天）。独立文件两个问题都没有。

## 一、认账号

`~/.claude.json` 的 oauthAccount 是 CLI 状态，CCD 切号后可能还停在旧账号（实测踩过，差点把方向搞反），**不能用它判断当前是谁**：

```bash
python3 "$SKILL_DIR"/scripts/current.py
```

脚本有两个判据，**锚点优先**：

1. **锚点**：本会话自己的索引文件落在哪个目录，哪个就是当前账号。CCD 只往当前账号目录
   写正在跑的会话。文件名由 `CLAUDE_CODE_HOST_SESSION_ID` 直接给出（形如 `local_<uuid>`，
   就是索引文件名去掉 `.json`），退路是拿 `CLAUDE_CODE_SESSION_ID` 去 grep 索引里的
   `cliSessionId`。
2. **leveldb**：桌面版自己的 `Local Storage/leveldb`，按 mtime 从新到旧扫，第一个含
   `account_uuid` 的文件作数，文件内取偏移最大的那次出现。频次不作数，旧文件不作数。

两边打架时**锚点赢**，脚本会打一屏 `!!` 警告。锚点也没有（不是在 CCD 会话里跑的）就只
剩 leveldb，这时候别闷头往下走，先跟用户核一遍邮箱。

### 栽过的跟头：认账号认反了两次

**2026-09-02 上午**，这里原本是一行 `strings 整个 leveldb 目录 | grep | uniq -c`，捞到的是
8 月的旧 .ldb（rira@franxx.ai），而当天 02:18 刚写的 `061265.log` 里的真账号
（dp0x7ce@gmail.com）因为两个字段在字节流里不相邻，那条正则压根没匹配上。照那个结论
SRC 和 DST 正好反过来，当天全部工作的索引会被 8 月的旧状态覆盖。于是有了上面第 2 条。

**2026-09-02 08:41**，只剩 leveldb 判据的版本又反了一次。用户 08:39 切号，08:41 跑
`current.py` 时 CCD 还在追写 `061284.log`——那一刻文件 47306 字节，里面只有旧账号
`d56e75fa` 的 10 条记录；新账号 `1e7f4a9f` 的 15 条（偏移 49448~60609）是几十秒后才落盘的。
"取最新文件里偏移最大的那次"这条规则没错，**错在文件还没写完**。

这个窗口不是小概率：用户跑这个 skill 的时机恰恰就是刚切完号，正撞在上面。当时是靠
`grep -rl <本会话 id>` 发现本会话索引写在了 `1e7f4a9f` 下，才把方向翻回来。锚点就是把这
一步固化进脚本——它不会半写，一个会话只可能属于一个账号。

然后列目录。这一步顺手把能捞到的 `accountUuid → 邮箱` 记进 `~/.claude/ccd-account-emails.json`——CCD 只保留当前登录账号的 profile，切号即覆盖，旧账号的邮箱不提前记就永远拿不到了：

```bash
python3 "$SKILL_DIR"/scripts/accounts.py
```

- **DST** = 上一步 `current.py` 报的那个 `accountUuid/orgUuid`。会话目录的 mtime 只是佐证，不当判据：CCD 一启动就写当前账号目录，传火本身也会把 SRC 的 mtime 顶上去。2026-09-02 那次 mtime 恰好指对了（DST 08:40 > SRC 08:37），指错的是 leveldb——所以顺序是**锚点 > mtime 佐证 > leveldb**，别再像旧版那样"打架时以 leveldb 为准"。一个 accountUuid 下可能有多个 orgUuid（传火会在旁边留下只含 `scheduled-tasks.json` 的空 org 目录），取有会话的那个，脚本已经挑好了。
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

**别纠结该不该传、是不是已经传过了。直接传。** 重复传是安全的：SRC 可见的每条都无条件
覆盖过去，覆盖成同样的内容而已。

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

merge_routines 不只补条目：DST 的配置按 SRC 对齐（cron 等，SRC 是刚交棒的火种，
配置最新——2026-09-01 实测 DST 的 cron 停在旧值，靠 SRC 修回），时间戳取两边较晚
的，然后把**其他所有账号目录**的 routine 掐灭（enabled=false + snuffedByPassFire
标记）。掐灭是防重复跑的关键：调度状态按账号隔离，哪个目录的 lastRunAt 停在过去，
CCD 在那个账号下醒来就当"错过了排期"补跑一遍——git log 里 08-20 21:21、08-21
19:50 的第二次 daily-skills bump 都是切号补出来的。火把只有一支，只在当前账号烧；
下次传火见到带标记的条目会自动重新点燃，用户手动关掉的（无标记）保持关闭。

输出四个数：传入 / 清掉 DST 里 SRC 已删的 / DST 更新跳过 / DST 独有保留。清掉的索引移到
`claude-code-sessions-pruned/`，是 move 不是 rm，搬回来即可恢复。

**"传入"不是增量，别拿它判断传没传成功。** 它就等于 SRC 当前可见的会话数，传第二遍还是
这个数（实测 2026-09-01 传完再跑，仍是 245）——脚本对 SRC 可见的每条都无条件 copyfile，
只有"DST 版本更新"那一条例外会跳过。唯一的同步信号是下面的"清掉 0"。

DST 独有的文件不受影响，当前正在跑的会话就在里面，所以别图省事 `rm -rf "$DST"` 再整个拷。

## 四、校验

再跑一次 dry-run，看"清掉 DST 里 SRC 已删的"是不是 0，是 0 就同步了（"传入"仍是满数，见上）：

```bash
python3 "$SKILL_DIR"/scripts/pass_fire.py "$SRC" "$DST"
```

（这里原来有个 `verify.py`，2026-08-21 删了。它靠"DST 有没有这个墓碑"判断漏没漏传，
而现在压根不搬墓碑，所以它会把用户删掉的会话全算成"漏传"，催着人再传一遍，正好把
刚清掉的又灌回去。）

最后重启 CCD 才会读到新索引，重启后随手开一个轮数多的会话，确认内容是最新的而不是停在过去。

## 之后

- 工具授权按账号存，恢复的 routine 建议各 Run now 一次重新批权限
- 旧账号目录的 routine 已在传火时掐灭，切回旧账号不会自己跑（也不会补跑）；要在旧账号跑就再传一次火，或 UI 里手动开

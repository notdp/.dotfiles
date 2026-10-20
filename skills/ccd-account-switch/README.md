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
| 从没见过这个 id | DST 独有 | 任一账号目录有墓碑就移走，否则原样留着 |

会话索引上，传火链最近的一棒是全集；墓碑不是——墓碑从不随传火搬，更早几棒删掉的会话在 SRC 里既没有 local 也没有墓碑。2026-10-19 切回 08 月的旧目录 ef26a102，146 条 8 月就删掉的会话因此被当成"DST 独有"挂回侧栏。所以 DST 独有的要拿**所有账号目录的墓碑并集**再筛一遍（`pass_fire.tombstones_anywhere`）；切回越旧的目录，这一项越大。

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

输出五个数：传入 / 清掉 DST 里 SRC 已删的 / 清掉 DST 独有但早几棒删过的 / DST 更新跳过 / DST 独有保留。清掉的索引移到
`claude-code-sessions-pruned/`，是 move 不是 rm，搬回来即可恢复。

**"传入"不是增量，别拿它判断传没传成功。** 它就等于 SRC 当前可见的会话数，传第二遍还是
这个数（实测 2026-09-01 传完再跑，仍是 245）——脚本对 SRC 可见的每条都无条件 copyfile，
只有"DST 版本更新"那一条例外会跳过。唯一的同步信号是下面的"清掉 0"。

DST 独有的文件不受影响，当前正在跑的会话就在里面，所以别图省事 `rm -rf "$DST"` 再整个拷。

## 四、校验

再跑一次 dry-run，看两个"清掉"是不是都是 0，是 0 就同步了（"传入"仍是满数，见上）：

```bash
python3 "$SKILL_DIR"/scripts/pass_fire.py "$SRC" "$DST"
```

（这里原来有个 `verify.py`，2026-08-21 删了。它靠"DST 有没有这个墓碑"判断漏没漏传，
而现在压根不搬墓碑，所以它会把用户删掉的会话全算成"漏传"，催着人再传一遍，正好把
刚清掉的又灌回去。）

最后重启 CCD 才会读到新索引，重启后随手开一个轮数多的会话，确认内容是最新的而不是停在过去。

## 环境（session preset）

环境选择器里自建的环境（"New environment" 建的 fleet / hive / otto 这类，SSH 或本地文件夹 + 模型/effort）按账号存在 `ccd-session-presets.json` 的 `byAccount.<accountUuid>` 下，切号后新账号是空的。2026-10-19 实测旧号 9 个、新号 0 个，会话索引里的 `envScopeId` 指向的环境也跟着没了。`merge_presets.py` 跟 routine 同一套规则：同 id 以 SRC 为准，DST 独有保留，只改 DST 那一个 key。

**`ccd-session-presets.json` 只是镜像，改它没用**：环境列表真正存在 claude.ai 页面自己的 localStorage 里，key 是 `persisted.ccd-session-presets.<accountUuid>`（值里带 `fileMirrored` 标记，账号 uuid 只在 key 名里），界面用 `SessionPresets.replaceAll` 把它写成这个文件。2026-10-19 实测两次：CCD 运行中写进 9 个，Cmd+R 后被写回 0；等 CCD 退出后再写、重开 30 秒复查还是 9，几小时后又被写回 0。

所以写入走页面存储。`merge_presets.py --go`（passfire 里的那一步）做两件事：

1. **自动**：起一个脱离 CCD 进程组的守护进程，等用户 Cmd+Q、CCD 主进程真正退出后，把 `Local Storage/leveldb` 整目录备份到 `~/.claude/ccd-ls-backup-<时间>`，用 `lsset.mjs`（node + classic-level，首次自动装到 `~/.cache/ccd-account-switch/node`）直接改 LevelDB 里那个 key 的 presets，再 `open -a Claude`，等页面把镜像文件刷新后比对环境 id。日志 `~/.claude/ccd-preset-apply.log`，最后一行 `OK` 或 `FALLBACK`。
   - Chromium localStorage 编码：key = `_https://claude.ai\x00\x01` + key 名；value = `\x01` + latin1，含 >0xFF 字符时 `\x00` + UTF-16LE。2026-10-19 在副本上读写、并用独立 headless Chrome 读回验证（118 个 key 都在、改的值读得出）。
   - CCD 开着时 LevelDB 有 LOCK，`lsset` 打不开就退出码 2、什么都不写（对真实库实测过）——用户抢先手动重开也安全。读回不一致会从备份整目录还原。
   - 对真实 CCD 的整条链 2026-10-19 在同一账号上实测过：写入时给某个环境的 `lastUsedAt` 加 1ms 当记号，Cmd+Q 后 12:33:18 写入 LevelDB，12:33:23 页面重开后把带记号的值写进镜像文件，说明页面读的就是写进去的值；日志最后一行 OK。真切号场景还没跑过。
   - **自动重启**：passfire `--go` 默认让守护进程 30 秒后用 `osascript -e 'tell application "Claude" to quit'` 正常退出 CCD（跟 Cmd+Q 一样会走退出流程，弹确认要用户点），没有环境要写也照样重开。这样整条传火链用户不用按键；代价是会打断其他正在跑的会话，所以确认按钮前要先列出来。`--no-restart` 关掉。2026-10-19 用假 CCD 进程测过「延时退出→写→重开」和「只重启」两条路径。

2. **兜底**：同时生成 `~/.claude/ccd-restore-env.js`，自动失败时用户在 CCD 里右键 → Inspect Element → Console（连在 `https://claude.ai`）粘贴执行：备份原值到 `<key>.bak-ccd-env`，只替换该账号的 presets，重载界面；结构对不上就报错停止。需要 `developer_settings.json` 里 `allowDevTools: true`。（2026-10-19 也实测成功过。）

事后单独改环境（批量改名之类）也走这条路：把想要的 DST 那一项存成 JSON，`merge_presets.py --catalog <file> <DST> --go`。

搬不了的：Cloud 环境和 Remote Control 下的机器在 claude.ai 服务端、归账号所有，跟 artifact 一样，切号后新账号看不到。SSH 连接本身（`ssh_configs.json`）不分账号，不用搬。

## 环境 star

环境选择器里的 Starred 存在页面 IndexedDB：`keyval-store` / `keyval` / `store:pin-state:epitaxy-starred-environments`，值是 JSON 字符串，`starredIds` 里是 `machine-preset:<环境 id>`。环境按账号存，star 挂在环境上，自然也按账号走；而且**切号时页面会把整个 IndexedDB 清空重建**（2026-10-19 18:51 实测：库里最早一条记录正好是切号那刻），所以传火跑的时候旧号的 star 已经没了，只能靠切号前的快照。

- **快照（事件驱动）**：`env_stars.py install` 装 launchd 常驻任务 `com.ccd-account-switch.env-stars`（KeepAlive），跑 `watch_stars.mjs`：用 kqueue 盯 IndexedDB 当前的 `NNNNNN.log` 文件，每次写入防抖 3 秒后直接在原始文件里读最新的 star 记录（key 是大端 UTF-16），`updatedAt` 变新了才调 `env_stars.py snapshot`，按账号存进 `~/.claude/ccd-env-stars.json`。读到空列表而已有非空快照时不覆盖（切号那一刻 config 可能还是旧账号、库已经清空）。
  - 2026-10-20 实测：`fs.watch(目录, {recursive:true})`（FSEvents）点星时一个事件都不报；盯 `.log` 文件本身（kqueue）每次点星都有 change。`.log` 会被 LevelDB 轮换（rename），切号时目录会被删了重建，所以同时盯 leveldb 目录和上一级 IndexedDB 目录，出事件就重新挂，外加每 60 秒自检一次。
  - 之前是每 30 分钟轮询：浪费，而且快照后、切号前点的星会丢（实测取消 5 个星后快照还停在 6 个）。
- **写回**：`merge_presets` 的守护进程在 CCD 退出后、重开前调 `env_stars.restore(SRC)`：备份 IndexedDB 到 `~/.claude/ccd-idb-backup-<时间>` → 拷到临时目录 → 用 `idbset.js` 合并 starredIds → 读回确认 → 替换真实目录。
- **为什么要同版本 Electron**：IndexedDB 的 LevelDB 用 Chromium 自定义排序规则 `idb_cmp1`、值是 V8 序列化，外部 LevelDB 库打不开；版本更高的 Chrome 可能把库格式升级掉、CCD 再读不了。所以从 `Electron Framework` 里读出 CCD 的 Electron 版本（2026-10-20 是 44.7.2 / Chromium 152），按需装到 `~/.cache/ccd-account-switch/electron-<版本>`（约 300MB；npm 有时不跑 electron 的 postinstall，脚本会手动补跑 `install.js`）。CCD 升级换了 Electron 版本会自动装新的。
- 2026-10-20 实测：真实 CCD 退出后写回 5 个 star，重开后 Starred 显示 6 个；守护进程整条链（延时退出→写 star→重开）用假 CCD 进程 + IndexedDB 副本测过。真切号场景还没跑过。

## 五、对账 pin

侧栏不直接用索引里的 `isStarred` 显示 Pinned，它有自己的 pin 存储（IndexedDB `https_claude.ai` 里的 `store:pin-state:dframe-starred-code`，`starredIds`）。切号重启后它从索引重新收 pin，2026-10-19 实测 27 条只收进 23 条：漏掉的 4 条索引里仍是 pinned、能搜到，就是不在 Pinned 区。不是按时间截断（最旧的 08-10 那条收进去了），原因不明。

`pins.py <DST>` 只读对账，列出侧栏漏掉的；补救走 app 自己的接口 `mcp__ccd_sidebar__set_pinned`，别直接改 IndexedDB。补完 3 秒内侧栏存储就更新了，再跑一次应是"漏掉 0"。

## 之后

- 工具授权按账号存，恢复的 routine 建议各 Run now 一次重新批权限
- 旧账号目录的 routine 已在传火时掐灭，切回旧账号不会自己跑（也不会补跑）；要在旧账号跑就再传一次火，或 UI 里手动开

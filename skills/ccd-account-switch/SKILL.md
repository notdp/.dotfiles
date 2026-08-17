---
name: ccd-account-switch
description: 切换 Claude 账号后恢复 Claude Code 桌面版的 session 列表和 scheduled task（routine）。当用户说切了账号、session 不见了、会话列表空了、历史会话没了、会话内容停在过去、轮数变少、routine 消失、定时任务不跑了时使用。
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

**覆盖前先预检。** DST 常常不是空目录（这个账号下用过、或以前恢复过），跟 SRC 有大量同名文件，全量覆盖会把其中比 SRC 新的那些盖回旧状态。先把清单拉出来：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && python3 - "$SRC" "$DST" <<'PY'
import json,glob,os,sys,datetime
SRC,DST=sys.argv[1:3]
t=lambda ms: datetime.datetime.fromtimestamp(ms/1000).strftime('%m-%d %H:%M') if ms else '?'
b=lambda p:{os.path.basename(x) for x in glob.glob(p+"/local_*.json")}
s,d=b(SRC),b(DST)
print(f"SRC {len(s)} / DST {len(d)}   SRC 独有 {len(s-d)}(会找回)   DST 独有 {len(d-s)}(原样保留)")
back=sorted((D['lastActivityAt'],S.get('lastActivityAt'),D.get('completedTurns'),S.get('completedTurns'),D.get('title',''))
            for f in s&d
            for S,D in [(json.load(open(SRC+"/"+f)),json.load(open(DST+"/"+f)))]
            if D.get('lastActivityAt',0) > S.get('lastActivityAt',0))[::-1]
print(f"覆盖后会回退的会话: {len(back)} / {len(s&d)} 共有")
for a in back: print(f"  {t(a[0])}->{t(a[1])}  turns {a[2]}->{a[3]}  {a[4][:50]}")
PY
```

回退数为 0 就直接往下走。非 0 就把清单给用户看，让他决定是接受回退（transcript 没丢，只是索引指回旧的那条，事后能从备份单独捞）还是挑着来——事前挑比事后从几百个文件里认出来省事得多。

有多个旧账号目录时也先用这个脚本比文件集合：老目录往往是最新那个的子集（每次恢复都往前滚），那就只恢复最新的一个，不用按顺序跑一遍。

先备份 DST，这步不可逆：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && rm -rf ../claude-code-sessions-backup && cp -R "$DST" ../claude-code-sessions-backup
```

复制索引（`SRC`/`DST` 换成上面查到的 `<accountUuid>/<orgUuid>`）。`deleted_*` 是删除标记，一起带上，否则删掉的会话会复活：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/"
cp -f "$SRC"/local_*.json "$DST"/
cp -f "$SRC"/deleted_* "$DST"/
```

**必须 `-f` 全量覆盖，绝对不要 `cp -n`。** DST 不一定是空目录——之前在这个账号下用过、或者以前恢复过，里面就有同名 `local_*.json`，而且往往是旧快照。`cp -n` 跳过已存在文件 = 保留旧的丢掉新的，索引里的 `cliSessionId` 指向 `~/.claude/projects/<项目>/<cliSessionId>.jsonl`，旧索引指着旧 transcript，**会话打开后内容停在过去、轮数变少**（实测一个 116 轮的会话显示成 19 轮）。这种错混在几百个文件里，只有逐个开会话才看得出来，极难发现。

`cp -f` 只覆盖 SRC 里有的文件，DST 独有的会原样保留——当前正在跑的会话就在这里面，所以别图省事 `rm -rf "$DST"` 再整个拷。

zsh 下 glob 没匹配会让整条 cp 失败，所以两类文件分开复制。旧账号有好几个的话，**从最旧的开始按顺序跑**，最新的最后写才能赢（这跟 `cp -n` 时代的顺序正好相反，别照抄老习惯）。

routine 注册表也先 diff 再决定。`scheduled-tasks.json` 的 `scheduledTasks` 是**数组**（不是以 id 为键的对象），每个元素带 `id` / `cronExpression` / `filePath` / `lastRunAt`，按 `id` 对：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && python3 - "$SRC" "$DST" <<'PY'
import json,sys
g=lambda p:{t['id']:t for t in json.load(open(p+"/scheduled-tasks.json"))['scheduledTasks']}
s,d=g(sys.argv[1]),g(sys.argv[2])
print("DST 独有(覆盖会丢):",[k for k in d if k not in s] or "无")
print("SRC 独有(覆盖会恢复):",[k for k in s if k not in d] or "无")
for k in s.keys()&d.keys():
    diff={f:(d[k].get(f),s[k].get(f)) for f in set(s[k])|set(d[k]) if s[k].get(f)!=d[k].get(f)}
    if diff: print(f"  {k}: DST->SRC {diff}")
PY
```

有 SRC 独有的任务、或配置漂移（实测 cron 被改过）就整个覆盖，一律以旧账号的为准：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && cp "$SRC/scheduled-tasks.json" "$DST/scheduled-tasks.json"
```

但如果两边任务集合一样、只有 `lastRunAt` 是 DST 更新，那就**别覆盖**——没东西可恢复，盖过去只会把执行时间往回拨，可能触发补跑。

覆盖完对一遍。SRC 该逐字节一致；回退项应该跟预检那步的数字对上（预检报 0 这里就该是 0，对不上说明中间有东西写进去了）：

```bash
cd "$HOME/Library/Application Support/Claude/claude-code-sessions/" && python3 - "$SRC" "$DST" ../claude-code-sessions-backup <<'PY'
import json,glob,os,sys,datetime
SRC,DST,BK=sys.argv[1:4]
t=lambda ms: datetime.datetime.fromtimestamp(ms/1000).strftime('%m-%d %H:%M') if ms else '?'
bad=[b for b in map(os.path.basename,glob.glob(SRC+"/local_*.json"))
     if open(SRC+"/"+b,'rb').read()!=open(DST+"/"+b,'rb').read()]
print(f"SRC 未生效: {len(bad)}  (应为 0)")
for b in map(os.path.basename,glob.glob(DST+"/local_*.json")):
    if not os.path.exists(BK+"/"+b): continue
    D=json.load(open(DST+"/"+b)); B=json.load(open(BK+"/"+b))
    if D.get('lastActivityAt',0) < B.get('lastActivityAt',0):
        print(f"回退 {t(B['lastActivityAt'])}->{t(D.get('lastActivityAt'))} "
              f"turns {B.get('completedTurns')}->{D.get('completedTurns')}  {B.get('title','')}")
PY
```

最后重启 CCD 才会读到新索引。重启后随手开一个轮数多的会话，确认内容是最新的而不是停在过去。

## 之后

- 工具授权按账号存，恢复的 routine 建议各 Run now 一次重新批权限
- 旧账号目录里的残留注册无害，切回去仍然生效，不用清

---
name: ccd-account-switch
description: 切 Claude 账号后，把上一个账号的 session 列表和 routine（scheduled task）传到新账号。当用户说切了账号、换号了、session 不见了、会话列表空了、历史会话没了、pin 的会话没了、会话内容停在过去、轮数变少、routine 消失、定时任务不跑了、想看某个账号下有哪些会话、或者要在账号之间搬会话记录时，都用这个 skill——哪怕用户只是问"我另一个号的会话还在吗"也该用。
---

# 切账号后传火

一条命令，只在 CCD 会话里跑（DST 靠本会话锚点判定，终端里没有锚点会直接退出）：

```bash
python3 ~/.claude/skills/ccd-account-switch/scripts/passfire.py        # 先看：不写
python3 ~/.claude/skills/ccd-account-switch/scripts/passfire.py --go   # 用户按了确认再跑
```

它自己完成：认当前账号（DST）→ 选上一棒（SRC = 其余目录里最后活动最近的）→ 备份 DST → 传 session 索引 → 传 routine 并掐灭其他目录的火把 → 传环境选择器里自建的环境 → 复核"DST 里 SRC 已删的 = 0，DST 独有但别处有墓碑的 = 0"。

**前置（每台机器一次）**：环境 star 切号时会被清空，只能靠切号前的快照搬。确认 `~/Library/LaunchAgents/com.ccd-account-switch.env-stars.plist` 存在；没有就跑 `python3 ~/.claude/skills/ccd-account-switch/scripts/env_stars.py install`（装一个常驻的 launchd 任务，star 一变就快照，要先跟用户说一声）。

**agent 要做的只有六件事，第二步必须有按钮**：
1. 先跑不带 `--go` 的。把输出里 SRC / DST 两行（邮箱 + uuid 前 8 位 + 最后活动时间）和五个数（传入 / 清掉 SRC 已删 / 清掉早几棒已删 / 跳过 / 独有）原样贴给用户，一个字不总结。
2. 用 AskUserQuestion 出确认按钮，选项固定三个：`确认传火`（推荐，写明"SRC=<邮箱> → DST=<邮箱>"）/ `换一个 SRC`（列出输出里的其他候选）/ `取消`。**没有这一步不许带 `--go`**——这条命令几秒就写完，快到没有反悔窗口，按钮就是反悔窗口。
   出按钮前先用 `mcp__ccd_session_mgmt__list_sessions` 查有没有别的会话 `isRunning: true`（本会话除外），有就在问题里点名：`--go` 30 秒后会自动让 CCD 退出，这些会话会被打断。
3. 用户点了确认才跑 `--go`；选了换 SRC 就用 `--src <accountUuid>/<orgUuid>` 重走第 1、2 步。复核不是 0 就把整段输出贴出来，别自己补救。
4. `--go` 跑完立刻结束这一轮回复，告诉用户：**30 秒后 CCD 会自动退出并重开，期间别点任何会话；弹出退出确认就点退出**（加 `--no-restart` 则改为用户自己 Cmd+Q，退出后同样自动写环境并重开）；恢复的 routine 各 Run now 一次重新批权限。
   CCD 把索引整份放内存，点开会话、退出时都会按内存写回盘：传火后点过的会话会被旧版本盖回去（2026-09-13 实测，122 轮被盖成 88 轮）。
   已经被盖的补救：在新会话里起一个盯 CCD 主进程 pid 的守护（`os.kill(pid,0)` 轮询，别用 pgrep -f 带 `$` 锚点，会误判），等它真退出后再从 SRC 拷那一条，然后用户重开 CCD。
5. 用户重启回来后复核环境和环境 star：`tail -4 ~/.claude/ccd-preset-apply.log`。「环境 star: 已写回 N 个」就是 star 也搬好了；说没有快照或没写的，让用户在环境选择器里手动点星。最后一行是 `OK` 就完事；是 `FALLBACK` 或「镜像里 DST 是 N 个」对不上，就让用户 `pbcopy < ~/.claude/ccd-restore-env.js`，在 CCD 里右键 → Inspect Element → Console（连在 https://claude.ai）粘贴执行。（环境存在页面 localStorage；`--go` 已起守护进程，Cmd+Q 后自动备份并直接写 LevelDB、再重开 CCD。用户 Cmd+Q 后等它自己重开。）
6. 对账 pin：`python3 ~/.claude/skills/ccd-account-switch/scripts/pins.py <DST>`。侧栏有自己的 pin 存储，切号后会漏收几条（索引里还是 pinned、能搜到，但不在 Pinned 区）。对输出里每条调 `mcp__ccd_sidebar__set_pinned(session_id, true)`，再跑一次确认"侧栏漏掉 0"。

不去读 README、不去逐个跑 `current.py` / `accounts.py` / `pass_fire.py`——那些是 passfire.py 的内部函数。只有两种情况需要人工：自动选的 SRC 不是用户想要的那棒（加 `--src <accountUuid>/<orgUuid>` 重跑，`accounts.py` 能列目录），或者用户只是想看某个账号里有什么（`table.py <accountUuid>/<orgUuid>`）。

artifact 不在传火范围内：它存在 claude.ai 服务端、归发布账号所有，切号后旧账号的 artifact 对新账号不可见也不可转移；源文件在本地，需要就重新发布。

心智模型、每一步为什么这么做、踩过的坑，见同目录 README.md（改脚本前读，日常不用读）。

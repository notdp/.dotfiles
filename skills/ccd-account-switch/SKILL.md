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

它自己完成：认当前账号（DST）→ 选上一棒（SRC = 其余目录里最后活动最近的）→ 备份 DST → 传 session 索引 → 传 routine 并掐灭其他目录的火把 → 复核"DST 里 SRC 已删的 = 0"。

**agent 要做的只有四件事，第二步必须有按钮**：
1. 先跑不带 `--go` 的。把输出里 SRC / DST 两行（邮箱 + uuid 前 8 位 + 最后活动时间）和四个数（传入 / 清掉 / 跳过 / 独有）原样贴给用户，一个字不总结。
2. 用 AskUserQuestion 出确认按钮，选项固定三个：`确认传火`（推荐，写明"SRC=<邮箱> → DST=<邮箱>"）/ `换一个 SRC`（列出输出里的其他候选）/ `取消`。**没有这一步不许带 `--go`**——这条命令几秒就写完，快到没有反悔窗口，按钮就是反悔窗口。
3. 用户点了确认才跑 `--go`；选了换 SRC 就用 `--src <accountUuid>/<orgUuid>` 重走第 1、2 步。复核不是 0 就把整段输出贴出来，别自己补救。
4. 提醒重启 CCD 才读到新索引；恢复的 routine 各 Run now 一次重新批权限。

不去读 README、不去逐个跑 `current.py` / `accounts.py` / `pass_fire.py`——那些是 passfire.py 的内部函数。只有两种情况需要人工：自动选的 SRC 不是用户想要的那棒（加 `--src <accountUuid>/<orgUuid>` 重跑，`accounts.py` 能列目录），或者用户只是想看某个账号里有什么（`table.py <accountUuid>/<orgUuid>`）。

artifact 不在传火范围内：它存在 claude.ai 服务端、归发布账号所有，切号后旧账号的 artifact 对新账号不可见也不可转移；源文件在本地，需要就重新发布。

心智模型、每一步为什么这么做、踩过的坑，见同目录 README.md（改脚本前读，日常不用读）。

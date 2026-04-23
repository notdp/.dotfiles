---
name: hive
description: Hive 基础 skill。让 agent 作为 Hive runtime 成员工作：发现上下文、查看成员、接收 <HIVE ...> 消息、发送消息，并加载更高层 workflow skill。
metadata: {"hive-bot":{"os":["darwin","linux"],"requires":{"bins":["tmux","python3","hive"]}}}
---

# Hive - agent 通信基础层

Hive CLI 是必须的外部依赖。安装方式：

```bash
pipx install git+https://github.com/notdp/hive.git
npx skills add https://github.com/notdp/hive -g --all
# 升级 CLI：
pipx upgrade hive
# 升级全局 skill（从 GitHub 安装的用户用这条）：
npx skills update hive -g
# 本地 repo checkout 的刷新（skills lock 不跟踪 local source，update 用不了）：
npx skills add "$PWD" -g --all
```

升级 Hive CLI 不会自动刷新已安装的 `hive` skill；当 skill 过期时，在 agent pane 里运行 `hive` 命令会收到 stderr 提醒，也可以显式运行 `hive doctor --skills` 查看详情。

运行 `hive --help` 确认安装成功。

---

你是运行在 Hive 里的 agent。Hive 是你的协作 runtime,不是某个特定 workflow。本 skill 的地图:

- **启动** — `hive init` 一条命令
- **命令速查** — 每天用的 CLI + `hive team` 字段语义
- **消息机制** — 怎么收、怎么发、thread / root 协议 / shell 安全(active-turn fork 和接管 handoff 见 `references/advanced-routing.md`)
- **协作规则** — 什么在 team 内消化,什么升给用户
- **Workflow 加载** — 在 Hive 之上叠更高层流程(如 code-review)
- **排障 + 协议边界** — 见 `references/debug.md`

## 启动

**加载 hive skill 后第一件事:跑 `hive init`,然后按 CLI 输出走。** `hive init` 幂等,报错会告诉你缺什么 —— `hive team` 等它完成之后再跑。

加载 hive skill 就代表你要进入 **peer group**(和 `/gang` 的 gang group 并列的基础协作模式;2 个 agent 互相 verify / review / confirm)。`hive init` 会自动给你配一个 **idle 异族**(model-family 不同)的 peer pane —— 优先在同 tmux session 里找现成的,找不到就在当前 window 现场 spawn 一个。两边 pane 都会打上 `@hive-group=peer`,在 `hive team` 里直接可见。

## 命令速查

```bash
hive team                            # 成员 + runtime(inputState/busy/turnPhase) + peer + group;`self` 是字符串,指你自己的 member name
hive send dodo "see attachment" --artifact /tmp/file.md   # 已有现成文件时
hive send dodo "see attachment" --artifact - <<'EOF'
# Findings
- item
EOF
hive reply dodo "ack, looking"       # 回复 dodo 最近一条给你的消息(自动 reply-to)
hive answer claude "yes"             # 回答 agent 的 pending question
hive notify "按 Space 和我对话"      # 桌面弹通知给当前 pane 的用户
# notify 只在你被阻塞、必须用户介入时用;文案结构:发生什么 / 为什么现在需要你 / 按 Space 回来后要做什么
```

### `hive team` 返回什么

去 `members` 里按 `self` 找自己那行,看完整状态。字段含义:

- **`self`** — 字符串 = 你自己的 member name(board/terminal pane 不会有 `model` / `sessionId` / `turnPhase` 等 runtime 字段,也不会伪造)
- **`group`** — 在 member 行上,只有 pane 打了 `@hive-group` 标签时才出现(例:peer group 成员 `group: peer`)
- **`inputState=waiting_user`** — 对方在等答案,用 `hive answer` 回答
- **`busy=true/false`** — tmux 输出层的秒级活动布尔,不等于语义上的 busy/idle
- **`turnPhase`** — 才是"现在插 new root 是否容易打断对方"的 transcript/JCL 语义层

## 消息机制

### 收消息

其他 agent 的消息以 `<HIVE from=... to=... msgId=... artifact=<path>>body</HIVE>` block 出现在你 pane 里 —— 这就是主通道。block 本身就带齐你要的所有东西:

- 短 body(sender 的摘要)在标签之间
- 详细内容在 `artifact=<path>` 指的文件里,用 Read tool 打开那条 path 就是全文

**原文永远在 `<HIVE>` block 里读。** `hive thread <msgId>` 和 `hive delivery <msgId>` 是排障入口(见 `references/debug.md`),agent 日常收信用不上。

### send vs reply(thread 模型)

Hive 的消息组织成 thread。每次发消息前问自己:**这是新话题,还是对已有 thread 的延续?**

- **新话题 → `hive send`**(新任务 / 新汇报 / 新提问 / 新发现,开新 thread)
- **对 inbound 的直接回应 → `hive reply`**(对方问的答、对方让你做的 ack,续 thread)

判断点是"**内容是不是对那条 inbound 的回应**",而不是"手头有没有 inbound"。典型陷阱:

- dodo 刚给你发"已就位"(inbound 在 inbox)
- 你现在想派 dodo 新任务"review PR #123"
  - 错:`hive reply dodo "review PR #123"` → autoReply 挂到"已就位"上,thread 污染
  - 对:`hive send dodo "review PR #123"` → 新任务开新 thread

#### `hive send`

开新 thread 的唯一入口,不接受 `--reply-to`。body 是短摘要,装不下时用 `--artifact`(见下文 root 协议)。即使对方刚给你发过 inbound,只要你现在要说的是新话题,也用 `send`。

#### `hive reply`

续 thread。没传 `--reply-to` 时 Hive 会挑"最近一条来自该 agent 且你还没回过的入站消息"作 anchor。autoReply 只省找 msgId 的步骤,不判断内容是否真的延续 —— 开新话题还是用 `send`。

显式传 `--reply-to <msgId>` 的场景:

- handoff / spawn 时 prompt 直接给了你 anchor msgId(你手头并没有那条 inbound)
- 你想跨越 autoReply 默认挑的那条,回一条更早的 thread

Hive 把 reply 严格锁在同 thread 内;没有可推断的入站消息且你也没传 `--reply-to` 时会直接报错。

### root 协议(send body 约束)

- root send(没有 `--reply-to`)的 `body` 永远是**短摘要**;详细内容放 `--artifact`
- `--artifact` 不是强制的 —— "ack"、"已就位"、"task done" 这类单行确认可以裸发 root send。信息一多就必须开 artifact
- `body` 命中下面任一条件会直接 reject,要移进 artifact:
  - 超过 `500` 字符
  - 一共有 `3` 行或更多
  - 含 fenced code:`` ``` ``
  - 任一非空行以 `#`、`-`、`*` 开头
- 首选 heredoc + stdin artifact:
  ```bash
  hive send <name> "<message>" --artifact - <<'EOF'
  # Findings
  - item
  EOF
  ```
- 带引号的 `EOF` 标签不做 shell 插值,markdown / 代码块 / 引号内容原样传过去
- `printf '%s\n' ... | hive send ... --artifact -` 只当备选,转义坑更多
- 多行 markdown / 代码走 heredoc + `--artifact -`;`$(cat <<EOF ...)` 这种命令替换的 shell 转义坑更深,heredoc 是唯一安全路径
- `reply` 不受这套 root 协议约束,可以只回一句短文本
- target 正在 active turn 时,root send 会自动 fork 一个 clone 接管(`routingMode=fork_handoff, routingReason=active_turn_fork`);不再有 `deferred` 状态。详见下文「busy-fork 路由」

### busy-fork 路由(摘要)

陌生 sender 向 target 发 root send 时,若 target 正在 active turn,消息会**自动 fork** 到一个 clone pane(`<target>-c1`)接管 —— 这不是 bug,是预期的保护机制。**peer 对** 和 **owner 父子**(双向)是 bypass 豁免关系,可直达原 target。

完整 3 条 bypass 判定 + clone pane 行为 + board pane 的文件通道例外 → `references/advanced-routing.md`。

### shell 安全

`hive send` 和 `hive reply` 的 body 里**反引号**(```````)会被 zsh/bash 当 command substitution 先执行,消息被悄悄改坏。含 markdown inline code 时走 heredoc + `--artifact -`,或 body 整句改用单引号包裹。

### 接管已有 thread 时的第一条 reply

被 spawn / handoff 到一条不是你自己的 thread 时,接管者要**显式 `--reply-to <msgId>`**;详见 `references/advanced-routing.md`。

## 协作规则

### team 内先,user 后

协作顺序是固定的:**先在 team 内把问题消化完,再对用户汇报**。每次想转向用户前,先跑 `hive team` 看有没有合适的 peer 可以接。

和 peer 讨论时,目标是**在 team 内把结论收敛**。对用户只给三样:

1. 已收敛的结论
2. 仍未收敛且真正阻断推进的**单个**问题
3. 你建议的下一步动作

仍在摇摆的 A/B/C、peer 的中间态分歧、你准备回去继续 challenge 的漏洞 —— 都留在 team 内消化完再出。peer 的论证有洞,先回 peer 挑明并收敛,由你自己处理完再对用户汇报(用户明确说要看原始讨论过程的除外)。

**以下 4 种情况才升级给用户**:

1. `hive team` 看过一遍,没有合适 agent 能接
2. 决策涉及不可逆外部副作用(`git push`、发 PR comment、删除数据、跑迁移、通知外部系统)
3. 需要用户提供 team 内 agent 都不掌握的信息、授权或偏好
4. 用户明确要求参与这类决策

升级的话术固定是:**"已先检查 hive team;这一步仍需你决定,因为 ..."** —— 直接给结论和问题。"找谁接手" 是你的判断,不是用户的决策。

### 默认分工

Claude 偏前端体验、文案收敛和发散式讨论;GPT 偏后端 correctness、约束检查和严谨 review。若项目已有更明确的人选或团队经验,以项目事实为准。

## Workflow 加载

更高层流程(如 `code-review`)在 Hive 之上加载:

- orchestrator 执行 `hive workflow load <agent> code-review`
- 或 spawn 时用 `hive spawn <agent> --workflow code-review`

workflow 加载后继续用 Hive 命令作为通信与状态底座。

## 排障 + 协议边界

排障命令清单(`hive doctor` / `delivery` / `thread` / `capture` / `inject` / `interrupt` / `kill` / `exec`)+ 协议硬约束(发送入口、`hive answer` 前提、非严格可靠队列语义、`gh` vs `hive` kernel 分工)→ `references/debug.md`。日常收发消息不用读这份;主通道见上文「消息机制」。

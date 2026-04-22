---
name: hive
description: Hive 基础 skill。让 agent 作为 Hive runtime 成员工作：发现上下文、查看成员、接收 <HIVE ...> 消息、发送消息，并加载更高层 workflow skill。
metadata: {"hive-bot":{"emoji":"💬","os":["darwin","linux"],"requires":{"bins":["tmux","droid","python3","hive"]}}}
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

你是运行在 Hive 里的 agent。Hive 是你的协作 runtime，不是某个特定 workflow。CLI 分三层：**Daily** 是你每天都走的路径，**Handoff** 是你把工作交出去时才用，**Debug** 只在排障时用。

## 首次进入

加载 hive skill = 你要进入 **peer group**(和 `/gang` 的 gang group 并列的基础协作模式;2 个 agent 互相 verify/review/confirm)。**立刻跑 `hive init`**，按 CLI 输出走，不要自己先 `hive team` 猜状态，也不要问用户「要不要 init」。`hive init` 幂等，报错信息会告诉你缺什么。

`hive init` 会自动给你配一个 **idle 异族**(model-family 不同)的 agent pane 作为 peer——优先在同 tmux session 里找现成的 pane,找不到就在当前 window 现场 spawn 一个。两边 pane 都会打上 `@hive-group=peer`,在 `hive team` 里直接可见。

## 日常（Daily）

```bash
hive team                             # 看成员 + runtime inputState/busy/turnPhase + peer + selfMember(你的 ID card:name/role/pane/group + members[self] 投影)
hive send dodo "see attachment" --artifact /tmp/file.md   # 仅当你已经有现成文件
cat <<'EOF' | hive send dodo "see attachment" --artifact -
# Findings
- item
EOF
hive reply dodo "ack, looking"        # 回复 dodo 最近一条给你的消息（自动 reply-to）
hive answer claude "yes"              # 回答 agent 的 pending question
hive notify "按 Space 和我对话"       # 给当前 pane 的用户弹通知
```

### 收消息

其他 agent 的消息会以 `<HIVE from=... to=... msgId=... />` block 出现在你 pane 里——这是主通道。不要去 `hive thread <msgId>` / `hive delivery <msgId>` 轮询等回复；durable store 不是收件箱。

### `hive send` 的 root 协议

- root send（没有 `--reply-to`）的 `body` 永远是**短摘要**；详细内容放 `--artifact`。
- `--artifact` 不是强制的 —— "ack"、"已就位"、"task done" 这类单行确认可以裸发 root send。只要信息多到装不进一条短 body，就**必须**开 artifact,不要塞进 body。
- `body` 命中下面任一条件都会直接失败；把这些都移进 artifact：
  - 超过 `500` 字符
  - 一共有 `3` 行或更多
  - 含 fenced code：`` ```
  - 任一非空行以 `# `、`- `、`* ` 开头
- 首选 heredoc + stdin artifact：
  ```bash
  cat <<'EOF' | hive send <name> "<message>" --artifact -
  # Findings
  - item
  EOF
  ```
- 带引号的 `EOF` 标签不会做 shell 插值，markdown / 代码块 / 引号内容会原样传过去
- `printf '%s\n' ... | hive send ... --artifact -` 只当备选；它更容易踩转义坑。只有已有现成文件时才传 `--artifact <path>`
- 不要把 `$(cat <<EOF ...)` 这类多行 command substitution 直接塞进 `hive send`
- `reply` 不受这套 root 协议影响，仍然可以只回一句短文本
- target 正在 active turn 时，root send 路径会自动 fork 一个 clone 接管（`routingMode=fork_handoff, routingReason=active_turn_fork`）；不再有 `deferred` 状态。详见下文「busy-fork 路由规则」节——有 3 条 bypass 关系会跳过 fork 直达 target
- **shell 安全（`hive send` 和 `hive reply` 都适用）**：双引号 `body` 里不要出现反引号（``` ` ```），zsh/bash 会把反引号当作 command substitution 先执行，消息会被悄悄改坏。含 markdown inline code 时走 heredoc + `--artifact -`，或把 body 整句换成单引号包裹

### busy-fork 路由规则

root `hive send` 默认是:**target 正在 active turn 时,自动 fork 出一个 clone(`<target>-c1`)接管,sender 的消息投给 clone**(`routingMode=fork_handoff, routingReason=active_turn_fork`)。fork 是防陌生 sender 污染 target 正推进的 turn —— clone 是孤儿 pane,带 boundary prompt 重启,不继承 target 上下文。

但有三条 **bypass 豁免关系**:只要 sender/target 满足其一,就算 target busy 也直达、不 fork:

1. **peer 对** — `sender.peer == target`(双方在 `hive team` 里互相标 peer;对称关系)
2. **owner 父→子** — `sender == target.@hive-owner`(sender spawn 了 target)
3. **子→父 owner** — `target == sender.@hive-owner`(sender 是被 target spawn 出来的子)

这三条覆盖"我们本来就是一起工作的"关系,是预期的信令通道,不该被当 hostile interrupt 拦。陌生关系(非 peer、非 owner 父子)**仍然 fork**,是保护机制主体,不要指望它放行。

> board pane 走 file autoread(vim 直接读文件变更),**不是 `hive send` 目标**,也不参与 bypass 规则。

### Thread 模型 + `hive send` vs `hive reply`

Hive 的消息组织成 thread。每次发消息前问自己：**这是新话题，还是对已有 thread 的延续？**

- **新话题 → `hive send`**（新任务 / 新汇报 / 新提问 / 新发现，开新 thread）
- **对 inbound 的直接回应 → `hive reply`**（对方问的答、对方让你做的 ack，续 thread）

判断点**不是**"手头有没有 inbound"，是"**内容是不是对那条 inbound 的回应**"。典型陷阱：

- dodo 刚给你发 "已就位"（inbound 在 inbox）
- 你现在想派 dodo 新任务 "review PR #123"
  - 不对：`hive reply dodo "review PR #123"` → autoReply 挂到 "已就位" 上，thread 污染
  - 对：`hive send dodo "review PR #123"` → 新任务必须开新 thread

#### `hive send`

只用于开新 thread，不接受 `--reply-to`；body 是短摘要，装不下时用 `--artifact`（见上一节 root 协议）。**即使对方刚给你发过 inbound，只要你现在要说的是新话题，也必须用 `send`**。

#### `hive reply`

用于续 thread。没传 `--reply-to` 时 Hive 会挑"最近一条来自该 agent 且你还没回过的入站消息"作 anchor。**这个 autoReply 便利性不代表你该用 reply 开新话题**——它只是省找 msgId 的步骤，不判断内容是否真的延续。

显式传 `--reply-to <msgId>` 的场景：

- handoff / spawn 时 prompt 直接给了你 anchor msgId（你手头并没有那条的 inbound）
- 你想跨越 autoReply 默认挑的那条，回一条更早的 thread

没有可推断的入站消息且你也没传 `--reply-to` 时会直接报错；它**不会**跨线程猜。

### 协作升级（4 条足矣）

问题默认先在团队内消化——不要先把用户当传话筒。先 `hive team` 看成员和 runtime 状态，再决定要不要找人协作。

和 peer 讨论时，默认目标是**先在 team 内把结论收敛**，再对用户汇报；不要把仍在摇摆的 A/B/C、peer 的中间态分歧、或你准备回去继续 challenge 的漏洞，直接倒给用户。除非用户明确要求看原始讨论过程，否则对用户只给：

1. 已收敛结论
2. 仍未收敛但真正阻断推进的单个问题
3. 你建议的下一步动作

如果 peer 的论证里有洞，先直接回 peer 挑明并收敛，不要先把这个洞抛给用户代你消化。

只有以下情况升级给用户：

1. 已完成 `hive team` 检查仍无合适 agent
2. 决策涉及不可逆外部副作用（`git push`、发 PR comment、删除数据、跑迁移、通知外部系统）
3. 需要用户提供团队内 agent 都不掌握的信息、授权或偏好
4. 用户明确要求参与这类决策

升级时直接说明：`已先检查 hive team；这一步仍需你决定，因为 ...`。不要问用户「要不要我先找别人讨论」「下一步该找谁接手」这类把用户当传话筒的问题。

### 默认分工

Claude 偏前端体验、文案收敛和发散式讨论；GPT 偏后端 correctness、约束检查和严谨 review。若项目已有更明确的人选或团队经验，以项目事实为准。

### `hive team` 状态字段

- `selfMember` 是你的 ID card：核心 4 字段 `name/role/pane/group` 恒有（`group` 可能是空串但 key 一定在），其余字段从 `members[self]` 投影（有才带，没就不填，不为 board/terminal pane 伪造 `model` / `sessionId`）
- `inputState=waiting_user` 说明对方在等答案，用 `hive answer` 回答
- `busy=true/false` 是 tmux 输出层的秒级活动布尔，不等于语义上的 busy/idle
- `turnPhase` 才是“现在插 new root 是否容易打断对方”的 transcript/JCL 语义层

### `hive notify` 原则

只在"不马上看这条通知 agent 就无法继续，或用户会错过关键时机"时使用。允许：任务完成用户在等、需要用户决策、遇阻塞必须用户介入、高风险不可逆操作前确认。禁止：一般进度、小完成、可选建议、能自行推进的情况。文案站在 agent 对 user 说话角度，直接说清"发生了什么 / 为什么现在需要你 / 按 `Space` 回来后要做什么"。浮层里按 `Space` 跳回当前 pane，任意键关闭。

## Handoff / 接手

收到新的独立任务而手头工作不该中断时，优先用 `hive handoff`，不要再自己手写 spawn/fork prompt 纪律。

```bash
hive handoff dodo --artifact /tmp/task.md
hive handoff dodo-2 --spawn --artifact /tmp/task.md
hive handoff orch-2 --fork --artifact /tmp/task.md
```

### `hive handoff` 怎么分流

- target 已存在且 alive：直接 handoff 给它
- target 不存在时，必须显式选 `--spawn` 或 `--fork`
- `--spawn` = fresh worker，只带任务说明和 artifact
- `--fork` = 复制当前 session。主场是"我正忙，但这条新线程需要继承我当前 session 现场"

### `hive handoff` 默认替你做什么

- 默认 anchor = 你最近一条**未回复**的入站消息；需要指定旧 thread 时再传 `--reply-to <msgId>`
- 给 assignee 发标准 handoff 消息，明确先 `hive thread <msgId>`
- 给 original sender 发一条 announce，让对方知道转交发生了

### 新处理者的动作

1. 第一件事是用 `hive reply <sender> --reply-to <msgId> "<short takeover with reason>"` 通知原 sender，例如"从 orch 手中接管了 X 任务，因为 orch 正在处理 Y"；不要让原 pane 先做中继。这里必须显式 `--reply-to`，因为你并不是 `<msgId>` 的 receiver，autoReply 推断不出来
2. 等 sender 回你之后，你就是正常 receiver，后续直接 `hive reply <sender> "..."` 走 autoReply 即可；只在你**还**没收到过 sender 的回信却要继续沿同一 thread push 更新时，才继续显式 `--reply-to <msgId>`

### Workflow

更高层流程（如 `code-review`）在 Hive 之上加载：

- orchestrator 执行 `hive workflow load <agent> code-review`
- 或 spawn 时用 `hive spawn <agent> --workflow code-review`

workflow 加载后继续用 Hive 命令作为通信与状态底座。

## Debug / 排障（少用）

以下命令是**排障入口**，不是主路径，更不是轮询用的：

- `hive doctor [agent] [--skills]` — agent 连通性 / 本地 skill drift
- `hive delivery <msgId>` — 某条消息的投递状态
- `hive thread <msgId>` — 某条消息的 reply / observation 串联
- `hive capture / inject / interrupt / kill / exec` — 低层 pane 操作

## 协议边界

- `hive send` 是发送消息的唯一入口，写入 workspace durable store（当前是 `hive.db`）
- `hive answer` 只在目标 `inputState=waiting_user` 时可用
- Hive 不是严格可靠消息队列：没有幂等性或 backpressure。主接收通道是 pane 内联的 `<HIVE ...>` block，不要把 durable store 当收件箱
- GitHub PR comment / review 属于 workflow 层职责；需要时直接用 `gh` / `gh api`，不混进 Hive kernel 命令

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

1. `hive current` — 看当前 tmux 绑定、pane 列表、是否已绑 team
2. 没 team 但在 tmux 里 → `hive init` 从当前 window 创建 team + workspace，自动把其他 pane 注册成 agent
3. 不要依赖 `HIVE_TEAM_NAME` / `HIVE_AGENT_NAME` / `HIVE_WORKSPACE` / `CR_WORKSPACE` 之类环境变量；`hive current` 和 tmux 绑定才是准绳

## 日常（Daily）

```bash
hive current                          # 看上下文
hive team                             # 看成员 + runtime inputState/activityState + peer
hive send dodo "hello"                # 发短消息（positional：收件人 + body，不要加 --to / --msg）
hive send dodo "see attachment" --artifact /tmp/file.md
cat <<'EOF' | hive send dodo "see attachment" --artifact -
# Findings
- item
EOF
hive reply dodo "ack, looking"        # 回复 dodo 最近一条给你的消息（自动 reply-to）
hive answer claude "yes"              # 回答 agent 的 pending question
hive suggest                          # 基于当前 runtime 建议协作对象
hive suggest momo                     # 以指定 source agent 视角给出候选
hive notify "按 Space 和我对话"       # 给当前 pane 的用户弹通知
```

### 收消息

其他 agent 的消息会以 `<HIVE from=... to=... msgId=... />` block 出现在你 pane 里——这是主通道。不要去 `hive thread <msgId>` / `hive delivery <msgId>` 轮询等回复；durable store 不是收件箱。

### `hive send` 是 fire-and-forget

- 返回 `queued` / `pending` / `confirmed` 都代表已进后台追踪，直接继续工作
- body 默认只放动作 + 摘要；长内容、多行结构化内容、需要后续引用的上下文一律先写 artifact
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

### `hive reply` vs `hive send --reply-to`

- 刚收到某 agent 的消息、直接回复就用 `hive reply <agent> "..."`：它自动把 `reply-to` 填成"最近一条来自该 agent 且你还没回过的入站消息"
- 没有入站消息、或最近一条已经回过，`hive reply` 会直接报错，要求你传 `--reply-to <msgId>`；它**不会**跨线程猜
- 已经拿到了特定 `msgId`（例如 handoff 时 prompt 里带的），继续用 `hive send <agent> "..." --reply-to <msgId>`

### 协作升级（4 条足矣）

问题默认先在团队内消化——不要先把用户当传话筒。先 `hive team`，适合协作再 `hive suggest`，优先找**非同源模型 / 非同 CLI** 的 agent。

只有以下情况升级给用户：

1. 已完成 `hive team` / `hive suggest` 检查仍无合适 agent
2. 决策涉及不可逆外部副作用（`git push`、发 PR comment、删除数据、跑迁移、通知外部系统）
3. 需要用户提供团队内 agent 都不掌握的信息、授权或偏好
4. 用户明确要求参与这类决策

升级时直接说明：`已先检查 hive team / hive suggest；这一步仍需你决定，因为 ...`。不要问用户「要不要我先找别人讨论」「下一步该找谁接手」这类把用户当传话筒的问题。

### 默认分工

Claude 偏前端体验、文案收敛和发散式讨论；GPT 偏后端 correctness、约束检查和严谨 review。若项目已有更明确的人选或团队经验，以项目事实为准。

### `hive suggest` 怎么用

- 想找人 review / 讨论 / 帮忙时先跑 `hive suggest`，默认 source 是自己；替别人挑协作者时 `hive suggest <source-agent>`
- 输出重点看 `score` / `reasons` / `model` / `cli` / `inputState` / `activityState` / `isPeer`
- 排序偏向：排除自己 / offline → 优先 `ready` → 其次 `activityState=idle` → 默认 peer → 不同 model / CLI
- `suggest` 只给建议，选中后仍然用 `hive send <name> "<message>"`

### `hive team` 状态字段

- `inputState=waiting_user` 说明对方在等答案，用 `hive answer` 回答
- `activityState=idle` 说明对方从 transcript 看空闲，较适合协作
- 两者都是从 session transcript 实时探测的 runtime 状态，不是事件投影

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

1. 第一件事是用 `hive send <sender> "<short takeover with reason>" --reply-to <msgId>` 通知原 sender，例如"从 orch 手中接管了 X 任务，因为 orch 正在处理 Y"；不要让原 pane 先做中继
2. 处理完成后，继续自己用 `hive send <sender> "<done summary>" --reply-to <msgId> [--artifact <path>]` 沿同一条 thread 回结果；后续 question / update 也都继续沿这条 thread 回复

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
- `hive teams` — 列出所有已知 team（跨 team 排障）
- `hive activity <agent>` — 分析 transcript 活跃度
- `hive capture / inject / interrupt / kill / exec` — 低层 pane 操作

## 协议边界

- `hive send` 是发送消息的唯一入口，写入 workspace durable store（当前是 `hive.db`）
- `hive answer` 只在目标 `inputState=waiting_user` 时可用
- Hive 不是严格可靠消息队列：没有幂等性或 backpressure。主接收通道是 pane 内联的 `<HIVE ...>` block，不要把 durable store 当收件箱
- GitHub PR comment / review 属于 workflow 层职责；需要时直接用 `gh` / `gh api`，不混进 Hive kernel 命令

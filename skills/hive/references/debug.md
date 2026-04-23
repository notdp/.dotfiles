# debug + 协议边界

排障命令清单和 hive kernel 的协议硬约束。主通道见 `../SKILL.md`「消息机制」;日常收发消息不读这份。

## Debug / 排障

- `hive doctor [agent] [--skills]` — agent 连通性 / 本地 skill drift
- `hive delivery <msgId>` — 某条消息的投递状态
- `hive thread <msgId>` — 某条消息的 reply / observation 串联
- `hive capture / inject / interrupt / kill / exec` — 低层 pane 操作

## 协议边界

- `hive send` 是发送消息的唯一入口,写入 workspace durable store(当前是 `hive.db`)
- `hive answer` 只在目标 `inputState=waiting_user` 时可用
- Hive 不是严格可靠消息队列 —— 没有幂等性或 backpressure。收件箱一律是 pane 内联的 `<HIVE ...>` block;durable store 是写入层,不作轮询对象
- GitHub PR comment / review 属于 workflow 层职责,直接用 `gh` / `gh api`;Hive kernel 命令保持单一职责

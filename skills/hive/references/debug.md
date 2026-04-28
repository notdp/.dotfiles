# debug + 协议边界

排障命令清单和 hive kernel 的协议硬约束。主通道见 `../SKILL.md`「消息机制」;日常收发消息不读这份。

## Debug / 排障

- `hive doctor [agent] [--skills]` — agent 连通性 / 本地 skill drift
- `hive delivery <msgId>` — 某条消息的投递状态
- `hive thread <msgId>` — 某条消息的 reply / observation 串联
- `hive capture / inject / interrupt / kill / exec` — 低层 pane 操作

### 日志位置

`hive doctor` 默认输出当前 workspace 的排障路径,不需要额外 flag:

- `runDir` — workspace 的运行时目录
- `logs.notify` — notify / idle watcher JSONL
- `logs.sidecar_stderr` — sidecar 未捕获异常和 stderr 兜底
- `logs.cvim_dir` — `hive cvim` / `hive vim` 每次调用的 per-run JSONL

日志 verbosity 默认由 Hive 源码位置推断:源码在 `site-packages` / `dist-packages` 下为 `normal`,否则为 `dev`。`normal` 只过滤 sidecar 心跳类事件;notify 和 cvim 的业务关键路径仍然全量记录。需要临时复现问题时可以用逃生口 `HIVE_LOG_VERBOSITY=dev|normal`。

## 协议边界

- `hive send` 和 `hive reply` 都通过同一 sidecar 通道(`request_send_payload`)写入 workspace durable store(当前是 `hive.db`);区别是 reply 必带 `in_reply_to`,send 永远是新 thread root
- `hive answer` 只在目标 `inputState=waiting_user` 时可用
- Hive 不是严格可靠消息队列 —— 没有幂等性或 backpressure。收件箱一律是 pane 内联的 `<HIVE ...>` block;durable store 是写入层,不作轮询对象
- GitHub PR comment / review 属于 workflow 层职责,直接用 `gh` / `gh api`;Hive kernel 命令保持单一职责

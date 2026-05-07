# advanced routing — thread takeover

hive 路由的低频场景。常规 `hive send` / `hive reply` 流程不需要读这份,主文 `../SKILL.md`「消息机制」章节已经覆盖。

命中以下情况才查这里:

- 你被 spawn / handoff 接管一条 thread,但你不是原 receiver

## 接管已有 thread 时的第一条 reply

被 spawn 或 handoff 到一条你不是原 receiver 的 thread 时,接管者直接对原 sender 回第一条,原 pane 不做中继:

1. **第一条动作**:`hive reply <sender> --reply-to <msgId> "<short takeover with reason>"` —— 告诉原 sender"从 X 手中接管了 Y 任务,因为 X 正在处理 Z"。这里必须**显式 `--reply-to`**,因为你并不是 `<msgId>` 的 receiver,autoReply 推断不出来
2. **sender 回你之后**,你就是正常 receiver,后续 `hive reply <sender> "..."` 走 autoReply 即可;只在还没收到 sender 回信却要继续沿同一 thread push 更新时,才继续显式 `--reply-to <msgId>`

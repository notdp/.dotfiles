# advanced routing — busy-fork + thread takeover

hive 路由的两个低频场景。常规 `hive send` / `hive reply` 流程不需要读这份,主文 `../SKILL.md`「消息机制」章节已经覆盖。

命中任一情况才查这里:

- 你向 target 发了 root send,消息最后落到了 `<target>-c1` 这种 clone pane,不是你期望的 target
- 你被 spawn / handoff 接管一条 thread,但你不是原 receiver

## busy-fork 路由(3 条 bypass)

root `hive send` 默认行为:**target 正在 active turn 时,自动 fork 出一个 clone(`<target>-c1`)接管,sender 的消息投给 clone**(`routingMode=fork_handoff, routingReason=active_turn_fork`)。fork 是防陌生 sender 污染 target 正推进的 turn —— clone 是孤儿 pane,带 boundary prompt 重启,不继承 target 上下文。

三条 **bypass 豁免关系** 会跳过 fork、直达 target(就算 target busy):

1. **peer 对** — `sender.peer == target`(双方在 `hive team` 里互相标 peer;对称关系)
2. **owner 父→子** — `sender == target.@hive-owner`(sender spawn 了 target)
3. **子→父 owner** — `target == sender.@hive-owner`(sender 是被 target spawn 出来的子)

这三条覆盖"本来就在一起工作"的关系,是预期的信令通道。陌生关系(非 peer、非 owner 父子)**仍然 fork**,这是保护机制主体。

> board pane 走 file autoread(vim 直接读文件变更),它是文件通道,不是 `hive send` 目标,也不参与 bypass 规则。

## 接管已有 thread 时的第一条 reply

被 spawn 或 handoff 到一条你不是原 receiver 的 thread 时,接管者直接对原 sender 回第一条,原 pane 不做中继:

1. **第一条动作**:`hive reply <sender> --reply-to <msgId> "<short takeover with reason>"` —— 告诉原 sender"从 X 手中接管了 Y 任务,因为 X 正在处理 Z"。这里必须**显式 `--reply-to`**,因为你并不是 `<msgId>` 的 receiver,autoReply 推断不出来
2. **sender 回你之后**,你就是正常 receiver,后续 `hive reply <sender> "..."` 走 autoReply 即可;只在还没收到 sender 回信却要继续沿同一 thread push 更新时,才继续显式 `--reply-to <msgId>`

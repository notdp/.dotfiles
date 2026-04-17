---
name: hive
description: Hive 基础 skill。让 agent 作为 Hive runtime 成员工作：发现上下文、查看成员、接收 <HIVE ...> 消息、发送消息，并加载更高层 workflow skill。
metadata: {"hive-bot":{"emoji":"💬","os":["darwin","linux"],"requires":{"bins":["tmux","droid","python3","hive"]}}}
---

# Hive - agent 通信基础层

Hive CLI 是必须的外部依赖。安装方式：

```bash
pipx install git+https://github.com/notdp/hive.git
npx skills add https://github.com/notdp/hive -g --skill hive --agent '*' -y
# 本地开发时改为当前 checkout：
npx skills add "$PWD" -g --skill hive --agent '*' -y
```

运行 `hive --help` 确认安装成功。

---

你是运行在 Hive 里的 agent。Hive 是你的协作 runtime，不是某个特定 workflow。

## 目标

1. 独立使用 Hive 基础能力
2. 先确定上下文，再执行消息/协作命令
3. 必要时再加载更高层 workflow skill（例如 `code-review`）

## 先确定上下文

优先顺序：

1. 直接运行 `hive current`
2. 如果已有 `team/workspace/agent`，继续用 Hive 命令
3. 如果没有 team 但在 tmux 里：
   - `hive current` 会显示检测到的 tmux 环境（session、window、pane 列表）
   - 运行 `hive init` 一键从当前 tmux window 创建 team + workspace，自动注册其他 pane 为 agent 并推送 `/skill hive`
4. 不要依赖 `HIVE_TEAM_NAME` / `HIVE_AGENT_NAME` / `HIVE_WORKSPACE` / `CR_WORKSPACE` 之类的环境变量；当前 tmux 绑定和 `hive current` 才是准绳

## 命令速查（注意参数都是 positional，不要加 --to / --msg）

```bash
hive current                          # 当前上下文（无 team 时自动发现 tmux）
hive init                             # 从 tmux window 创建 team，自动注册所有 pane
hive team                             # 查看成员、peer 关系和 runtime inputState/activityState
hive peer show                        # 查看当前 team 的默认 peer 关系
hive send claude "hello"              # 发短消息（第1个参数=收件人，第2个=简短正文）
hive send claude "see attachment" --artifact /tmp/file.md
printf '%s\n' "# Findings" "- item" | hive send claude "see attachment" --artifact -
hive fork --join-as orch-2 --prompt "先跑 hive thread Veh9 看原始内容，开始后先 reply-to lulu 说明接管，处理完再 reply-to lulu"   # agent 默认分身/接管用法
# bare hive fork 仅在你明确只想开一个未注册的旁路 pane 时才用，不是默认 agent 分工命令
# orch-2 处理完后沿同一条 thread 回结果
hive send lulu "done: see attachment" --reply-to Veh9 --artifact /tmp/result.md
hive answer claude "yes"              # 回答 agent 的 pending question
hive doctor --skills                  # 显式检查当前 CLI 的 hive skill 是否过期
hive suggest                          # 基于当前 runtime 建议优先协作对象
hive suggest momo                     # 以指定 source agent 视角给出候选
hive thread Ab12                      # 恢复某条消息的 reply/observation 串联；不要拿它轮询等回复
hive notify "按 Space 和我对话"       # 给当前 pane 对应的用户弹出通知（Space 跳回这里，任意键关闭）
hive notify "重构完成，帮我 review 一下"
hive teams                            # 列出已知 team
```

### `hive suggest` 怎么用

- 当你想“找谁讨论 / 找谁 review / 找谁帮忙”时，先跑 `hive suggest`
- 默认 source 是当前 agent；如果你在替别人挑协作者，可以显式传 `hive suggest <source-agent>`
- 输出会给候选列表，重点看：
  - `score`
  - `reasons`
  - `model`
  - `cli`
  - `inputState`
  - `activityState`
  - `isPeer`
- 当前排序规则偏向：
  - 排除自己
  - 排除 offline
  - 优先 `ready`
  - 其次优先 `activityState=idle`
  - 再看默认 `peer`
  - 最后再看不同 `model` / `cli`
- `suggest` 只是建议，不会自动发消息；选中对象后仍然用 `hive send <name> "<message>"`
- 默认决策模板：先判断这是不是团队内可以消化的问题；只要属于评审、设计分歧、风险判断、卡住、能力不匹配、或需要别人接手，就先 `hive suggest`，不要先把用户当传话筒
- 默认分工启发：Claude 偏前端体验、文案收敛和发散式讨论；GPT 偏后端 correctness、约束检查和严谨 review。若当前项目已有更明确的人选或团队经验，以项目事实为准

## 工作原则

1. 先 `hive current`（无 team 时跑 `hive init`）
2. 再 `hive team`
3. 其他 agent 发来的消息会直接以 `<HIVE ...> ... </HIVE>` 形式出现在当前 pane
4. `hive send` 是 fire-and-forget：只要返回 `queued` / `pending` / `confirmed`，默认继续当前工作，不要停下来等回复，也不要用 `hive thread <msgId>` / `hive delivery <msgId>` 轮询；新的入站消息以 pane 内联 `<HIVE ...>` 为准。
5. `hive send` 的 message body 默认只放动作 + 摘要；只有在内容本身足够短、单行且不需要保留详细上下文时，才直接把正文塞进消息
6. 发任务、回传结果、同步进度时，默认写成 `hive send <name> "<short summary>" --artifact <path>`；不要把长报告、长 checklist、详细设计讨论、长 diff 说明直接塞进消息正文
7. 详细内容、多行结构化内容、需要后续引用的上下文一律先写 artifact。首选 stdin artifact：`... | hive send <name> "<message>" --artifact -`；只有已有现成文件时才传 `--artifact <path>`。不要把 `$(cat <<EOF ...)` 这类多行 command substitution 直接塞进 `hive send`
8. `hive team` 显示每个 agent 的默认 `peer`、runtime `inputState` 和 `activityState`；如果某个 agent 的 `inputState` 是 `waiting_user`，说明它在等答案，用 `hive answer` 回答；`activityState=idle` 说明从 transcript 已落盘状态看，它更像空闲可协作对象
9. 协作升级原则：当你想向用户提问、请求用户确认技术方案、打断用户、或让用户决定该找谁讨论/接手时，先把它当成团队内问题处理，不要直接升级。默认动作是先跑 `hive team`，问题适合协作再跑 `hive suggest`，并优先联系 **非同源模型 / 非同 CLI** 的 agent；凡属设计判断、方案评审、策略推荐、风险判断、实现卡住、上下文不足、能力不匹配、需要接手或需要 review，也都先走这条路径。只有在以下情况下才允许升级给用户：(a) 已完成 `hive team` / `hive suggest` 检查仍无合适 agent；(b) 决策涉及不可逆外部副作用，如 `git push`、发 PR comment、删除数据、跑迁移、通知外部系统；(c) 需要用户提供团队内 agent 都不掌握的信息、授权或偏好；(d) 用户明确要求参与这类决策。升级时必须直接说明为什么团队内无法消化，优先使用这种句式：`已先检查 hive team / hive suggest；这一步仍需你决定，因为 ...`；不要问用户 `要不要我先找别人讨论`、`要不要我先问 orch/xxx`、`下一步该找谁 review/接手`，也不要把用户当传话筒。
10. `hive notify` 原则：只在“不马上看这条通知，agent 就无法继续，或者用户会错过关键时机”时使用，且对象始终是当前 pane 的用户，不是其他 agent。允许：任务完成且用户明确在等结果；需要用户做决策；遇到阻塞且必须用户介入；执行 `git push`、覆盖文件、跑迁移、删除数据等高风险动作前需要确认。禁止：普通进度汇报、阶段性小完成、可选建议、agent 仍可自行继续推进的情况；凡是能通过 `hive team` 或 artifact 表达的，就不要打断用户。文案应站在 agent 对 user 说话的角度，直接说清楚“发生了什么 / 为什么现在需要你 / 按 `Space` 回来后要做什么”；浮层里按 `Space` 会跳回当前 pane，按任意键只关闭浮层。
11. 收到新的独立任务而你手头工作不该中断时，agent 默认使用 `hive fork --join-as <name> --prompt "<task summary>"` 或 `hive spawn` 分出处理者；bare `hive fork` 仅限你明确只想开一个未注册的旁路 pane，不算正常分工/接管路径。
12. `--prompt` 里要直接写清 initial prompt：先跑 `hive thread <msgId>` 拿原始上下文、要处理什么、相关 artifact 在哪、开始后要先 reply-to 谁说明接管、以及处理完成后应该继续 reply-to 谁回结果。只有在你没用 `--prompt` 时，才退回手动 `hive send <fork-name> "<task summary>" [--artifact <path>]` 给分身下任务。
13. 新的处理者收到 initial prompt 后，第一件事是用 `hive send <sender> "<short takeover with reason>" --reply-to <msgId>` 通知原 sender "这个任务现在由我接管"，并顺手说明为什么换人，例如"从 orch 手中接管了 X 任务，因为 orch 正在处理 Y"；不要让原 pane 先做中继。
14. 新的处理者完成处理后，继续自己用 `hive send <sender> "<done summary>" --reply-to <msgId> [--artifact <path>]` 沿同一条 thread 回结果；后续 question / update 也都继续沿这条 thread 回复。

## 协议边界

- `hive send` 是发送消息的唯一入口，会写入 workspace durable store（当前是 `hive.db`）
- `hive answer` 用于回答 agent 的 pending question（AskUserQuestion）；只有目标处于 `waiting_user` 时才允许
- `hive team` 的 `inputState` / `activityState` 字段都是从 agent session transcript 实时探测的 runtime 状态，不是事件投影
- GitHub PR comment / review 属于 workflow 层职责；需要发评论时直接用 `gh` / `gh api`，不要把这类 API 混进 Hive kernel 命令
- Hive 不是严格可靠消息队列：没有幂等性或 backpressure；消息接收主通道是 pane 内联的 `<HIVE ...>` block，不要把 durable store 当收件箱。消息正文应保持短小，详细上下文默认放 artifact；`hive delivery` / `hive thread` 只用于恢复上下文、人工检查和排障，不用于轮询等回复

## 加载 workflow

Hive 是基础 skill。更高层流程应在 Hive 之上加载，例如：

- 由 orchestrator 执行 `hive workflow load <agent> code-review`
- 或在 spawn 时使用 `hive spawn <agent> --workflow code-review`

当 workflow skill 被加载后，继续使用 Hive 命令作为通信与状态底座。

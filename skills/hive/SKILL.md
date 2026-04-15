---
name: hive
description: Hive 基础 skill。让 agent 作为 Hive runtime 成员工作：发现上下文、查看成员、接收 <HIVE ...> 消息、发送消息，并加载更高层 workflow skill。
metadata: {"hive-bot":{"emoji":"💬","os":["darwin","linux"],"requires":{"bins":["tmux","droid","python3","hive"]}}}
---

# Hive - agent 通信基础层

Hive CLI 是必须的外部依赖。安装方式：

```bash
pipx install git+https://github.com/notdp/hive.git
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
hive team                             # 查看成员和 runtime inputState
hive send claude "hello"              # 发消息（第1个参数=收件人，第2个=内容）
hive send claude "see attachment" --artifact /tmp/file.md
printf '%s\n' "# Findings" "- item" | hive send claude "see attachment" --artifact -
hive answer claude "yes"              # 回答 agent 的 pending question
hive notify "按 Space 和我对话"       # 给当前 pane 对应的用户弹出通知（Space 跳回这里，任意键关闭）
hive notify "重构完成，帮我 review 一下"
hive teams                            # 列出已知 team
```

## 工作原则

1. 先 `hive current`（无 team 时跑 `hive init`）
2. 再 `hive team`
3. 其他 agent 发来的消息会直接以 `<HIVE ...> ... </HIVE>` 形式出现在当前 pane
4. 发任务用 `hive send <name> "<message>"`
5. 完成任务或回传结果时，用 `hive send <name> "<message>" [--artifact <path>]`
6. 大内容或多行结构化内容优先直接走 stdin artifact：`... | hive send <name> "<message>" --artifact -`；只有已有现成文件时才传 `--artifact <path>`。不要把 `$(cat <<EOF ...)` 这类多行 command substitution 直接塞进 `hive send`
7. `hive team` 显示每个 agent 的 runtime `inputState`（ready / waiting_user / unknown / offline）；如果某个 agent 的 `inputState` 是 `waiting_user`，说明它在等答案，用 `hive answer` 回答
8. `hive notify` 只面向当前 pane 的用户，不用于 agent 之间互相通知
9. 只有当"不马上看这条通知，agent 就无法继续，或者用户会错过关键时机"时，才允许 `hive notify`
10. 允许触发 `hive notify` 的典型场景：任务完成且用户明确在等结果；需要用户做决策；遇到阻塞且必须用户介入；执行 `git push`、覆盖文件、跑迁移、删除数据等高风险动作前需要确认
11. 禁止用 `hive notify` 做这些事：普通进度汇报、阶段性小完成、可选建议、agent 仍可自行继续推进的情况；凡是能通过 `hive team` 或 artifact 表达的，就不要打断用户
12. `hive notify` 的文案应站在 agent 对 user 说话的角度，直接说清楚"发生了什么 / 为什么现在需要你 / 按 `Space` 回来后要做什么"；浮层里按 `Space` 会跳回当前 pane，按任意键只关闭浮层
13. 升级顺序：有疑问时先用 `hive send` 问团队里的其他 agent。只有满足以下任一条件时才升级给用户：(a) 团队内没有其他 agent 可问；(b) 决策涉及不可逆外部副作用（`git push`、发 PR comment、删除数据、通知外部系统）；(c) 用户明确要求参与该类决策。

## 协议边界

- `hive send` 是发送消息的唯一入口，会写入 workspace durable store（当前是 `hive.db`）
- `hive answer` 用于回答 agent 的 pending question（AskUserQuestion）；只有目标处于 `waiting_user` 时才允许
- `hive team` 的 `inputState` 字段是从 agent session transcript 实时探测的 runtime 状态，不是事件投影
- GitHub PR comment / review 属于 workflow 层职责；需要发评论时直接用 `gh` / `gh api`，不要把这类 API 混进 Hive kernel 命令
- Hive 不是严格可靠消息队列：没有幂等性或 backpressure；需要恢复上下文时，应依赖 durable store 投影（如 `hive inbox` / hidden `hive delivery`）和 workspace artifact

## 加载 workflow

Hive 是基础 skill。更高层流程应在 Hive 之上加载，例如：

- 由 orchestrator 执行 `hive workflow load <agent> code-review`
- 或在 spawn 时使用 `hive spawn <agent> --workflow code-review`

当 workflow skill 被加载后，继续使用 Hive 命令作为通信与状态底座。

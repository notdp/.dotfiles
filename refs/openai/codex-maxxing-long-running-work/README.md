# Codex-maxxing for Long-Running Work 参考笔记

来源：OpenAI 白皮书《Codex-maxxing for long-running work — How Codex helps work continue beyond a single prompt》。
本地原件：同目录 `OAI_WhitePaper_Codex-maxxing26.pdf`（27 页，约 3.5MB）。
线上：https://openai.com/index/codex-maxxing-long-running-work （PDF 直链：https://cdn.openai.com/pdf/8a9f00cf-d379-4e20-b06f-dd7ba5196a11/OAI_WhitePaper_Codex-maxxing26.pdf ）

> 真实性说明：这是 OpenAI 的 **Codex 产品白皮书（marketing 体裁）**，全文唯一署名信源是创作者 Jason Liu 的个人用法。约一半篇幅是 Codex 特定 UI 形态（durable threads / voice input / remote control / side panel / mobile app），属于**产品功能展示，不是可迁移方法论**。本文按 `[推断]` / `[未验证]` 处理其中的效果性描述；不能当作官方事实或对其他 agent（CC / Droid / kilo / opencode）成立的结论直接引用。收录动机见同目录 PDF 与下方「可迁移机制」表。

## 一句话

把「单 prompt 一次性任务」升级为「跨多 prompt 持续推进的长任务」，靠给工作一个**可持续存在的载体**：持久线程 + 共享可复用记忆 + 工具访问 + 周期性自唤醒 + 对产物本身的复查。白皮书把这套抽象成一条 5 元 loop。

## 核心模型：5 元 loop（Section 08，本文最有价值的单点）

```
[Context] → [Tools] → [Memory] → [Recurrence] → [Review] ↺
```

长任务的能力不来自单个功能，而来自这五者闭环：拿到上下文 → 调工具干活 → 把有用信息沉淀成可复查的记忆 → 周期性回到同一线程继续 → 对产物复查后进入下一轮。**缺 Review 这环时，Memory 只是在记录「agent 自称完成了」**——这一判断与 `refs/long-running-agent` 笔记里「必须有独立 Judge」同构。

## 十节速览（区分「方法论」与「产品 UI」）

| # | 节 | 性质 | 一句话 |
|---|---|---|---|
| 01 | Durable threads | 产品 UI | 重要工作流用「常驻线程」当家，上下文/偏好/旧决策/未闭合 loop 在此累积；代价是长线程更贵 |
| 02 | Voice input | 产品 UI | 语音把「未加工的真实想法」（半记得的名字、模糊方向、不确定）喂进来，比打字更接近原始意图 |
| 03 | Steering | **方法论** | agent 干活**期间**追加下一条指令：纠偏 / 补上下文 / 批准下一步 / 排队下一动作 |
| 04 | Memory | **方法论** | 记忆要做成「能打开、能改、能 diff、能复用」的文件，而非埋在对话历史里的模糊印象 |
| 05 | Computer & browser use | 产品 UI | 区分可触达面：browser surface / 登录态 Chrome / computer use(GUI) / connectors / skills |
| 06 | Remote control | 产品 UI | 从手机等设备远程查看长任务、批准/改向；「远程 ≠ 跳过复查」 |
| 07 | Thread automations | **方法论** | 心跳式周期唤醒，定时回到同一线程推进；可多调度、可跑到条件满足、可调节奏 |
| 08 | Three loops | **方法论** | 三个落地例子（见下）演示 5 元 loop |
| 09 | Goals | **方法论** | 设「可验证的目标」而非「实现这个 plan」 |
| 10 | Side panel | 产品 UI | 产物（md/表格/csv/pdf/html/Storybook…）进同一线程当可复查对象，评论即指令 |

## 可迁移到 dotfiles 的机制（重点）

| 白皮书机制 | dotfiles 现有最近能力 | 关系 / 可吸收点 |
|---|---|---|
| **5 元 loop**（Context→Tools→Memory→Recurrence→Review） | `dev-long-run` / `operational-task` 工作流；`refs/long-running-agent` 的 Brain/Hands/Memory/Judge 四层 | 互为印证。其 Review=本仓库 Judge 层（`guard-verify`/`guard-check`）。可作为 long-run 类 skill 的「五件套自检清单」 |
| **Goals you can verify**（弱目标「实现这个 plan」vs 强目标「移植库，保持 public API，以原单测为成功判据，测试通过 + diff 有记录才算 done」） | 闭环验证红线 + `guard-verify` + dev-long-run 的 assertion/spec 文件 | 直接强化「验收先于实现」。Rich→Rust 例子=「用原测试套当外部成功标准」，正是本仓库「无证据的完成不接受」 |
| **Memory as reviewable vault**（`vault/` 下 AGENTS.md/TODO.md/projects/people/notes，loop 关闭就标 closed，决策写下「为什么重要」） | `docs/`、`~/.claude/.../memory/`（含本仓库的 MEMORY.md 索引 + 单文件单事实 + Why/How）、append-only logs | 形态高度一致。其「decision + why it matters」「loop closed 显式标注」可补进本仓库 memory/project 类条目纪律 |
| **Steering**（干活期间追加指令） | commit `8fdd85b` 已 document 的 Claude Code steering surfaces | 已覆盖。可作为跨 agent steering 差异化记录的外部佐证 |
| **Thread automations**（心跳周期唤醒、跑到条件满足、调节奏） | `ScheduleWakeup` / `CronCreate` / `/loop` 动态节奏 | 概念同构。「可调 cadence、可跑到条件满足、可多调度」与 /loop 的 fallback heartbeat 设计一致 |
| **Bounded action + 人审闸门**（三个 loop 都是「draft only, do not send」「any irreversible action → you decide」） | `/guard-gitops` SSOT 红线、guard-* 闸门、capsule 的 operational-task 契约（apply 需显式确认 + rollback） | 同向。不可逆动作前置人审，与本仓库「触碰仓库外可见状态先过 gitops」一致 |

## 三个 loop 例子（Section 08，均为 bounded + 人审）

1. **Chief of Staff**：定时查 Slack/Gmail 未回消息 → 检索上下文 → 起草回复；**用户仍决定发不发**（approval / tone / timing / final decision）。
2. **Monitor for feedback**：盯 Slack 反馈线程 → 更新 Remotion 工程 → 重渲染 → 备好修订待审；「Draft only. Do not post.」。
3. **Get a refund**：每 5 分钟查客服是否接入，接入后切到每分钟；准备状态检查/草稿回复/证据/建议下一步，**consent / approval / 任何不可逆动作留给用户**。

共同纪律：**任务可在用户离开时继续，但「动作」始终有界、不可逆操作必须人审**。

## 不要照搬（关键判断，非白皮书结论）

- **[推断] 一半内容是 Codex 产品特定 UI**（durable threads / voice / remote control / side panel / mobile QR），绑定 Codex 形态，对 markdown-prompt 的 skill harness 无直接迁移价值——只抄背后的「让工作有持续载体 + 闭环复查」思想。
- **[未验证] 全文无量化证据**，唯一信源是单个创作者用法；任何「效果更好」类描述不可当事实引用，更不能假设对 CC/Droid/kilo/opencode 成立（参见 memory：CC 原生特性采纳原则）。
- **[推断] 其 Memory/Goals 纪律本仓库已有更强版本**（真实性纪律、guard-verify、memory 单文件单事实 + Why/How）。迁移时不要被白皮书较弱的「生成期约束」带得降级。

## 与本仓库其他参考的关系

- `refs/long-running-agent/README.md`：同主题的另一份笔记（Brain/Hands/Memory/Judge 四层、Cursor 拓扑演进 Planner/Worker/Judge）。**两份互补**：那份偏多 agent 拓扑与故障墙，本份偏单 agent 的 loop 五件套与 bounded automation。长任务类 skill 改造时建议同读。

## 参考

- 白皮书页面：https://openai.com/index/codex-maxxing-long-running-work
- PDF 直链：https://cdn.openai.com/pdf/8a9f00cf-d379-4e20-b06f-dd7ba5196a11/OAI_WhitePaper_Codex-maxxing26.pdf
- 本地原件：`OAI_WhitePaper_Codex-maxxing26.pdf`（同目录）

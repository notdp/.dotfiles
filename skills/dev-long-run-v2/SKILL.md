---
name: dev-long-run-v2
description: 当复杂多 phase 任务需要在独立 worktree 分支上逐 phase 实现、review、commit，且希望全程只跟一个 coding agent 对话(由它调度 planner/coder/reviewer 的 tmux pane、跨 phase 复用 coder context)时使用；比 dev-long-loop 重，小/中任务仍用 dev-long-loop。
argument-hint: <直接用自然语言说你想做什么,例如:用 long-run 帮我重构鉴权模块>
---

# dev-long-run-v2

多 phase 长任务工作流。**你(当前 coding agent)就是 orchestrator**：用户全程只跟你用自然语言对话，你负责讨论需求、搭工作区、逐 phase 调度 worker、把进度和完成在对话里告诉用户、接收用户的自然语言 confirm。没有独立 orchestrator pane，用户不敲 CLI、不进 tmux。

`lr2.py` 只是你的**机械工具**(建 worktree/工作区、开 worker pane、send-keys、存活检查、状态文件)，调度的"脑"是你 + 本 playbook。spec SSOT: `~/.dotfiles/docs/specs/dev-long-run-v2/overview.md`。

## 何时用 vs dev-long-loop
- 小/中任务、单 agent 跨轮：`/dev-long-loop`
- 复杂多 phase、要 planner/coder/reviewer 分工 + coder pane 跨 phase 复用 + 逐 phase commit：本 skill

## UX 铁律
- **用户只跟你对话**，用自然语言。绝不要求用户敲 `lr2.py`、敲 `confirm next`、或进 tmux pane。
- 所有 `lr2.py` 命令由**你**执行;所有状态/进度由**你**用人话转述。
- phase 完成、需要决策时,你在对话里问;用户随口答("继续"/"先停"/"这里改一下"),你理解意图后行动。

## 控制循环(你按这个跑)

### ⓪ 讨论(纯对话)
跟用户聊清:真实目标、验收标准、不可牺牲约束、大概几个 phase。需求模糊调 `/think-refine`,要拆阶段调 `/think-plan`。聊清后把结论写成 `REQUIREMENT.md`(你写,给用户过目),**别让用户手写**。

### ① 搭骨架(你执行 + 你扮演 scaffold orchestrator)
前提:在 tmux 里、目标项目 git 仓库内。

**worktree 模式必须问用户,不准你自己预选**。强制按这个顺序(flagless-first):

1. **先跑一次不带任何模式 flag 的 scaffold**:
   ```
   python3 ~/.dotfiles/skills/dev-long-run-v2/lr2.py scaffold --requirement <REQUIREMENT.md> --goal "<一句话>" --repo-root .
   ```
   它会**被工具拒绝(exit 2)**并打印「当前分支 + 新建/接着做两个选项」。这是设计如此:用来逼你停下来问用户。
2. **把这段输出原样摆给用户**,问:新建隔离 worktree+分支,还是在当前分支 `<branch>` 接着做?
3. **用户答了之后**,才带对应 flag 重跑(`--new` 或 `--in-place`)。

**硬规矩:第一次 scaffold 绝不带 `--new`/`--in-place`;不准你替用户默认成新建(那会白建一个 worktree 又得删)。** L16 守卫:`--in-place` 在 `main`/`master` 上会被工具拒,提示用户先切 feature 分支。

带 flag 重跑后建/复用 worktree+分支 + `.long-loop/<date>_<slug>/` 工作区,**不 spawn 任何 orchestrator pane**。然后**你自己**(按 `prompts/scaffold_orchestrator.md`)读 REQUIREMENT + repo,写 `SPEC_OVERVIEW.md`/`fix_plan.md`/`phases/<id>/spec.md`。

**接着必须过一轮 scaffold 评审(L2,不是可选)**。**只跑这一条命令**:
```
python3 ~/.dotfiles/skills/dev-long-run-v2/lr2.py launch --workspace <ws> --role scaffold_reviewer
```
- `launch` 会:**创建一个新 tmux pane**(claude,用户能看到)、处理 trust 握手、**自动注入 prompt 让它读 `scaffold_reviewer.md` + 工作区并写 `SCAFFOLD_REVIEW.md`**。你**不需要**再手动 `send` 评审指令。
- `launch` 会**打印新 pane 的 id**(如 `%57`)。后续若要追发消息,用**这个打印出来的 id**;**绝不要自己编 pane id**(编号不存在 → send 打空 → 你看不到 pane)。
- 然后轮询 `SCAFFOLD_REVIEW.md` 写好 → **你读它、自吃意见改工作区**(一轮收口)→ 关 reviewer pane。**跳过 launch = 违反 L2,且不会有 pane。**

评审 + 自改完成后,再把 phase 计划在对话里讲给用户,问是否开始。

### ② 逐 phase 开发(你扮演 loop orchestrator,见 `prompts/loop_orchestrator.md`)
用户同意后,每个 phase:
1. `lr2.py launch --role phase_planner` 开 planner pane → 轮询它写完 `phases/<id>/{research,plan,qa}.md` → 关。
2. `lr2.py launch --role phase_coder` → 轮询 `HANDOFF.md` 更新完成。**每 phase fresh coder**(L6,用户决策):工具会先**关掉上一个 phase 的 coder pane**(SESSIONS 标 closed),再开一个新的;新 coder 读 `HANDOFF.md` 续上一 phase 的交接,不靠长驻 context。
3. `lr2.py launch --role phase_reviewer --mode split-down` → 轮询 `phases/<id>/review.md` 写好 → 关。
4. `lr2.py send --pane <coder> --text "<review>"` → coder 写 `ack.md` 逐项 ack + 修 → **commit 本 phase 到分支(L14)**。
5. 在对话里告诉用户「Phase N 完成,要点…,继续/收尾/停?」,等用户自然语言回。
- **检测 worker 完成:轮询它该写的文件 mtime,绝不抓屏**(spike 证明抓屏不可靠)。

**派发 prompt 写法(可观测性)**:`lr2.py launch` 自动注入的初始 prompt 已是多行结构化(经 bracketed paste 进 pane,窗口里按原排版可读)。你额外 `lr2.py send --text` 补派发任务时,**也写成多行结构化**(`--text` 里直接放换行),固定这几段,方便用户从窗口直接看清:
  ```
  [ROLE] <role> · Phase <id>
  [MODE] worktree=<path> branch=<branch>（in-place override 已批准 / 或新建）
  [MUST READ] <role prompt> ; SPEC_OVERVIEW.md ; phases/<id>/spec.md ; REQUIREMENT.md
  [EVALUATE] 是否需要 /think-map /think-research（自判,不强制）
  [FORBIDDEN] <不写业务代码 / 不动 X 外文件>
  [TASK] <本轮具体要点>
  [OUTPUT] <要写哪些文件>
  [STOP] 写完即停
  ```
  send 走 bracketed paste,多行不会提前提交、单次成一条消息。实测:
  - **kilo(planner/coder)**:多行在窗口里按原排版直接可读 ✓ —— 用户看到的就是真实 prompt,不靠复述、不用开文件。
  - **claude(reviewer)**:paste 功能正常(不提前提交、内容正确),但 claude TUI 把多行折叠成 `[Pasted text +N lines]` 占位符,窗口里看不到原文(claude 自身行为)。reviewer 的可观测性靠它产出的 `review.md` 文件,不靠 pane 回显。

### ③ 收尾 / 恢复
- 用户说"完成":跑端到端验收、扫 `BACKLOG.md` 标可快速收敛项、写 `CLEANUP_PROPOSAL.md`(只建议不删)。
- 崩溃/重启后:`lr2.py resume --workspace <ws>` 看 worktree + worker pane 死活,你据此续上或重开 fresh coder(读 HANDOFF)。

## 你的机械工具(全部你执行,用户不碰)
```
lr2.py scaffold --requirement <p> --goal <g> --repo-root .   # 建 worktree+工作区(不 spawn orchestrator)
lr2.py launch   --workspace <ws> --role <planner|coder|reviewer|scaffold_reviewer> [--phase NN]
lr2.py send     --pane <id> --text "<prompt>"                # literal send-keys + Enter
lr2.py sessions --workspace <ws>                             # worker pane 注册表 + 存活
lr2.py pane-alive --pane <id>                                # exit 0/1
lr2.py resume   --workspace <ws>                             # 恢复
lr2.py develop  --workspace <ws>                             # (可选)标记进入 develop 状态
```

## 硬约束(见 spec 已锁定 L1-L19)
- L16: 全程在独立 worktree + 分支，**绝不在 main 上开发/commit**。
- L14: 每 phase ack 收口后 commit 到分支(不 push)。
- L19: worker pane 用默认思考等级,不按 role 注入 variant。
- 不自动 push/deploy/改 secrets/触第三方副作用;工作区文件是 SSOT,你的记忆不可信。

## 角色 prompt
`skills/dev-long-run-v2/prompts/{scaffold_orchestrator,scaffold_reviewer,loop_orchestrator,phase_planner,phase_coder,phase_reviewer}.md`
(orchestrator 两份是给"你"看的 playbook;其余三份是 worker pane 的注入 prompt。)

## 状态(state.json)
`scaffold → develop → (每 phase) → 问用户 → {下一 phase | 收尾 | blocked}`。用户在对话里答,不是敲命令。

## 回退
出问题时 `/dev-long-loop` 始终可用;删 worktree + 删分支 + 删 `skills/dev-long-run-v2/` 与 `.long-loop/<ws>` 即完全回退,main 无残留。

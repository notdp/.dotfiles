---
name: dev-long-run-v2
description: 当复杂多 phase 任务需要在独立 worktree 分支上逐 phase 实现、review、commit，且希望全程只跟一个 coding agent 对话(由它调度 planner/coder/reviewer 的 tmux pane、每 phase fresh coder 靠 HANDOFF 续接)时使用；单次小改动不走本 skill，用 /dev-tdd。
argument-hint: <直接用自然语言说你想做什么,例如:用 long-run 帮我重构鉴权模块>
---

# dev-long-run-v2

多 phase 长任务工作流。**你(当前 coding agent)就是 orchestrator**：用户全程只跟你用自然语言对话，你负责讨论需求、搭工作区、逐 phase 调度 worker、把进度和完成在对话里告诉用户、接收用户的自然语言 confirm。没有独立 orchestrator pane，用户不敲 CLI、不进 tmux。

`lr2.py` 只是你的**机械工具**(建 worktree/工作区、开 worker pane、send-keys、存活检查、状态文件)，调度的"脑"是你 + 本 playbook。spec SSOT: `~/.dotfiles/docs/specs/dev-long-run-v2/overview.md`。

## 何时用
- 单次代码改动（一个 feature / bug fix）：`/dev-tdd`
- 复杂多 phase、要 planner/coder/reviewer 分工 + 每 phase fresh coder(HANDOFF 续接) + 逐 phase commit：本 skill
- 跨子系统/不可逆大改的交付治理：`/dev-large-delivery`(Phase 内可嵌套本 skill)

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
   python3 ~/.dotfiles/coding-skills/dev-long-run-v2/lr2.py scaffold --requirement <REQUIREMENT.md> --goal "<一句话>" --repo-root .
   ```
   它会**被工具拒绝(exit 2)**并打印「当前分支 + 新建/接着做两个选项」。这是设计如此:用来逼你停下来问用户。
2. **把这段输出原样摆给用户**,问:新建隔离 worktree+分支,还是在当前分支 `<branch>` 接着做?
3. **用户答了之后**,才带对应 flag 重跑(`--new` 或 `--in-place`)。

**硬规矩:第一次 scaffold 绝不带 `--new`/`--in-place`;不准你替用户默认成新建(那会白建一个 worktree 又得删)。** L16 守卫:`--in-place` 在 `main`/`master` 上会被工具拒,提示用户先切 feature 分支。

带 flag 重跑后建/复用 worktree+分支 + `.long-loop/<date>_<slug>/` 工作区,**不 spawn 任何 orchestrator pane**。然后**你自己**(按 `prompts/scaffold_orchestrator.md`)读 REQUIREMENT + repo,写 `SPEC_OVERVIEW.md`/`fix_plan.md`/`phases/<id>/spec.md`。

**接着必须过一轮 scaffold 评审(L2,不是可选)**。**双路 reviewer 并发**(L-dual):
```
python3 ~/.dotfiles/coding-skills/dev-long-run-v2/lr2.py launch --workspace <ws> --role scaffold_reviewer_a
python3 ~/.dotfiles/coding-skills/dev-long-run-v2/lr2.py launch --workspace <ws> --role scaffold_reviewer_b
```
- 两个 `launch` 各**创建一个 tmux pane**(一个 kilo、一个 cc,由 config.yaml 决定),各自独立审查。
- 记下两个 pane id(如 `%57`、`%58`)。**绝不要自己编 pane id**。
- 分别 `await` 等两个 reviewer DONE:
  ```
  lr2.py await --status <ws>/scaffold_reviewer_a.status --pane <pane_a>
  lr2.py await --status <ws>/scaffold_reviewer_b.status --pane <pane_b>
  ```
- **降级(D3)**:一路返回 DEAD/TIMEOUT → 在对话里告知用户哪路挂了,用另一路的 review 继续,不卡流程。
- 两份 review 都完成后 → **你读 `SCAFFOLD_REVIEW_A.md` + `SCAFFOLD_REVIEW_B.md`、汇总自吃意见改工作区**(一轮收口)→ 关两个 reviewer pane。
- **旧单路 config 兼容**:如果 config 里是 `scaffold_reviewer`(非 `_a`/`_b`),按原单路流程跑。

评审 + 自改完成后,再把 phase 计划在对话里讲给用户,问是否开始。

### ② 逐 phase 开发(你扮演 loop orchestrator,见 `prompts/loop_orchestrator.md`)
用户同意后,每个 phase:
1. `lr2.py launch --role phase_planner` 开 planner pane → 轮询它写完 `phases/<id>/{research,plan,qa,verify_plan}.md`（四个文件）→ `lr2.py close --role phase_planner`(或交给 complete-phase 兜底)。
2. `lr2.py launch --role phase_coder` → `await` 等到 **`DONE impl`**(coder 实现完、**verify.sh 写好并本地跑过**、HANDOFF 已更新、**未 commit**,等 review;两段式信号的前半段)。**每 phase fresh coder**(L6,用户决策):工具会先**关掉上一个 phase 的 coder pane**(SESSIONS 标 closed),再开一个新的;新 coder 读 `HANDOFF.md` 续上一 phase 的交接,不靠长驻 context。
3. **双路 review(L-dual)**:
   ```
   lr2.py launch --role phase_reviewer_a --mode split-down --phase NN
   lr2.py launch --role phase_reviewer_b --mode split-down --phase NN
   ```
   分别 `await` 两个 reviewer(各自写 `review_a.md` / `review_b.md` + 各自的 status):
   ```
   lr2.py await --workspace <ws> --phase NN --role phase_reviewer_a --pane <pane_a>
   lr2.py await --workspace <ws> --phase NN --role phase_reviewer_b --pane <pane_b>
   ```
   **降级(D3)**:一路返回 DEAD/TIMEOUT → 告知用户,用另一路继续。两路都完成后关两个 reviewer pane。
   **旧单路 config 兼容**:config 里是 `phase_reviewer`(非 `_a`/`_b`)则按原单路跑。
4. **先 `lr2.py reset-status --phase NN --role phase_coder`**(清掉残留的 `done impl`,防 stale done 误判)→ 把两份 review 拼接发给 coder:
   ```
   lr2.py send --pane <coder> --text "## Review A\n<review_a 内容>\n\n## Review B\n<review_b 内容>" --workspace <ws>
   ```
   coder 写 `ack.md`(含 `## Blocker Resolutions`,每行 `- [fixed] A:B1 …` 或 `- [rejected] B:B2 理由…` 带来源前缀+ID)逐项仲裁 + 修认同的(含 verify.sh 的 Verification Coverage blocker) → **commit 本 phase 到分支(L14)** → `await` 等到 **`DONE commit=<hash>`**。
   注意：reviewer 现在会检查 verify.sh 对 verify_plan.md 的覆盖度，可能产出 Verification Coverage blocker；coder 修 verify.sh 时不得降低 verify_plan auto 项的覆盖。verify_plan 覆盖度检查是 prompt-level gate（靠 reviewer blocker 拦），不是 lr2.py 的机器 gate。
5. **完成门禁(L23,硬门)**:`lr2.py verify --phase NN`(真跑 verify.sh)→ qa.md 有 `## 人工验证` 就把 目的/操作/观察 贴给用户点验确认(**在 complete-phase 之前**——翻勾必须是最后一步,没有翻回去的工具)→ `lr2.py complete-phase --phase NN`(过门禁才翻 `fix_plan [x]`,exit 2 就打回,**绝不手翻**;门禁含 verify.json.ok + review 非空 + 每个 blocker 都有裁决(fixed 或 rejected) + **commit 证据**:status 声明的 `commit=<hash>` 必须真实在分支上)。
6. 在对话里告诉用户「Phase N 完成(门禁已过、verify 真跑通),要点…,继续/收尾/停?」,等用户自然语言回。
- **检测 worker 完成:用 `lr2.py await --workspace <ws> --phase NN --role <role> --pane <pane>`**(lr2 内部用 resolve_phase_dir 拼出真实 status 路径,**不要手拼 `phases/<id>/<role>.status`**;查机器可读 status token + 每轮查 pane 死活 + **idle 兜底** + 有界超时;退出码 `0 DONE`/`2 BLOCKED`/`3 DEAD`/`4 TIMEOUT`/`5 COMPACT`/`6 IDLE`)。worker 完成时把 `.status` 整文件写成一行 `done commit=<hash>`(只写状态,别带文件名/等号)。`6 IDLE` = 干完回到输入框却没写 status(最常见假死),await 附 pane tail,据此 send 重发提示或标 stuck;`4 TIMEOUT` 同样看 tail 判处理。**绝不手写 `sleep(60)` 去 grep prose**(coder 早完成也等不到、还查不出 pane 死活——这正是卡死过的坑),也绝不抓屏。

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
- 用户说"完成":写根 `acceptance.sh` → `lr2.py verify --acceptance`(真跑端到端验收)→ 人工验收项贴给用户确认 → `lr2.py complete-run`(门禁=**fix_plan 全勾 + acceptance 过**,才置 `state=completed`,**没过不准说完成**;过后自动关所有 worker pane,要留现场调试加 `--keep-panes`)→ 扫 `BACKLOG.md` 标可快速收敛项、写 `CLEANUP_PROPOSAL.md`(只建议不删)。
- 崩溃/重启后:`lr2.py resume --workspace <ws>` 看 worktree + worker pane 死活,你据此续上或重开 fresh coder(读 HANDOFF)。**resume 后优先检查当前 phase 是否缺 `verify_plan.md`**：缺则先 launch phase_planner 补产(brief 说明是 resume 补缺),planner done 后再 launch coder/reviewer。

## 你的机械工具(全部你执行,用户不碰)
```
lr2.py scaffold --requirement <p> --goal <g> --repo-root .   # 建 worktree+工作区(不 spawn orchestrator)
lr2.py launch   --workspace <ws> --role <phase_planner|phase_coder|phase_reviewer_a|phase_reviewer_b|scaffold_reviewer_a|scaffold_reviewer_b> [--phase NN]
lr2.py send     --pane <id> --text "<prompt>" --workspace <ws>  # bracketed paste + Enter(--workspace 校验 pane 在 SESSIONS 注册过,防灌错 pane,默认带上)
lr2.py close    --workspace <ws> --role <role>               # 关该 role 存活 pane + SESSIONS 标 closed(幂等)
lr2.py sessions --workspace <ws>                             # worker pane 注册表 + 存活
lr2.py pane-alive --pane <id>                                # exit 0/1
lr2.py resume   --workspace <ws>                             # 恢复
lr2.py develop  --workspace <ws>                             # (可选)标记进入 develop 状态
lr2.py verify   --workspace <ws> --phase NN                  # 在 worktree 真跑 verify.sh,写 verify.json(执行证据)
lr2.py verify   --workspace <ws> --acceptance                # 真跑根 acceptance.sh,写 acceptance.json(端到端验收)
lr2.py stats    --workspace <ws>                             # (L26)只读:读 metrics.jsonl 出 run/per-phase 进度 + 卡死汇总(给用户报进度,别靠记忆复述)
lr2.py reset-status --workspace <ws> --phase NN --role <r>   # status 重置为 coding(发 review 前清 stale `done impl`)
lr2.py gate     --workspace <ws> --phase NN                  # 只读查门禁(不翻 fix_plan),BLOCK 原因同 complete-phase
lr2.py complete-phase --workspace <ws> --phase NN            # 过门禁才翻 fix_plan [x](唯一标完成入口);不过 exit 2;过后自动关 planner/reviewer 残留 pane
lr2.py complete-run   --workspace <ws> [--keep-panes]        # 过 acceptance 门禁才置 state=completed;过后自动关所有 worker pane(--keep-panes 保留现场)
```

## 硬约束(见 spec 已锁定 L1-L26)
- L16: 全程在独立 worktree + 分支，**绝不在 main 上开发/commit**。
- L14: 每 phase ack 收口后 commit 到分支(不 push)。
- L19: worker pane 用默认思考等级,不按 role 注入 variant。
- **L23(完成门禁)**: phase 完成 / run 收尾**只能经 `lr2.py complete-phase` / `complete-run` 过门禁**,不许手翻 `fix_plan.md`、不许手置 `state=completed`。门禁五条:① `verify.sh` 必须由 `lr2.py verify` **真跑**且过(verify.json.ok=真,测试写了不跑=没写);② review 必须存在非空(双路时至少一路有产出;reviewer 环节不可静默跳过);③ review 每个 `[blocker <源>:B<n>]` 必须在 ack 有裁决——`[fixed]` 或 `[rejected]`(不许 deferred;双路时 coder 是仲裁者,rejected 不阻塞但必须有理由);④ **commit 证据**:`phase_coder.status` 声明的 `commit=<hash>` 必须真实存在于 worktree 分支(L14 不收口头声明);⑤ 收尾必须 fix_plan 全勾 + `acceptance.sh` 真跑过 + 人工验收项经用户确认。**首次实战(00167)就栽在"验证只写没跑 + blocker 静默放行 + acceptance 没执行",L23 就是堵这个。**
- 不自动 push/deploy/改 secrets/触第三方副作用;工作区文件是 SSOT,你的记忆不可信。

## 角色 prompt
`skills/dev-long-run-v2/prompts/{scaffold_orchestrator,scaffold_reviewer,loop_orchestrator,phase_planner,phase_coder,phase_reviewer}.md`
(orchestrator 两份是给"你"看的 playbook;其余三份是 worker pane 的注入 prompt。)

## 状态(state.json)
`scaffold → develop → (每 phase) → 问用户 → {下一 phase | 收尾 | blocked}`。用户在对话里答,不是敲命令。

## 验收 / 停止 / 风险(quality gate)
- **验收(acceptance)**:跑通一个真实多 phase 任务、coder 真 commit 到分支(`git log`)、reviewer 真出 `phases/<id>/review.md`、用户能 phase 间介入。**光单测过不算完成**——要端到端可观察证据。
- **停止条件**:每 phase 进 wait_confirm 停等用户;`lr2.py await` 返回 `BLOCKED/DEAD/TIMEOUT/IDLE` 立即停并报告给用户,不空转;`IDLE/TIMEOUT` 先按 await 附的 pane tail 重发提示或调大超时,连续卡住别硬冲,escalate。
- **(L26)卡死信号**:`lr2.py verify` 失败会持久化 `stuck.json`(失败指纹计数);连续 2 次**同指纹**失败时 verify 输出 `STUCK:` 行——这是磁盘上的客观计数,不是你凭记忆数的。看到 STUCK 别再盲改重试,调 `/think-unstuck` 或问用户。计数跨 compact/resume 不丢(`resume`/`stats` 都会重新暴露)。
- **风险 / gotchas**:
  - worker 完成**只认 status 文件**(`lr2.py await`),**禁止 grep prose / 抓屏**(曾因此假死)。
  - claude reviewer pane 收多行 prompt 会折叠成 `[Pasted +N]`,原文看 `review.md` 不看 pane。
  - **false-IDLE**:worker 跑长时间无输出的命令(大型测试套件等)时,画面静止 + 就绪标识在屏 → 可能被误判 IDLE。await 的 `6 IDLE` 永远先看附带的 pane tail 再处置;预期有长静默步骤的 phase 把 `--idle-timeout` 调大(不是只调 `--timeout`)。
  - 每 phase **关旧 coder 开新 fresh**(不长驻),续接靠 `HANDOFF.md`。
  - 不在 `main` 上开发/commit;不自动 push/deploy。
  - **旧 workspace resume 缺 `verify_plan.md`**:旧 workspace 已跑完 planner 但未进 coder/review 时,当前 phase 目录可能没有 `verify_plan.md`。resume 后在启动 coder 前检查：缺 `verify_plan.md` → 先 launch phase_planner 补产,planner done 后再 launch coder。
  - **verify_plan.md 自身出错**:verify_plan 覆盖度检查是 prompt-level gate（靠 reviewer blocker 拦），不是 lr2.py 的机器 gate。reviewer 标 blocker 后 coder 可修改 verify_plan.md（唯一允许 coder 改 planner 产物的场景）；coder blocked（verify_plan conflict）时 orchestrator 回退 planner 修订。

## 回退
出问题时删 worktree + 删分支 + 删 `.long-loop/<ws>` 即丢弃整次运行,main 无残留;代码已 commit 在 `lr2/<slug>` 分支上,删前确认不要了。

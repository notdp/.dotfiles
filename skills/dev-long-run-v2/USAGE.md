# dev-long-run-v2 上手操作手册(首次使用)

> 状态:v0。整条管道实测跑通过,但完整多 phase 自动循环还没在真实任务上跑完过 —— 你这次是第一次实战,盯紧点。代码只落在独立 worktree + `lr2/<slug>` 分支,**main 永远不会被碰**,出事直接删 worktree + 删分支即可全退。

## 全景:它怎么跑

三个命令,对应三个阶段。中间你通过 attach 进 tmux 看 agent 干活、在 pane 里给指令。

| 阶段 | 命令 | 谁在干活 | 你要做什么 |
|---|---|---|---|
| ① 搭骨架 | `scaffold` | scaffold orchestrator(kilo)+ reviewer(claude) | 看它拆的 phase 合不合理 |
| ② 逐 phase 开发 | `develop` | loop orchestrator 调度 planner/coder/reviewer | 每个 phase 结束时打 `confirm next/done` |
| ③ 崩溃恢复 | `resume` | — | 看 pane 死活,按提示恢复 |

记住一个变量,后面都用它:

```
LR2=~/.dotfiles/skills/dev-long-run-v2/lr2.py
```

## 前提(三个,缺一不可)

1. 在**目标项目的 git 仓库根目录**里(main 脏也行,流程不碰 main,只会警告)。
2. **在 tmux 里**(orchestrator 和 coder 都是 tmux pane;不在 tmux 里 attach 不进去看)。
3. kilo / claude 命令能正常跑。

## 步骤 ①:写需求 + scaffold

先在任意位置手写 `REQUIREMENT.md`,白话写清:要做什么、目标、怎样算做完。写得越清,后面质量越好。

然后在项目根目录跑:

```
python3 $LR2 scaffold --requirement ~/REQUIREMENT.md --goal "你的任务一句话" --repo-root .
```

它会打印 4 个路径。**把 workspace 路径记下来**,后面两步都要用:

```
scaffold ready.
  workspace: <项目>/.long-loop/<日期>_<slug>     ← 记这个
  worktree : ../<项目>-lr2-<slug>                ← 代码改在这里
  branch   : lr2/<slug>
  orch pane: %552 (tmux attach -t lr2-<slug>)
```

这时 scaffold orchestrator 已经在一个 kilo pane 里跑起来了。attach 进去看:

```
tmux attach -t lr2-<slug>
```

它会读你的需求,产出 `SPEC_OVERVIEW.md` / `fix_plan.md` / 各 phase 的 `spec.md`,再开一个 claude reviewer 审一轮、自己改。

**你这一步要做的**:看它拆出来的 phase 合不合理。不对就直接在 pane 里跟它说。看完按 `Ctrl-b` 再按 `d` 退出来(pane 继续活着)。

## 步骤 ②:develop 逐 phase 开发

scaffold 满意后:

```
python3 $LR2 develop --workspace <步骤①记下的 workspace>
```

loop orchestrator 起来,开始循环:planner 增强 → coder 实现 → reviewer 审一轮 → coder 逐项回应 + 修 + **commit 到 `lr2/` 分支** → 然后**停下来等你**。

attach 进 orchestrator pane,它会提示:

```
Phase 01 complete. confirm next / confirm done / block <reason>
```

你**就在它这个 pane 里**直接打字:

1. `confirm next` — 做下一个 phase
2. `confirm done` — 收尾(跑验收 + 出 `CLEANUP_PROPOSAL.md` + 扫 backlog)
3. `block 原因` — 卡住,记录原因

phase 之间你可以去 worktree(`../<项目>-lr2-<slug>`)自己跑测试、看 diff、合 PR,再回来 `confirm next`。

## 步骤 ③:resume 恢复

pane 被误关、电脑重启、或你想接着上次:

```
python3 $LR2 resume --workspace <workspace>
```

它告诉你 worktree 在不在、每个 pane 死活,并给恢复建议(比如 coder pane 死了:重开 fresh 读 `HANDOFF.md` 续,或标 failed)。

## tmux 速查(不熟 tmux 看这个)

| 你想做 | 按键 / 命令 |
|---|---|
| 进入会话看 agent | `tmux attach -t lr2-<slug>` |
| 退出但不杀 agent | 先按 `Ctrl-b`,松开,再按 `d` |
| 在多个 pane 间切换 | `Ctrl-b` 然后方向键 |
| 看有哪些会话 | `tmux ls` |
| 看每个 pane 死活 | `python3 $LR2 sessions --workspace <ws>` |

## 出问题先自查这几样

1. **看状态文件**:`<workspace>/state.json`(现在到哪一步)、`SESSIONS.md`(各 pane 注册表)、`logs.md`(流水)。
2. **看 pane 死活**:`python3 $LR2 sessions --workspace <ws>`。
3. **agent 跑偏了**:直接 attach 进它的 pane 纠正它,或在 orchestrator pane 打 `block 原因`。
4. **完全乱了想重来**:`tmux kill-session -t lr2-<slug>`,删 worktree(`git worktree remove --force ../<项目>-lr2-<slug>`),删分支(`git branch -D lr2/<slug>`),删 `.long-loop/<workspace>`。main 不受影响。

遇到上面解决不了的,把**报错原文 + 你跑的命令 + `state.json` 内容**发给我。

## 这次实战要盯的点(v0)

- coder 的代码是否真的 commit 到了 `lr2/` 分支(去 worktree `git log` 看)。
- orchestrator 是否在每个 phase 结束正确停下等你 confirm(而不是自己往下冲)。
- reviewer 的 `phases/<id>/review.md` 是否真写出来了。

哪一条不对,就是个反馈点,发给我。

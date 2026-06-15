# dev-long-run 上手操作手册(首次使用)

> 代码只落在独立 worktree + `lr/<slug>` 分支(或你选的当前分支),**main 永不被碰**,出事删 worktree+分支即可全退。

## 一句话

你**只跟一个 coding agent 对话**,不敲命令、不写文件、不进 tmux。agent 当 orchestrator 替你干所有机械活,**每个 phase 做完都停下问你**,你说一句就推进。全程分 4 步,下面按步走。

```
⓪ 讨论需求  →  ① 搭骨架(选分支 + 评审)  →  ② 逐 phase 开发循环  →  ③ 收尾
   你来回聊        看计划说"可以"            每段说"继续/停/改"        说"完成"
```

---

## ⓪ 讨论需求

跟 agent 说你想做什么,来回聊清:目标、验收标准、约束。
> 例:"用 long-run 帮我重构鉴权模块,要平滑迁移,别动现有调用方。"

agent 会问几个问题,然后**替你写好 `REQUIREMENT.md`** 给你过目。你不用自己写文件。

## ① 搭骨架(选分支 + 评审)

确认需求后,agent 先问你 **worktree 模式**(它会显示当前分支):
- **新建**:新建隔离 worktree + `lr/<slug>` 分支。
- **接着做**:在当前分支接着干(延续已有工作时选)。

选完它建工作区、拆出 phase 计划,**再开一个 reviewer pane 审一轮**(你当前 tab 里会看到这个 pane),审完自己改,然后把 phase 计划讲给你:
> "拆成 3 个 phase:①…②…③…,phase 1 先开始?"

你看计划合不合理,说"可以"或"②先别动数据库"之类。

## ② 逐 phase 开发循环 ← 你主要在这控制

跟 agent 说"开始" / "进入 Phase 01"。它每个 phase 自动跑:
planner 充实计划 → coder 写代码 → reviewer 审 → coder 改 + **commit 到分支** → **停下来问你**。

你当前 tab 里会看到 planner/coder/reviewer 的 pane split 出来(纯旁观,`Ctrl-b`+方向键切过去看)。

**你的控制台就是这几句话(每个 phase 结束时说):**

| 你想 | 说 |
|---|---|
| 做下一个 phase | **"继续" / "下一个"** |
| 暂停,我先看看 | "先停" / "等一下" |
| 这里要调整 | "把 X 改成 Y" |
| 全做完了收尾 | "完成" / "收尾" |
| coder 卡死了 | "重开 coder,读 HANDOFF 续" |

**可以一直 "继续" 推到底**:它每个 phase 都停着等你,一次"继续"推进一个 phase,你始终捏着闸,不会自己冲完。中途想插手随时说话打断。

## ③ 收尾

最后一个 phase 后说"完成"。agent 跑端到端验收、扫出可顺手收敛的 backlog 项、写 `CLEANUP_PROPOSAL.md`(只建议不删),问你要不要做哪个。

---

## 前提(三个)
1. 在**目标项目的 git 仓库根目录**里。
2. **在 tmux 里**(worker pane 要 split 进你当前 window)。
3. kilo / claude 命令能正常跑。

## 出问题
- **崩溃/重启**:跟 agent 说"恢复 long-run",它跑 `resume` 续上。
- **想全删重来**:说"删掉这次 long-run",它关 worker pane + 删 worktree + 删分支,main 不受影响。
- **agent 跑偏**:对话里直接纠正,或说"停"。
- 卡住自己搞不定:把**报错原文 + 当时在做什么 + `state.json`** 发给我。

## 要盯的点
- agent 该**开独立 coder pane** 写代码,不是在对话里自己写。怀疑时说"给我看 `lr.py sessions`":有 `phase_coder` pane=对;一个 pane 没有=纠正它去 launch。
- 每个 phase 真停下问你了吗(没停就提醒它要 confirm)。
- coder 真 commit 到 `lr/` 或你的分支了吗(让它给你看 `git log`)。
- reviewer 真写出 `phases/<id>/review.md` 了吗。

哪条不对,就是反馈点,发我。

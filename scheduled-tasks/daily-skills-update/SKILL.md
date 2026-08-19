---
name: daily-skills-update
description: 每天 09:00 用 npx skills update 更新本机 agent skills
---

每日更新本机通过 npx skills 安装的 agent skills。

执行：`npx -y skills update -g -y`（非交互，全局 scope）。
实体目录为 ~/.agents/skills/，lock 文件为 ~/.dotfiles/skills/.skill-lock.json（symlink 进 ~/.claude/skills/）。

约束：
- 更新会改动 ~/.dotfiles 里的 lock 文件，这是预期行为。跑完必须提交，别把 diff 攒在仓库里。提交一律落在 main 上，只提交这一个文件，不要碰仓库里的其他改动。本任务直接 git commit，不走 ce-commit skill。

  不要 checkout 切分支（~/.dotfiles/skills/.skill-lock.json 就是 live 文件，切走会把它还原成旧版，跟 ~/.agents/skills/ 里已装的新 skill 对不上）。不管当前在哪个分支，都走同一条路：先 fetch，再用临时 worktree 基于**刚取回的 origin/main** 提交。绝不能基于本地 main —— 本地 main 可能落后远端，那样 push 必被拒，还会在本地攒下推不上去的滞留提交。

  ```
  git -C ~/.dotfiles fetch -q origin main
  W=$(mktemp -d)/main
  git -C ~/.dotfiles worktree add -q --detach "$W" origin/main
  cp ~/.dotfiles/skills/.skill-lock.json "$W/skills/.skill-lock.json"
  git -C "$W" diff --quiet -- skills/.skill-lock.json || {
    git -C "$W" commit -q -m "chore(skills): bump lockfile from daily skills update" -- skills/.skill-lock.json
    git -C "$W" push origin HEAD:main
  }
  git -C ~/.dotfiles worktree remove --force "$W"
  ```

  push 成功后，如果当前就在 main 上，让本地 main 跟上远端：

  ```
  git -C ~/.dotfiles checkout origin/main -- skills/.skill-lock.json
  git -C ~/.dotfiles merge --ff-only origin/main
  ```

  第一行不能省。此刻 lock 在工作区里相对 HEAD 仍是"已修改"，`merge` 只看这个脏标记、不管内容其实已经等于目标提交，直接 ff 会被拒；先把该路径对齐 origin/main（内容一致，落盘零变化）再 ff 才过得去。ff 不动说明本地 main 与远端有分歧，别强推，写进汇总。不在 main 上就保持原样，当前分支会留着 lock 的未提交改动（等它 rebase/merge 到 main 就没了），汇总里写一句分支名。

  push 失败（远端有分歧等）不要自己 rebase 或 force，如实写进汇总。
- 单个 skill 更新失败先原地重试一次（`npx -y skills update -g -y <name>`），仍失败才算失败并在汇总里写明。
- Claude Code plugin（ponytail / hive / hive-channel / cloudflare）的 marketplace 已全部开启 autoUpdate，不在本任务范围内，不要更新它们。

输出：简短中文汇总哪些 skill 更新了（名称及来源仓库）、哪些失败及原因；全程无更新则回复"今日无更新"。提交所在分支不是 main 时，末尾补一句分支名。不要生成 HTML 报告。

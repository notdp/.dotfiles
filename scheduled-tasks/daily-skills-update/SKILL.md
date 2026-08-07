---
name: daily-skills-update
description: 每天 09:00 用 npx skills update 更新本机 agent skills
---

每日更新本机通过 npx skills 安装的 agent skills。

执行：`npx -y skills update -g -y`（非交互，全局 scope）。
实体目录为 ~/.agents/skills/，lock 文件为 ~/.dotfiles/skills/.skill-lock.json（symlink 进 ~/.claude/skills/）。

约束：
- ~/.claude/skills/ordo-platform 是手工维护的本地 skill，不归 npx skills 管，不要动它。
- 更新会改动 ~/.dotfiles 里的 lock 文件，这是预期行为。跑完必须提交，别把 diff 攒在仓库里：
  `git -C ~/.dotfiles diff HEAD --quiet -- skills/.skill-lock.json || git -C ~/.dotfiles commit -m "chore(skills): bump lockfile from daily skills update" -- skills/.skill-lock.json`
  只提交这一个文件，不要碰仓库里的其他改动。本任务直接 git commit，不走 ce-commit skill。
  提交后 push：`git -C ~/.dotfiles push`。push 失败（远端有分歧等）不要自己 rebase 或 force，如实写进汇总。
- 单个 skill 更新失败先原地重试一次（`npx -y skills update -g -y <name>`），仍失败才算失败并在汇总里写明。
- Claude Code plugin（ponytail / hive / hive-channel / cloudflare）的 marketplace 已全部开启 autoUpdate，不在本任务范围内，不要更新它们。

输出：简短中文汇总哪些 skill 更新了（名称及来源仓库）、哪些失败及原因；全程无更新则回复"今日无更新"。不要生成 HTML 报告。
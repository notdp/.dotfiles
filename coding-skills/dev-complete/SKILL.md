---
name: dev-complete
description: 当小到中等需求想要完备开发流程（spec→kilo+gpt coding→CC+kilo dual review→verify）但不需要分 phase 时使用；单次大改动用 /dev-long-run，纯 bug fix 用 /dev-tdd。
argument-hint: <直接用自然语言说你想做什么>
---

# dev-complete

单 pass 完备开发。**你(当前 coding agent)就是 orchestrator**：用户全程只跟你用自然语言对话，你负责写 spec、调度 coder+reviewer pane、报进度。没有独立 orchestrator pane，用户不敲 CLI、不进 tmux。

`dc.py` 是你的**机械工具**（建 workspace、开 pane、send-keys、存活检查、verify、gate），调度的"脑"是你 + 本 playbook。

> **路径约定**：下文所有裸写 `dc.py <cmd>` 的地方，实际执行时一律用 `python3 ~/.dotfiles/coding-skills/dev-complete/dc.py <cmd>`。

## 何时用
- 单次 bug fix / 纯测试：`/dev-tdd`（无 tmux 依赖）
- 小到中等需求，想要完整 spec→code→review→verify 链但不需要分 phase：**本 skill**
- 复杂多 phase 长任务：`/dev-long-run`

## UX 铁律
- **用户只跟你对话**，用自然语言。绝不要求用户敲 `dc.py`、敲 `confirm`、或进 tmux pane。
- 所有 `dc.py` 命令由**你**执行；所有状态/进度由**你**用人话转述。

## 控制循环

### ⓪ 讨论(纯对话)
跟用户聊清需求：真实目标、验收标准、不可牺牲约束。需求模糊调 `/think-refine`。聊清后把结论写成 `REQUIREMENT.md`(你写,给用户过目)。

### ① 写 spec(你直接写)
**你自己**写 `spec.md` + `qa.md`，不开 planner pane。spec 包含：目标、改动范围、关键接口、验证策略。qa.md 包含自动化验证项（最终变成 verify.sh）和人工验证项。**写完给用户过目，批准后才继续。**

### ② scaffold workspace
前提：在 tmux 里、目标项目 git 仓库内。

**worktree 模式必须问用户**（同 dev-long-run 的 flagless-first）：
1. 先跑不带 flag 的 scaffold → 被拒(exit 2) + 打印选项
2. 把选项给用户，问新建还是接着做
3. 用户答了才带 flag 重跑

scaffold 建好后，把你写的 spec.md + qa.md 复制到 workspace。

### ③ launch coder → await DONE impl
```
dc.py launch --workspace <ws> --role coder
```
记下 pane_id。coder 读 spec+qa 实现代码 + 写 verify.sh 并本地跑过 → status 写 `done impl`。
```
dc.py await --workspace <ws> --role coder --pane <pane>
```

### ④ launch dual reviewers → await both
```
dc.py launch --workspace <ws> --role reviewer_a --mode split-down
dc.py launch --workspace <ws> --role reviewer_b --mode split-down
```
分别 await：
```
dc.py await --workspace <ws> --role reviewer_a --pane <pane_a>
dc.py await --workspace <ws> --role reviewer_b --pane <pane_b>
```
**降级**：一路返回 DEAD/TIMEOUT → 告知用户，用另一路继续。两路都完成后关 reviewer pane。

### ⑤ coder 仲裁 reviews
**先 `dc.py reset-status --workspace <ws> --role coder`**（清掉残留 `done impl`）→ 把两份 review 拼接发给 coder：
```
dc.py send --workspace <ws> --pane <coder> --text "## Review A\n<review_a 内容>\n\n## Review B\n<review_b 内容>"
```
coder 写 ack.md 逐项仲裁 + 修认同的 + commit → await `DONE commit=<hash>`。

### ⑥ verify + complete
```
dc.py verify --workspace <ws>
```
pass → 人工验证项(如有)贴给用户确认 → `dc.py complete --workspace <ws>`。
fail → 发失败信息给 coder → reset-status → await → 重跑 verify。

**完成后告诉用户：代码在哪个分支、commit hash、验证结果。**

## 你的机械工具(全部你执行)
```
dc.py scaffold   --requirement <p> --goal <g> [--new|--in-place]
dc.py launch     --workspace <ws> --role <coder|reviewer_a|reviewer_b> [--mode split-right|split-down]
dc.py send       --workspace <ws> --pane <id> --text "<prompt>"
dc.py close      --workspace <ws> --role <role>
dc.py await      --workspace <ws> --role <role> --pane <id> [--timeout 600] [--idle-timeout 120]
dc.py sessions   --workspace <ws>
dc.py reset-status --workspace <ws> --role <role>
dc.py verify     --workspace <ws>
dc.py complete   --workspace <ws>
```

await 退出码：`0 DONE` / `2 BLOCKED` / `3 DEAD` / `4 TIMEOUT` / `5 COMPACT` / `6 IDLE`。
`6 IDLE`：先看 pane tail 判断是真停了还是在跑长命令；真停了 send 重发提示再 await。

## 门禁(complete gate)
1. verify.json.ok = true
2. review_a.md 或 review_b.md 存在非空（至少一路）
3. ack.md 每个 blocker 有 [fixed] 或 [rejected]+理由
4. coder.status 含 commit=<hash>，hash 在分支上存在

## 硬约束
- 默认在独立 worktree + 分支；`--in-place` 仅限非 main/master 的 feature 分支。**绝不在 main 上开发/commit**。
- 不自动 push/deploy/改 secrets。
- 工作区文件是 SSOT，你的记忆不可信。
- **门禁只能经 `dc.py complete` 通过**，不许手标完成。

## 验收 / 停止 / 风险
- **验收**：verify.sh 真跑过 + review 存在 + blocker 全裁决 + commit 在分支上 = 门禁四条。
- **停止条件**：`dc.py await` 返回 `BLOCKED/DEAD/TIMEOUT/IDLE` 立即停并报告用户，不空转。
- **风险**：需求超出单 coder context window 时应回退到 `/dev-long-run`。

## 回退
删 worktree + 删分支 + 删 `.long-loop/<ws>` 即丢弃，main 无残留。

---
name: cross-review
description: 基于 tmux 的双 Agent 交叉 PR 审查。在当前 tmux window 中 split pane 启动交互式 droid，文件系统传递任务和结果。
metadata: {"cross-review-bot":{"emoji":"🔀","os":["darwin","linux"],"requires":{"bins":["tmux","droid","gh","python3"]}}}
---

# Cross Review - 双 Agent 交叉审查

在当前 tmux window 中 split 出 pane 运行审查 Agent。
Orchestrator 就是当前 droid，Claude 和 GPT 出现在旁边的 pane 中，用户直接可见。

## 1. 启动

Orchestrator（当前 droid）初始化 workspace，然后 spawn agent：

```bash
SKILL_DIR="$HOME/.factory/skills/cross-review"

# 初始化 workspace
"$SKILL_DIR/scripts/cr-init.sh" <repo> <pr_number> <base> <branch> <pr_node_id>
export CR_WORKSPACE="/tmp/cr-<safe_repo>-<pr_number>"
```

然后在阶段 1 中通过 `cr-spawn.sh` 启动 Claude 和 GPT。

---

## 2. 角色

| 角色             | 位置              | 职责                           |
| ---------------- | ----------------- | ------------------------------ |
| **Orchestrator** | 当前 pane（你）   | 编排流程、判断共识、决定下一步 |
| **Claude**       | split pane        | PR 审查、交叉确认、执行修复    |
| **GPT**          | split pane        | PR 审查、交叉确认、验证修复    |

模型可通过环境变量覆盖：`CR_MODEL_CLAUDE`, `CR_MODEL_GPT`

---

## 3. 流程总览

```
开始 → 阶段1(并行审查) → 阶段2(判断共识)
                              ├─ both_ok ──────→ 阶段5(汇总)
                              ├─ same_issues ──→ 阶段4(修复) → 阶段5
                              └─ divergent ────→ 阶段3(交叉确认)
                                                   ├─ 无需修复 → 阶段5
                                                   └─ 需修复 ──→ 阶段4 → 阶段5
```

### 阶段执行

**每个阶段执行前，必须先读取对应 stages/ 文件获取详细指令！**

| 阶段 | Orchestrator 读取                        | Agent 读取                |
| ---- | ---------------------------------------- | ------------------------- |
| 1    | `stages/1-review-orchestrator.md`        | `stages/1-review-agent.md` |
| 2    | `stages/2-judge-orchestrator.md`         | (不参与)                  |
| 3    | `stages/3-crosscheck-orchestrator.md`    | `stages/3-crosscheck-agent.md` |
| 4    | `stages/4-fix-orchestrator.md`           | `stages/4-fix-agent.md` / `stages/4-verify-agent.md` |
| 5    | `stages/5-summary-orchestrator.md`       | (不参与)                  |

---

## 4. 通信架构

### tmux 布局

```
当前 tmux window (main-vertical layout):
┌──────────────┬──────────────┐
│              │    claude    │
│ orchestrator ├──────────────┤
│   (你)       │     gpt      │
└──────────────┴──────────────┘
```

每个 agent 的 pane ID 存储在 `$CR_WORKSPACE/state/pane-{agent}`，
Orchestrator 通过读取该文件寻址：

```bash
PANE=$(cat "$CR_WORKSPACE/state/pane-claude")
tmux send-keys -t "$PANE" -l "..."
tmux send-keys -t "$PANE" Enter
```

### 文件系统 workspace

```
$CR_WORKSPACE/
├── state/
│   ├── stage                     # 当前阶段 (1-5/done)
│   ├── s2-result                 # both_ok / same_issues / divergent
│   ├── s4-branch                 # 修复分支名
│   ├── s4-round                  # 当前修复轮次
│   ├── pane-claude               # claude pane ID
│   ├── pane-gpt                  # gpt pane ID
│   ├── pr-node-id                # PR GraphQL node ID
│   ├── repo                      # owner/repo
│   ├── pr-number                 # PR 编号
│   ├── branch                    # PR 分支
│   └── base                      # 目标分支
├── tasks/
│   └── {agent}-{stage}.md        # Orchestrator 写入的任务文件
├── results/
│   ├── {agent}-r1.md             # 审查结果
│   ├── {agent}-crosscheck.md     # 交叉确认结果
│   ├── {agent}-fix.md            # 修复结果
│   ├── {agent}-verify.md         # 验证结果
│   └── {agent}-{stage}.done      # 完成标记 (sentinel)
└── comments/
    └── cr-summary.id             # 最终总结评论 node ID
```

### 通信流程

**发送任务**：Orchestrator 写任务文件 → `tmux send-keys` 告诉 Agent 读取并执行

```bash
# 1. 写任务文件
cat > "$CR_WORKSPACE/tasks/claude-review.md" << 'EOF'
...
EOF

# 2. 发送给 Agent（-l 和 Enter 必须分开两次调用）
PANE=$(cat "$CR_WORKSPACE/state/pane-claude")
tmux send-keys -t "$PANE" -l "Read and execute $CR_WORKSPACE/tasks/claude-review.md"
tmux send-keys -t "$PANE" Enter
```

**等待完成**：轮询 sentinel 文件

```bash
$HOME/.factory/skills/cross-review/scripts/cr-wait.sh claude r1 600
```

---

## 5. Agent 启动

Orchestrator 在当前 tmux window 中 split 出 pane：

```bash
$HOME/.factory/skills/cross-review/scripts/cr-spawn.sh claude "$MODEL_CLAUDE"
$HOME/.factory/skills/cross-review/scripts/cr-spawn.sh gpt "$MODEL_GPT"
```

Agent pane 自动出现在 orchestrator 旁边。

---

## 6. Orchestrator 行为规范

**禁止：**

- 执行 `cr-spawn.sh orchestrator`（你就是 orchestrator）
- 直接读取 PR diff 或代码（阶段 5 除外）
- 自己审查代码
- 在阶段 1-4 发布 PR 评论（仅阶段 5 发最终结论）

**必须：**

- 通过 `cr-spawn.sh` 启动 Claude/GPT Agent
- 通过文件系统交换任务/结果
- 等待 sentinel 文件确认 Agent 完成
- 在阶段 5 完成后调用 `cr-cleanup.sh` 清理

---

## 7. 脚本清单

| 脚本 | 用途 | 示例 |
|------|------|------|
| `cr-init.sh` | 初始化 workspace | `cr-init.sh owner/repo 123 main feat/x PR_xxx` |
| `cr-spawn.sh` | split pane 启动 droid | `cr-spawn.sh claude custom:claude-opus-4-6` |
| `cr-wait.sh` | 等待 sentinel 文件 | `cr-wait.sh claude r1 600` |
| `cr-status.sh` | 查看状态 | `cr-status.sh` |
| `cr-comment.sh` | GitHub 评论（仅阶段 5） | `cr-comment.sh post "body"` |
| `cr-cleanup.sh` | kill agent pane + 删 workspace | `cr-cleanup.sh` |

---

## 8. 状态管理

```bash
echo "2" > "$CR_WORKSPACE/state/stage"
STAGE=$(cat "$CR_WORKSPACE/state/stage")
```

---

## 9. Cleanup

Orchestrator 在阶段 5 完成后调用 `cr-cleanup.sh`，仅 kill agent pane 并删除 workspace，不影响当前 tmux session。

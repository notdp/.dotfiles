---
name: cross-review
description: 基于 tmux 的双 Agent 交叉 PR 审查。在 tmux session 中启动交互式 droid，通过 send-keys/capture-pane 通信，文件系统传递任务和结果。
metadata: {"cross-review-bot":{"emoji":"🔀","os":["darwin","linux"],"requires":{"bins":["tmux","droid","gh","python3"]}}}
---

# Cross Review - 双 Agent 交叉审查

基于 tmux 的多 Agent PR 审查系统。每个 Agent 是一个运行在 tmux session 中的交互式 `droid`，
Orchestrator 通过 tmux send-keys 发送任务、通过文件系统交换结果。

## 1. 启动

调用方初始化 workspace，然后依次 spawn orchestrator、claude、gpt 三个 droid：

```bash
# 初始化
SKILL_DIR="$HOME/.factory/skills/cross-review"
"$SKILL_DIR/scripts/cr-init.sh" <repo> <pr_number> <base> <branch> <pr_node_id>

export CR_WORKSPACE="/tmp/cr-<safe_repo>-<pr_number>"
export CR_SOCKET="$(cat "$CR_WORKSPACE/socket.path")"

# 启动 orchestrator（创建 session，pane 0）
"$SKILL_DIR/scripts/cr-spawn.sh" orchestrator <orchestrator_model>

# 向 orchestrator 发送初始 prompt（它会 spawn claude 和 gpt）
PANE=$(cat "$CR_WORKSPACE/state/pane-orchestrator")
tmux -S "$CR_SOCKET" send-keys -t "$PANE" -l "Load skill: cross-review. ..."
tmux -S "$CR_SOCKET" send-keys -t "$PANE" Enter

# 用户观察
tmux -S "$CR_SOCKET" attach -t cr
```

---

## 2. 角色

| 角色             | 默认模型          | 职责                           |
| ---------------- | ----------------- | ------------------------------ |
| **Orchestrator** | 执行 skill 的 droid | 编排流程、判断共识、决定下一步 |
| **Claude**        | custom:claude-opus-4-6 | PR 审查、交叉确认、执行修复    |
| **GPT**         | custom:gpt-5.3-codex   | PR 审查、交叉确认、验证修复    |

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

### tmux 拓扑

```
tmux socket: $CR_SOCKET
└── session: cr
    └── window 0 (main-vertical layout)
        ├── pane 0: orchestrator (编排 droid)
        ├── pane 1: claude       (审查 droid)
        └── pane 2: gpt          (审查 droid)

┌──────────────┬──────────────┐
│              │    claude    │
│ orchestrator ├──────────────┤
│              │     gpt      │
└──────────────┴──────────────┘

用户观察: tmux -S "$CR_SOCKET" attach -t cr
```

每个 agent 的 pane target 存储在 `$CR_WORKSPACE/state/pane-{agent}`，
Orchestrator 通过读取该文件寻址：

```bash
PANE=$(cat "$CR_WORKSPACE/state/pane-claude")
tmux -S "$CR_SOCKET" send-keys -t "$PANE" -l "..."
tmux -S "$CR_SOCKET" send-keys -t "$PANE" Enter
```

### 文件系统 workspace

```
$CR_WORKSPACE/
├── socket.path                   # tmux socket 路径
├── state/
│   ├── stage                     # 当前阶段 (1-5/done)
│   ├── s2-result                 # both_ok / same_issues / divergent
│   ├── s4-branch                 # 修复分支名
│   ├── s4-round                  # 当前修复轮次
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
... 任务内容 ...
当完成后，执行: touch $CR_WORKSPACE/results/claude-r1.done
EOF

# 2. 读取 pane target，发送给 Agent（-l 和 Enter 必须分开两次调用）
PANE=$(cat "$CR_WORKSPACE/state/pane-claude")
tmux -S "$CR_SOCKET" send-keys -t "$PANE" -l "Read and execute $CR_WORKSPACE/tasks/claude-review.md"
tmux -S "$CR_SOCKET" send-keys -t "$PANE" Enter
```

**等待完成**：轮询 sentinel 文件

```bash
$HOME/.factory/skills/cross-review/scripts/cr-wait.sh claude r1 600
```

**读取结果**：直接读文件

```bash
cat "$CR_WORKSPACE/results/claude-r1.md"
```

---

## 5. Agent 启动

Orchestrator 使用 `cr-spawn.sh` 在同一 session 中添加 pane 启动 Claude 和 GPT：

```bash
$HOME/.factory/skills/cross-review/scripts/cr-spawn.sh claude "$MODEL_CLAUDE"
$HOME/.factory/skills/cross-review/scripts/cr-spawn.sh gpt "$MODEL_GPT"
```

三个 droid 在同一 session 的三个 pane 中运行，用户可直接观察：

```bash
tmux -S "$CR_SOCKET" attach -t cr
```

---

## 6. Orchestrator 行为规范

**角色：监督者 + 仲裁者**

- 启动 Claude/GPT，分配任务
- 读取 Agent 结果，判断共识
- 在僵局时介入仲裁

**禁止：**

- 执行 `cr-init.sh`（调用方已完成）
- 执行 `cr-spawn.sh orchestrator`（你就是 orchestrator）
- 直接读取 PR diff 或代码（阶段 5 除外）
- 自己审查代码
- 在阶段 1-4 发布 PR 评论（中间过程留在 workspace，仅阶段 5 发最终结论）

**必须：**

- 通过 `cr-spawn.sh` 启动 Claude/GPT Agent（它们会出现在你旁边的 pane 中）
- 通过文件系统交换任务/结果
- 等待 sentinel 文件确认 Agent 完成
- 在阶段 5 完成后调用 `cr-cleanup.sh` 清理

---

## 7. 脚本清单

| 脚本 | 用途 | 调用方 | 示例 |
|------|------|--------|------|
| `cr-spawn.sh` | 启动交互式 droid | Orchestrator | `cr-spawn.sh claude custom:claude-opus-4-6` |
| `cr-wait.sh` | 等待 sentinel 文件 | Orchestrator | `cr-wait.sh claude r1 600` |
| `cr-status.sh` | 查看所有 agent 状态 | Orchestrator | `cr-status.sh` |
| `cr-comment.sh` | GitHub 评论操作（仅阶段 5） | Orchestrator | `cr-comment.sh post "body"` |
| `cr-init.sh` | 初始化 workspace + socket | Orchestrator | `cr-init.sh owner/repo 123 main feat/x PR_xxx` |
| `cr-cleanup.sh` | 清理 sessions + 文件 | Orchestrator | `cr-cleanup.sh` |

---

## 8. 状态管理

文件系统替代 SQLite，读写直接用 shell：

```bash
# 写入
echo "2" > "$CR_WORKSPACE/state/stage"
echo "divergent" > "$CR_WORKSPACE/state/s2-result"

# 读取
STAGE=$(cat "$CR_WORKSPACE/state/stage")
```

---

## 9. Cleanup

Orchestrator 在阶段 5 完成后调用 `cr-cleanup.sh` 清理 tmux sessions 和 workspace。

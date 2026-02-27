---
name: cross-review
description: 基于 Mission 的双 Agent 交叉 PR 审查。通过 mission CLI 启动 Agent，文件系统传递任务和结果。
metadata: {"cross-review-bot":{"emoji":"🔀","os":["darwin","linux"],"requires":{"bins":["tmux","droid","gh","python3","mission"]}}}
---

# Cross Review - 双 Agent 交叉审查

通过 `mission` CLI 在当前 tmux window 中启动审查 Agent。
Orchestrator 就是当前 droid，Claude 和 GPT 出现在旁边的 pane 中。

## 1. 启动

Orchestrator（当前 droid）通过 `mission create` 初始化 workspace 和 team，然后 spawn agent：

```bash
export CR_WORKSPACE="/tmp/cr-<safe_repo>-<pr_number>"
export CR_TEAM="cr-<safe_repo>-<pr_number>"

mission create "$CR_TEAM" -d "Cross review PR #<pr_number>" \
  --workspace "$CR_WORKSPACE" \
  --reset-workspace \
  --state "repo=<repo>" \
  --state "pr-number=<pr_number>" \
  --state "base=<base>" \
  --state "branch=<branch>" \
  --state "pr-node-id=<pr_node_id>" \
  --state "stage=1"
```

然后在阶段 1 中通过 `mission spawn` 启动 Claude 和 GPT。

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

### 布局

```
当前 tmux window (由 mission 管理):
┌──────────────┬──────────────┐
│              │    claude    │
│ orchestrator ├──────────────┤
│   (你)       │     gpt      │
└──────────────┴──────────────┘
```

### 发送任务给 Agent

```bash
# 1. 写任务文件
cat > "$CR_WORKSPACE/tasks/claude-review.md" << 'EOF'
...
EOF

# 2. 通过 mission type 发送给 Agent
mission type claude "Read and execute $CR_WORKSPACE/tasks/claude-review.md" -t "$CR_TEAM"
```

### 等待完成

轮询 sentinel 文件：

```bash
mission wait claude r1 -t "$CR_TEAM" --workspace "$CR_WORKSPACE" --timeout 600
```

### 文件系统 workspace

```
$CR_WORKSPACE/
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

---

## 5. Agent 启动

Orchestrator 通过 mission spawn 启动 Agent：

```bash
MODEL_CLAUDE="${CR_MODEL_CLAUDE:-custom:claude-opus-4-6}"
MODEL_GPT="${CR_MODEL_GPT:-custom:gpt-5.3-codex}"

mission spawn claude -t "$CR_TEAM" -m "$MODEL_CLAUDE" --skill cross-review \
  -e "CR_WORKSPACE=$CR_WORKSPACE"
mission spawn gpt -t "$CR_TEAM" -m "$MODEL_GPT" --skill cross-review \
  -e "CR_WORKSPACE=$CR_WORKSPACE"
```

---

## 6. Orchestrator 行为规范

**禁止：**

- 直接操作 tmux（通过 mission 命令交互）
- 直接读取 PR diff 或代码（阶段 5 除外）
- 自己审查代码
- 在阶段 1-4 发布 PR 评论（仅阶段 5 发最终结论）

**必须：**

- 通过 `mission spawn` 启动 Claude/GPT Agent
- 通过 `mission type` 发送任务指令
- 通过文件系统交换任务/结果
- 等待 sentinel 文件确认 Agent 完成
- 在阶段 5 完成后调用 `mission delete` 清理

---

## 7. 工具清单

| 命令 | 用途 | 示例 |
|------|------|------|
| `mission create` | 创建 team + 初始化 workspace | `mission create "$CR_TEAM" -d "..." --workspace "$CR_WORKSPACE" --state "repo=..." ...` |
| `mission spawn` | 启动 Agent | `mission spawn claude -t "$CR_TEAM" -m model --skill cross-review -e "CR_WORKSPACE=..."` |
| `mission type` | 发送任务给 Agent | `mission type claude "Read and execute ..." -t "$CR_TEAM"` |
| `mission status` | 查看 Agent 状态 | `mission status -t "$CR_TEAM"` |
| `mission capture` | 查看 Agent 输出 | `mission capture claude -t "$CR_TEAM"` |
| `mission wait` | 等待 sentinel 文件 | `mission wait claude r1 -t "$CR_TEAM" --workspace "$CR_WORKSPACE" --timeout 600` |
| `mission comment` | GitHub 评论（仅阶段 5） | `mission comment post "body" --workspace "$CR_WORKSPACE"` |
| `mission delete` | 删 team + workspace | `mission delete "$CR_TEAM"` |

---

## 8. 状态管理

```bash
echo "2" > "$CR_WORKSPACE/state/stage"
STAGE=$(cat "$CR_WORKSPACE/state/stage")
```

---

## 9. Cleanup

Orchestrator 在阶段 5 完成后调用 `mission delete "$CR_TEAM"`，删除 mission team 并清理 workspace。

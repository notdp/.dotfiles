# 阶段 3: 交叉确认

**执行者**: Orchestrator

## 流程图

```mermaid
flowchart TD
    Start([开始]) --> Mode{判断场景}
    
    Mode -->|场景1: Opus有发现, Codex=OK| S1[Codex 评估 Opus]
    Mode -->|场景2: Codex有发现, Opus=OK| S2[Opus 评估 Codex]
    Mode -->|场景3: 双方都有不同发现| S3[双向汇总确认]
    
    S1 --> S1R{Codex 回复}
    S1R -->|全部 ✅| Fix([阶段 4: 修复])
    S1R -->|有 ❌| Dialog1[转入对话]
    
    S2 --> S2R{Opus 回复}
    S2R -->|全部 ✅| Fix
    S2R -->|有 ❌| Dialog2[转入对话]
    
    S3 --> Collect[收集双方回复]
    Collect --> Judge{判断共识}
    Judge -->|全部达成共识| Consensus[汇总结果]
    Judge -->|有分歧| NextRound{轮数 < 5?}
    NextRound -->|是| S3
    NextRound -->|否| Timeout[标记未达成共识]
    
    Dialog1 --> S3
    Dialog2 --> S3
    
    Consensus -->|有需修复项| Fix
    Consensus -->|全部不需修复| Summary([阶段 5: 汇总])
    Timeout --> Summary
```

## 3.1 初始化

```bash
$S/duo-set.sh $PR_NUMBER stage 3
$S/duo-set.sh $PR_NUMBER s3:round 1
```

## 3.2 判断场景

Orchestrator 根据阶段 1 收到的结果判断：

| 场景 | Opus   | Codex          | 处理方式                 |
| ---- | ------ | -------------- | ------------------------ |
| 1    | 有发现 | OK             | 单向：Codex 评估 Opus    |
| 2    | OK     | 有发现         | 单向：Opus 评估 Codex    |
| 3    | 有发现 | 有发现（不同） | 双向：汇总后双方 confirm |

---

## 场景 1: Codex 评估 Opus（单向）

Opus 有发现，Codex 说 OK。

### 发送给 Codex

```bash
$S/fifo-send.sh codex $PR_NUMBER "
## 你是 Codex，任务：评估 Opus 的发现

Opus 在 PR #$PR_NUMBER 中发现了以下问题：

<opus-findings>
$OPUS_FINDINGS
</opus-findings>

请逐条评估：
- ✅ 认可 - 确实是问题，需要修复
- ❌ 不认可 - 误报，附上理由

## 输出格式（必须严格遵循）

先获取时间戳：TIMESTAMP=\$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M')

评论内容必须是：
<!-- duo-cross-codex-r1 -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg' width='18' /> Codex 交叉确认 | Round 1
> 🕐 \$TIMESTAMP

### 评估结果
| 问题 | 判断 | 理由 |
| ---- | ---- | ---- |
| O1   | ✅/❌ | ...  |
| O2   | ✅/❌ | ...  |

### 结论
(总结你的判断)

## 完成后
1. \$S/post-comment.sh \$PR_NUMBER \$REPO \"\$COMMENT_CONTENT\"
2. \$S/fifo-send.sh orchestrator $PR_NUMBER '<CODEX>评论内容</CODEX>'
"
```

### Orchestrator 处理回复

收到 Codex 回复后：
- 全部 ✅ → 共识达成，进入阶段 4
- 有 ❌ → 把 Codex 的理由转发给 Opus，转入场景 3（双向确认）

---

## 场景 2: Opus 评估 Codex（单向）

Codex 有发现，Opus 说 OK。

### 发送给 Opus

```bash
$S/fifo-send.sh opus $PR_NUMBER "
## 你是 Opus，任务：评估 Codex 的发现

Codex 在 PR #$PR_NUMBER 中发现了以下问题：

<codex-findings>
$CODEX_FINDINGS
</codex-findings>

请逐条评估：
- ✅ 认可 - 确实是问题，需要修复
- ❌ 不认可 - 误报，附上理由

## 输出格式（必须严格遵循）

先获取时间戳：TIMESTAMP=\$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M')

评论内容必须是：
<!-- duo-cross-opus-r1 -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg' width='18' /> Opus 交叉确认 | Round 1
> 🕐 \$TIMESTAMP

### 评估结果
| 问题 | 判断 | 理由 |
| ---- | ---- | ---- |
| C1   | ✅/❌ | ...  |
| C2   | ✅/❌ | ...  |

### 结论
(总结你的判断)

## 完成后
1. \$S/post-comment.sh \$PR_NUMBER \$REPO \"\$COMMENT_CONTENT\"
2. \$S/fifo-send.sh orchestrator $PR_NUMBER '<OPUS>评论内容</OPUS>'
"
```

### Orchestrator 处理回复

收到 Opus 回复后：
- 全部 ✅ → 共识达成，进入阶段 4
- 有 ❌ → 转入场景 3（双向确认）

---

## 场景 3: 双向汇总确认

双方都有发现但不同，或单向评估后仍有分歧。

### 发送给 Opus

```bash
$S/fifo-send.sh opus $PR_NUMBER "
## 你是 Opus

## 待确认问题列表（Round $ROUND）

### Opus 发现
O1. [P1] $OPUS_FINDING_1
O2. [P2] $OPUS_FINDING_2

### Codex 发现
C1. [P1] $CODEX_FINDING_1
C2. [P3] $CODEX_FINDING_2

请逐条评估所有问题（包括你自己的和 Codex 的）：
- ✅ 认可（确实是问题，需修复）
- ❌ 不认可（误报，附理由）

## 输出格式（必须严格遵循）

先获取时间戳：TIMESTAMP=\$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M')

评论内容必须是：
<!-- duo-cross-opus-r$ROUND -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg' width='18' /> Opus 交叉确认 | Round $ROUND
> 🕐 \$TIMESTAMP

### 评估结果
| 问题 | 判断 | 理由 |
| ---- | ---- | ---- |
| O1   | ✅/❌ | ...  |
| O2   | ✅/❌ | ...  |
| C1   | ✅/❌ | ...  |
| C2   | ✅/❌ | ...  |

### 结论
(总结)

## 完成后
1. \$S/post-comment.sh \$PR_NUMBER \$REPO \"\$COMMENT_CONTENT\"
2. \$S/fifo-send.sh orchestrator $PR_NUMBER '<OPUS>评论内容</OPUS>'
"
```

### 发送给 Codex

```bash
$S/fifo-send.sh codex $PR_NUMBER "
## 你是 Codex

## 待确认问题列表（Round $ROUND）

### Opus 发现
O1. [P1] $OPUS_FINDING_1
O2. [P2] $OPUS_FINDING_2

### Codex 发现
C1. [P1] $CODEX_FINDING_1
C2. [P3] $CODEX_FINDING_2

请逐条评估所有问题（包括你自己的和 Opus 的）：
- ✅ 认可（确实是问题，需修复）
- ❌ 不认可（误报，附理由）

## 输出格式（必须严格遵循）

先获取时间戳：TIMESTAMP=\$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M')

评论内容必须是：
<!-- duo-cross-codex-r$ROUND -->
## <img src='https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg' width='18' /> Codex 交叉确认 | Round $ROUND
> 🕐 \$TIMESTAMP

### 评估结果
| 问题 | 判断 | 理由 |
| ---- | ---- | ---- |
| O1   | ✅/❌ | ...  |
| O2   | ✅/❌ | ...  |
| C1   | ✅/❌ | ...  |
| C2   | ✅/❌ | ...  |

### 结论
(总结)

## 完成后
1. \$S/post-comment.sh \$PR_NUMBER \$REPO \"\$COMMENT_CONTENT\"
2. \$S/fifo-send.sh orchestrator $PR_NUMBER '<CODEX>评论内容</CODEX>'
"
```

### 收集双方回复

等待双方都回复后，Orchestrator 判断每个问题的共识：

```plain
收到：
Opus:   O1:✅  O2:✅  C1:❌(理由A)  C2:✅
Codex:  O1:✅  O2:❌(理由B)  C1:✅  C2:✅

判断：
O1: 双方 ✅ → 达成共识，需修复
O2: Opus✅ Codex❌ → 分歧
C1: Opus❌ Codex✅ → 分歧
C2: 双方 ✅ → 达成共识，需修复
```

### Round 2+: 针对分歧项继续确认

如果仍有分歧，Orchestrator 汇总分歧项和双方理由，分别发送给双方（格式同上，更新问题列表为分歧项）。

### 循环终止条件

1. **全部达成共识** - 所有问题双方都 ✅ 或都 ❌
   - 有需修复项 → 阶段 4
   - 全部不需修复 → 阶段 5

2. **达到轮数上限（5 轮）** - 仍有分歧 → 阶段 5（标记需人工审查）

---

**重要**：交叉确认评论必须用 `post-comment.sh` 发新评论，形成对话流。不要用 `edit-comment.sh` 更新原评论。

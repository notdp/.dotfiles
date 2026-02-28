# 阶段 5: 汇总 - Orchestrator

## 禁止操作

- 不要直接操作 tmux

生成最终汇总，发布唯一一条 PR 评论，然后清理。

## 执行

```bash
echo "5" > "$CR_WORKSPACE/state/stage"
```

## 步骤

### 1. 收集所有结果

```bash
CLAUDE_REVIEW=$(cat "$CR_WORKSPACE/results/claude-r1.md" 2>/dev/null || echo "N/A")
GPT_REVIEW=$(cat "$CR_WORKSPACE/results/gpt-r1.md" 2>/dev/null || echo "N/A")
S2_RESULT=$(cat "$CR_WORKSPACE/state/s2-result" 2>/dev/null || echo "N/A")
CROSSCHECK=$(cat "$CR_WORKSPACE/results/crosscheck-summary.md" 2>/dev/null || echo "N/A")
FIX_RESULT=$(cat "$CR_WORKSPACE/results/claude-fix.md" 2>/dev/null || echo "N/A")
VERIFY_RESULT=$(cat "$CR_WORKSPACE/results/gpt-verify.md" 2>/dev/null || echo "N/A")
```

### 2. 生成汇总 + inline comments

**注意**：仅在此阶段允许 Orchestrator 读取代码（用于 inline comments）。

```bash
BASE=$(cat "$CR_WORKSPACE/state/base")
BRANCH=$(cat "$CR_WORKSPACE/state/branch")
```

**⚠️ 重要：仅读取与已确认 findings 相关的文件 diff，不要读取全量 diff！**

```bash
git diff "origin/$BASE...origin/$BRANCH" -- path/to/relevant-file.py
```

如果 findings 涉及多个文件，逐个读取而不是一次性全量 diff。**禁止不带路径的 `git diff`** — 大 PR 的全量 diff 会导致超时。

#### 2.1 汇总评论模板

```markdown
<!-- cr-summary -->
## {✅|⚠️} Cross Review Summary
> 🕐 {TIMESTAMP}

### 审查时间线

| 时间 (UTC) | 事件 |
|------------|------|
| MM-DD HH:MM | Round 1 启动 - Claude & GPT 并行审查 {branch} |
| MM-DD HH:MM | Claude 发现 [P0] ... / Claude 未发现问题 |
| MM-DD HH:MM | GPT 发现 [P0] ... / GPT 未发现问题 |
| MM-DD HH:MM | 交叉验认 - {双方问题均已确认 / 存在分歧} |
| MM-DD HH:MM | 共识: {结论} |
| MM-DD HH:MM | Claude 修复: {描述} |
| MM-DD HH:MM | GPT 验证通过 / 验证失败 |
| MM-DD HH:MM | ✅ 审查完成 |

{如有 findings:}
### 审查发现

| # | 问题 | 状态 |
|---|------|------|
| 1 | 🔴 [P0] ... | ✅ 已修复 / ⏭️ 跳过 |

{如有修复:}
**修复分支**: [`{branch}`](https://github.com/{REPO}/compare/{BRANCH}...{fix_branch}) ([`{short_hash}`](https://github.com/{REPO}/commit/{full_hash}))

### 审查结论

| Agent | 结论 |
|-------|------|
| <img src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg" width="16" /> Claude | {结论} |
| <img src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg" width="16" /> GPT | {结论} |

**结论**: {一句话总结}

<details>
<summary>Session Info</summary>

从 `mission status -t "$CR_TEAM"` 获取 agent session ID：

- Orchestrator: `$DROID_SESSION_ID`（当前 droid 自身的 session）
- Claude: `{sessionId from status}` (model: `$CR_MODEL_CLAUDE`)
- GPT: `{sessionId from status}` (model: `$CR_MODEL_GPT`)
- Team: `$CR_TEAM`
- Workspace: `$CR_WORKSPACE`
</details>
```

#### 2.2 生成 inline comments（仅已修复的 findings）

**仅针对已修复的 findings** 生成 inline comments，在代码位置标注：
- 问题是什么
- 影响是什么
- 如何修复的

**跳过的 findings 不生成 inline comment**（已在 summary 表格说明跳过原因）。

**⚠️ 关键：inline comment 必须指向原 PR diff 中的问题行**

```bash
git diff origin/$BASE...origin/$BRANCH -- path/to/relevant-file.yml
```

行号必须是**原 PR diff 中有问题的代码行**，而不是修复后的行号。

**JSON 格式：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `path` | ✅ | 文件路径（相对仓库根目录） |
| `line` | ✅ | 结束行号（原 PR diff 中的新文件行号） |
| `start_line` | ❌ | 起始行号（多行时需要，单行时省略） |
| `body` | ✅ | 评论内容（见下方模板） |

**注意**：行号必须在原 PR diff 的变更范围内（新增或修改的行），否则 API 报 422。

**Body 模板：**

```markdown
**<sub><sub>![{P0|P1|P2|P3} Badge]({badge_url})</sub></sub>  {标题}**

{问题描述 1-2 段}

Useful? React with 👍 / 👎.
```

**Badge URLs：**

| 级别 | URL |
|------|-----|
| P0 | `https://img.shields.io/badge/P0-red?style=flat` |
| P1 | `https://img.shields.io/badge/P1-orange?style=flat` |
| P2 | `https://img.shields.io/badge/P2-yellow?style=flat` |
| P3 | `https://img.shields.io/badge/P3-green?style=flat` |

### 3. 发布 PR 评论

这是整个 pipeline 中**唯一一次**发布 PR 评论。

```bash
REPO=$(cat "$CR_WORKSPACE/state/repo")
PR_NUMBER=$(cat "$CR_WORKSPACE/state/pr-number")
```

#### 有已修复的 findings → 一条 PR review（summary + inline comments）

```bash
mission comment review-post "$SUMMARY_BODY" "$INLINE_COMMENTS_JSON" --workspace "$CR_WORKSPACE"
```

#### 无 findings 或全部 Skip → 一条普通评论

```bash
SUMMARY_NODE_ID=$(mission comment post "$SUMMARY_BODY" --workspace "$CR_WORKSPACE")
echo "$SUMMARY_NODE_ID" > "$CR_WORKSPACE/comments/cr-summary.id"
```

### 4. 清理并完成

```bash
echo "done" > "$CR_WORKSPACE/state/stage"

mission delete "$CR_TEAM"
```

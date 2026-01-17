# 阶段 5: 汇总

**执行者**: Orchestrator

## 执行

```bash
$S/duo-set.sh $PR_NUMBER stage 5
TIMESTAMP=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M')
RUNNER=$($S/duo-get.sh $PR_NUMBER runner)
ORCHESTRATOR_SESSION=$($S/duo-get.sh $PR_NUMBER orchestrator:session)
OPUS_SESSION=$($S/duo-get.sh $PR_NUMBER opus:session)
CODEX_SESSION=$($S/duo-get.sh $PR_NUMBER codex:session)
```

根据前面阶段结果，选择对应模板生成汇总评论。

## 评论模板

**通用结构**:

```markdown
<!-- duoduo-summary -->
## {✅|⚠️} Duo Review Summary
> 🕐 $TIMESTAMP

| Agent                                                                                                   | 结论   |
| ------------------------------------------------------------------------------------------------------- | ------ |
| <img src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/openai.svg" width="16" /> Codex      | {结论} |
| <img src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/claude-color.svg" width="16" /> Opus | {结论} |

{可选: 修复分支链接}

**结论**: {一句话总结}

<details>
<summary>Session Info</summary>

- Runner: `$RUNNER`
- Orchestrator: `$ORCHESTRATOR_SESSION`
- Opus: `$OPUS_SESSION`
- Codex: `$CODEX_SESSION`
</details>
```

**结论填写规则**:

| 情况                | 图标 | Agent 结论        | 总结                        |
| ------------------- | ---- | ----------------- | --------------------------- |
| both_ok             | ✅    | 未发现问题        | PR 可以合并                 |
| 修复验证通过        | ✅    | 已修复 / 验证通过 | 问题已修复，附修复分支链接  |
| 达成共识无需修复    | ✅    | 交叉确认结论      | 经确认无需修复，PR 可以合并 |
| 未达成共识/修复失败 | ⚠️    | 各自结论          | 需人工审查                  |

## 发布

```bash
$S/post-comment.sh $PR_NUMBER $REPO "$SUMMARY_CONTENT"
$S/duo-set.sh $PR_NUMBER stage done
```

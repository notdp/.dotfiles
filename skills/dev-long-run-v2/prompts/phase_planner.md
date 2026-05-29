# Role: phase planner

为单个 phase 做调研增强。不写业务代码。

## 必读输入
- `<workspace>/SPEC_OVERVIEW.md`、`phases/<id>/spec.md`、目标 worktree 代码

## 必写产出(增强当前 phase 目录)
- `phases/<id>/research.md`：相关代码事实、依赖、风险
- `phases/<id>/plan.md`：实现步骤拆解
- `phases/<id>/qa.md`：该 phase 的验收点

## 完成信号(机器可读)
- 三个文件写完后,写 **`phases/<id>/phase_planner.status` = `done`**(卡住写 `blocked <reason>`)。orchestrator 靠它判完成,别只在 pane 里说。

## 约束
- 评估是否需要 `/think-map` `/think-research`，不强制。
- 不写代码、不动其他 phase。
- 状态写 done 后即结束本轮，pane 可关。

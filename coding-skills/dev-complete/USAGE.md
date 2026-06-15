# dev-complete 用户指南

> 单 pass 完备开发。代码落在独立 worktree + `lr/<slug>` 分支，**main 永不被碰**，出事删 worktree+分支即可。

## 什么时候用

| 场景 | 推荐 |
|------|------|
| 单次 bug fix / 纯测试 | `/dev-tdd` |
| 小到中等需求，想要 spec→code→review→verify 完整链 | **`/dev-complete`** |
| 复杂多 phase 长任务 | `/dev-long-run` |

## 用法

直接用自然语言告诉 agent 你想做什么：

```
/dev-complete 给 API 加分页支持
```

agent 会：
1. 跟你讨论需求、写 spec 给你过目
2. 开 coder pane（kilo+gpt）写代码
3. 开两个 reviewer pane（kilo + CC）并发审查
4. coder 仲裁 review、修代码、commit
5. 跑 verify.sh 验证、过门禁
6. 报告完成

## 你需要做什么

- **用自然语言回答**：agent 问你 spec 是否 OK、选新建还是接着做、人工验证项是否通过。
- **不需要碰 CLI 或 tmux**：所有操作 agent 替你执行。

## 注意事项

- agent 开独立 coder pane 写代码，不是在对话里自己写。
- 代码 commit 到 `lr/` 分支，不在 main 上。
- 完成后不会自动 push，你自己决定。

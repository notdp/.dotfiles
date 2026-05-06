---
name: guard-check
description: 当任务完成、准备合并或需要交付前总检查时使用；交付前总入口，统一编排 review/secure/verify/ship 的裁决（与 guard-close 区别：本 skill 是检查链编排，不判停/继续）。
argument-hint: <diff 范围|留空=当前未提交变更>
---

# Guard Check

`guard-check` 不是新的底层审查器，而是交付前总入口。

## 目标

1. 统一判断当前变更该走哪些检查链路
2. 复用已有 `guard-review`、`guard-secure`、`guard-verify`、`guard-ship`
3. 当存在已批准 spec / plan / prompt artifact 时，补看实现是否偏离意图
4. 在一个入口里给出最终交付裁决

## 默认路由

具体规则见 `references/check-routing.md`。

- 默认先看 diff 范围
- 安全敏感改动追加 `guard-secure`
- 声称“已完成 / 可交付”时追加 `guard-verify`
- 需要 PR / 发布动作时切到 `guard-ship`
- 改动会影响仓库外可见状态（远程机器、部署产物、数据库、secrets、运行时配置、仓库外二进制、第三方面板）时追加 `guard-gitops`；发现存在"绕过 git"的副作用一律升 Critical
- diff 或 PR 描述引用 spec / plan / prompt artifact 时，在 review 摘要里增加 intent alignment：目标、边界、Non-goals、验证策略是否仍与 artifact 一致

## 边界

- 它不替代 `guard-review`
- 它不直接实现安全扫描或验证逻辑
- 它只负责编排和裁决汇总
- 它不要求所有任务都创建 artifact；只在 artifact 已存在时把它作为对齐基准

## Gotchas

- 不要把所有任务都升级成深审查；按 diff 风险决定
- 不要复制现有 skills 的细则，避免双重真相

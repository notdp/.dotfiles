---
name: agent-health
description: 当需要审计当前 agent 配置栈、skills wiring、hooks、MCP 或全局规则是否健康时使用；输出结构化问题清单和证据。
argument-hint: <仓库路径|留空=当前目录>
---

# Agent Health

对当前仓库的 agent 配置进行本地健康审计。

## 目标

1. 审计 `AGENTS.md`、skills、hooks、MCP 等关键资产是否存在
2. 输出结构化 summary / issues / evidence
3. 把“看起来不对劲”变成可追踪的问题清单

## 默认流程

1. 先解析本 skill 的安装目录，运行 `<skill_dir>/scripts/collect_data.sh <目标仓库路径>`
2. 先读 summary，再看 issues
3. 需要更细分析时，再让 inspector agents 深挖

不要直接运行目标仓库里的 `scripts/collect_data.sh`；该脚本是本 skill 自带资产，目标仓库只是被审计对象。

## 资产

- `scripts/collect_data.sh`
- `agents/inspector-context.md`
- `agents/inspector-control.md`

## 边界

- 第一版只做本地仓库结构审计
- 不做远端服务、在线 API 或运行时性能健康检查
- 不替代 `guard-verify`、`dev-debug`

## Gotchas

- 不要把“缺少文件”直接等同于 bug；先结合仓库约定看严重度
- 不要把配置审计和代码正确性审计混为一谈

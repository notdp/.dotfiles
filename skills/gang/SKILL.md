---
name: gang
description: GANG entry skill. 用户打 /gang 表示要把当前 pane 升级成 GANG orchestrator 并启动 gang 闭环。skill 内容 = 跑 `hive gang init`,把当前 pane 搬到新 window,布好 board + skeptic,并自动 dispatch /gang-orch 接管 duty。
---

# GANG — entry

你被 `/gang` 触发,用户要启动 GANG 闭环。**你做一件事**:在当前 pane 执行:

```bash
hive gang init
```

完事。执行后你会看到:

- 当前 pane 切到新的 gang window,orch 身份带过去
- 同 window 出现 skeptic(异族 CLI,claude↔codex;droid 默认 claude)和 board(vim 打开 BLACKBOARD.md)
- `/gang-orch` 自动接管 orch pane,本 skill 退场

用户想显式指定 gang 实例名可传 `--name <name>`;不传就由 CLI 自动分配。

## 前置

- **当前 pane 正在跑 agent CLI**(claude / codex / droid),不是光秃秃 shell
- workspace 不需要先 `hive init` —— `hive gang init` 可独立运行,未 init 时自动建 team / workspace

## 边界(本 skill 只做一件事)

本 skill 只负责跑 `hive gang init`。其余职责在 CLI 和下游 skill 里已经归位:

- **tmux 窗口 / 分栏布局** — `hive gang init` 自己做
- **skeptic / board spawn** — `hive gang init` 内部负责
- **workspace 路径 / agent name** — 从当前 pane 上下文自动推断,直接用
- **planning / 拆 feature** — 是 `/gang-orch` 接管之后的 duty,本 skill 不涉

## 报错兜底

- `hive: command not found` → 告诉用户 `pipx install git+https://github.com/notdp/hive.git`
- 报 "not an agent pane" → 当前 pane 不是 agent CLI,换到跑着 claude/codex/droid 的 pane 再 `/gang`

## 模型异质

`hive gang init` 默认会用 anti-orch 家族 CLI 起 skeptic(claude↔codex;droid 默认 claude)。若当前 CLI 是 droid 但跑的是 Anthropic 模型(opus / sonnet),显式 override:

```bash
hive gang init --peer-cli codex
```

## 多 gang 共存

多个 gang 可以同时存在,彼此寻址天然隔离。你不用关心 CLI 怎么分配 / 去重 gang 名 —— `hive gang init` 自己搞定。

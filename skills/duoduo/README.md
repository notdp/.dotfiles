# Duoduo - 双 Agent 交叉审查

双 AI Agent（Opus + Codex）交叉审查 PR，自动判断共识、决定是否需要修复。

## 使用方式

### 本地使用（通过 Droid）

在 PR 分支上启动 Droid，然后说：

```
load skill: duoduo
```

或直接说：

```
帮我 review 这个 PR
```

Droid 会自动检测当前 PR 并启动审查流程。

### GitHub Actions 自动触发

在仓库配置 workflow 后，每次 PR 创建或更新时自动触发审查。

详见 [../../.github/workflows/README.md](./../../.github/workflows/README.md)

## 流程概览

```
┌─────────────┐     ┌─────────────┐
│    Opus     │     │   Codex     │
│ (Claude 4.5)│     │  (GPT-5.2)  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 ▼
         ┌──────────────┐
         │ Orchestrator │
         └──────┬───────┘
                ▼
    1. 并行审查 PR
    2. 判断共识
    3. 交叉确认（如有分歧）
    4. 自动修复 + 验证
    5. 发布汇总评论
```

## 文件结构

```
duoduo/
├── README.md         # 本文件
├── SKILL.md          # Droid skill 定义
├── actions/          # GitHub Actions
│   ├── README.md     # Workflow 配置说明
│   └── duo-review.yml
├── scripts/          # 脚本
└── stages/           # 各阶段 prompt 模板
```

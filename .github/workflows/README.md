# Duo Review - GitHub Actions 配置

## 快速开始

在你的仓库创建 `.github/workflows/duo-review.yml`：

```yaml
name: Duo Review

on:
  pull_request:
    types: [opened, synchronize]

concurrency:
  group: duo-${{ github.event.pull_request.number }}
  cancel-in-progress: true

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  review:
    uses: notdp/.dotfiles/.github/workflows/duo-review.yml@main
    with:
      pr_number: ${{ github.event.pull_request.number }}
      pr_branch: ${{ github.head_ref }}
      base_branch: ${{ github.base_ref }}
      repo: ${{ github.repository }}
    secrets:
      # 选择以下任一方式
      # 方式 A: GitHub App（推荐）
      DUO_APP_ID: ${{ secrets.DUO_APP_ID }}
      DUO_APP_PRIVATE_KEY: ${{ secrets.DUO_APP_PRIVATE_KEY }}
      # 方式 B: GitHub Actions Bot
      # GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 认证方式

### 方式 A：使用 GitHub App（推荐）

评论以你的 GitHub App 身份发布。

**配置步骤**：

1. 创建 GitHub App，配置权限：
   - `Contents`: Read and write
   - `Pull requests`: Read and write
   - `Issues`: Read and write
2. 安装到目标仓库
3. 在仓库 Settings → Secrets and variables → Actions 添加：
   - `DUO_APP_ID`: App ID
   - `DUO_APP_PRIVATE_KEY`: Private Key

```yaml
secrets:
  DUO_APP_ID: ${{ secrets.DUO_APP_ID }}
  DUO_APP_PRIVATE_KEY: ${{ secrets.DUO_APP_PRIVATE_KEY }}
```

### 方式 B：使用 GitHub Actions Bot

评论以 `github-actions[bot]` 身份发布，无需额外配置。

```yaml
secrets:
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## @Mention 触发

在 PR 评论中 @mention bot 与审查交互，创建 `.github/workflows/duo-mention.yml`：

```yaml
name: Duo Mention

on:
  issue_comment:
    types: [created]

concurrency:
  group: duo-mention-${{ github.event.issue.number }}

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  get-runner:
    if: |
      github.event.issue.pull_request &&
      (contains(github.event.comment.body, '@your-bot-name') ||
       (startsWith(github.event.comment.body, '>') &&
        (contains(github.event.comment.body, 'Opus') ||
         contains(github.event.comment.body, 'Codex') ||
         contains(github.event.comment.body, 'Orchestrator'))))
    runs-on: [self-hosted, macos, arm64]
    outputs:
      runner: ${{ steps.get.outputs.runner }}
      pr_branch: ${{ steps.get.outputs.pr_branch }}
      base_branch: ${{ steps.get.outputs.base_branch }}
    steps:
      - name: Get runner and PR info
        id: get
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          PR_NUMBER=${{ github.event.issue.number }}
          REPO=${{ github.repository }}
          
          # 获取 PR 信息
          PR_INFO=$(gh pr view $PR_NUMBER --repo $REPO --json baseRefName,headRefName)
          echo "pr_branch=$(echo $PR_INFO | jq -r .headRefName)" >> $GITHUB_OUTPUT
          echo "base_branch=$(echo $PR_INFO | jq -r .baseRefName)" >> $GITHUB_OUTPUT
          
          # 从 SQLite 获取 runner
          SAFE_REPO=$(echo $REPO | tr '/' '-')
          DB_PATH="/tmp/duo-${SAFE_REPO}-${PR_NUMBER}.db"
          RUNNER=""
          if [ -f "$DB_PATH" ]; then
            RUNNER=$(sqlite3 "$DB_PATH" "SELECT value FROM state WHERE key='runner'" 2>/dev/null || echo "")
          fi
          
          echo "runner=$RUNNER" >> $GITHUB_OUTPUT

  duoduo:
    needs: get-runner
    if: needs.get-runner.outputs.runner != ''
    uses: notdp/.dotfiles/.github/workflows/duo-mention.yml@main
    with:
      pr_number: ${{ github.event.issue.number }}
      repo: ${{ github.repository }}
      pr_branch: ${{ needs.get-runner.outputs.pr_branch }}
      base_branch: ${{ needs.get-runner.outputs.base_branch }}
      comment_body: ${{ github.event.comment.body }}
      comment_author: ${{ github.event.comment.user.login }}
      runner: ${{ needs.get-runner.outputs.runner }}
      bot_name: your-bot-name
    secrets:
      DUO_APP_ID: ${{ secrets.DUO_APP_ID }}
      DUO_APP_PRIVATE_KEY: ${{ secrets.DUO_APP_PRIVATE_KEY }}
```

将 `@your-bot-name` 替换为你的 GitHub App bot 用户名（如 `@duo-bot`）。

**触发方式**：

- `@your-bot-name` 直接 @ bot
- Quote reply 任何包含 Opus/Codex/Orchestrator 的评论

**用途**：

- 发起审查（即使之前没有审查记录）
- 重新审查
- 询问问题
- 请求操作（删除评论、合并等）

## 前置要求

- **Self-hosted runner**（macOS arm64）
- Runner 上需安装：
  - `droid` CLI（[Factory](https://factory.ai)）
  - `gh` CLI（已认证）
  - `pipx`（用于安装 duo-cli）
  - `sqlite3`（用于状态存储）

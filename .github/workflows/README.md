# Duo Review - GitHub Actions 配置

## 快速开始

在你的仓库创建 `.github/workflows/duo-review.yml`：

```yaml
name: Duo Review

on:
  pull_request:
    types: [opened, synchronize]

concurrency:
  group: duoduo-${{ github.event.pull_request.number }}
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
      # 方式 A: GitHub App
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
   - `Contents`: Read-only
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

## 前置要求

- **Self-hosted runner**（macOS arm64）
- Runner 上需安装：
  - `droid` CLI（[Factory](https://factory.ai)）
  - `redis-server`
  - `gh` CLI（已认证）

---
name: guard-ship
description: 当改动已完成、需要创建 PR、合并分支或推送到远端时使用；支持 PR 模式与直接发布模式。
argument-hint: <pr|publish|skip-review|目标分支>
---

# Ship

## Decision Principles

- `guard-ship` 优化的是可追溯、可回滚、可验证的交付，不是最快把改动推出去。
- PR 是默认路径，因为它保留 review、CI 和协作缓冲；publish 只适合用户明确授权且验证、预检、GitOps 都闭环的场景。
- keep 是有效交付裁决：当需求未闭合、风险未解释清楚或需要用户判断时，保留分支比带着不确定性推送更安全。
- discard 只在用户明确确认后执行，因为它以丢失本地工作为代价换取状态清理。

## 1. 预检（两种模式共用）

优先跑一键预检脚本：

```
bash "<dotfiles_root>/scripts/preflight.sh"
```

它会产出固定 Markdown 表，覆盖：

| Check | 说明 |
|-------|------|
| branch | 当前分支 vs 默认分支 |
| working tree | `git status` 是否干净 |
| sensitive scan | diff 中敏感模式扫描（api_key/token/password/私钥） |
| remote sync | 与 origin/<branch> 同步状态 |
| tracked secret files | .env / *.key / *.pem 等被追踪 |

exit code：0=全绿、1=软警告（需确认）、2=严重阻断（敏感信息）。

补充人工项（脚本外）：

- [ ] 测试通过（走 `<dotfiles_root>/scripts/run-verify.sh <target_repo_root>` 或手动跑）
- [ ] `/guard-verify` 已通过
- [ ] GitOps 合规（详见 `/guard-gitops`）：本次改动全部可通过 `git diff` / `git log` 复盘，无"绕过 git 直接改线上/远程/部署产物"的副作用；例外仅限 `guard-gitops` 白名单

预检出现 FAIL 则停止，报告问题。

## 2. 解析参数

解析 `$ARGUMENTS`：

- `pr` → PR 模式（创建 Pull Request）
- `publish` → 直接发布模式（推送 main + 发布）
- `skip-review` → 跳过自动 review
- 位置参数作为目标分支（留空则使用仓库默认分支）
- **未指定 `pr` 或 `publish` → 询问用户选择模式**

## 3. Review（可跳过）

除非 `skip-review`，否则自动执行一次 simple review：

- 审查未提交或已提交但未推送的变更
- Critical issues → 阻断交付，要求修复
- Important/Minor → 列出但不阻断，由用户决定

---

## 模式 A：PR 模式（`pr`）

### A1. 提交与推送

- 如有未提交变更，引导用户 commit（建议 commit message）
- `git push` 到远程

### A2. 创建 PR

- 自动生成 PR 描述：变更摘要、关键修改、测试说明
- PR 描述必含 `## 可观测性与监控` 段：本次改动出问题时怎么发现、看什么信号、怎么回滚。无运行时影响时写一行 `无额外监控需求` + 理由。段内列：
  - 排障入口：相关日志关键字 / trace id 字段 / 可查的 metric 或面板（按项目已有设施；没有就写出问题时依赖什么观察）
  - 健康信号 vs 失败信号：正常态什么样、异常态什么样
  - 回滚 / 缓解触发条件
- `gh pr create --base <目标分支>`（如有 gh CLI）
- 输出 PR URL

### A3. 交付路径选择

如果用户不想创建 PR，提供备选：

| 路径 | 说明 |
|------|------|
| PR | 创建 Pull Request（默认）：适合需要 review / CI / 可回滚记录的变更，代价是交付更慢 |
| merge | 在本地合并到目标分支，验证后再 push：适合已批准且需要线性推进的变更，代价是本地操作复杂度更高 |
| keep | 保留当前分支，不创建 PR，不合并：适合需求未闭合或风险待确认的变更，代价是不完成交付 |
| discard | 丢弃当前分支上的本次变更：只适合用户明确放弃本轮工作，代价是本地改动不可保留 |

各路径执行方式：

- **PR**：push 当前分支 → `gh pr create --base <目标分支>`
- **merge**：切到目标分支 → 拉取最新 → 合并当前分支 → 运行验证 → push
- **keep**：只做预检和 review，保留当前分支，输出下一步建议
- **discard**：先展示将被丢弃的变更，用户明确确认后再执行回退/删分支

---

## 模式 B：直接发布模式（`publish`）

### B1. 安全检查

- 确认当前分支是 main（或目标分支），如果不是则先合并
- `git pull --rebase` 拉取最新
- 再次运行预检确认合并后无问题

### B2. 提交与推送

- 如有未提交变更，引导用户 commit（建议 commit message）
- `git push origin main`（或目标分支）
  - **注意**：`command_guard` hook 会 deny 向 main/master 的推送（保护共享历史）。publish 模式必须先过 `/guard-gitops` 并取得用户显式批准后，由用户手动执行该 push（如 `! git push origin main`），agent 不自动放行。推送到 feature 分支则不受此限。

### B3. 发布

检测项目类型，执行对应发布流程：

| 项目类型 | 检测方式 | 发布动作 |
|---------|---------|---------|
| npm | `package.json` 存在 | 提示 version bump → `npm publish` 或 `pnpm publish` |
| Python | `pyproject.toml` / `setup.py` | 提示 version bump → `python -m build && twine upload` |
| GitHub Release | `.github/` 或通用 | `gh release create` 自动生成 release notes |
| 其他 | 无法检测 | 询问用户发布方式 |

发布步骤：

1. **询问版本号**：展示当前版本，建议 patch/minor/major，等用户确认
2. **更新版本**：修改对应的版本文件
3. **创建 tag**：`git tag v{version}`
4. **推送 tag**：`git push origin v{version}`
5. **执行发布命令**：按检测到的项目类型执行
6. **创建 GitHub Release**（如有 gh CLI）：`gh release create v{version} --generate-notes`

## Gotchas

- `guard-ship` 的前提是先完成 `/guard-verify`，不是拿它代替验证
- 未看 `git status` 和 `git diff --cached` 就交付，很容易把无关文件或敏感信息带上
- 发布动作带远程副作用；高风险步骤必须先确认当前分支、目标分支和发布方式
- review 可以跳过，但跳过不等于风险消失；要在交付说明里明确记录
- 线上/运行时/部署产物已经被改过但仓库未反映 → 先按 `/guard-gitops` 把仓库拉成事实源，再谈 ship；不能一边 ship 一边留下漂移

## 扩展阅读

- `docs/software-engineering-research/other-directions.md`

## 关联技能

- 预检失败 → `/dev-debug` 排查
- 未跳过 review → 自动触发 `/guard-review`
- 交付前验证 → `/guard-verify`
- 涉及远程/部署/线上状态 → `/guard-gitops`

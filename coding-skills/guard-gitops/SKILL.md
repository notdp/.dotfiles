---
name: guard-gitops
description: 当改动会影响仓库外可见状态、或准备触碰线上/远程/部署产物时使用；强制 git 仓库作为唯一事实源。
argument-hint: <改动范围|准备动作>
---

# Guard GitOps

本 skill 是**纪律层**，不是强制层。真正的硬门在 CI / 受保护分支 / 只读凭据 / hook。
这里规定 agent 的默认行为边界：**凡是会改变仓库外可见状态的改动，先过 gitops。**

## 1. SSOT 铁律

Git 仓库是唯一事实源。任何改动只有三种合法存在形式：

1. 已 commit 到某个分支
2. 正在 working tree 里、路径明确、准备 commit
3. 已推到远程的 branch / PR / tag

以下不算存在：

- 线上控制台 / Web UI 里的临时修改
- SSH / kubectl / psql / redis-cli 里的就地改动
- 运行时进程内存（feature flag、动态配置、热修改）
- 本机 `~/.config`、`~/.local/bin` 下未纳入 git 的产物

**"没有 commit 记录的改动 = 不存在的改动"**。

## 2. 触发条件（出现任一，必须进入本 skill）

| 类别 | 示例 |
|------|------|
| 远程机器 | SSH 改配置、直接改 `/etc/*`、手动改容器里的文件 |
| 部署产物 | 直接改 k8s manifest、helm values、terraform state、CI 环境变量 |
| 数据层 | 线上 DB schema 变更、直接改生产数据、手动改 migration 表 |
| Secrets | 控制台改 secrets / KMS / vault 条目 |
| 运行时 | feature flag 面板、监控规则、告警阈值、流量路由 |
| 仓库外二进制 | 手动替换 `~/.local/bin/*` 且脚本未进 git |
| 第三方面板 | Grafana / Sentry / Linear / Notion 里的"配置类"改动 |

只做只读查询（看日志、看状态、dry-run）不触发本 skill。

## 3. 合法路径（唯一）

```
working tree 改动
  → 本地验证
  → commit（消息说明 why）
  → push
  → PR / code review
  → merge 到受保护分支
  → 声明式部署 / 拉取同步
```

禁止动作（无例外）：

- 跳过 working tree，直接在目标系统上改
- 绕过 PR 直推受保护分支
- `git push --force` 共享分支
- "先改线上跑起来，回头再提 PR"
- "小改动不用走 PR"

## 4. 动手前门禁清单

```
[ ] git status 干净，或显式承认当前 dirty 且能说明 dirty 内容属于本次任务
[ ] HEAD 不是 detached 状态
[ ] 本次改动在仓库里有对应声明文件（配置/manifest/migration/脚本）
    → 没有？先补文件再改；"补 SSOT" 本身也是一次独立 commit
[ ] 目标分支有远程上游；没有就先 push -u 建上游
[ ] 目标环境的变更入口是 PR / merge / pipeline，而不是手工 apply
```

任一不通过 → 停下，先修齐，再谈改动。

## 5. 例外白名单（仅以下几类，其它一律不允许）

| 例外 | 条件 |
|------|------|
| 只读诊断 | 看日志、看状态、dry-run、`--dry-run` 类命令 |
| 本机个人工具 | 如 `commands/droid-mod.md`：脚本本身已在 git，只改本机二进制 |
| 临时 debug 日志 | 必须在验证结束前回滚或并入 commit，不允许留在线上 |
| 紧急止血（break-glass） | 仅允许"回滚类"手工操作（重启、下线实例、切流量），且事后必须 **48h 内** 补 PR 把线上状态写回仓库 |

"场景特殊""只改一下""临时用一下"不是例外。

## 6. 漂移处理

发现线上状态 ≠ 仓库声明时：

1. 先把**仓库**拉回成事实源（把线上真实状态如实写进仓库并 commit），而不是反向同步
2. 用 PR + review 走正式路径修正到目标状态
3. 事后做一次漂移根因归档（谁、什么时候、绕了哪一步）

漂移恢复规则：先记录 observed drift，再通过 repo / PR / review 修正目标状态。

## 7. 和其它 skill 的衔接

- 由 `/guard-check` 默认路由进来（详见 `${HOME}/.dotfiles/coding-skills/guard-check/SKILL.md`）
- 是 `/guard-ship` 的前置门禁（预检会显式检查）
- 漂移定位 → `/dev-debug`
- 漂移修复需要测试护栏 → `/dev-tdd`
- 不知道该改哪个声明文件 → `/think-map` 先建立仓库地图

## 8. Gotchas

- "先在线上改，改完再同步回仓库" 会破坏 SSOT；正确路径是先更新仓库声明
- "这个配置仓库里没有声明" ≠ 可以直接改线上；应先把声明补进仓库
- 手工执行一条改动后才 commit 脚本 = 仓库还是滞后事实源；应该先 commit 脚本，再执行
- 面板类改动（Grafana/Sentry/Linear）容易被忽视；只要该面板有"导出为代码"的路径，就按 gitops 走
- 本 skill 不承诺硬拦截；真正硬门需要受保护分支、只读凭据、CI 校验、pre-push hook

## 9. Hard stops

- 仓库声明尚未 commit 时，状态为 `not ready to run`。
- "紧急"只能进入第 5 节的 break-glass 路径，事后补 PR/review。
- 发现漂移后，先把 observed drift 写回仓库事实源，再通过正式路径修正。
- 例外白名单只适用于第 5 节列出的场景。

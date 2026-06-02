---
name: guard-threat-model
description: 当项目首次做安全审查、架构发生变更或需要建立 STRIDE 威胁建模 SSOT 时使用；产出 docs/threat-model.md 作为 guard-secure 的前置输入。
argument-hint: <留空=全仓库|子系统名|模块路径>
---

# Threat Model

定位：建立项目级威胁模型 SSOT。`/guard-secure` 在每次审查时读取本文件作为基线，避免每次审查都从零做架构分析。

## 1. 触发条件

- 项目首次做安全审查（无 `docs/threat-model.md`）
- 重大架构变更后（新引入 service / 数据流 / 信任边界 / 第三方依赖）
- 已有威胁模型 `生成日期` 距今 > 90 天
- 用户显式要求

## 2. 资产识别

读 README / 入口文件 / API 路由 / DB schema，列出系统资产：

| 资产类型 | 示例 | 关注点 |
|---------|------|-------|
| **数据资产** | 用户密码 / PII / 财务 / 业务核心数据 / 私钥 / token | 静态加密、传输加密、访问控制 |
| **功能资产** | 认证流程 / 支付 / 提权 / 数据导出 | 完整性、不可绕过、审计 |
| **基础设施资产** | DB / 缓存 / 队列 / secret store / CI 凭证 | 隔离、最小权限、轮换 |
| **信任声誉** | 域名信誉、不被列为 phishing | 反垃圾、滥用防护 |

每个资产标注：

- **敏感度**：高 / 中 / 低
- **存储位置**：DB / 缓存 / 文件系统 / 第三方
- **访问者**：角色清单（user / admin / service / public）

## 3. 数据流梳理

为每条主要数据流画出 path：

```
来源 (untrusted/trusted) → 边界 (validation 点) → 处理 → 存储 → 输出
```

至少覆盖：

- 用户输入流（HTTP / WebSocket / 文件上传 / Webhook）
- 认证流（登录 / token 刷新 / SSO / OAuth）
- 数据导出流（API 响应 / 报表 / 备份）
- 第三方调用流（出向 HTTP / 队列消费 / 外部 webhook）
- 内部 RPC / event flow（如果跨服务）

每条数据流标注**信任边界**：哪个点之前是 untrusted，必须做验证。

### 数据流图（示例）

```
[Browser] ──https──> [LB/WAF] ──> [API Gateway] ──> [App Server]
                                                          │
                              ─JWT验证─┘                  │
                                                          ├──> [DB (encrypted at rest)]
                                                          ├──> [Cache (token, query)]
                                                          └──> [Third-party API (signed)]
```

实际产出可用 mermaid 或 ASCII。

## 4. STRIDE 矩阵

对每个**(数据流 × STRIDE 维度)** 组合分析。可省略明显不适用的格子。

| 数据流 | S | T | R | I | D | E |
|-------|---|---|---|---|---|---|
| 用户登录 | 凭证爆破 / 钓鱼 | CSRF / token 篡改 | 无登录日志 | 用户名枚举 / 时序攻击 | 登录 rate limit | 默认权限过高 |
| 文件上传 | — | 文件名注入 / 内容篡改 | 上传无审计 | 上传内容含 PII 暴露 | 大文件 DoS | 上传到敏感目录提权 |
| ... | ... | ... | ... | ... | ... | ... |

### 每个威胁项填写

```
威胁: <一句话>
触发条件: <什么场景会出现>
当前缓解: <已有什么防护>
残余风险: 高 / 中 / 低
建议: <加固方案>
```

## 5. 产出 `docs/threat-model.md`

写入仓库内（不依赖 `.factory`）：

```markdown
# Threat Model — <项目名>

> 生成日期: <YYYY-MM-DD>
> 触发条件: <首次 / 架构变更 / 90 天到期 / 手动>
> 维护者: <责任人>
> 关联审查 skill: /guard-secure

## 1. 资产清单
| 资产 | 类型 | 敏感度 | 存储位置 | 访问者 |
| ... |

## 2. 信任边界
- <边界 1：浏览器 / API Gateway>
- <边界 2：API Gateway / 内部服务>
- ...

## 3. 数据流
（mermaid 或 ASCII 图 + 简述）

## 4. STRIDE 矩阵
（见第 4 节模板）

## 5. 已有缓解措施
- [x] HTTPS 强制
- [x] JWT 短期 + refresh
- [x] DB 静态加密
- [x] CSP / X-Frame-Options
- [ ] Rate limit（缺失，待补）
- ...

## 6. 待办风险（追踪项）
| ID | 威胁 | 严重度 | 负责人 | 计划 |
| TM-001 | 登录无 rate limit | 高 | @x | Q3 接 redis-token-bucket |
| ... |

## 7. 重跑触发
出现以下任一条件时重跑 /guard-threat-model：
- 新引入对外 service / API
- 新增第三方依赖（payment / OAuth provider 等）
- 修改认证 / 鉴权逻辑
- 修改数据存储结构（含加密策略）
- 距上次生成 > 90 天
```

## 6. 跨 agent 适配

- 任意 agent 都可执行：仅需读 README / 代码 + 写一个 markdown 文件
- 派发资产识别 / 数据流梳理为并行子任务可加速；无并行子任务能力的平台顺序处理
- 不依赖任何特定 agent 工具

## Gotchas

- 不要把"理论威胁清单"当成威胁模型；必须落到本项目的具体数据流
- 不要列了威胁不写"当前缓解" —— 没有现状对比，威胁清单没用
- "已有缓解措施"必须在代码中验证存在，不能凭印象
- 待办风险必须可追踪：有 ID、有负责人、有计划；否则只是抱怨清单
- 90 天是经验值；架构剧烈变化时应缩短为 30 天

## 禁止

- 用通用模板填空而不读项目代码
- 把所有威胁标"中"或"高"，丧失优先级信号
- 写完不让 `/guard-secure` 引用，导致 SSOT 形同虚设

## 关联技能

- 建立基线后 → `/guard-secure` 每次审查时引用本文件
- 待办风险需要修复 → `/dev-tdd`（修复）+ `/guard-verify`（验证）
- 架构理解不足 → 先 `/think-architecture` / `/think-map`
- 涉及对外发布 → `/guard-ship`

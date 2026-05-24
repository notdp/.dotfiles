---
name: guard-secure
description: 当改动触及认证、授权、数据处理、网络边界或外部依赖，或需要做漏洞扫描和攻击面评估时使用；基于 STRIDE 威胁建模。
argument-hint: <pr|weekly|full|staged|commit-range|文件/目录|功能描述|留空=pr>
---

# Secure

## 1. 确定 Scan Mode

解析 `$ARGUMENTS`：

| 模式 | 触发 | 范围 |
|------|------|------|
| `pr` | 默认 / 留空 / 当前是 PR 上下文 | 当前分支 vs base 的 diff |
| `staged` | `staged` | 已 stage 但未 commit 的变更 |
| `weekly` | `weekly` | 默认分支最近 7 天的提交 |
| `full` | `full` | 全仓库（首次审查或重大架构变更后） |
| `commit-range` | `a1b2..HEAD` 等 range | 指定 commit 范围 |
| 路径 / 功能描述 | 文件/目录/`"用户认证模块"` | 该范围内全文件 |

### 范围采集命令（参考）

```bash
# pr
git diff $(git merge-base HEAD <base>)..HEAD --name-only
# staged
git diff --staged --name-only
# weekly
git log --since="7 days ago" --name-only --pretty=format: | sort -u
# full
git ls-files
# commit-range
git diff <range> --name-only
```

## 2. Threat Model SSOT

进入正式分析前，检查项目级威胁模型：

1. 读取 `docs/threat-model.md`（项目级 SSOT）
2. 如不存在 → 提示用户先跑 `/guard-threat-model` 建立基线；本次审查降级为通用 STRIDE 分析
3. 如存在但 `生成日期` 距今 > 90 天 → 标注 `[威胁模型可能过时]`，仍可继续
4. 读取后用其中的"资产清单"和"信任边界"指导 STRIDE 检查重点

威胁模型不是强制前置；缺失时仅降级，不阻断。

## 3. 安全授权边界

先区分本次任务是只读审查，还是会对外部系统产生安全测试副作用：

- 只读审查、代码级漏洞分析、本地配置检查、已授权范围内的本地验证可以继续，但 findings 仍必须给证据。
- 对外部目标执行扫描、exploit、C2、phishing simulation、credential access、lateral movement、暴力测试、绕过认证或破坏性测试前，必须先拿到明确授权范围、允许动作、停止条件和验证方式。
- 授权范围不明确时不要执行安全工具或攻击模拟；改为说明缺少的 scope，并提供只读审查路径。

需要扩展检查面时，读取 `references/security-taxonomy.md`；该 reference 只作为分类导航，不是 ATT&CK / NIST 覆盖率 SSOT。

## 4. 威胁建模（STRIDE 检查表）

对目标范围逐维度分析。每条检查点给出常见模式 + 触发关键词供 grep。

### S — Spoofing（伪装）

- 弱认证：明文密码存储、可逆加密代替哈希、无 salt
- Session token：localStorage 存敏感 token、缺 `httpOnly` / `secure` / `sameSite`
- API key 暴露：硬编码 key、日志打印 key、前端 bundle 含 secret
- JWT 漏洞：`alg: none` 可绕过、弱 secret（短/可猜）、不验证签名、不校验 `exp` / `iss` / `aud`
- MFA 缺失：敏感操作（改密码 / 转账 / 提权）无 step-up auth
- 身份混淆：信任 client 传入的 user_id 而非 session 派生

关键词：`jwt.decode` `localStorage.setItem.*token` `bcrypt|argon2|scrypt` 缺失

### T — Tampering（篡改）

- **SQL Injection**：字符串插值 / 拼接构造 SQL（`f"SELECT ... {user_input}"` / `${input}` / `+`）
- **Command Injection**：`exec` / `system` / `subprocess.shell=True` / `child_process.exec` 拼用户输入
- **Path Traversal**：用户输入直接拼接到文件路径（`../`、绝对路径未校验）
- **XSS**：`innerHTML` / `dangerouslySetInnerHTML` / 模板未转义 / `v-html` 接受用户输入
- **Mass Assignment**：`Object.assign(model, req.body)` / Rails `params.permit` 不当
- **Server-Side Template Injection**：用户输入进入 Jinja / EJS / Handlebars 渲染
- **CSRF**：状态变更接口无 CSRF token / `SameSite` 不当
- **Open Redirect**：用户输入作为 redirect URL 不校验白名单
- **SSRF**：fetch / requests / curl URL 来自用户输入，未做 host 白名单

关键词：`exec` `eval` `innerHTML` `dangerouslySetInnerHTML` `f"SELECT` `subprocess.*shell=True` `Object.assign(.*req`

### R — Repudiation（抵赖）

- 关键操作（auth / 权限变更 / 数据删除 / 资金）无审计日志
- 日志可被用户篡改（用户写自己的日志）
- 时间戳不可信（来自 client）
- 操作 ID 缺失或可被预测覆盖

### I — Information Disclosure（信息泄露）

- 错误响应含 stack trace / SQL / 内部路径
- 日志含 PII / 密钥 / token / 完整请求体
- API 返回多余字段（serializer 不裁剪）
- 调试端点在生产可访问（`/debug` `/admin` `/swagger` `/.env`）
- IDOR：响应他人资源（`GET /orders/123` 不校验 owner）
- Timing attack：用户名存在性 / 密码比较未用 constant-time
- 缓存毒化：基于 user-controlled header 缓存

关键词：`console.log.*req` `printStackTrace` `password.*==.*password`

### D — Denial of Service（拒绝服务）

- 无 rate limit（登录 / 重置密码 / 发送邮件 / API）
- 无输入大小限制（body / file / array length / regex backtracking）
- 无超时（外部 HTTP 调用 / DB 查询）
- 无分页（list 接口返回全量）
- 用户可触发 N+1 / 大查询
- ReDoS：用户输入进入复杂正则
- Zip bomb / billion laughs（XML / archive）

### E — Elevation of Privilege（提权）

- 权限检查跳过：only check on `GET`，但 `POST` 漏检
- 角色验证逻辑错误：`role == 'admin' || role == 'user'` 永真
- IDOR + 写：他人资源可被覆盖
- 路径穿越提权：上传文件名含 `../` 写到系统目录
- Prototype pollution（JS）
- TOCTOU：检查后再使用，中间可被修改
- 反序列化：`pickle.loads` / Java ObjectInputStream / PHP `unserialize` 接受用户数据

## 5. 依赖 CVE 检查

- [ ] 项目已配置漏洞扫描（`npm audit` / `pip-audit` / `cargo audit` / `go list -m -u all` / GitHub Dependabot / Snyk / Trivy）
- [ ] 锁文件（`package-lock.json` / `pnpm-lock.yaml` / `poetry.lock` / `Cargo.lock` / `go.sum`）已 commit 且与 manifest 一致
- [ ] 新增依赖经过 license + supply chain 审查
- [ ] 高危 CVE 有跟进计划（不要求每个都立即修，但要可见）

## 6. 输出

```markdown
### Scan Context
- Mode: <pr|weekly|full|staged|commit-range|path>
- 范围: <文件数 / commit 数>
- Threat model: <已读取 docs/threat-model.md / 缺失，降级 / 过时 N 天>

### 发现

#### Critical（必须修后才能合并）
- [威胁类型] file:line — 问题 — 触发路径 — 缓解建议

#### Important
- ...

#### 信息性 / 加固建议
- ...

### 缓解措施验证
- [ ] 已有的认证 / 鉴权 / 加密 / 日志 / rate limit 是否覆盖本次改动
- [ ] 依赖 CVE 检查（见第 4 节）

### 总体评估
- 安全风险等级：高 / 中 / 低
- Ready for merge?: Yes / No / With fixes
```

## 7. 规则

- 只报告有证据的风险，不报告理论上的可能性
- 每个 finding 必须给：威胁类型 + file:line + 触发路径 + 缓解建议
- 关注数据流：用户输入 → 处理 → 存储 → 输出的每个环节
- 命中 Critical 必须给出 Ready for merge? = No
- MySQL/InnoDB schema、索引、命名和性能规范不在本 skill 展开；需要时串联 `/guard-mysql-review`。如果 `/guard-mysql-review` 命中 SQL injection 或未参数化 SQL，再回到本 skill 做安全裁决。

## Gotchas

- “理论上可能”不等于安全问题；要给触发条件、影响路径和证据
- 不要只盯单点 API；安全问题通常跨越输入、存储、权限和输出链路
- 缺少认证/鉴权/速率限制时，要区分这是已知设计选择还是实际漏洞
- 安全审查结论必须可执行，不能只留下抽象恐吓
- 威胁模型缺失不是免责，仍要做通用 STRIDE 检查；但要把"建议先建威胁模型"作为加固建议提出

## 扩展阅读

- `docs/software-engineering-research/other-directions.md`
- OWASP Top 10、OWASP ASVS、CWE Top 25

## 关联技能

- 缺少威胁模型基线 → `/guard-threat-model` 建立 SSOT
- MySQL/InnoDB schema、索引、DDL 或查询性能审查 → `/guard-mysql-review`
- 发现漏洞需修复 → `/dev-debug`（定位）+ `/dev-tdd`（修复）
- 安全审查通过后 → `/guard-ship` 交付

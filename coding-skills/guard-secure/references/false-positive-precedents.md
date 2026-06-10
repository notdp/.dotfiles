# 误报判例库（false-positive precedents）

安全审查的负样本知识：**"不报什么"与"找什么"同等重要**。来源是 `refs/anthropics/claude-code-security-review` 的两套过滤规则（GitHub Action 版 `claudecode/claude_api_client.py:243-284`，slash command 版 `.claude/commands/security-review.md:139-170`），合并去重后逐条裁决。这些判例是真实误报数据蒸馏出的裁决经验，不是漏洞分类学。

消费方：
- `/guard-secure` 的 FP 裁决 phase（per-finding 注入相关条目）
- `security-fp-judge` subagent（判例匹配步骤）

裁决标记：**吸收**（直接生效）/ **调整**（改写后生效，理由必读）/ **拒绝**（不生效，理由必读）。与 STRIDE 检查表冲突的条目全部显式裁决，不沉默选边。

## 模式降权总则（已锁定决策，2026-06-10）

| 模式 | DoS / 资源耗尽类（STRIDE D 维度命中项） |
|---|---|
| `pr` / `staged` / `commit-range` | 最高只进"信息性 / 加固建议"，不阻断合并，标注 `[D 维度 PR 模式降权]` |
| `full` / `weekly` / 路径 / 功能描述 | D 维度全权重，正常分级 |

理由：上游把 DoS 整类硬排除是面向"PR 阻断"场景的取舍；本仓库 guard-secure 还服务架构审查，全量丢弃会丢掉"新增无超时外部调用"这类真实信号。降权发生在 finding 分级时（FP 裁决之前），已是最低级的项不再消耗裁决。

## 硬排除（裁决后）

| # | 规则 | 来源 | 裁决 | 触发样例 |
|---|---|---|---|---|
| H1 | DoS / 资源耗尽 / rate limiting 缺失 / 内存 CPU 耗尽 | api_client 排除 1,3,4；正则层 findings_filter.py:31-79 | **调整**：按模式降权（见总则），不硬排除 | "登录接口无 rate limit" |
| H2 | secrets/credentials 落盘（"另有系统管理"） | api_client 排除 2 | **拒绝**：本仓库无独立 secret 管理系统兜底，secrets 落盘照报；与 MCP/Browser 边界检查（SKILL.md 第 6 节"auth state 按 secret 处理"）一致 | `auth.json` 明文写入仓库目录 |
| H3 | 非安全关键字段缺输入校验、泛化的"缺 hardening" | api_client 排除 5,7 | **吸收**：只报具体漏洞，不报最佳实践缺失 | "昵称字段没限制长度" |
| H4 | 理论性 race condition / timing attack | api_client 排除 8 | **吸收**：只报有具体危害路径的并发问题 | "读取后写入之间理论上可被抢占" |
| H5 | 过期第三方依赖漏洞 | api_client 排除 9；判例 7 | **调整**：FP 裁决不处理依赖类 finding；依赖走 SKILL.md 第 5 节 CVE 检查渠道，不进漏洞表 | "lodash 版本过旧" |
| H6 | 内存安全问题（Rust 等内存安全语言） | api_client 排除 10；正则层仅 C/C++ 扩展名保留 | **吸收**：内存安全类 finding 仅在 C/C++ 代码中有效 | "Rust 代码 use-after-free" |
| H7 | 纯测试文件中的漏洞 | api_client 排除 11 | **吸收**：test-only 文件不报（fixture 中的"硬编码密码"等） | `tests/fixtures/fake_creds.py` |
| H8 | log spoofing（未消毒输入进日志） | api_client 排除 12 | **吸收** | "用户名含换行可伪造日志行" |
| H9 | 只控制 path 的 SSRF | api_client 排除 13 | **吸收**：SSRF 必须能控制 host 或 protocol 才报 | `fetch(BASE + userPath)` |
| H10 | 用户内容进入 AI prompt 不算漏洞 | api_client 排除 14 | **拒绝（限定）**：对普通应用吸收；但对 agent harness 资产（hook / skill / subagent / capsule 等会进入 model context 的路径）**拒绝**——prompt injection 是本仓库一等威胁（AGENTS.md 边界决策把 context-surface 列为高风险边界），照报 | 外部网页内容未隔离直接拼进 system prompt |
| H11 | 内部私有依赖不在公共源 | api_client 排除 15 | **调整**：不报"依赖不可得"，但**保留 dependency confusion 警惕**——若同名公共包可被抢注且安装配置未锁源，照报 | `pip install internal-utils` 无 index 约束 |
| H12 | 只导致 crash 不构成漏洞的代码缺陷 | api_client 排除 16 | **吸收**：null/undefined 崩溃归 bug 渠道（/dev-debug），不进安全表 | "变量可能为 undefined" |
| H13 | markdown 等纯文档文件中的 finding | slash 版排除 16；正则层结构规则 | **吸收**：文档不报；例外——本仓库的 skill/agent .md 是可执行资产，其中的命令注入/路径逃逸照报（同 H10 限定逻辑） | README 里的示例弱密码 |
| H14 | regex injection / ReDoS | slash 版排除 15,16 | **调整**：regex injection 吸收（不报）；ReDoS 归 D 维度按模式降权，不硬排除 | "用户输入拼进正则" |

## 判例（裁决后）

| # | 规则 | 来源 | 裁决 | 触发样例 |
|---|---|---|---|---|
| P1 | 明文记录高价值 secret 是漏洞；记录 URL 默认安全；记录 request headers 默认危险（常含凭证） | api_client 判例 1 | **吸收**：作为日志类 finding 的默认信任边界 | `logger.info(headers)` 报；`logger.info(url)` 不报 |
| P2 | UUID 视为不可猜测，无需校验；依赖"猜中 UUID"的攻击无效 | 判例 2 | **吸收** | "攻击者可枚举 order UUID" |
| P3 | 缺审计日志不是漏洞 | 判例 3 | **调整**：STRIDE R 维度保留检查；但"缺审计日志"单独出现时归"加固建议"，不进 Critical/Important——区分设计选择与实际漏洞（SKILL.md Gotchas 既有原则），full/weekly 模式下若涉及资金/权限变更等关键操作可升 Important | "删除操作没写审计日志" |
| P4 | env var 和 CLI flag 是可信值；依赖控制 env var 的攻击无效 | 判例 4 | **吸收**：安全环境下攻击者改不了进程环境 | "如果攻击者设置了 `DEBUG_HOST`…" |
| P5 | 内存/文件描述符泄漏类资源管理问题无效 | 判例 5 | **吸收**：归代码质量渠道 | "未 close 文件句柄" |
| P6 | tabnabbing / XS-Leaks / prototype pollution / open redirect 等低影响 web 漏洞默认不报，除非极高置信 | 判例 6（slash 版加"extremely high confidence"例外） | **调整**：保留 STRIDE T/E 维度对应检查点；报出门槛改为"有具体利用链且极高置信"，否则归加固建议 | "`target=_blank` 缺 `rel=noopener`" |
| P7 | React/Angular 默认防 XSS；仅 `dangerouslySetInnerHTML` / `bypassSecurityTrustHtml` 等 unsafe 方法才报 XSS | 判例 8（slash 版含 Angular） | **吸收** | React 组件渲染用户输入（无 unsafe 方法） |
| P8 | GitHub Actions workflow 漏洞多数不可利用，必须有具体攻击路径才报 | 判例 9；api_client 排除 6 | **吸收**：`pull_request_target` + 不可信 checkout 这类有明确路径的照报 | "workflow 引用了 `github.event.title`" |
| P9 | 客户端 JS/TS 缺权限检查/认证不是漏洞，校验责任在服务端 | 判例 10 | **吸收**：前端隐藏按钮≠权限控制，但报的对象应是服务端缺校验 | "前端没判断 admin 角色" |
| P10 | MEDIUM 级 finding 只报"明显且具体"的 | 判例 11 | **吸收**：对应本仓库 Important 级的报出门槛 | — |
| P11 | ipynb 漏洞多数不可利用，须具体不可信输入路径 | 判例 12 | **吸收** | "notebook 里 eval 了变量" |
| P12 | 记录非 PII 数据不是漏洞，即使"看起来敏感"；只报暴露 secret/密码/PII 的日志 | 判例 13 | **吸收** | `logger.debug(internal_config)` |
| P13 | shell 脚本命令注入通常不可利用，须具体不可信输入路径 | 判例 14 | **调整**：一般仓库吸收；本仓库 hooks/脚本的输入常来自 agent 生成内容（PostToolUse 输入、diff 内容），这条路径视为不可信输入，照报 | hook 脚本把 commit message 拼进 `eval` |
| P14 | 客户端 JS 的 SSRF / path traversal 无效（不绕防火墙、不读服务端文件） | 判例 15 | **吸收** | "前端 fetch 可被改 URL" |
| P15 | `../` path traversal 只在文件读取场景有效，HTTP 请求路径中的 `../` 一般无害 | 判例 16 | **吸收** | "API 路径参数含 ../" |
| P16 | 注入日志查询语句一般不报，除非确定导致敏感数据外泄 | 判例 17 | **吸收** | "搜索词拼进日志查询 DSL" |

## SIGNAL QUALITY 四问（残余 finding 逐条过）

来源：api_client SIGNAL QUALITY（与 slash 版一致），**吸收**：

1. 是否存在具体可利用的漏洞和清晰的攻击路径？
2. 这是真实安全风险，还是理论上的最佳实践缺失？
3. 是否有确切代码位置和可复述的触发步骤？
4. 安全工程师会在 PR review 里自信地提出这条吗？

## 维护规则

- 新增判例必须带：规则 + 来源（误报实例或上游 file:line）+ 裁决 + 触发样例；无样例不收（上游 evals 无 ground truth 的教训）
- 上游两套规则各自迭代、并不同步（action 版无 Angular/notebook 限定差异等）；更新 refs 后 diff 两处再合并，不单边照搬
- 与 STRIDE 检查表新增冲突时，显式裁决入表，禁止沉默选边

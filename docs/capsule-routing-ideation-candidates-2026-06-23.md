# Capsule 路由改进 — 发散候选(B 工作流输入,2026-06-23)

> 产出方式:`/think-ideate` 实跑(同时作为 ideation 技能的 A2 验证)。
> 性质:**发散候选,未裁决。** 下一步交 `/think-compare` 按硬约束打分,接 B 工作流(见 `harness-governance-prd-2026-06-23.md` 工作流 B)。
> 不可牺牲约束:hook 快 / fail-open / 跨 agent(CC·Droid 原生 + kilo·opencode 经 .mjs)/ advisory 不硬拦截。

## 问题重新框定(双菱形发散)
① 怎么让分类更准?(原框定) ② 怎么让分类错了也不疼? ③ 凭什么是 prompt 前分类器决定? ④ 到底要不要逐条路由? ⑤ 怎么让系统自己越用越准?

## 候选清单(本质不同,不评判)

| # | 候选 | 框定/技法 | 差异点 | 适用前提 |
|---|------|---------|--------|---------|
| 1 | **自门控 capsule**:照常注入,capsule 开头加"若与当前任务无关请忽略",过滤权交给看到全上下文的主模型 | ②反向+约束反转 | 不追求分类准,让强模型 post-filter | 主模型够听话;capsule 短到误注入不疼 |
| 2 | **拉取而非推送**:hook 只注入一行"可用纪律菜单",模型判相关时自己拉全文(=把 capsule 变 skill) | ③④反转时机/决策者 | 决策者 弱分类器→强主模型 | 各 agent 有 on-demand 拉取 |
| 3 | **行为触发**:不靠 prompt 猜,在 PreToolUse 按真实信号(将编辑 secrets/schema、将 git push)触发 boundary/security/gitops | SCAMPER 重排时机+换信号源 | 用高信号"动作"代替低信号"prompt 文本" | 该类 capsule 有确定动作信号(部分已被 boundary_gate/command_guard 体现) |
| 4 | **分层路由**:hard-signal capsule(security/gitops 靠 git push/secrets 文件)用确定性规则,LLM 只判模糊的(scope vs planning) | SCAMPER 删减 | 不让 LLM 干 regex 能完美干的 | capsule 可按信号确定性分两类 |
| 5 | **反馈飞轮**:capsule 注入后观察建议是否被采纳(说 think-scope 却只改一行=负例),从 transcript 自动攒 eval 集/负例 | 类比垃圾邮件过滤+⑤ | 不手工调,让使用自标注 | 有 transcript(agentsview 已有) |
| 6 | **置信度分级注入**:高置信→全文;中→一行提示;低→不注 | SCAMPER 改放大 | 降 FP 伤害而非提 F1 | 分类器能出置信度 |
| 7 | **不确定就问人**:低置信不猜也不丢,systemMessage 让用户一键确认 | 换决策者(人)+fail-loud | fail-open 改成 fail-to-user | 用户在场可交互 |
| 8 | **环境常驻/砍路由**:便宜纪律(四红线)直接常驻,纯噪声 capsule 直接删 | PO 挑衅 | 重新质疑"要不要逐条路由" | 部分 capsule 价值不值路由成本 |
| meta | **形态箱(生成器)**:`信号源(prompt/文件/工具/diff/历史)× 决策者(regex/小LLM/主模型/用户/动作规则)× 时机(pre-prompt/pre-tool/post-tool/stop)× 强度(全文/提示/无)` | 形态分析 | 上面多数候选是此箱某格 | — |

## 轻收敛(聚类,不裁决)
- **方向 A 改分类器本身**:定义重写 / DSPy / #6 分级 / #5 飞轮——保留 prompt 前分类器,受"模糊边界天花板"限制。
- **方向 B 换决策者·信号·时机**:#1 自门控 / #2 拉取 / #3 行为触发 / #4 分层 / #7 问人——不赌低上下文分类器,有几条直接绕开 F1 问题。
- **方向 C 质疑要不要路由**:#8 环境常驻 + 砍低价值。

## 下一步
- 交 `/think-compare` 按 4 条硬约束(快/fail-open/跨 agent/advisory)打分取舍。
- #3 与现有 boundary_gate/command_guard 重叠,性价比疑似高;#5/#7 依赖 agentsview transcript 数据。
- 与 R3/R4 衔接:先 B1 验证 capsule 危害,再决定投入哪个方向。

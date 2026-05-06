---
name: guard-verify
description: 当准备声称“已完成/已修复/可交付”时使用；必须给出验证证据，不能空口收尾。
argument-hint: <交付物|验证范围>
---

调用本 skill 后，必须提供验证证据。没有验证结果 = 不能声称完成。

## 触发时机

适用于即将向用户报告“已完成”/“已修复”/“已实现”的场景。

## 验证清单

1. **提取可验证交付物** — 先把用户要求拆成 1-N 条“现在应该能够做到什么”，作为后续验收清单
2. **自动跑 test/build/lint** — 优先用 `scripts/run-verify.sh` 一键探测并运行；不适配时手动跑项目对应命令
3. **功能验证** — 对每条交付物执行验证命令或操作，确认预期行为
4. **回归检查** — 确认没有破坏已有功能
5. **结构性验证** — 若本次改动涉及架构/重构/大 diff，补充说明影响面是否合理、验证护栏是否足够；必要时引用 `/think-quality` 结论

## UI 任务额外门禁

当交付物涉及 UI、CSS、React/Vue/Svelte 组件、页面、设计系统或视觉调整时，自动验证不够。必须补充视觉证据：

| Check | 必需证据 |
|---|---|
| 页面入口 | URL、本地 route、Storybook story 或组件预览入口 |
| Viewport | 至少 mobile + desktop；建议 `390x844`、`1280x900` |
| Screenshot | 每个关键 viewport 的截图路径 |
| DOM snapshot | 关键区域 snapshot 或 selector 查询结果 |
| Horizontal overflow | `scrollWidth <= innerWidth` 或等价检查 |
| Text overflow | 聚焦区域无截断、遮挡、按钮撑破的证据 |
| Interaction state | 关键控件 hover/focus/disabled/loading/error 中适用状态 |
| DESIGN.md adherence | 若存在 `DESIGN.md`，说明已读取并给出 token / direction 遵守证据；若偏离，说明理由 |
| Reference diff | 有参考图时引用 `/fe-ui-visual-iterate` 差异表 |

禁止把“测试通过”“肉眼看了下”当成 UI verified。缺截图或 overflow 证据时，UI 交付物状态只能是 `partial`。

## 工具化步骤

```
bash scripts/run-verify.sh
```

- 自动探测 package.json / pyproject.toml / Cargo.toml / Makefile / go.mod 等并运行对应 test / lint / typecheck / build
- 输出固定 Markdown 表，agent 直接贴进报告作为 Evidence
- exit code 0=全绿，1=有失败，2=无任何可检测命令（需要手动补）

### Verification: None 强制声明

当出现以下任一情况时，**禁止**在报告里写 "verified pass"：

- `scripts/run-verify.sh` 退出码为 `2`（无任何可探测的 test / lint / build 命令）
- 没有探测到自动化测试入口，且本次也未补 characterization
- 仅靠"看上去对"或"本地手动跑过一次"作为证据

此时必须在报告中显式输出一行：

```
verification: none -- structural gap
```

并把"补可执行验证"列入"待补 / Followups"，不能让缺验证伪装成通过。

## 验证三层级（每条 Deliverable 都必须分别给 L1/L2/L3 证据）

文件 / 函数能找到 ≠ 实现到位。三层级缺一不算 verified：

| 层级 | 含义 | 不充分的反例 |
|---|---|---|
| **L1 Exists** | 目标文件 / 函数 / 路由 / 配置 / 命令在仓库里真实存在 | 只能找到名字但函数体是 `pass` / `TODO` |
| **L2 Substantive** | 实现非空、有真实逻辑、不是 stub / placeholder / 抛 NotImplemented | 函数返回硬编码常量、永远走 happy path |
| **L3 Wired** | 调用方真的接到了：被路由注册、被前端引用、被 CLI 暴露、CI 真的会跑 | 实现存在但没人调用，孤岛代码 |

每条 must-have 必须分别提供：

- L1 证据：`Grep` / `Glob` / `LS` 命中（路径 + 行号）
- L2 证据：函数体片段、关键分支或具体行为说明
- L3 证据：调用点、注册位置、入口绑定（路径 + 行号）

任意层级缺证据 → 该条交付物状态为 `partial`，不能算 verified pass。

## 输出格式

完成报告必须包含以下固定结构：

```markdown
## 验证结果

### Deliverables（三层级，缺一不可）
| # | 交付物 | L1 Exists | L2 Substantive | L3 Wired | 状态 |
|---|--------|-----------|----------------|----------|------|
| 1 | <用户要求 1> | path:line | 行为/逻辑片段 | 调用点 path:line | verified / partial |
| 2 | <用户要求 2> | ... | ... | ... | ... |

### 自动验证（scripts/run-verify.sh）
| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| tests | `...` | pass (Ns) | N passed |
| lint  | `...` | pass | ... |

（若 exit=2 / 未探测到测试命令 / 无 characterization：在此节末尾追加 `verification: none -- structural gap`）

### UI 视觉验证（仅 UI 任务）
| Check | Result | Evidence |
|-------|--------|----------|
| viewport | pass/partial | `390x844`, `1280x900` |
| screenshot | pass/partial | `/tmp/.../page.png` |
| horizontal overflow | pass/partial | `scrollWidth <= innerWidth` |
| text overflow | pass/partial | selector / screenshot region |
| interaction states | pass/partial | selector / screenshot / snapshot |
| DESIGN.md adherence | pass/partial | `DESIGN.md` path + token/direction evidence |

### 结构性评估
- 影响面: ...
- 护栏是否足够: yes / no（理由）
- 是否需要 `/think-quality`: yes / no
```

### Long-loop 每轮验证（仅 long-loop 任务）

当交付物来自 `.long-loop/` 工作流时，额外输出：

```markdown
### Long-loop 轮次验证
| Iteration | Plan item | Agent result | Verify | Diff scan | State update | Verdict |
|---|---|---|---|---|---|---|
| 1 | ... | pass/fail | pass/fail | pass/fail | pass/fail | continue/stop |

### Stop check
- [ ] 未超过 max_iterations / max_minutes
- [ ] `.long-loop/progress.md` 已更新
- [ ] `.long-loop/state.json` 已更新
- [ ] 未触发远端副作用
```

## 规则

- 没有跑过验证命令，不能声称完成
- 测试/构建通过 ≠ 用户可感知行为已经成立；交付物必须单独验收
- "应该没问题"/"改动很小不需要验证" = 不接受
- 验证失败 → 修复 → 重新验证，直到通过

## Anti-Rationalization Guard

声称"已验证"前常见的"放行借口"，命中即拒绝标 verified pass：

| 借口 | 反驳 |
|---|---|
| "本地手测过了" | 必须在仓库测试套件里跑通；本地一次性手测不算证据 |
| "测试改了但意图不变" | 测试改写需独立 review，不能既当被验证对象又当验证者 |
| "没探测到测试命令但能编译" | 编译 ≠ 验证；走 `verification: none -- structural gap` 流程 |
| "之前同类改过没问题" | 每次必须重跑当前 diff，不能继承上次结论 |

## Gotchas

- 测试通过不等于交付物成立；用户要求必须逐条验收
- 没有证据截图、命令输出或可复现步骤，就不要写“已完成”
- 文档/配置类改动也要验证链接、路径、命令和引用是否仍然成立
- 若验证发现范围外回归，必须回退到对应 skill 修复，而不是在总结里弱化问题

## 关联技能

- 需要补结构性判断 → `/think-quality`
- 验证通过 → 可进入 `/guard-ship` 交付
- 验证失败 → 回到对应 skill 修复（`/dev-debug`、`/dev-tdd`）

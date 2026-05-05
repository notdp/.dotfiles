# Debug 调研

调研对象：Superpowers (systematic-debugging + verification-before-completion)、GSD (debug + forensics + verifier)、mattpocock/skills (`diagnose`)。CCPM 无调试相关内容。

## 各项目方案摘要

### Superpowers — 4 阶段根因分析

严格的科学方法：观察 → 假设 → 预测 → 测试 → 结论。4 阶段流程：
1. 理解（复现 bug，精确描述症状 vs 预期）
2. 分析（从错误点回溯，列出假设并排序）
3. 修复（先写失败测试 → 最小修复 → 验证）
4. 验证（原始 bug、回归、边界用例全部验证）

核心原则：不猜测，不撒网式修复（shotgun debugging）。每个假设必须有证据支撑或排除。Reference 文件提供 root-cause-tracing、defense-in-depth、condition-based-waiting 等技术细节。

### GSD — 子 agent 隔离调试

debug 命令派发专门的 debugger agent（42K 字符定义），在独立 context window 中调试，避免污染主 session。流程：
1. 精确复现 → 最小复现
2. 分层假设生成（语法/逻辑/集成/环境/并发/数据）
3. 二分法定位（git bisect / 代码注释 / 日志注入）
4. 根因确认 → 修复 → 回归验证

独特点：失败后自动触发 forensics（事后取证），分析 git 历史和文件状态。HANDOFF.json 支持跨 session 暂停/恢复调试。

### mattpocock/skills — 反馈环优先

`diagnose` 把调试核心定义为先构造 agent 可反复运行的 pass/fail signal。它给出反馈环优先级：失败测试、HTTP 脚本、CLI fixture、headless browser、trace replay、throwaway harness、property / fuzz loop、bisection harness、differential loop、HITL 脚本。

独特点：

- 反馈环本身是调试产品：要更快、更准、更稳定。
- 非确定性 bug 不追求一次干净复现，先提高复现率。
- 临时 debug log 必须带唯一 prefix，收尾时 grep 清理。
- 性能问题先 baseline / profiler / query plan，再修复。

## 共识

1. **根因优先** — 不做表面修复，找到真正原因
2. **科学方法** — 假设→预测→测试→结论，不撒网
3. **先复现后修复** — 不能复现的 bug 不要尝试修
4. **证据驱动** — 每个假设必须有证据支撑或排除
5. **先测试后修复** — 先写捕获 bug 的失败测试
6. **最小修复** — 只改必要的，不顺手重构
7. **回归验证** — 修复后验证原始 bug + 周边功能
8. **反馈环优先** — 没有可重复运行的信号，就没有可靠调试
9. **临时插桩可清理** — debug log 必须有唯一 prefix，收尾能一次性搜出

## 已采纳到 canonical skill

| 决策 | 状态 | 落点 |
|------|------|------|
| 内联调试为默认，复杂 bug 再派 researcher/worker | 已采纳 | `skills/dev-debug/SKILL.md` |
| 连续失败升级到 `/think-unstuck` | 已采纳 | `skills/dev-debug/SKILL.md` |
| bug 修复先写失败测试 | 已采纳 | `skills/dev-debug/SKILL.md`、`skills/dev-tdd/SKILL.md` |
| 反馈环作为 Phase 1 硬门控 | 已采纳 | `skills/dev-debug/SKILL.md` |
| debug prefix + 收尾清理 | 已采纳 | `skills/dev-debug/SKILL.md`、`skills/guard-diff-scan/SKILL.md` |

## 仍待决策

### 1. 调试架构

| 方案 | 来源 | 取舍 |
|------|------|------|
| 内联（在当前 session 中调试） | Superpowers / mattpocock | 已作为默认 |
| 子 agent 隔离（独立 context window） | GSD | 已作为复杂 bug 升级路径 |

### 2. 状态持久化

| 方案 | 来源 | 取舍 |
|------|------|------|
| 无持久化，单 session 内完成 | Superpowers / mattpocock | 已作为默认 |
| HANDOFF.json 跨 session 暂停/恢复 | GSD | 暂不采纳，除非后续出现跨 session 调试需求 |

### 3. 事后取证

GSD 有 forensics（git 历史分析+状态取证），Superpowers 和 mattpocock/skills 没有。当前暂不新增独立 skill，作为复杂 bug 的可选证据收集。

### 4. 调试日志注入

采用定向插桩，不做“自动日志撒网”。任何临时日志必须带唯一 prefix，并在收尾阶段清理。

### 5. 假设数量限制

已采用 3-5 个假设并排序，避免单假设锚定和过度发散。

## 精华提取

| 技巧 | 来源 | 说明 |
|------|------|------|
| 假设分层 | GSD | 语法/逻辑/集成/环境/并发/数据，按层排序减少搜索空间 |
| 二分法定位 | GSD | git bisect + 代码注释 + 日志注入三种手段 |
| 不做撒网修复 | Superpowers | "try this and see if it works" = 禁止 |
| 最小复现 | 两者 | 从完整场景逐步剥离到最小触发条件 |
| Red Flags | Superpowers | "改了好几个地方但不确定哪个修好了" = 停下来，回退 |
| defense-in-depth | Superpowers | 多层防御而非单点修复 |
| condition-based-waiting | Superpowers | 用条件等待替代 sleep/延时 |
| 反馈环优先级 | mattpocock/skills | test / HTTP / CLI / browser / trace / harness / fuzz / bisect / differential / HITL |
| debug prefix | mattpocock/skills | 临时日志统一 `[DEBUG-...]` 前缀，收尾 grep 清理 |

---
name: readable-rewrite
description: 当存在概念散落、横向铺表、抽象描述代替具体机制的技术内容需要重写时使用；走 writer 出稿 + critic 子任务审稿的 3 轮迭代，输出对象清单、槽位表、重写正文与改动轨迹（与 readable-metrics 的区别是它聚焦数字解读，本 skill 聚焦结构化对象重写）。
argument-hint: <原文路径 或 原文片段>
---

# Readable Rewrite

## Role

把"看起来有结构、读完抓不住"的技术内容重写成"一次讲透一个对象"。核心不是改措辞，是用 writer-critic 迭代外审打破自查盲区。

## Why this skill exists

AI 默认写作有两个失效点：

- **结构盲点**：横向"对象 × 维度"配置表看起来紧凑，读者要理解一个对象必须扫多列再心理重组
- **自查盲点**：让 agent 自己扫 AI 味、自查槽位完整性，准确率低，模型的生成偏差强于读到的原则

本 skill 通过强制 writer 走结构模板 + 派发独立 critic 子任务的方式，把"读者一次只加载一个对象"做成可验证的流程。

## SSOT

- `skills/readable-rewrite/references/rubric.md`：writer 和 critic 共享的评分标准（4 维度、P0/P1/P2、Hard rules、5 槽位）
- `skills/readable-rewrite/references/critic-prompt.md`：critic 子任务的固定 prompt 和输出 schema

任何时候 writer 或 critic 的判断有歧义，回到 rubric.md 裁决。

## 核心流程

### Phase 0：Writer 出 v1

按 `references/rubric.md` 走：

1. 抽对象清单（脚本 / 模块 / 概念 / 规则 / 事件 / hook）
2. 每对象填 5 槽位（是什么 / 机制 / 输入输出 / 触发时机 / 边界属性）
3. 完整性检查：空槽位标 `[待澄清]`，不编造
4. 依赖排序：前置概念在前
5. 纵向重写：一对象一节，节内按槽位顺序展开

**短文本捷径**：原文 < 200 字 或 对象数 <= 2 时跳过 Phase 1-3，单趟出稿即返回。

### Phase 1..3：迭代外审（默认 max 3，硬上限 5）

每轮做三件事：

#### 1. 派发 critic 子任务

派发只读 critic 子任务，传入：

- `original`：原文全文
- `current`：当前版本 vN
- `rubric`：`skills/readable-rewrite/references/rubric.md` 内容
- `critic-prompt`：`skills/readable-rewrite/references/critic-prompt.md` 内容
- `last_findings`：上一轮 findings ID 列表（首轮传空）

期待输出：固定 findings 表（schema 见 critic-prompt.md）。

平台映射：

- 有子任务能力的平台 → 派发独立 sub-agent
- 无子任务能力的平台 → 见 Fallback 节

#### 2. 停止判定

满足任一条件即停，进 Finalize：

- findings 表为空（P0 + P1 + P2 = 0）
- N >= max（默认 3）
- 震荡：本轮 findings ID 集合与上轮 Jaccard 相似度 >= 0.8

Jaccard 算法：`|本轮 ∩ 上轮| / |本轮 ∪ 上轮|`。agent 用脑算即可，数据量小（通常 < 20 个 ID）。

#### 3. Writer 改 v(N+1)

输入：v(N) 全文 + 本轮 findings 表

动作（按优先级从高到低）：

- **P0 全改**：fidelity 类一律改；structure / slot 的 P0 必须改
- **P1 尽量改**：能改不引入新问题就改
- **P2 判断保留**：ai-flavor 类如果改会损精度可保留，但必须在 changelog 备注理由

输出本轮 changelog：

```markdown
## Changelog (round N+1)

| Finding ID | Action | Diff summary |
|------------|--------|--------------|
| <id> | fixed / kept-with-note / partial | 一句话 |
```

### Finalize

最终输出按 Output Format 节组装。

## Fallback（无子任务平台）

平台不支持隔离子任务时，降级流程：

1. orchestrator 在主上下文里加载 `references/critic-prompt.md` 和 `references/rubric.md` 全文
2. 切换为 critic 角色：用一段隔离指令"现在严格按 critic-prompt 输出 findings 表，不重写、不输出散文"
3. 输出 findings 表后切回 writer 角色继续迭代
4. 在最终输出元信息标 `mode: fallback (no isolated sub-agent)`

已知代价：

- 主 context 被 rubric / critic-prompt 占用
- critic 与 writer 共享同一份生成偏差，AI 味漏报率上升
- fidelity 检查相对可靠（基于原文对比），不受 fallback 太大影响

## 跨 agent 派发约定

- 派发描述统一用"派发只读 critic 子任务，输入 original + current + critic-prompt + rubric，期待 findings 表"
- 不写平台专属语法
- 工具引用使用 Read / Edit 等通用名
- 路径相对仓库根

## Output Format

```markdown
## Final Version

<vFinal 全文>

## 对象清单

| # | 对象 | 类型 | 槽位完整性 |
|---|------|------|-----------|
| 1 | <name> | script / concept / rule / event | full / partial / pending |

## 改动轨迹

### Round 1 → 2
<changelog 表>

### Round 2 → 3
<changelog 表>

## 残留 findings（如有）

<critic 最后一轮 findings 表 + Round summary>

## [待澄清]

- <用户需要补的信息 1>
- <用户需要补的信息 2>

## 元信息

- Rounds run: N
- Stop reason: empty-findings / max-rounds / oscillation
- Mode: isolated-subagent / fallback
- Short-text shortcut applied: yes / no
```

## Evidence

- 对象清单非空，每对象 5 槽位完整性显式标记（full / partial / pending）
- 重写正文按对象分节，无跨对象横向矩阵作主结构
- 改动轨迹覆盖所有迭代轮（短文本捷径时显式标 N=0）
- critic 最后一轮 findings 为空 或 残留已说明

## Stop

- critic findings 为空 → 自然停
- N = max（默认 3，硬上限 5）→ 强制停，进残留报告模式
- 震荡（Jaccard >= 0.8）→ 停，避免反复挑刺
- 用户只要诊断不要重写 → 跑 Phase 0 第 1-3 步即停

## Risk

- 迭代不收敛：rubric 模糊导致 critic 反复挑刺 → max + 震荡保护兜底
- writer / critic 标准漂移：双方读不同版本 → 强制都引用 `references/rubric.md` SSOT
- fidelity 检查依赖原文上下文 → critic 派发必须带 `original`
- 成本：3 轮 × (write + critique) → 短文本捷径 + max 默认 3
- 跨平台失败 → Fallback 节定义的降级路径，输出元信息显式标 mode

## Gotchas

- 纯属性对照表（如"runtime 支持矩阵"）不是横向铺表，是合法辅助。判定见 `rubric.md` 2.1 例外条款。
- 伪代码不是 Python 缩写，是让读者看到判断逻辑、分支、数据流向。
- 短文本捷径不能用来逃避迭代。原文 >= 200 字 且 对象 > 2 时必须走完整流程。
- critic 子任务不能修改 writer 的稿，只能给 findings。
- AI 味自查准确率有限，本 skill 的 ai-flavor 信号只能算启发式。硬扫描脚本是 backlog。
- fallback 模式下漏报 ai-flavor 是已知代价，不要假装能完全等价。

## 关联技能

- `/readable-metrics`：数字解读（基线、变化、影响）
- `/readable-html-artifact`：把 vFinal 转 HTML companion
- `/think-architecture`：架构成文（不是重写既有文）
- `/readable-final-answer`：本 skill 拆分前的旧版；Mode B/C（最终答复体裁、过程播报）后续迁回 `agents/context-capsules/`

# leonxlnx/taste-skill

- 上游仓库: `https://github.com/leonxlnx/taste-skill`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/leonxlnx/taste-skill`
- Source SHA: `06d6028b5c623016c59ce8536f578e5a1127b499`（heads/main），分析日期: 2026-06-25
- 主分类: **前端 UI / 设计系统**（agent skill 形态的设计品味引擎）
- 能力标签: `anti-slop 规则化`, `数值旋钮调参(dial-driven)`, `机械可校验 Pre-Flight checklist`, `brief 推断`, `风格 skill 矩阵`, `image-first 图生码`, `canonical 代码骨架`, `research 驱动 prompt 方法论`
- 一句话总结: 把"前端审美/品味"这种主观能力，拆成一套确定性的 anti-slop（反 AI 套路）prompt——三个数值旋钮 + 几十条带 override 路径的硬禁令 + 可机械计数的 Pre-Flight 检查表 + canonical 代码骨架——让 coding agent 把"好看"当成可执行可校验的合同来产出。

## 核心机制

它的关键转向是 **把"审美"实现为负向工程**：不正向定义"什么是好看"（主观、不可校验），而是穷举"LLM 会犯的统计性默认套路（AI tells）"并逐条点名禁止，每条降维到 hex 色值 / 字体名 / CSS class 这种可机械比对的特征。核心 `taste-skill`（v2，1206 行）用一条三段式管线驱动：

1. **§0 Brief Inference（读空气）**：先读 page kind / vibe 词 / 参考链接 / 受众 / 已有品牌资产 / 隐性约束，输出一行 `Reading this as: <page kind> for <audience>, with a <vibe> language`。歧义时只问一个问题，不瞎猜也不多问。
2. **§1 三旋钮**：`DESIGN_VARIANCE` / `MOTION_INTENSITY` / `VISUAL_DENSITY`（基线 8/6/4，各 1–10），由 Design Read 经"信号→旋钮值"映射表 + use-case preset 表**自动反推**，对话式 override 而非改文件；旋钮再 gate 后续每条布局/动效/密度决策。
3. **§2 Brief→设计系统映射 + §4/§9 反套路工程**：brief 命中 Material/Fluent/Carbon/Polaris/GOV.UK 等就装官方包（诚实规则：不手搓其 CSS）；只是个美学风格就用 web 标准并在注释标注"借鉴非官方"。然后逐条纠偏排版/配色/布局/动效，§9 列 AI tells 硬禁。
4. **§14 Final Pre-Flight Check**：60+ 条必过 checkbox（含机械计数项），开头标 `THIS IS NOT OPTIONAL`，任一不能诚实打勾即判未完成必须返工。

围绕核心又长出一圈正交分工的子 skill（风格档案 / 图生成 / 审计 / 输出纪律），并用 `research/laziness` 给"为什么 LLM 会偷懒/产生套路"提供方法论背书。

## 关键设计

- **旋钮把主观调参数值化 + 自动反推**：[事实] §1 三旋钮基线 8/6/4，§1.A/§1.B 两张表从 brief 自动反推；§7 给每旋钮分 1-3/4-7/8-10 三档具体 CSS 落地定义。让一个 skill 覆盖从极简到 Awwwards 的连续光谱。
- **每条规则 contextual + 强制 override 路径**：[事实] SKILL.md:9 `Every rule below is contextual. None of it fires automatically`；几乎每条禁令（serif/Inter/AI 紫/centered hero/beige-brass 色族）都配 `Override: 当 X 显式成立时允许`——这是它区别于一刀切黑名单的安全阀。
- **禁令做成可机械检测**：[事实] §4.7 EYEBROW 要求 `count instances of uppercase tracking … > ceil(sectionCount/3) 则 fails`；§4.2 把禁用调色板精确到 hex 族（#f5f1ea/#f7f5f1/#b08947/#b6553a…），把"品味"降维成可数可比对的字符串特征，还带"上个同类项目用过此族则本次必须换族"的轮换规则。
- **binary-ban 措辞工程**：[事实] §9.G 把 em-dash 定为"#1 最常被违反的 tell"，明写历史上 `use sparingly` 被 agent 无视，故改成二元 `zero em-dashes，出现一个就 Pre-Flight Fail`——把会被钻空子的软约束改成 0/1 硬约束。
- **诚实规则**：[事实] §2.A 命中官方系统就装官方包不手搓 CSS、不导入 token 又改 90%；§2.B Apple Liquid Glass 明确"无官方 `liquid-glass.css`，标注为 approximation"——对治 agent 编造不存在依赖/API。
- **v1→v2 演进可追溯**：[事实] CHANGELOG 记录 v1"方向正确但易被略读"，production testing 暴露同样的 tell 反复出现（em-dash、section-number eyebrow、fake screenshot、坏掉的 GSAP trigger），v2 用 hard rules + canonical code skeletons + pre-flight checklist 补缺口；v1（226 行）保留可 pin 回退。

## 资产盘点

| 资产 | 说明 | 规模 |
|---|---|---|
| `skills/taste-skill/SKILL.md` | 核心 anti-slop 引擎 v2：brief 推断→三旋钮→设计系统映射→反套路→AI tells 硬禁→GSAP 代码骨架→redesign 协议→Pre-Flight Check | 1206 行 |
| `skills/taste-skill-v1/SKILL.md` | 旧版，对比看"方向→硬规则化"演进，可 pin 回退 | 226 行 |
| `skills/{brutalist,minimalist,soft}-skill/` | 命名风格档案（Swiss/CRT、Notion/Linear、agency 软质感），各含精确字体/hex/CSS 滤镜 | 85–98 行 |
| `skills/redesign-skill/SKILL.md` | 存量审计先行（scan→diagnose→fix），按风险优先级，不重写只改进 | 178 行 |
| `skills/gpt-tasteskill/SKILL.md` | GPT/Codex 变体：模拟 Python RNG 确定性种子强制 variance | 74 行 |
| `skills/image-to-code-skill/SKILL.md` | 图生码：强制 image-first 三步序，图为 source of truth | 1228 行 |
| `skills/imagegen-frontend-{web,mobile}/` | 只出参考图不出码，硬规则"每 section 一张独立图" | 987 / 1465 行 |
| `skills/brandkit/SKILL.md` | 品牌系统图生成，先推 brand strategy 再生成 identity board | 798 行 |
| `skills/output-skill/SKILL.md` | 反偷懒/反截断：禁 placeholder、scope 计数、`[PAUSED—X of Y]` 续接 | 49 行 |
| `research/laziness/` | 方法论背书：LLM 偷懒/截断的成因（RLHF/训练数据偏置/输出限额）+ 补救 + 实验引用 | ~9 个 md |
| `CHANGELOG.md` / `.claude-plugin/` | v1→v2 演进 rationale；plugin marketplace 分发机制 | — |

## 与本仓库映射 + 吸收裁决

详细裁决见 [`docs/refs-update-absorption-2026-06-25.md`](../../refs-update-absorption-2026-06-25.md)。摘要：

**已覆盖（不重复吸收）**：反 AI-slop 负向工程立场（`fe-ui-design/refs/anti-ai-slop.md` + `scan_ui_artifact.py` + `fe-audit`）、DESIGN.md 视觉契约 SSOT（`design-md` + `fe-ui-design-system`）、"完成前必过 checkbox 闸门"（`guard-verify`/`guard-check`）、image-first 迭代（`fe-ui-visual-iterate`）、em-dash 禁用（文字域 `write-voice`）。

**吸收候选**：

| 候选 | classify | 落点 | Level | 裁决 |
|---|---|---|---:|---|
| binary-ban + contextual-override 配对成 prompt 写作模式 | method | `skill-patterns.md` | L2 | **absorb** |
| 规则带 production 证据来由的演进治理纪律 | docs | `skill-authoring.md` | L1 | **absorb** |
| 3 条确定性 anti-tell 正则（em-dash / eyebrow 候选 / 米色-黄铜 hex 族） | script | `scan_ui_artifact.py` | L3 | **absorb**（候选级，不进 gating） |
| `research/laziness` 成因分析 | docs | 本文件 observe | L0 | observe（实验引用 **[未验证]**，不当事实） |
| 风格 skill 矩阵 / imagegen / brandkit | runtime | — | — | **reject**（平行入口 + 图生成产品形态，把审美冻结成字典） |
| gpt-taste 的 RNG 强制 variance | method | — | — | **reject**（把"随机"误当"发散"，对 `think-ideate` 是错误范式） |
| 禁用色族反重复轮换 | method | — | — | research-later（需真实跨任务 memory 状态，否则是伪能力） |

## Premise collapse 与风险

- **主观审美硬规则化是头号风险**：风格 skill 的固定 hex/字体清单、禁用色族本质是作者一家 taste 默认而非普适真理。本仓库刻意不内置风格字典（`fe-ui-design/refs` 是原则非配方），照搬会倒退。凡涉审美常量只能"默认值 + 可被设计契约覆盖"，绝不进 gating。
- **binary-ban 不可滥用**：仅对可枚举、可机械检测、0 容忍的项做二元化；密度/节奏/对比强度等连续光谱 taste 维度强行 0/1 会制造新死板，必须保留 contextual + override 安全阀。
- **[未验证]** `research/laziness` 引用的激励实验（如 "$200 tip +45% 质量"）在本仓库无可核验原始出处，不得当事实写进任何 skill 或外推为规则依据。
- 许可：MIT（Copyright 2026 Leonxlnx）。吸收 anti-tell 正则为 clean-room 重写，非搬运。

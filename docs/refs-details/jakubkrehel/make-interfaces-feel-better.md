# jakubkrehel/make-interfaces-feel-better

- 上游仓库: `https://github.com/jakubkrehel/make-interfaces-feel-better`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/jakubkrehel/make-interfaces-feel-better`
- Source SHA: `384562064fcdd99778fcbafd8729626fe6aab02f`（heads/main），分析日期: 2026-06-25
- 主分类: **前端 UI / 设计工程**（design engineering polish）
- 能力标签: `UI 微交互规则库`, `progressive disclosure 组织`, `动效/transition 规范`, `排版渲染细节`, `surface/阴影/圆角`, `review 输出格式契约`, `精确数值阈值`, `框架自适应`
- 一句话总结: 一个单 skill，把"界面手感(feel)"拆成排版/表面/动画/性能四维，用 SKILL.md 路由表 + 分文件 progressive disclosure 组织 16 条带精确硬阈值的可执行微交互规则，并把 review 输出体裁（Before/After 表格）也写成硬约束。

## 核心机制

它把抽象的"界面手感"操作化为 **16 条带精确数值的硬规则**，覆盖 Typography / Surfaces / Animations / Performance 四维。`SKILL.md`（148 行）作为单一入口：顶部 `Quick Reference` 路由表把每个维度映射到一个分主题 `.md`（主文件给原则摘要 + 何时跳读哪个文件，深度代码下沉分文件），中部给 16 条 Core Principles 浓缩版 + Common Mistakes 速查 + Review Checklist，底部强制规定 review 输出体裁。

核心特征是 **用"魔法常量 + 显式禁令"剥夺 agent 的自由发挥空间**来换取一致手感：
- scale on press 永远 `0.96`、`never < 0.95`；
- 图标动画 scale `0.25→1`（`never 0.5/0.6`）、blur `4px→0`、spring `bounce: 0`；
- enter stagger `~100ms`、标题逐词 `~80ms`；hit area `40×40px`；
- image outline 必须纯黑 `rgba(0,0,0,0.1)` / 纯白 `rgba(255,255,255,0.1)`，禁任何 tinted neutral（slate/zinc），否则"reads as dirt on the image edge"。

## 关键设计

- **路由表 + 分文件 progressive disclosure**：[事实] SKILL.md:10-18 用 Quick Reference 表把四维映射到四个 `.md` 并注明各自 When to Use；主文件只放 16 条摘要，大段对照代码下沉分文件（主文件 148 行，分文件 88–379 行），按需加载不一次灌入上下文。
- **把"手感"操作化为带硬阈值的常量**：[事实] 规则不给区间而给精确不可偏离值并显式禁止偏离（scale 0.96 / never <0.95、bounce 必须 0）——把主观审美降维成 agent 可确定性执行的常量。
- **框架自适应分支**：[事实] animations.md:255-264 给决策表 + `Check package.json for motion or framer-motion`：有则用 Motion，无则用 CSS cross-fade，`don't add a dependency just for icon transitions`。两套等价实现按项目现状选——体现"适配项目现状不强引依赖"的工程克制。
- **规则带边界与反例后果（非教条）**：[事实] concentric radius 在 `padding>24px` 时改"treat as separate surfaces"不强套公式（surfaces.md:13）；`text-wrap: balance` 仅 ≤6 行（Chromium）/≤10 行（Firefox）有效否则被静默忽略（typography.md:9）；keyframe 中断会 "snaps or restarts—feels broken"（animations.md）。为规则写"何时不适用 + 违反会怎样"。
- **强制 review 输出体裁（Before/After 表格契约）**：[事实] SKILL.md:100-124 规定 review 必须是 markdown 表格、Before/After 两列、按原则分组、每行单 diff、`Include every change—not just a subset`、无改动则 `omit that table entirely—empty tables add noise`。把"怎么汇报"也治理。
- **三层冗余互证闭环**：[事实] Core Principles（19-83）→ Common Mistakes 速查（85-98）→ Review Checklist 复选框（126-141），同一组规则三种形态分别服务学习/查阅/收尾验证。

## 资产盘点

| 资产 | 说明 | 规模 |
|---|---|---|
| `skills/.../SKILL.md` | 入口：触发词丰富的 frontmatter + 路由表 + 16 条原则 + Common Mistakes + Review 输出契约 + Checklist | 148 行 |
| `.../animations.md` | CSS transition vs keyframe 可中断性、enter split&stagger、subtle exit、icon 动画两套实现、scale on press、`initial={false}` | 379 行 |
| `.../surfaces.md` | concentric radius 公式、optical alignment（图标 -2px / play 三角 +2px）、shadow-instead-of-border、image outline 纯黑白、min hit area | 256 行 |
| `.../typography.md` | text-wrap balance/pretty 适用上限、macOS antialiased、tabular-nums 防数字抖动 + Inter caveat | 135 行 |
| `.../performance.md` | 禁 `transition:all` 改显式属性、`will-change` 仅 transform/opacity/filter 且仅首帧 stutter 时加 | 88 行 |

## 与本仓库映射 + 吸收裁决

详细裁决见 [`docs/refs-update-absorption-2026-06-25.md`](../../refs-update-absorption-2026-06-25.md)。摘要：

**已覆盖（不重复吸收）**：四维知识与 `fe-ui-design/refs/motion.md`+`interaction.md` 大量重叠（transform+opacity only、exponential easing、反 bounce、stagger 上限、will-change、reduced-motion、8 态、44px hit area）；progressive disclosure 路由表与 `fe-ui-design/SKILL.md`（主流程 + 11 个 refs/*.md）同构；确定性 grep 扫 slop 已由 `scan_ui_artifact.py` + `fe-ui-lint-artifact` 覆盖。

**吸收候选**：

| 候选 | classify | 落点 | Level | 裁决 |
|---|---|---|---:|---|
| "审美降维为硬常量 + never-use 反向禁令"的规则书写模式 | method | `skill-patterns.md` | L2 | **absorb**（必带 premise-collapse 边界） |
| 为规则补"适用边界 + 违反后果机理"两栏 | docs | `skill-authoring.md` | L2 | **absorb** |
| 4 条真增量微规则（concentric radius / optical -2px / tabular-nums / image outline 纯黑白） | docs | `fe-ui-design/refs/spatial.md`+`typography.md` | L2 | observe（**需先逐行核对是否已覆盖**） |
| 框架自适应（探测 package.json 选实现） | method | `fe-ui-design` | L1 | observe |
| review 输出体裁内嵌 skill 契约 | method | — | L1 | observe（`fe-ui-critique` 已有输出契约） |
| press-scale 0.96 / transition:all 探针 | script | `scan_ui_artifact.py` | L3 | research-later（transition:all 较稳，scale 0.96 误报高） |
| 新增独立 `fe-ui-micro-polish` skill | runtime | — | L4 | **reject**（与 `fe-ui-design` 高度重叠，违反"不扩 skill 数量"） |

## Premise collapse 与风险

- **scale=0.96 / bounce=0 / outline 纯黑白是作者一家 taste 默认，不是普适真理**：品牌语气明确要轻快物理反馈时 `bounce>0` 合理（`fe-ui-design/refs/motion.md` 本身允许）。直接把常量写进本仓库规则正文会与"装饰服务信息层级、按任务判断"原则冲突，把可推理判据退化成教条。只能以"默认值 + 可被设计契约覆盖"形式登记，绝不进 gating。
- **[未验证]** 4 条"真增量"微规则的判断尚未与 `fe-ui-design/refs/spatial.md`+`typography.md` 逐行比对，落地前必须核对避免重复吸收。
- 许可：MIT。

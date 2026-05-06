# DESIGN.md 美学工作流调研

调研对象：

- `refs/google-labs-code/design.md`，来源 `https://github.com/google-labs-code/design.md`，快照 commit `1d002db4db180bf3cf5e69b0cf9d776c9a823354`。
- `refs/voltagent/awesome-design-md`，来源 `https://github.com/voltagent/awesome-design-md`，快照 commit `da068674dbe2f7073059d0c38c0ac60aa83c1660`。

## 结论

[确认] `google-labs-code/design.md` 把 DESIGN.md 定义为面向 coding agent 的视觉 identity 文件。核心结构是：

1. YAML front matter：机器可读 design tokens。
2. Markdown body：人类可读的设计 rationale 和应用规则。

[确认] `VoltAgent/awesome-design-md` 是 DESIGN.md 样本库。README 显示它收集了 71 个来自公开网站的 DESIGN.md，覆盖 AI、开发工具、SaaS、设计工具、金融、零售、媒体、汽车等类别。

[推断] 对本仓库最有价值的不是新增一套 UI runtime，而是把 UI 任务固定成：

```text
选择风格参考 -> 建立 DESIGN.md contract -> 实现 -> 截图 -> critique -> 小步迭代 -> verify
```

这样解决的是“agent 凭默认审美自由发挥”的问题，而不是靠更多形容词让模型临场变会设计。

## 两个仓库分别提供什么

| 仓库 | 价值 | 不应怎么用 |
|---|---|---|
| `google-labs-code/design.md` | 格式规范、section 顺序、token schema、CLI lint/diff/export | 不应在未验证 npm 可用时把 CLI 设成硬门禁 |
| `VoltAgent/awesome-design-md` | 大量品牌风格样本，适合帮助选择 visual direction | 不应直接复制某品牌 identity 到自己的产品 |

## DESIGN.md 格式要点

[确认] 官方规范的关键点：

- DESIGN.md 是 plain text。
- YAML front matter 可包含 `colors`、`typography`、`rounded`、`spacing`、`components`。
- token reference 使用 `{path.to.token}` 语法。
- Markdown sections 建议顺序：
  1. `Overview`
  2. `Colors`
  3. `Typography`
  4. `Layout`
  5. `Elevation & Depth`
  6. `Shapes`
  7. `Components`
  8. `Do's and Don'ts`
- tokens 是规范值，prose 提供应用语境。

### 最小 contract 示例

```md
---
version: alpha
name: Product Utility
colors:
  background: "#f7f5f0"
  surface: "#ffffff"
  foreground: "#1a1c1e"
  muted: "#6c7278"
  border: "#d8d2c8"
  accent: "#b8422e"
typography:
  display:
    fontFamily: Public Sans
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1.1
  body:
    fontFamily: Public Sans
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: 4px
  md: 8px
spacing:
  sm: 8px
  md: 16px
  lg: 32px
---

## Overview

Tool-first interface for focused daily work. It should feel calm, precise,
and readable under pressure.
```

## awesome-design-md 的正确用法

[确认] 该库提供 ready-to-use DESIGN.md 文件，也在 README 中列出每个样本的风格摘要。

[推断] dotfiles 应把它当作“参考库”，而不是“品牌复制库”。推荐用法：

1. 选择一个主参考：例如 Linear 表达“深色、克制、工程感”。
2. 选择一个反参考：例如禁用 glassmorphism 或过度渐变。
3. 提取 3-5 条可迁移规则：色彩预算、字体层级、spacing 节奏、组件状态、禁用项。
4. 写成项目自己的 DESIGN.md。

## 当前 dotfiles 映射

| 现有能力 | 当前作用 | DESIGN.md 增强方向 |
|---|---|---|
| `fe-ui-design-system` | 生成轻量设计 contract | 输出真实 DESIGN.md 结构 |
| `fe-ui-design` | UI 实现前的设计规则 | 开工前先读取或创建 DESIGN.md |
| `fe-ui-critique` | 诊断 UI 质量 | 增加 contract adherence 检查 |
| `fe-ui-visual-iterate` | 截图迭代 | 差异表增加 token adherence 和 direction fit |
| `fe-ui-lint-artifact` | 扫 AI slop 和硬编码问题 | 可补 DESIGN.md token drift 扫描 |
| `guard-verify` | 交付前验证 | UI 任务补 DESIGN.md 读取与遵守证据 |

## 建议吸收项

### 修改增强

| 文件 | 建议 |
|---|---|
| `skills/fe-ui-design-system/SKILL.md` | 输出格式升级为 YAML front matter + Markdown sections |
| `skills/fe-ui-design/SKILL.md` | UI 任务先查项目 `DESIGN.md`，没有则生成临时 contract |
| `skills/fe-ui-critique/SKILL.md` | Findings 增加 `Contract` 列，检查 token 和 rationale 偏离 |
| `skills/fe-ui-visual-iterate/SKILL.md` | Diff 表增加 DESIGN.md adherence 与 direction fit |
| `skills/guard-verify/SKILL.md` | UI 交付证据增加 DESIGN.md 读取、遵守或偏离说明 |
| `skills/think-plan/SKILL.md` | UI plan 中明确 DESIGN.md 来源 |

### 新增

| 文件 | 作用 |
|---|---|
| `commands/design-md.md` | 作为低认知负担入口，说明如何建立、使用、诊断和验证 DESIGN.md |
| `docs/software-engineering-research/design-md-aesthetic-workflow.md` | 保存本次调研与吸收策略 |

### 暂不建议

| 方案 | 原因 |
|---|---|
| 默认安装 `@google/design.md` | npm registry、环境和包版本需要另行验证 |
| 把 DESIGN.md 写入全局 `AGENTS.md` | 会增加全局上下文负担，违反本仓库分层原则 |
| 默认从 awesome-design-md 复制品牌样本 | 容易变成仿站，而不是建立自己的视觉系统 |

## 个人设计美学工作流

```text
1. Brief
   写清页面类型、受众、使用压力、不能做什么。

2. Reference
   从 awesome-design-md 选主参考和反参考。

3. Contract
   写 DESIGN.md。tokens 定数值，prose 定为什么。

4. Build
   实现前读取 DESIGN.md。颜色、字体、间距只从 contract 派生。

5. Capture
   用真实浏览器截图，不用想象评估 UI。

6. Critique
   按 DESIGN.md、CRAP、AI slop、overflow、状态覆盖诊断。

7. Iterate
   每轮只改 1-2 个视觉维度，再复拍。

8. Verify
   提交前给截图、viewport、overflow、contract adherence 证据。
```

## 风险与坑

- [推断] 如果没有截图闭环，DESIGN.md 只是更体面的 prompt，无法阻止实现漂移。
- [推断] 如果 DESIGN.md 写得过长，agent 会只执行最显眼的 token，忽略 prose 中的审美取舍。
- [推断] 如果样本参考来自强品牌，直接复制会带来不合适的品牌暗示。
- [未验证] `@google/design.md` CLI 在当前环境中的 npm 安装和运行情况尚未验证。

## 参考路径

- `refs/google-labs-code/design.md/README.md`
- `refs/google-labs-code/design.md/docs/spec.md`
- `refs/google-labs-code/design.md/examples/atmospheric-glass/DESIGN.md`
- `refs/voltagent/awesome-design-md/README.md`
- `refs/voltagent/awesome-design-md/design-md/linear.app/DESIGN.md`
- `refs/voltagent/awesome-design-md/design-md/vercel/DESIGN.md`

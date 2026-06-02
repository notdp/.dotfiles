---
name: fe-ui-visual-iterate
description: 当需要对照参考图反复迭代 UI 视觉效果、或持续对比当前界面与目标样式差异时使用；产出截图证据与固定差异表，驱动到视觉收敛。
argument-hint: <目标页面 URL|组件名|参考图路径>
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*), Bash(scripts/ui-visual-capture.sh:*)
---

# UI Visual Iterate

对照参考图反复调 UI。每轮结束前用截图 + 固定差异表决定继续、停止、记录取舍或请求用户确认。

## 证据门

- **编辑前需要真实页面 Capture**：当前页面状态来自 `ui-visual-capture.sh` 或显式 `agent-browser open ... && agent-browser screenshot ...`；用户给的参考图只作为目标，不作为当前页面证据。
- **Capture 证据可追溯**：每轮报告贴出实际执行的命令、截图路径、DOM snapshot 路径；命令失败时，下一步是修 Capture 链路或报告 blocker。
- **Change 后进入 Re-capture 状态**：凡是改了 UI 文件，下一步重新打开页面并截图；Re-capture + 新差异表齐备后，才进入总结、验证或交付。
- **停止由差异表决定**：差异表还有 `偏/差异大/未通过` 时，下一步是继续、说明 blocker、记录取舍或等待用户确认。

## 核心循环

为什么这样循环：视觉判断最容易被记忆和主观感觉污染。Declare 先固定目标和变量，Capture / Diff 让差异可观察，Change 小步修改，Re-capture 防止凭印象收尾，Decide 用差异表决定继续、停止或记录取舍。

```
Declare → Capture → Diff → Change → Re-capture → Decide
```

默认小步循环：一轮只动 1-2 个维度，不把所有差异一次全改，避免改完不知道谁在起作用。是否进入下一轮由差异表、任务目标、成本和 blocker 决定，不把循环写成无条件脚本。

## 1. Declare（前置声明）

动手前用下表先把目标锁定：

| 字段 | 示例 | 说明 |
|---|---|---|
| 目标 URL | `https://tagent.ordo.global/campaign/xxx` | 要调的页面 |
| 组件/区域 | 表头下拉 / 侧边栏 / 某 modal | 本轮聚焦范围，其它不动 |
| 参考图 | `/Users/.../reference.png` | 用户给的样式目标 |
| DESIGN.md | `DESIGN.md` / 临时 contract / 无 | 本轮视觉契约来源 |
| Viewport | `1280x900` | 固定，避免响应式干扰 |
| 语言/主题 | `zh-CN` / `light` | i18n 和 theme 是视觉差异常见来源 |
| 认证方式 | profile / state / 无 | 参考 `agent-browser` 的 auth 选项 |
| 本轮只动 | 例：面板宽度 + 圆角 | 只挑 1-2 个维度 |

缺任何一项时，通过询问用户或读取代码补齐后再进入循环。

## 2. Capture（自动截图）

先做浏览器能力检查：

```
command -v agent-browser || command -v npx
```

处理规则：

| 状态 | 动作 |
|---|---|
| `agent-browser` 可用 | 直接用 `agent-browser open/screenshot/snapshot` |
| 只有 `npx` 可用 | 用 `npx -y agent-browser ...` 临时执行，并在 Capture 里写清实际命令 |
| `agent-browser` 报缺 Chromium/Chrome | 暂停视觉迭代，提示用户可运行 `agent-browser install`；只有用户明确同意代安装时才执行 |
| `agent-browser` 和 `npx` 都不可用 | 暂停视觉迭代，提示安装命令 |

推荐安装命令：

```
npm i -g agent-browser
agent-browser install
```

全局安装或下载浏览器会修改用户环境/缓存；只有用户明确说"帮我安装"或"可以代安装"时才执行。

优先用 dotfiles helper，并把命令和 stdout Markdown 表原样贴进报告：

```
bash "<dotfiles_root>/scripts/ui-visual-capture.sh" <url> [out_dir] \
  [--viewport 1280x900] [--selector ".dropdown-panel"] [--wait networkidle] \
  [--profile ~/.xxx] [--state ./auth.json]
```

脚本会输出固定 Markdown 表（页面截图 / 元素截图 / DOM snapshot / meta）。把这段表原样贴进本轮报告。
`scripts/ui-visual-capture.sh` 来自 dotfiles；目标项目只提供 URL、状态文件或输出目录。

如果目标是 `localhost` 且脚本不在当前仓库，直接用 `agent-browser` 明确打开和截图：

```
agent-browser open <url> && agent-browser wait --load networkidle
agent-browser screenshot /tmp/visual-qa/<round>/page.png
agent-browser snapshot -i > /tmp/visual-qa/<round>/snapshot.txt
```

报告中说明这是**真实打开页面截图**，并列出截图路径。

## 3. Diff（固定差异表，强制输出）

看参考图 vs 当前截图，逐条填：

```markdown
## 视觉差异（Round N）

| 维度 | 参考图 | 当前 | 差异程度 | 下一步 |
|---|---|---|---|---|
| 面板宽度 | ~320px 宽松 | ~240px 偏窄 | 偏窄 | +padding / +min-width |
| 圆角 | rounded-xl 明显卡片感 | rounded 太硬 | 接近但偏硬 | rounded-xl |
| 阴影 | 柔和大面积 | 细黑线 | 偏生硬 | shadow-lg + 柔化 |
| 内边距 | p-3 宽松 | p-0.5 贴边 | 差异大 | p-3 |
| item 高度/密度 | ~40px | ~28px 太挤 | 偏密 | py-2 + leading |
| hover/checked 态 | 浅灰整行高亮 | 仅文字变色 | 差异大 | 整行 bg-gray-50 |
| 字号/字重 | text-sm 常规 | text-xs 偏小 | 偏小 | text-sm |
| 色彩 | 白底 + 浅灰边 | 白底 + 深灰边 | 边框偏重 | border-gray-200 |
| i18n 文案 | 全中文 | `AE/AR/AZ` 未翻译 | 未通过 | 走 formatter |
| DESIGN.md token adherence | 使用 `colors.accent` / `typography.body` | 硬编码新色 / 新字号 | 未通过 | 回到 token |
| Direction fit | 克制工具型 / editorial / tech-utility | 视觉套路偏 marketing | 偏 | 收敛装饰 |
| 文本溢出 | 长文案自然换行 | 按钮文案撑破 | 未通过 | 改 max-width / wrap |
| 横向滚动 | 无横向滚动 | scrollWidth > innerWidth | 未通过 | 修 grid / min-width |
| 亲密性 | label/value 成组 | label 离 value 太远 | 偏散 | 收紧 group gap |
| 对齐性 | 左边缘一致 | 图标/文字中心线漂移 | 偏 | align-items:center |
| 重复性 | 同类 item 一致 | 第 3 项 padding 不同 | 偏 | 统一 token |
| 对比性 | 主次 CTA 清晰 | secondary 太像 primary | 差异大 | 降低视觉重量 |
| 状态覆盖 | hover/focus/checked 可见 | focus 不明显 | 未通过 | 加 focus-visible |
| 响应式 | mobile/desktop 都稳 | mobile 卡片破版 | 未通过 | 调整断点 |
```

差异程度四档：`接近` / `偏小偏大/偏轻偏重` / `差异大` / `未通过（功能/i18n）`。

UI 任务即使没有参考图，也必须填 CRAP/overflow 行；参考图只决定目标视觉，不取消基础设计质量门槛。

## 4. Change（小步改，只动 1-2 条）

挑表里优先级最高的 1-2 行改代码，**其它维度这一轮不动**。审美准则必须遵守：

- 细节规范（圆角、阴影、间距、色彩、typography、交互状态）见 `/fe-ui-design`
- 反模式（glassmorphism、纯黑白、渐变文字、卡片嵌套卡片）也在 `/fe-ui-design`

## 5. Re-capture（重新截图 + 重新填表）

改完立即再跑一次 `ui-visual-capture.sh`，贴新截图，重填差异表。

用 Re-capture 证据更新判断，而不是用实现意图替代视觉结果。

如果 Re-capture 失败：

1. 暂停继续修改样式
2. 把失败命令、错误信息、当前已改文件列出来
3. 先修复截图链路；修不好才报告 blocker

Re-capture 后如果还有非 `接近` 项，直接开始 `Round N+1`，或记录 blocker、取舍说明、ROI 判断或用户确认。

## 6. 停止条件

停止需要同时满足基础证据门和至少一个业务终止条件。

基础证据门：

- 当前目标 viewport 无横向滚动
- 聚焦区域无文字溢出、遮挡、按钮撑破
- 关键交互控件有 hover/focus/active/disabled 中适用的状态证据
- 存在 DESIGN.md 时，关键 token 与视觉方向已遵守，或明确记录偏离理由

业务终止条件：

- 差异表所有关键维度都是 `接近`
- 亲密性、对齐性、重复性、对比性均为 `接近`，或有明确设计取舍说明
- 用户显式说 OK / 这个状态可以
- 剩余差异是参考图本身的设计取舍、非本轮目标或 ROI 明显不足，转为 backlog 并写清理由

`已经接近参考图` 这个结论只在差异表里的关键项为 `接近`，或剩余项已标注为取舍、blocker、非本轮目标、backlog、用户确认时成立。

停止前检查：

- 已打开目标 URL 并获取当前页面截图
- UI 修改后已有 Re-capture
- lint/test/build 之外已有视觉复拍证据
- 剩余 Round N+1 项有 blocker、取舍说明、ROI 判断或用户确认

## 每轮输出模板（强制）

```markdown
## Round N

### Declare
（前置声明表）

### Capture
- Command: `...`
- Result: pass/fail
（ui-visual-capture.sh 输出的产物表原样贴入，或 agent-browser 截图/snapshot 路径）

### Diff
（视觉差异表）

### Change
- 本轮只改：xxx, yyy
- 文件：`path/to/Component.tsx`（行号）
- 代码变化（核心片段，≤ 20 行）

### Next
- 本轮解决：... (参见 Diff 表)
- 还剩：... (留给 Round N+1)
```

## 与相邻 skill 的边界

| 关注点 | 去哪个 skill |
|---|---|
| 审美原则、反模式、typography/color/spacing 细则 | `/fe-ui-design` |
| 浏览器打开、点击、表单、认证、DOM 取值底层 | `/agent-browser` |
| 交付前验证（lint/test/build） | `/guard-verify` |
| 多文件视觉重构、跨组件影响面 | 先 `/think-context-map` 再回本 skill |
| 连续 2 轮差异表没收敛 | `/think-unstuck` |

本 skill 不做：像素 diff、visual regression baseline、Percy/Chromatic 的替代。那些是 CI 级工具；本 skill 是 inner-loop。

## Gotchas

- 像素 diff 对业务 UI 价值低；差异识别靠 agent 看图 + 固定维度表格
- 不固定 viewport / 语言 / 登录态，每轮截图会有系统性漂移，差异表就不可信
- 一轮改超过 2 个维度，后面很难归因谁在起作用；要克制
- hover/focus/checked 态不主动触发就截不到；`agent-browser` 需要 `hover`/`click` 后再截
- 只对着截图调样式容易漏 i18n、空状态、错误态；差异表最后一行专门留给功能性缺陷
- 对齐参考图 ≠ 好设计；参考图本身可能违反 `/fe-ui-design`，发现冲突要提醒用户
- 认证 state/profile 文件含 session token，只本地用，`.gitignore`
- 参考图可能是 dribbble 风格炫技，拿来当标准前先做一次 AI slop 自检（见 `/fe-ui-design`）

## 关联技能

- 审美细则 → `/fe-ui-design`
- 浏览器底层 → `/agent-browser`
- 迭代收敛后要交付 → `/guard-verify` → `/guard-ship`
- 视觉涉及多组件重构 → `/think-context-map` → `/dev-refactor`
- 连续 2 轮没收敛 → `/think-unstuck`

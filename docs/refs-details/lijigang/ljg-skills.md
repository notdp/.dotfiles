# lijigang/ljg-skills

- 上游仓库：`https://github.com/lijigang/ljg-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/lijigang/ljg-skills`
- 主分类：**技能集合与市场（个人认知 / 内容 / 写作技能集）**
- 能力标签：`Claude Code Skill`, `认知工具`, `内容铸卡`, `论文阅读`, `中文写作`, `org-mode/md 双格式`
- 一句话总结：作者 lijigang 的个人 Claude Code 技能集（22 个 `ljg-*` skill + 2 个工作流），以「认知解剖 / 论文消化 / 内容视觉化 / 中文写作」为主轴，统一走 org-mode（master）与 Markdown（md 分支）双格式分发，并打包为 Claude Code plugin / marketplace。

## 能力概览

- **认知 / 思维类**：`ljg-learn`（概念八维解剖→一句顿悟）、`ljg-think`（追本之箭，纵向钻到本质）、`ljg-rank`（降秩，找领域的独立生成器）、`ljg-plain`（白话引擎，改写到 12 岁可懂）、`ljg-roundtable`（结构化多人辩证圆桌 + ASCII 框架图）。
- **阅读 / 论文类**：`ljg-paper`（面向非学术人的论文核心提取）、`ljg-paper-river`（倒读法递归挖前序论文，最多 5 层）、`ljg-book`（以「问题」为轴的拆书 + ASCII 参考系图）、`ljg-qa`（核心观点抽成 Q-A 链）、`ljg-read`（伴读：信达雅三层翻译 + 结构标注 + 深度提问）。
- **内容视觉化类**：`ljg-card`（内容铸卡，7 种模具：长图 / 信息图 / 多卡 / 视觉笔记 / 漫画 / 白板 / 大字，HTML 模板 + Playwright 截图出 PNG）、`ljg-library`（取景框借书卡 PNG）、`ljg-present`（演讲铸造，高桥流 / 标语流）、`ljg-travel`（城市文化研究文档 + 便携卡片）。
- **写作 / 领域类**：`ljg-writes`（写作引擎，剖开一个观点 1000-1500 字）、`ljg-word`（英语单词深度拆解）、`ljg-invest`（投资分析：是否「秩序创造机器」）、`ljg-relationship`（关系五层结构诊断）。
- **元 / 运维类**：`ljg-skill-map`（扫描已装技能渲染可视化总览）、`ljg-push`（把本地 `~/.claude/skills/ljg-*` 一键同步到 GitHub master + md 双分支）。
- **工作流**：`ljg-paper-flow`（ljg-paper → ljg-library）、`ljg-word-flow`（ljg-word → ljg-card -i），将多 skill 串成一条命令。

## 资产盘点

- 22 个 skill（`skills/ljg-*`，含 2 个 flow 工作流型 skill）。
- 双分发格式：`master` 分支输出 org-mode（`.org`，面向 Emacs/Denote），`md` 分支输出 Markdown（面向 Obsidian/VSCode/Notion），功能等价。
- Claude Code plugin / marketplace 形态：`.claude-plugin/plugin.json` + `marketplace.json`（version 1.17.35），`skills` 指向 `./skills`。
- 安装链路：依赖 `vercel-labs/skills` CLI（`npx skills add lijigang/ljg-skills`），支持 `--all` / `--skill` / `#md` / `-l`。
- 复杂 skill 自带 `references/`（分模具拆 doc）、`assets/`（HTML 模板 + `capture.js` 截图脚本）、`scripts/`。
- `ljg-card` 唯一外部依赖：Node.js + Playwright（`npm install && npx playwright install chromium`）。

## 关键文件

- `README.md` — 技能总表 + 安装方式 + 双格式说明
- `CLAUDE.md` — 仓库结构与 SKILL.md frontmatter 约定（`name` / `description` / `user_invocable` / `version`）
- `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`
- `skills/ljg-card/SKILL.md` + `skills/ljg-card/references/*.md` + `skills/ljg-card/assets/*_template.html` + `assets/capture.js`
- `skills/ljg-learn/SKILL.md`（认知解剖类代表，纯 prompt 无依赖）
- `scripts/sync-push.sh`、`scripts/install.sh`

## 与本仓库的关系 / 可吸收点

- 定位与本仓库 `writing-refs/` 同生态（中文写作 / 认知向 skills），但更偏「单 skill = 一种思维操作（解剖 / 降秩 / 追本 / 拆书）」的原子化设计，prompt 工程密度高、结构骨架清晰。
- 整体可迁移性偏低：ljg-skills 是个人认知/内容/写作集，与本仓库工程 harness 内核（think-/dev-/guard-）domain mismatch。真正有价值的吸收点集中在写作/可读性层。

### 吸收裁决（2026-06-23，依 `refs-absorption-methodology.md`）

| 候选手法 | 裁决 | 落点 / 原因 |
|---|---|---|
| `ljg-card` 模具分流（单入口多参数 + references 按模具加载） | **absorbed (L2)** | 已写入 `docs/software-engineering-research/skill-patterns.md` 模式 O「单入口多模具分流」；含「参数 ≤ 5」护栏 |
| `ljg-card` taste.md 的 AI 伪造信号清单（假数据/Jane Doe/纯黑/Inter） | **candidate** | 拟扩 `writing-skills/_shared/writing-constraints.md §2` 数据/命名层（现仅文本套话层）；视觉项 cross-check `fe-ui-design/refs/anti-ai-slop.md` 多已覆盖 |
| `ljg-plain` 句子级「说人话」红线（口语检验/零术语/短词/具体/诚实/信任读者/查译感） | **absorbed (L2)** | 2026-06-23 用户点名吸收。已加进 `coding-skills/readable-final-answer/SKILL.md` Mode A §3「说人话红线」子节 + 2 条自检 + 跨 Mode B/C 适用 + description 加"说人话"触发；剥掉 org/Denote 私货。**更正**：此项原属下方 reject 的 cognitive 簇，workflow 低质量分析漏判其句子级价值，由用户发现 |
| ljg-paper 三档变焦压缩 / ljg-read 单锚点贯穿 | **observe** | 可折进 `readable-final-answer` / `write-outline`，价值中等，看写作诉求频率 |
| 认知簇（八维解剖/纵向穿透/降秩/生成器判据）| **reject** | think-* / think-unstuck / think-quality(PIEV/premise-collapse) 已覆盖；勿为凑数新建方法论文档 |
| meta-infra（ljg-skill-map / ljg-push / 双格式分发 / SKILL.md 格式）| **reject** | 本仓库已有更强等价：`catalog.json`(SSOT) / `guard-gitops` / `verify_skills`；agentsview(程序 C) 已超越静态地图 |
| 红线检验 / 形式化 / 断言式约束 / 不确定标记 | **covered** | `guard-verify` L1-L3、`writing-constraints [硬]`、`think-research [推断]/[未验证]`、`dev-long-run 降级` 已实现 |

- 调研经由 workflow 并行深读 + 人工批判过滤：原始产出 30+ 候选严重注水（多为「L1 再写一篇方法论文档」），按保守原则筛至上述少数；cognitive 簇输出有乱码字符已折扣；meta-infra 簇 workflow 失败，由人工读 `ljg-skill-map`/`ljg-push` 源文件补判为低相关。

## 备注

- 高度个人化（`ljg-` 命名、作者私人审美与中文语境），并非通用工程 skill 集；与本仓库 `guard-*` / `dev-*` 工程交付链路无直接重叠，价值在「认知 / 内容 / 写作」侧。
- org-mode 为默认格式，落地到本仓库（Markdown 生态）需取 `md` 分支或转换。

## 最近 14 天更新（2026-06-09 ~ 2026-06-23）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/master` @ `2bcce7c`，仓库累计 117 commits
- [事实] 窗口内提交聚焦 `ljg-library`（取景框借书卡，迭代到 v2.3.0）、`ljg-paper`、`ljg-paper-flow`、`ljg-push`
- [事实] 代表提交：
  - `2026-06-19` `feat: sync ljg-* skills [ljg-paper-flow] (v1.17.35)`
  - `2026-06-19` `docs(readme): ljg-paper-flow 改为 ljg-paper → ljg-library（铸取景框借书卡）`
  - `2026-06-15` `feat: sync ljg-* skills [ljg-library ljg-push] (v1.17.32)`
  - `2026-06-13` `feat: sync ljg-* skills [ljg-paper ] (v1.17.31)`
  - `2026-06-10` `feat: sync ljg-* skills [ljg-book ] (v1.17.28)`
- [推断] 近期主线是把 `ljg-library`（取景框→意向画面枢轴 + 费曼讲解 + 继刚墨像）打磨成型，并将 `ljg-paper-flow` 工作流改接到 `ljg-library`。
<!-- recent-updates:end -->

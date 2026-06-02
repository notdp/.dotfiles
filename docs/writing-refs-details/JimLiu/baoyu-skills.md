# JimLiu/baoyu-skills
- 仓库 / owner JimLiu (宝玉) / 实测★ ~20.2k / vendored commit e6f4cd8a / 分类 卡片/封面/社交图 / 核实日期 2026-06-02

## 思路哲学（Why）

核心定位：这是一套面向「日常内容生产」的 Claude Code marketplace plugin，21 个 `baoyu-` 前缀 skill 覆盖图片卡片、信息图、封面、漫画、幻灯片、配图、发帖、转换等。对中文写作 skills 体系而言，最有借鉴价值的是其中**视觉内容生成簇**（baoyu-xhs-images / baoyu-infographic / baoyu-cover-image / baoyu-comic / baoyu-slide-deck / baoyu-article-illustrator / baoyu-diagram）。

它要解决的真实痛点与设计哲学：

- **「内容 → 视觉资产」是一个有结构的转换问题，不是一次性提示词**。作者把它拆成稳定流水线：分析内容 → 结构化 → 推荐组合 → 用户确认 → 写 prompt 文件 → 调后端出图 → 报告。每一步都有产物落盘（`analysis.md` / `outline.md` / `structured-content.md` / `prompts/NN-*.md`），让流程可中断、可复现、可回滚。
- **正交维度组合优于预设堆叠**。xhs-images 把视觉拆成 Style(12) × Layout(8) × Palette(3) 三个独立旋钮自由组合（`skills/baoyu-xhs-images/SKILL.md` 的 Dimensions 表），infographic 拆成 Layout(21) × Style(22)，cover-image 拆成 Type/Palette/Rendering/Text/Mood/Font 五维。这把组合爆炸用少量维度表达，再用 `--preset` 提供命名快捷组合（如 `knowledge-card = notion + dense`），兼顾灵活与易用。[推断] 这是为了既给高级用户细粒度控制、又给普通用户一句话出图的取舍。
- **prompt 文件即唯一事实源（SSOT）**。硬约束「每张图的完整最终 prompt 必须先写到 `prompts/NN-*.md` 再调任何后端」（SKILL.md「Prompt file requirement (hard)」），目的是：换后端不用重写 prompt、修改图只改 prompt 文件、出错可对比保留候选。
- **后端无关 / runtime 无关**。skill 不绑定某个出图模型，而是定义一套「后端解析规则」（current-request override → saved preference → auto-select → ask），既能跑在 Codex 原生 `imagegen`、也能跑 `codex-imagegen` wrapper、也能用 baoyu-image-gen 多 provider。CLAUDE.md 明确声明每个 skill 要可被单独抽取使用（self-containment），所以共享约定是**内联复制**而非跨文件引用。
- **确认是硬门禁，不是礼貌**。Confirmation Policy 把「显式调用 / 文件路径 / 匹配到 preset / EXTEND.md 默认」全部降级为「推荐输入」，明确声明它们都不授权跳过确认，只有当前请求里出现 `--yes`/「直接生成」等显式措辞才放行 —— 这是 Fail-Safe（默认拦截而非放行）的体现。

## 特殊技巧（How）

1. **维度旋钮 + 命名 preset + 自动选择三层 API**。同一能力暴露三种入口：`--style/--layout/--palette` 细粒度旋钮、`--preset knowledge-card` 命名组合、以及内容信号→组合的 Auto-Selection 表（`baoyu-xhs-images/SKILL.md` 的 Auto-Selection 与 Style×Layout 兼容矩阵 ✓✓/✓/✗）。证据：xhs SKILL.md 的 Dimensions / Presets / Auto-Selection / Style×Layout Matrix 四张表。
2. **image-1 锚点链解决多图一致性**。xhs 把「先生成封面图1（不带 ref），再把图1 作为 `--ref` 传给后续每张图」称为「the single most important consistency trick」（Step 3）；用户自带 ref 与内部锚点链分层叠加，且明确「图2+ 不再叠用户 ref，避免信号冲突」。
3. **角色一致性靠 character reference sheet**。comic 用 `characters/characters.md` 模板（脸型/发型/瞳色/服装/配色 hex/表情范围/年龄变体）先生成角色定稿 sheet，再据此画每页，解决「AI 每次画的人都不一样」（`baoyu-comic/references/character-template.md`）。
4. **样式定义文件的标准化 schema**。每个 style 文件统一含 Color Palette(带 hex) / Visual Elements / Typography / Style Enforcement / Avoid / Best For 六段（`baoyu-infographic/references/styles/morandi-journal.md`）。「Avoid」与「Style Enforcement」是负向约束，专门压制模型漂移回默认审美。
5. **prompt 渲染的防漏措施（reusable 反模式清单）**。`baoyu-article-illustrator/references/prompt-construction.md` 沉淀了一组通用 prompt 注入规则：颜色 hex「仅作渲染指导，不要把色名/hex 当文字画进图里」；人物「用简化剪影/符号，不要写实脸」；文字「大、手写体、只放关键词」；并附 Infographic/Scene/Flowchart/Comparison/Framework/Timeline 等类型模板 + style×palette 的成品 prompt 片段。
6. **两条出图红线（⛔ 硬约束）**：(a) 永不用 SVG/HTML/Canvas 等代码渲染替代位图生成；(b) 永不用 ImageMagick/Pillow 等在已生成位图上「补字」修文字 —— 文字错了只能改 prompt 重生成。每个出图 skill 的 SKILL.md 顶部都内联这两条。
7. **EXTEND.md 三级配置 + first-run setup 阻塞**。配置按 `项目 → XDG → home` 三路径优先级查找（first hit wins），首次运行（交互模式）强制走 setup 并落盘后才继续；`--yes` 则跳过 setup 用内建默认（`baoyu-xhs-images/SKILL.md` Step 0 ⛔ BLOCKING）。schema 显式化为 YAML（`references/config/preferences-schema.md`），含 watermark/preferred_style/custom_styles/preferred_image_backend/generation_batch_size。
8. **批量出图策略带优先级降级**：后端原生 batch → runtime 并行 tool call（默认 4，clamp 1-8）→ 顺序，且「不用 subagent 单纯为并行渲染」。同时定义重试语义「失败项只重试一次，不重生成已成功项」。
9. **统一备份规则**：覆盖任何文件（source/outline/prompt/image）前先重命名为 `<name>-backup-YYYYMMDD-HHMMSS.<ext>`，保护用户手改。这是贯穿全流程的硬规则。
10. **平台特化的内容分析框架**。xhs 的 `analysis-framework.md` 针对小红书做了 Hook 类型（数字/痛点/好奇/利益/身份钩子）、用户画像表（学生党/打工人/宝妈…→风格映射）、收藏价值/分享触发/评论诱导评估 —— 把「爆款方法论」编码成可执行分析维度。
11. **多策略大纲生成（Path C）**：xhs 详细模式生成 A/B/C 三个结构不同、推荐风格也不同的大纲（Story-Driven / Information-Dense / Visual-First），frontmatter 带 `style_reason`，让用户挑或合并。
12. **authoring 自纪律**：`docs/creating-skills.md` 规定 SKILL.md 正文 < 500 行、references 只一层深、description 第三人称含 what+when、强制 EXTEND.md 加载段与 User Input Tools 段内联。仓库用 `scripts/verify-skill-release-commits.mjs` 等脚本 + githooks 守发布流程。

## 可借鉴点（for writing-skills）

1. **正交维度 + 命名 preset + 自动推荐的三层 API**，可直接迁移到中文写作 skill：例如「文章体裁 × 语气 × 结构 × 受众」拆成独立旋钮，再给 `--preset 公众号深度长文` 这类命名组合，再加内容信号→组合的自动推荐表。降低普通用户门槛同时保留高级控制。
2. **prompt/产物文件即 SSOT**：写作 skill 同样可以把「大纲 / 分析 / 每段成稿」落盘为可复现文件，支持中断续跑、改某段不重跑全文、保留候选对比。我们体系已有 dev-operational-task 的可恢复理念，这里给了具体落盘命名约定（`NN-{type}-{slug}.md` + backup 规则）。
3. **负向约束清单（Avoid / Style Enforcement / 反模式 prompt 注入）**：写作里对应「禁用 AI slop、禁用 em dash/动物比喻、禁用空话套话」。可把这些做成像 morandi-journal style 文件那样的结构化「风格契约 + Avoid 段」，而不是散落在正文提醒里 —— 与我们已有的 readable-* 文风约束、fe-ui 的 AI slop 检测思路一致，可统一成「写作风格契约文件」。
4. **确认即硬门禁、默认拦截**：把「匹配到 preset / 有默认配置」一律降级为推荐输入，只有显式措辞才跳过确认。这与我们 AGENTS.md 的「故障导向安全」「边界决策需用户批准」高度契合，可作为写作 skill 在「定稿/发布/覆盖原文」前的统一确认规范。
5. **EXTEND.md 三级配置 + 显式 YAML schema + 首次 setup**：给「用户长期写作偏好」（语气、称谓、禁用词、署名/水印、语言）一个可持久化、可被项目覆盖的配置层，schema 显式化而非靠对话记忆。比把偏好塞进一次性 prompt 更稳。
6. **多策略产物让用户选（Path C）**：写作里对应「同一主题出 3 个结构不同的大纲/开头让用户挑」，且每个标注选它的理由（`style_reason`）。适合 think-plan / 写作初稿阶段。
7. **self-containment + 内联共享约定**：若中文写作 skills 也要能被单独抽取分发，应学它「不跨 skill 引用、共享约定内联复制、docs/ 只给作者看」的纪律，避免相对路径在 standalone 使用时断裂。注意取舍：这与 DRY 冲突（同一段约定在 21 个 SKILL.md 里重复），是用「分发独立性 > 去重」的显式取舍换来的。

## 资产盘点（事实）

实际读到的关键文件：

- 仓库结构：`.claude-plugin/marketplace.json`（单 plugin 注册 21 skills，version 2.4.0）、`CLAUDE.md`（架构 / self-containment / image-gen 后端 / user-input 约定 / 发布流程）、`docs/creating-skills.md`（authoring 规范）。
- SKILL.md 完整读：`skills/baoyu-xhs-images/SKILL.md`（484 行，最完整）、`skills/baoyu-infographic/SKILL.md`、`skills/baoyu-cover-image/SKILL.md`（部分）。
- reference 文件读：`baoyu-infographic/references/base-prompt.md`（模板占位符 `{{LAYOUT}}`/`{{STYLE}}`/`{{CONTENT}}` 等）、`baoyu-infographic/references/styles/morandi-journal.md`（style 文件 schema 样例）、`baoyu-infographic/references/layouts/bento-grid.md`（layout 文件样例）、`baoyu-comic/references/character-template.md`、`baoyu-comic/references/workflow.md`（部分）、`baoyu-article-illustrator/references/prompt-construction.md`（最丰富的 prompt 工程沉淀）、`baoyu-xhs-images/references/config/preferences-schema.md`、`baoyu-xhs-images/references/workflows/analysis-framework.md`。
- 21 个 skill 清单（来自 marketplace.json）：article-illustrator、comic、compress-image、cover-image、danger-gemini-web、danger-x-to-markdown、diagram、electron-extract、format-markdown、image-gen、infographic、markdown-to-html、post-to-weibo、post-to-wechat、post-to-x、slide-deck、translate、url-to-markdown、wechat-summary、xhs-images、youtube-transcript。外加 `.claude/skills/release-skills`（仓库内部维护用）。
- 资源规模（事实）：infographic 22 个 style 文件 + 21 个 layout 文件；xhs 12 style preset + 多 palette + workflows；comic 6 art-style + 7 tone + 7 layout + 5 preset；附 `screenshots/` 大量样图（未读图片二进制）。
- 出图后端：`packages/baoyu-codex-imagegen`（spawn `codex exec` 走用户订阅，免 API key）、`baoyu-image-gen/scripts/providers/`（openai/azure/google/dashscope/minimax/openrouter/replicate/seedream/zai/jimeng/codex-cli 多 provider，含 *.test.ts）。

## 备注 / 风险

- 本项目是**视觉内容生成**为主，不是纯文字写作；其文字层主要是「prompt 工程 + 内容分析框架」。借鉴时要把「出图 prompt」类比映射到「写作 prompt / 文体契约」，不能直接照搬出图专属机制（image-1 锚点链、character sheet、位图防补字）。
- [未验证] 实测★ ~20.2k、commit e6f4cd8a 为题面给定，我未联网核对 star 数；vendored commit 我读到本地 git HEAD 为 `e6f4cd8a46a66d8c6291873a5e397dcd959fd29d`，与题面一致。
- [未验证] 我未读完全部 21 个 SKILL.md 与全部 reference（如 slide-deck/diagram 的 SKILL.md 正文、各 provider 实现细节、发帖类 CDP skill），结论聚焦在视觉生成簇 + authoring 约定；utility/publish 类 skill 只做了文件级盘点。
- [推断] 21 份 SKILL.md 大量内联重复同一套 User Input Tools / Image Generation Tools / Confirmation Policy 文本，维护成本高、易漂移；作者用 `docs/*.md` 作者侧 canonical + 脚本校验来缓解，但同步仍是手工。我们若采用 self-containment 路线需要同等的校验脚本兜底。

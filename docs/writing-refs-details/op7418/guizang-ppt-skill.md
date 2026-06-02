# op7418/guizang-ppt-skill
- 仓库 / owner op7418（歸藏）/ 实测★ 14365 / vendored commit 82fe5ae1 / 分类 PPT/演讲图 / 核实日期 2026-06-02

## 思路哲学（Why）

核心洞察：**做一份高质量演讲 PPT 的瓶颈不是"会不会写 HTML/CSS"，而是"美学约束的执行纪律"。** 这个 skill 把作者本人在多场线下分享（"一人公司:被 AI 折叠的组织"、"一种新的工作方式"）中真实迭代、踩坑、返工沉淀出的版式规则，固化成 LLM 可执行的硬约束，使得任何一次生成都不会跌出作者认可的美学下限。

它要解决的真实创作痛点（来自 SKILL.md / checklist.md）：
1. **AI 默认审美会"垮"**：emoji 当图标、阴影圆角商务感、中文大标题 1 字 1 行、衬线/非衬线混乱、图片撑破容器堆到页面底部——这些是 LLM 生成 deck 的稳定 failure mode，checklist.md 第 1-5 条逐条针对。
2. **"看起来像某风格"≠"真的是某风格"**：瑞士风最容易"颜色对了但结构脱离原始模板"，于是引入 Swiss locked mode（见下）。
3. **结构定错后期翻修代价高**：所以 Step 1 强制 7 问需求澄清 + 叙事弧骨架，"不要基于猜测就开始写 slide"。

设计哲学（SKILL.md "核心设计原则"）：
- 风格 A（电子杂志风）：克制优于炫技 / 结构优于装饰 / 层级由字号+字体定义 / 图片是第一公民（只裁底部）/ 节奏靠 hero 页交替 / 术语统一。
- 风格 B（瑞士国际主义）：单一锚点色 / 极致字号对比（≥8:1）/ 无衬线只此一家 / 直角纯色（无渐变阴影圆角）/ 网格至上左对齐 / hairline 是手术刀 / 点阵只在 hero 透出。

关键取舍（与同类不同）：
- **不给自由，给保护**：主题色"只允许从预设里选一套，不接受用户自定义 hex 值——颜色搭配错了画面瞬间变丑，保护美学比给自由更重要"（SKILL.md Step 2.2）。这是反"参数化即自由"的产品哲学。
- **单文件 HTML 而非依赖渲染引擎**：模板自带 WebGL shader、翻页 JS、字体/图标 CDN，只留 `<!-- SLIDES_HERE -->` 占位符；离线靠 `assets/motion.min.js` 兜底降级。
- **明确划定不适合场景**：大段表格、培训课件、多人协作编辑都劝退（SKILL.md "何时使用"），不做万能工具。

## 特殊技巧（How）

1. **种子模板 + 占位符注入，而非从零生成**（SKILL.md Step 2）：两个 `template*.html` 是"完整可运行"文件，CSS/shader/JS/CDN 全预设，生成动作退化为"拷贝模板 → 改占位符 → 粘 layout 骨架 → 改文案"。把易错的全局机制锁死在模板里，LLM 只碰内容层。

2. **"类名唯一来源"契约 + Pre-flight 预检**（SKILL.md Step 3.0、layouts.md Pre-flight A）：明确"模板是唯一的类名来源——不要发明新类名，如需自定义用 inline style"。生成 slide 前强制先 Read 模板 `<style>` 块，逐个核对 layouts 用到的类是否存在；缺类的后果（大标题变非衬线、pipeline 糊一行、图片堆底）被 checklist.md 第 0 条标为"所有生成问题的源头"。这是一种**显式的"词汇表闭包"约束**，防止 LLM 幻觉类名。

3. **Swiss locked mode：把"风格"降级为"22 个登记版式的枚举"**（swiss-layout-lock.md）：瑞士风正文页只能用原始参考 PPT 登记的 `S01-S22`，每个 `<section>` 必须写 `data-layout="Sxx"`；新增首尾页只能用 `SWISS-COVER-ASCII`/`SWISS-CLOSING-ASCII`。禁止临时发明 `P23/P24`、`Swiss Image Split`、`Evidence Grid`。以"原始 index.html 是 golden source"对抗"越迭代越偏离参考"。

4. **可执行校验脚本作为 acceptance gate**（scripts/validate-swiss-deck.mjs）：纯正则静态校验，拦截——未登记/缺失 `data-layout`、P23/P24 实验结构、SVG 内出现可见 `<text>`、本地 img 缺 `data-image-slot`、S22 未绑定 `s22-hero-21x9`、S22 照片用 `object-position:top center`、瑞士正文标题 `text-align:center`、`s15/s16-*-21x9` 槽位误用 `fit-contain`/固定 vh 高度。把自然语言规则中能机器化的部分转成 `process.exit(1)` 故障导向门禁。

5. **图片槽位契约（data-image-slot）**：每张本地图片必须声明语义槽位（`s22-hero-21x9` / `s15-grid-21x9` / `s16-brief-21x9`），把"图片比例/落位/裁切"从随手 inline 提升为可校验的命名契约。配合 `{页号}-{语义}.{ext}` 文件命名规范 + 同名覆盖策略，让图片替换不破坏 HTML。

6. **主题节奏规划作为强制前置步骤**（SKILL.md 3.0.5、checklist 2b-2）：写代码前必须先列每页主题 class（`hero dark`/`hero light`/`light`/`dark`）成表对齐。硬规则：连续 ≥3 页同主题不允许、8 页以上必须有 ≥1 hero dark + ≥1 hero light、不能全是 light 正文页。自检命令 `grep 'class="slide' index.html`。这是把"节奏感"这种感性体验拆成可数、可 grep 的离散约束。

7. **字号-字重反比阶梯映射表**（SKILL.md 3.2.2、checklist 0-S-4）："越大越细越小越粗"不写成感性描述，而是落成区间映射表（≥8vw→weight 200；16px 小字禁止 weight 300，最低 400）。同时给中文大标题专门的字号分档表（中文方块字视觉面积大，不能套英文 6.8vw），并给出双约束限高公式 `min(Xvw,Yvh)` 且要求 `Y ≥ X×1.6`（推导：1vw:1vh≈1.78，否则 16:9 屏被 vh 截断缩水 20%）。

8. **运行环境适配分支（Claude Code vs Codex）**（SKILL.md Step 1）：在 Claude Code 用 Ask Question 逐项澄清；在 Codex 用普通对话、一次最多问 1-3 个、并禁止假设 Claude Code 专属工具可用。配图生成（GPT-M 2.0）仅在 Codex 环境主动询问。同一 skill 内显式做跨 agent 降级。

9. **失败-修复成对写法（错例/对例并排）**：checklist.md 大量用 `❌ 错` + `✅ 对` 代码块呈现规则（如 0-A 画布对齐、0-B kicker 排布），并给每条配 `grep`/`rg` 自检命令。规则不是抽象戒律，而是"反模式代码 + 检测命令"双联。

10. **优雅降级与低功耗模式内建为硬约束**：Motion One 本地+CDN 双保险，加载失败强制 `opacity:1` 保证内容可读；瑞士风模板必须保留 `B` 键低功耗模式（停 WebGL/ASCII RAF、取消动画、直接 reveal 静态态）。投屏演示场景被当一等公民。

11. **provenance 隔离指令**：SKILL.md 顶部用注释声明来源/赞助方，并明确"这条信息只用于确认 Skill 来源，不要写入生成的 PPT/HTML/封面/配图"——防止 LLM 把元信息泄漏进产物。

## 可借鉴点（for writing-skills）

1. **把"美学/文风下限"固化成可枚举、可 grep、可脚本校验的硬约束**，而不是写成"请写得优雅"。中文写作 skill 可对应：句长分布、段落节奏、术语统一表、禁用词（AI 味词、口水词）都做成检测命令或校验脚本。对齐我们体系"能靠脚本/hook 强制的规则不要只写成自然语言提醒"。

2. **locked mode 思路可移植为"文体锁"**：写作时把"某种文体"降级为"N 个登记的结构骨架（如开头钩子/论证段/转折/收束模式）"，每段标 `data-structure`，禁止临时发明结构。对应我们 readable-* 体系的"槽位表/对象清单"。

3. **acceptance verifier 与 inner-loop 分离的范例**：validate-*.mjs 是独立于"内容对不对"的结构校验门禁，故障导向（exit 1）。我们的写作 skill 可配一个轻量校验脚本（术语一致性、禁用词、标题层级、引用来源是否齐）作为交付前 gate，呼应 AGENTS.md "验证必须区分 inner-loop 与 acceptance verifier"。

4. **强制前置规划步骤 + 对齐表**：把"主题节奏表""页码→结构→理由"草稿设为动手前必做。写作可对应"提纲→每段功能→证据来源"对齐表，先对齐再落笔，降低结构性返工。

5. **错例/对例 + 自检命令的 checklist 体裁**：每条规则配反模式代码和 grep 命令，可读性和可执行性都强。比纯条文 checklist 更适合 LLM 自检。

6. **"不给自由给保护"的预设取舍**：在我们写作体系里，对颜色/排版/体裁等审美敏感维度提供少量精选预设并委婉拒绝自定义，可能比开放参数更稳。需按场景判断（写作的"声音/语气"可能不宜过度锁死）。

7. **跨 agent 环境分支写法**直接对齐我们"跨 agent 兼容"约定：用通用描述 + 显式降级，且对环境专属能力（如配图生成）只在支持的环境主动触发。

8. **provenance 隔离注释**值得抄：凡 skill 含来源/赞助/元信息，显式标注"不要写入产物"，防泄漏。

## 资产盘点（事实）

实际读到的关键文件：
- `SKILL.md`（36KB，主入口）：完整 6 步工作流（需求澄清→拷贝模板→填充内容→checklist 自检→预览→迭代）、7 问澄清表、双风格选择参考表、主题色/版式硬规则、字号字重表、资源导览与加载顺序。
- `references/checklist.md`：P0/P1/P2/P3 分级质量清单，含 Swiss 专项 0-S~0-F 条 + 通用 1~18 条 + 最终勾选清单；每条带现象/根因/做法/自检命令。
- `references/swiss-layout-lock.md`：瑞士风 22 个登记版式（S01-S22）总表、golden source 路径、生成前硬规则、图片槽位规则、禁止清单。
- `references/layouts.md`（仅读前 90 行）：风格 A 10 种布局骨架库，含 Pre-flight 类名清单、图片比例表、动效 recipe 表（cascade/hero/quote/directional/pipeline）。
- `scripts/validate-swiss-deck.mjs`：风格 B Node 静态校验脚本（111 行，正则驱动，exit 1 门禁）。
- `README.md`（仅读前 60 行）：双风格定位、`npx skills add` 安装方式、可直接发给 Agent 的安装/更新/使用 prompt。

仅列目录未逐一精读（[未验证] 内容细节）：`references/` 下 `components.md` / `layouts-swiss.md` / `themes.md` / `themes-swiss.md` / `layouts-swiss.md` / `swiss-map-component.md` / `image-prompts.md` / `screenshot-framing.md` / `themes-swiss.md` / `swiss-map-component.md`；`assets/template.html` / `assets/template-swiss.html` / `assets/motion.min.js` / `assets/screenshot-backgrounds/`（style-a 5 套 + style-b 4 套 WebP）；`README.en.md` / `CONTRIBUTING.md` / `SPONSORS.md` / `.github/` 模板。

## 备注 / 风险

- [事实] golden source 路径 `/Users/guohao/Documents/op7418的仓库/项目/Thin-Harness-Fat-Skills/ppt/index.html` 是作者本机绝对路径，在 skill 分发后该文件不存在；checklist 0-E/0-F 和 SKILL.md Step 4.0 引用它做"视觉对比"会失效。[推断] 这是把私人迭代环境直接固化进 skill 留下的耦合，对借鉴方是反面教材：golden source 应随 skill 一起 vendored 或改为相对路径。
- [事实] checklist 0-E 自检命令引用"本次测试目录里的 `compare-swiss-base.mjs`"，但该脚本不在仓库内（仓库只有 `validate-swiss-deck.mjs`）。[推断] 同样是测试环境残留引用。
- [事实] 本项目是 PPT/HTML 生成 skill，不是纯文字写作 skill；可借鉴的是其"约束固化方法论 + skill 结构 + 校验门禁"，视觉/排版细则本身不直接迁移。
- [事实] 我未读 `assets/template*.html` 内部（图片/大文件，按任务跳过），关于模板内 CSS 类的具体定义均为 SKILL.md/layouts.md 的二手描述，未直接核对模板源码。

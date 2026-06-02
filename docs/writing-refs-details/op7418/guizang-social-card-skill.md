# op7418/guizang-social-card-skill
- 仓库 / owner op7418 / 实测★ ~2.6k / vendored commit 032782ff / 分类 卡片/封面/社交图 / 核实日期 2026-06-02

## 思路哲学（Why）

核心命题在 `PRODUCT.md` 第 1 节写得极清楚：**"真正的问题不是画图，是把一篇文章变成一组能打的小红书图"**。它不把自己定位成 prompt-to-image，而是定位成 article→deck 的"内容编排 + 视觉论证"工具。

几条贯穿全局的设计哲学：

1. **表达优先（Expression comes first）**。SKILL.md "Core Principle" 明确：目标不是把文字塞进海报，而是把素材变成"清晰的视觉论证（visual argument）"。每页强制回答四问：一眼要看懂什么 / 什么证据支撑 / 哪些字必须大 / 哪些字属于正文该删掉。

2. **质量是分水岭，不是效率**。`PRODUCT.md` 第 1 节列出"质量 / 效率 / 不假"三角，并断言 Canva 已解决效率、AI 已解决速度，唯独没解决"看一眼就知道用心做的"。视觉锚点写成具体参照系：上海译文封面 / The New Yorker 内文 / Kinfolk 留白 / Vignelli 瑞士网格——"被偏爱的杂志"而非"好看"。

3. **诚实的能力圈（capability circle）**。SKILL.md 把小红书 11 个高频品类切成三桶：端到端强 / 文本结构强但图需用户给 / 超出能力圈直接拒。第三桶（OOTD 全身、菜品大片、梦核/Y2K/kawaii）在 intake 阶段就要主动 push back，"不接"被定义为产品决策而非技术缺口。这是非常罕见的"主动收窄 scope"取舍。

4. **风格与内容类型解耦**。`style-system.md` "Style ↔ content type are decoupled" 反复强调：Editorial 和 Swiss 是"视觉立场（visual stance）"不是"内容品类"。职场随笔可以 Editorial，旅行流水账可以 Swiss。选择依据是编辑意图——"这是 feature story 还是 release note？"——而不是查表。这避免了"模板按品类硬绑"的套路化。

5. **反 AI 感**。多处把"AI 感"当作头号敌人：用户只给文字时一次性"三选一"提问（A 自己的照片最不 AI 感 / B 网络找图 / C AI 生成），并明确"你自己的照片是让海报不像 AI 生成的关键"。

## 特殊技巧（How）

1. **种子模板 + 占位符替换，禁止从零写 HTML**（SKILL.md Step 4.5）。两个 seed（`assets/template-editorial-card.html` / `template-swiss-card.html`）已接好字体加载、主题 token、三种尺寸、grain/背景层、所有 recipe 引用的 class。agent 只替换 `<!-- POSTERS_HERE -->` 区域，每页塞一个 recipe 骨架。把"生成"降级成"填空"，大幅压缩自由度与出错面。

2. **可执行的视觉契约校验器 `validate-social-deck.mjs`**：用 Playwright 渲染真实 HTML，对每个 `.poster` 跑 7 条规则（R1 溢出 / R2 footer 碰撞 / R3 Swiss 粗体大标题 / R4 最小字号 / R5 4 横带密度 / R6 h-xl 行数上限 / R7 figure 默认 margin 漂移），FAIL 即 exit 1。这是"把审美规则编译成确定性测试"的范例——R5 甚至做了逐行像素占用 bitmap 来算 3:4 卡的密度，R3 直接读 computed `font-weight>=600 && size>=72` 来判 Swiss"越大越细"违规。

3. **设计 token 化的类型系统**。`components.md` 把字号/字重/字族做成表：Editorial display 124px/500、Swiss h-hero 240px/200，统一遵守 **"the larger, the lighter"** 硬规。中文标题按"字数带（length band）"先选档再定号（1 行≤6 字 vs 2 行 9-12 字对应不同 px），并给出每个 board（xhs/square/wide）的 h-xl 行数与字符硬上限，注明"超了会发生什么"（标题挤掉 ledger/matrix 越界）。

4. **recipe DSL**：`layout-recipes.md` 用 M01-M16（Editorial）/ S01-S12（Swiss）编号化布局，每条带 Structure / Style / **Minimum density** 段。"最小密度"是逐 recipe 写明能填满 3:4 画布的最小内容集（如 M11 = 2 行标题 + 3 段 + 5-7 条 marginalia），不够就要换 recipe 或缩成 1:1，而非欠填发布。

5. **3:4 必须吃满画布的硬约束**。SKILL.md 末尾用中文强调内容须覆盖 ≥75% 画布高度，>15% 纯空白带需要"留白理由"，并**明令禁止 `<div style="flex:1"></div>` 上下夹击**——理由写得很到位：杂志靠对开页吸收留白，社交卡逐张独立刷，欠填看着像 PPT 漏排。

6. **1:1 短标题独立生成（不是裁剪长标题）**。`title-shortener.md` 给出 5 步提取法（抓核心动词→核心宾语→压到 4-10 字→去英文→必要才加副标题）、4 种 pattern（动宾/双句切分/巨字 Big Word/数字打头）和反模式表，并用实测对照表证明"硬塞 21:9 标题会溢出/换 3 行像段落"。

7. **图文叠加的多模态主体安全协议**（`image-overlay.md` + SKILL Step 6）：照片覆盖 ≥60% 必须先过 quiet-zone/光线测试；放标题前用 Read 工具读图、用自然语言描述人脸/焦点位置、把 subject map 写成 HTML 注释贴在 hero 块旁；每张图必须 inline 写 `object-position`（给了按主体位置取值的表）；最后做"缩到 360px 缩略图"可读性测试。这条被标为 Anti-Pattern D，强调只有看真实渲染尺寸才能抓到。

8. **流程内置人在环（human-in-the-loop）礼仪**。Step 7 "先给用户看，按需才校验"：渲染后立刻贴图 + 一句话总结，问"先你自己看，还是我先自动核查"，反对默认跑校验器（耗时且用户更快发现问题）。Step 1 的"三选一"是 one-shot，明确"不要后续反复 nudge 用户传照片"。

9. **网络找图的来源治理**：grab first / disclose after / 让用户决定署名；五个免费图库按场景排序（Pexels 支持中文关键词优先用于国内场景，Flickr CC 补"纪实真实感"）；强制写 `assets/SOURCES.md` 记录 provenance，即便用户不署名也保留。

10. **反模式驱动文档**。`style-system.md` 的 Anti-Pattern A-D 全部来自"真实 demo 渲染没报错但对比 reference 才发现失败"，并给出 WRONG/RIGHT 代码对照。还有两套 **Identity Test**（Swiss 四条全过、Editorial 三条全过才算数），把"编译通过≠风格对"显式化。

11. **Why/How 文档分层**：`PRODUCT.md` 讲为什么、`HANDOFF.md` 讲事实交接、`references/` 14 个文件按能力切分（platform-specs / theme-presets / 各 recipe / qa-checklist），SKILL.md 用"Required References + 何时读"做路由索引。

## 可借鉴点（for writing-skills）

1. **把审美/质量规则编译成确定性 verifier**。我们的写作 skills 体系一直强调"验证比生成贵"，这个项目证明了连"视觉密度/字重/标题行数"都能写成 exit-code 测试。中文写作可类比：句长上限、段落密度、标题字数带、术语一致性、禁用词都可做成 lint 脚本，而不是只写自然语言提醒（对齐我们 CLAUDE.md "能靠脚本强制的不要只写提醒"）。

2. **种子模板 + 占位符替换的"填空式生成"**。比"自由生成 + 事后审"更可预测、可局部修改、可验证——正合我们 AI-friendly 代码约束。中文写作可提供文体骨架（综述/复盘/PR 描述的固定槽位表），agent 只填槽不重排结构。

3. **能力圈三桶 + intake 阶段主动拒**。值得借鉴到 think-scope / 写作 skill 的边界设计：把"做得好/需用户补料/不接"显式列表，超出范围在动手前 push back，而不是硬接出半成品。这是对"理解问题纪律 / 不凭工程默认自决边界"的具体落地。

4. **"风格是立场不是品类"的解耦**。提醒我们写作体裁不应按"主题"硬绑，而应按"表达意图"选；可在 readable-* 体裁 skill 里借鉴"按意图选体裁，给 Identity Test 自检"。

5. **Minimum density / 留白理由**这类"反欠填"约束，对应到长文/答案写作就是"反空洞、反占位、反 filler copy"——可做成可检查的密度/信息量门禁。

6. **reference 文件按能力切分 + SKILL.md 做路由索引 + Why/How 分层（PRODUCT vs HANDOFF）**。和我们"AGENTS.md 短硬、细则下沉、refs 沉淀调研"的指令分层完全同构，是一个成熟的多文件 skill 组织范本。

7. **one-shot 提问 + 先给结果再按需校验的人在环礼仪**：避免反复 nudge、避免默认跑昂贵校验，值得抄进交付类 skill 的交互规范。

## 资产盘点（事实）

实际读到的关键文件：

- `SKILL.md`（约 300 行，含 frontmatter `name`/`description`、能力圈三桶、6 步 workflow、Non-Negotiables）
- `validate-social-deck.mjs`（Playwright + 7 规则 R1-R7 的确定性校验器，全文读过）
- `agents/openai.yaml`（interface 元数据 + `allow_implicit_invocation: true`，brand_color `#002FA7`）
- `PRODUCT.md`（讲 Why，读了前 70 行：问题定义、三角矛盾、视觉锚点、用户画像与反向画像）
- `references/components.md`（全文：字体栈、type scale、中文标题字数带、h-xl 硬上限、card-fill 互斥、image-container 比例类、spacing token、Lucide 图标规则）
- `references/style-system.md`（全文：两套 mode、解耦说明、Identity Test、Anti-Pattern A-D）
- `references/title-shortener.md`（全文：5 步提取、4 pattern、反模式、跨平台配对表）
- `references/content-planning.md`（全文：压缩阶梯、页面角色、封面 hook 句式、image-led 序列、页数指南）
- `references/layout-recipes.md`（831 行，读了前 90 行 + 结构：M01-M16 / S01-S12 recipe DSL，每条带 Minimum density）

未深读（仅扫了首 5 行 / 标题）：`HANDOFF.md`、`README.md` / `README.en.md`、`background-systems.md`、`category-cookbook.md`、`image-overlay.md`、`map-component.md`、`platform-specs.md`、`portrait-fill.md`、`production-workflow.md`、`qa-checklist.md`、`screenshot-treatment.md`、`theme-presets.md`、两个 `assets/template-*.html` 与 `assets/magazine-bg-webgl.js`。

## 备注 / 风险

- 仓库内多处引用 `local-tests/`（如 `demo-showcase/editorial.html` 作为 source-of-truth）和 `MAPBOX_ACCESS_TOKEN`，但 vendored 副本里**未见 `local-tests/` 目录**[未验证]——可能 `.gitignore` 排除或未随包发布，引用的实证 demo 本地不可达。
- 校验器依赖 `playwright`（`package.json` 声明）+ swiftshader 软件渲染，跑起来需安装 chromium，属重型 inner-loop verifier。
- 该 skill 的视觉效果（是否真"像被偏爱的杂志"）属主观且需真实渲染才能判断，本次仅做静态阅读，未运行渲染/校验，无法核实最终出图质量 [未验证]。
- `description` 同时塞了大量中英文触发词（小红书/Rednote/3:4/微信公众号/Swiss Style 等），属典型"靠 description 关键词堆触发"的隐式调用设计（`allow_implicit_invocation: true`）。

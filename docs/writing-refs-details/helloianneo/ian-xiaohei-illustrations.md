# helloianneo/ian-xiaohei-illustrations
- 仓库 / owner helloianneo / 实测★ ~1.7k / vendored commit 793dddb9 / 分类 正文配图/插图 / 核实日期 2026-06-02

## 思路哲学（Why）

核心洞察：作者不把"配图"当成给文章贴一张好看的图，而是定义成"把文章里的一个关键认知动作画出来"。README 的一句话总结很精准：**让 AI 不只是"配一张图"，而是把文章里的一个关键认知动作画出来。**（README.md:17）这是它和通用插画 prompt、PPT 信息图模板的根本分野。

它要解决的真实创作痛点：

1. **配图同质化 / 没有识别度**：内容创作者（尤其知识型、方法论、AI 工作流博主）需要一种比 PPT 信息图"更轻、更怪、更有个人识别度"的视觉语言（README.md:28）。作者用一个固定 IP "小黑" + 一套克制的手绘 DNA，把"个人品牌视觉"固化成可复用 skill。
2. **AI 配图要么过满、要么沦为装饰**：作者反复强调"一张图只讲一个核心结构"、"小黑必须承担核心动作"，直接对抗大模型生图容易堆元素、把角色画成角落吉祥物的两个典型失败模式。
3. **平均配图的浪费**：明确反对"平均配图"，要求只挑"认知锚点"（核心判断、两个断点、输入输出闭环、分流、前后对比、常见坑、承接路径、角色状态变化），把"选哪里配图"本身当成核心工作（SKILL.md:36，examples/prompts.md:35-40）。

设计哲学，几个关键取舍：

- **风格收敛 vs 自由度**：风格 DNA 高度收敛（纯白底、黑手绘线、红橙蓝三色有严格语义分工），但隐喻必须每次重新发明——收敛的是"质感"，放开的是"创意"。这是它最聪明的取舍。
- **反模板 / 反复刻**：它带了 8 张示例图，却用整节强约束"不要复刻"——示例只用于校准线条密度、留白、颜色克制、小黑气质，禁止复用旧构图（composition-patterns.md:76-91，SKILL.md:23,66）。这是同类"prompt 模板库"几乎不会做的反向约束。
- **窄定位换稳定性**：明确列出"不适合谁"（要商业插画、品牌 KV、PPT 架构图、儿童卡通、可编辑矢量的人），主动放弃通用性换取风格一致性（README.md:32-38）。
- **让图自己说话**：输出口径要求"不要长篇解释风格理论"（SKILL.md:106），把 token 留给图本身。

## 特殊技巧（How）

1. **IP 作为"核心动作主体"的硬判据**：给出一个可证伪的判断标准——"如果去掉小黑，图的核心隐喻还能完全成立，说明小黑太装饰了"（xiaohei-ip.md:52-53，README.md:232）。把抽象审美要求"角色要参与"转成一个可执行的反事实检验。

2. **颜色语义表（数据驱动）**：黑=主体线稿/角色/文字，红=重点/问题/结果，橙=主流程/路径/箭头，蓝=补充说明/系统状态/AI 提示；且"蓝色不是每张必须用"（style-dna.md:20-27）。把"配色克制"从感觉变成一张可对照的语义表，并写进 prompt 模板的 `Color use` 段。

3. **量化的留白与文字预算**：主体占画面 40%-60%、至少 35% 空白、最多 5-8 处批注、每处 2-8 字（style-dna.md:13-15）。把"简洁"翻译成可检查的数字，QA 时能直接对照。

4. **三步原创隐喻生成法 + 物件池 + 动作池**：(1) 抽象概念→物理动作（卡住/漏掉/变重/分拣/沉淀/发酵）；(2) 系统结构→低科技物件（坏机器/纸箱/漏斗/秤/邮筒/井/梯子）；(3) 让小黑承担动作（composition-patterns.md:56-73）。物件池和动作池是受限词表，"用时只选 1-2 个，不要堆满"——既给灵感又防过载。

5. **8 种结构类型分流表**：Workflow / 系统局部 / 前后对比 / 角色状态 / 概念隐喻 / 方法分层 / 地图路线 / 小漫画分镜，每种带"适合什么 + 怎么画"（composition-patterns.md:6-53）。先选结构类型再发明隐喻，把生图拆成"选骨架→填血肉"两步。

6. **填槽式 prompt 模板**：英文骨架 + `{中文变量}` 槽位（Theme / Structure type / Core idea / Composition / Suggested elements / Chinese handwritten labels / Color use / Constraints），把全部 DNA 和禁忌预置在英文里，只让 agent 替换内容变量（prompt-template.md:5-37）。英文写约束 + 中文写画面内容，规避中文 prompt 在生图模型里的不稳定。

7. **改图 prompt 单独成档**："去标题"和"增强怪诞感"两个高频迭代动作各有专用 edit prompt，去标题那条强调"只删 X、用同色白底填充、其余完全保留、不新增任何文字物件"（prompt-template.md:40-51）。把局部编辑当成一等公民操作。

8. **QA 双清单 + 交付判据**：必过项 / 失败信号两张对照清单（qa-checklist.md），加一句体验级验收标准——"高质量图应该让读者先觉得'有点怪'，然后 1 秒内看懂结构；如果第一眼像教程页，就不合格"（qa-checklist.md:43-46）。把审美验收转成可感知的时序体验。

9. **触发与边界设计**：SKILL.md 的 description 把触发词写得极宽（"怪诞/小黑/手绘/正文配图/文章插图/shot list/去标题/改图"），同时 openai.yaml 开 `allow_implicit_invocation: true`（openai.yaml:6），让 skill 在 Codex 里能被隐式命中。同时用工作流分支区分"只规划 shot list"vs"直接生成"：用户说"分析/思考哪里配图"先出 shot list，说"生成/输出/做图"就不停下来等确认直接生图（SKILL.md:38-54）。

10. **上下文预算的显式管理**：SKILL.md 顶部"先读这些参考"明确写"按任务需要读取，不要一次塞满上下文"（SKILL.md:14-23），并把 5 个 reference 拆成独立小文件按需加载。assets/examples 标注"只作低频视觉校准，不进入默认生成路径"。

11. **资产命名与不覆盖约定**：交付保存到 `assets/<article-slug>-illustrations/`，按 `01-topic.png` 顺序命名，"保留原始生成文件，不要覆盖已有资产，除非用户明确要求替换"（SKILL.md:82-95）。

## 可借鉴点（for writing-skills）

1. **把"选哪里配图/写哪段"提升为一等工作**：对应到中文写作体系，可以做一个"认知锚点 shot list"前置步骤——不平均用力，先让 agent 标出文章里真正承担认知转折的段落，再决定哪里加例子、加图、加小标题。这正好契合我们 `think-scope` / `readable-rewrite` 里"先定对象再写"的思路。

2. **风格收敛 + 创意放开的双层结构**：可借鉴到"文风 skill"——把"质感层"（句长、标点、禁用词、节奏）做成强约束的 DNA 表，把"内容层"（比喻、例子、结构）每次重新发明。我们的 `readable-final-answer` 体裁规范已有禁用词清单（emoji/em dash/动物比喻），可以再补一张正向"质感 DNA"表。

3. **可证伪的质量判据，而非形容词**：小黑的"去掉它图还成立就是装饰"是范本。我们的可读性/写作 skill 应多用这种反事实检验（如"删掉这句话信息是否丢失""读者第一眼 1 秒能否抓到结论"），代替"要清晰、要简洁"这类不可执行的形容词。

4. **量化预算**：把"简洁"翻译成数字（段落字数、每段一个论点、标注上限）。可落到 `readable-metrics` / `readable-rewrite` 的可检查门槛。

5. **受限词表（物件池/动作池）防过载**：写作里可做"过渡词池""比喻类型池""结构骨架池"，明确"用时只选 1-2 个，不要堆满"，既给灵感又防 AI 堆砌。

6. **双清单 QA（必过项 / 失败信号）+ 体验级验收**：直接可移植成中文写作的交付 checklist，并补一条体验判据（如"通读一遍是否需要回读"）。

7. **填槽式英文骨架 + 中文内容变量**：虽是生图技巧，但"把全部硬约束和禁忌预置在固定骨架、只暴露内容槽位给 agent"的模式，对任何需要稳定输出契约的写作 skill 都适用——减少 agent 自由发挥导致的风格漂移。

8. **改图/改稿 prompt 单独成档**：把高频迭代动作（去标题=删冗余开头、增强 X=强化核心论点）做成专用 micro-prompt，对应写作里的"删套话开头""把结论提前""加一个具体例子"等定向重写指令。

## 资产盘点（事实）

实际读到的全部关键文件（仓库很小，已全覆盖非二进制内容）：

- `ian-xiaohei-illustrations/SKILL.md` — skill 主体：核心定位、参考索引、5 步工作流（消化正文→shot list→单张生成→QA→保存）、输出口径。带 YAML frontmatter（name + 宽触发 description）。
- `ian-xiaohei-illustrations/references/style-dna.md` — 风格 DNA：必须项、量化留白/文字预算、红橙蓝颜色语义表、"绝对不要"禁忌清单、审美方向。
- `ian-xiaohei-illustrations/references/xiaohei-ip.md` — 小黑 IP 定义：外形/性格/常见职责/禁止项/"去掉它图还成立就是装饰"判据。
- `ian-xiaohei-illustrations/references/composition-patterns.md` — 8 种结构类型分流表 + 三步原创隐喻生成法 + 物件池/动作池 + 反复刻规则（列出 8 个禁止默认复用的旧构图）。
- `ian-xiaohei-illustrations/references/prompt-template.md` — 填槽式英文生图 prompt 模板 + 两个改图 edit prompt（去标题 / 增强怪诞）。
- `ian-xiaohei-illustrations/references/qa-checklist.md` — 必过项 + 失败信号双清单 + 迭代方法 + 体验级交付判据。
- `ian-xiaohei-illustrations/agents/openai.yaml` — Codex agent 接口配置：display_name、short_description、default_prompt、`allow_implicit_invocation: true`。
- `examples/prompts.md` — 7 个可直接复制的使用 prompt（规划/生成/单观点/工作流/改图/样片）。
- `README.md` — GitHub 分享文档：定位、适用/不适用人群、产出契约、视觉风格、安装、用法、目录结构、注意事项、作者引流。
- `NOTICE.md` / `LICENSE` — 署名要求（保留 "Ian Xiaohei Illustrations" 名或注明出处）+ MIT。
- `assets/`、`examples/images/`、`ian-xiaohei-illustrations/assets/examples/` — 二进制图片资产（未读，按指示跳过），其中 examples/images 含 8 张命名样例（01-two-breakpoints … 08-trust-bridge）。

结构事实：安装单元是子目录 `ian-xiaohei-illustrations/`（SKILL + agents + references + assets），根目录 README/LICENSE/NOTICE/examples 仅作 GitHub 展示（README.md:218-224）。无 scripts/、无代码、无测试、无 hook——纯 prompt/reference 型 skill。

## 备注 / 风险

- 这是 **Codex skill**（OpenAI），不是 Claude Code skill；触发机制依赖 `agents/openai.yaml` 与 `$skill-name` 调用约定，移植到我们体系需改写 frontmatter/触发层。[推断]
- 生图依赖内置 `image_gen` 能力（SKILL.md:54），强绑定多模态生图模型；我们的纯文本写作体系不能直接复用其"生成"环节，可借鉴的是其**方法论结构**（锚点选择/DNA 收敛/可证伪判据/双清单 QA），而非生图实现。
- 反复刻规则与"原创隐喻"高度依赖模型创意，效果稳定性[未验证]——作者自己也在 README/SKILL 多处提示生图可能错字、幻觉标签、风格漂移，需人工 QA。
- ★ ~1.7k 为题面给定的实测值，本次未联网核实。[未验证]
- 全部分析基于本地 vendored commit 793dddb 实际读到的文件；examples/ 与 assets/ 下图片为二进制未读。

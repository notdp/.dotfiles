# writing-refs 写作技能研究汇总

面向**中文内容创作**的外部参考仓库汇总，与编程向的 [`refs-summary.md`](./refs-summary.md) 平行。
对应 vendored submodule 在 `writing-refs/<owner>/<repo>`，逐仓库分析在 `docs/writing-refs-details/`。

写作类 skill 默认只挂给创作项目（软连接到项目 `.claude/skills` → `writing-skills/`），**不暴露给编程 agent**。

## 核实说明

- 下表 star 数为 **2026-06-02** 通过 GitHub 页面/API 实测值；宣传来源图中的标注普遍略低于实测（图为更早快照，自然增长，无虚标）。
- 每个仓库已 vendored 为 git submodule 并 pin 到具体 commit（见各 details 文件）。
- 深度资产盘点（具体 skill 文件、prompt、脚本）标注为「待补」，需读仓库后补全，未读不编造。

## 分类

- **去 AI 味 / 拟人化**：检测并改写 AI 写作痕迹，让文本更像真人。代表：`op7418/Humanizer-zh`
- **选题 / 商业表达诊断**：选题诊断、爆款标题、商业模式与内容诊断。代表：`dontbesilent2025/dbskill`
- **资料驱动写作**：基于自有知识库 / 检索资料写作，减少胡编空泛。代表：`PleasePrompto/notebooklm-skill`、`content-research-writer`（存疑，见备注）
- **长文 / 深度分析**：公众号长文、万字深度分析、AI 热点解读。代表：`KKKKhazix/khazix-skills`
- **正文配图 / 插图**：把文章观点画成风格化正文插图。代表：`helloianneo/ian-xiaohei-illustrations`
- **卡片 / 封面 / 社交图**：长文拆小红书卡片、公众号封面、信息图工具箱。代表：`op7418/guizang-social-card-skill`、`JimLiu/baoyu-skills`
- **PPT / 演讲图**：文章观点变幻灯片、演讲图、分享图。代表：`op7418/guizang-ppt-skill`
- **多格式产出**：Markdown 变海报 / 卡片 / HTML / PNG。代表：`nexu-io/html-anything`

## 项目总表

| 项目 | 分类 | 实测★ (2026-06-02) | 一句话总结 |
|---|---|---|---|
| [`op7418/Humanizer-zh`](./writing-refs-details/op7418/Humanizer-zh.md) | 去 AI 味 / 拟人化 | ~8.99k | Humanizer 的简体中文汉化版 Claude Code Skill，规则检测并改写文本中的 AI 写作痕迹。 |
| [`dontbesilent2025/dbskill`](./writing-refs-details/dontbesilent2025/dbskill.md) | 选题 / 商业表达诊断 | ~5.98k | 从 1.2 万条推文蒸馏出的商业诊断 skills 工具箱，覆盖商业模式、选题、爆款标题到执行诊断。 |
| [`PleasePrompto/notebooklm-skill`](./writing-refs-details/PleasePrompto/notebooklm-skill.md) | 资料驱动写作 | 6,812 | 第三方 skill，让 Claude Code 直连自己的 Google NotebookLM，基于自有知识库给带引用的回答。 |
| [`KKKKhazix/khazix-skills`](./writing-refs-details/KKKKhazix/khazix-skills.md) | 长文 / 深度分析 | ~13.1k | 「数字生命卡兹克」开源的 AI Agent skills 合集，含公众号长文写作、横纵深度分析等。 |
| [`helloianneo/ian-xiaohei-illustrations`](./writing-refs-details/helloianneo/ian-xiaohei-illustrations.md) | 正文配图 / 插图 | ~1.7k | Codex Skill，把文章核心认知点画成 16:9 白底手绘「小黑」风格正文配图。 |
| [`op7418/guizang-social-card-skill`](./writing-refs-details/op7418/guizang-social-card-skill.md) | 卡片 / 封面 / 社交图 | ~2.6k | 把内容自动排版成小红书图文轮播 + 公众号封面对（多布局多主题，HTML→PNG）。 |
| [`JimLiu/baoyu-skills`](./writing-refs-details/JimLiu/baoyu-skills.md) | 卡片 / 封面 / 社交图 | ~20.2k | 宝玉（@dotey）发布的 AI agent 效率 skill 合集，含封面图、结构图、信息图、小红书图等 20+。 |
| [`op7418/guizang-ppt-skill`](./writing-refs-details/op7418/guizang-ppt-skill.md) | PPT / 演讲图 | 14,365 | 一句话生成杂志风 / 瑞士风 HTML 幻灯片，含图片提示词、社交封面、WebGL 演示运行时。 |
| [`nexu-io/html-anything`](./writing-refs-details/nexu-io/html-anything.md) | 多格式产出 | 5,851 | 本地 agentic HTML 编辑器，把 Markdown/CSV/JSON 转成 9 类版面，导出 HTML/PNG。 |

## 备注（未 vendored / 存疑项）

- **content-research-writer**（宣传图 #03，标注 12.6k★）：**未作为独立 submodule vendored**。它不是独立仓库，而是通用合集 [`ComposioHQ/awesome-claude-skills`](https://github.com/ComposioHQ/awesome-claude-skills)（该合集 62.9k★）里的一个子目录；同名的独立仓库均为 0 star。**图中 12.6k 对不上任何真实来源** [已验证存疑]。如需该 skill，从母合集子目录取，不单独 vendored 一个 62.9k 的通用合集。
- **作者归属更正**：`html-anything` owner 是组织账号 **nexu-io**，[未验证] 与「归藏」本人的直接关系；若有宣传把它归到归藏名下并不准确。`khazix-skills` 作者是 `KKKKhazix`（4 个 K），`ian-xiaohei-illustrations` 作者是 `helloianneo`。
- **安全敏感**：`PleasePrompto/notebooklm-skill` 依赖浏览器自动化 + 持久登录，使用前应审脚本与权限。

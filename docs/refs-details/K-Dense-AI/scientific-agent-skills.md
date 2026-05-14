# K-Dense-AI/scientific-agent-skills

- 上游仓库：`https://github.com/K-Dense-AI/scientific-agent-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/K-Dense-AI/scientific-agent-skills`
- 当前引用提交：`cbcae7b`（`2026-05-11`，`chore: update security scan report [skip ci]`）
- 主分类：**科研 / 数据分析 / 领域技能**
- 能力标签：`Agent Skills`, `science`, `research`, `bioinformatics`, `cheminformatics`, `clinical research`, `scientific databases`, `security scan`
- 一句话总结：大型科学研究 skill 集合，把科研数据库、科学 Python 包、实验平台、医学/临床工作流、科学写作和可视化整理成可被多种 agent 读取的 `SKILL.md` 能力包。

## 能力概览

- [事实] `README.md` 宣称仓库提供 135 个 ready-to-use scientific and research skills，面向支持 Agent Skills 标准的 Cursor、Claude Code、Codex、Gemini CLI 等 agent。
- [事实] 本地 `scientific-skills/*/SKILL.md` 实际计数为 137 个；`SECURITY.md` 记录扫描 136 个 skill；这些数量与 README 的 135 口径不一致，后续引用总数时应重新核验。
- [事实] 覆盖面包括 Scientific Databases & Data Access、Scientific Integrations、Scientific Packages、Bioinformatics & Genomics、Cheminformatics & Drug Discovery、Clinical Research、Medical Imaging、Machine Learning & AI、Materials Science、Data Analysis & Visualization、Laboratory Automation、Scientific Communication、Research Methodology、Regulatory & Standards、Web Search 等。
- [事实] `database-lookup` 一个 skill 覆盖 78 个公开数据库；README 还提到 100+ scientific/financial databases、70+ optimized Python package skills、9 个 scientific integration skills、30+ analysis/communication tools。
- [推断] 它更像“领域知识和工具手册压缩层”，不是本仓库当前 `dev-*`、`guard-*` 这类工程工作流 skill 的同构替代品。

## 关键文件

- `README.md`：仓库定位、安装方式、分类概览、安全免责声明、示例 prompt、贡献和 FAQ。
- `scientific-skills/`：主 skill 目录，每个子目录至少包含 `SKILL.md`，部分附带 `scripts/` 和 `references/`。
- `docs/scientific-skills.md`：按领域列出的 taxonomy 和每个 skill 的用途说明。
- `docs/examples.md`：跨 skill 的科学 workflow 示例。
- `docs/open-source-sponsors.md`：底层科学开源项目清单。
- `SECURITY.md`：Cisco AI Defense Skill Scanner 扫描结果。
- `scan_skills.py`：扫描 `scientific-skills/` 并生成安全报告。
- `scan_pr_skills.py`：扫描 PR 中变化的 skill，并支持 `--fail-on CRITICAL` 门禁。
- `.github/workflows/pr-skill-scan.yml`、`.github/workflows/security-scan.yml`、`.github/workflows/release.yml`：PR 扫描、周期扫描和发布流水线。
- `pyproject.toml`：项目依赖与 Python 版本约束。

## Skill 结构观察

- [事实] `SKILL.md` 使用 YAML frontmatter，常见字段包括 `name`、`description`、`license`、`metadata.skill-author`。
- [事实] 普通 skill 多用 `Overview`、`When to Use`、`Core Capabilities`、`Installation`、`Core Workflows`、`Best Practices`、`Common Issues` 等结构。
- [事实] 重型 skill 会附带脚本与参考文档，例如：
  - `scientific-skills/rdkit/scripts/similarity_search.py`
  - `scientific-skills/scanpy/references/standard_workflow.md`
  - `scientific-skills/database-lookup/references/pubchem.md`
  - `scientific-skills/hugging-science/scripts/fetch_catalog.py`
- [推断] 对本仓库可复用的结构是“短入口 SKILL.md + 可执行脚本 + references 分册”，适合知识密度高、依赖多、需要示例代码的领域 skill。

## 安全与适配风险

- [事实] `SECURITY.md` 生成于 `2026-05-11 11:18 UTC`，记录 `Skills scanned: 136`、`Total findings: 794`、`Critical: 63`、`High: 18`、`Safe skills: 106/136`。
- [事实] README 明确提醒不要一次性安装全部 skill，应先阅读 `SKILL.md`，并按需安装。
- [事实] 多个 skill 涉及网络请求、外部 API、API key、环境变量、医疗/临床数据、实验室自动化、文件写入或代码执行。
- [事实] Python 版本口径存在差异：README 写 Python 3.11+、推荐 3.12+；`pyproject.toml` 写 `requires-python = ">=3.13"`。
- [推断] 本仓库如果吸收其中能力，应优先作为 reference 或按单 skill 精选迁移，不应整包镜像到全局 skills。

## 对本仓库的参考价值

1. **领域 taxonomy 可复用**：对科学、医学、数据分析和研究自动化这类长尾领域，先建 taxonomy，再落单个 skill，比直接写大 prompt 更可维护。
2. **安全扫描门禁可借鉴**：全量扫描、PR 增量扫描、severity gate、Markdown 安全报告，适合本仓库未来扩大 skill catalog 后使用。
3. **重型 skill 拆分方式可借鉴**：`SKILL.md` 只做入口与流程，细节放 `references/`，可执行样例放 `scripts/`。
4. **风险分级必须前置**：触及医疗、临床、secrets、外部 API、网络和本地文件修改的 skill，应默认走安全审查和运行时边界检查。

## 不建议照搬

- 不建议整包安装或复制全部 scientific skills 到本仓库全局 skill 目录。
- 不建议把有临床/医疗建议性质的 skill 直接纳入默认触发路径。
- 不建议在未重新扫描前引用 `SECURITY.md` 里的扫描结果作为当前安全状态，只能作为该提交的历史证据。

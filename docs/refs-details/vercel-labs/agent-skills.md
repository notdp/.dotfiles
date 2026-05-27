# vercel-labs/agent-skills

- 上游仓库：`https://github.com/vercel-labs/agent-skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/vercel-labs/agent-skills`
- 主分类：**前端 UI / 设计系统**
- 能力标签：`React`, `React Native`, `部署`, `Vercel`
- 一句话总结：Vercel 出品的技能集合，覆盖 React/React Native、组合模式、UI 评审与 Vercel 部署。

## 能力概览

- React/Next.js 性能与最佳实践规则库。
- React Native / Expo 性能、动画、导航、UI、monorepo 规则库。
- React 组合式 API 设计与组件架构模式。
- 提供 web-design-guidelines 审查包装器与 Vercel 部署技能。

## 资产盘点

- 6 个 skills。
- 4 个 zip 包。
- 3 个 AGENTS 汇编文档。
- 2 个部署脚本。

## 关键文件

- `README.md`
- `skills/react-best-practices/SKILL.md`
- `skills/react-native-skills/SKILL.md`
- `skills/deploy-to-vercel/SKILL.md`

## 2026-05-27 本地 range 调研

- [事实] 本轮 range：`b9c8ee0643d87d3c5a953d1e22382ff2ead39229..180115660cfb8a86b808f117475a01f54caf3bc5`。
- [事实] 上游新增大型 `vercel-optimize` skill，资产包括 `SKILL.md`、README、AGENTS、metadata、`lib/`、`scripts/`、`references/`、`playbooks/`、`support-topics/`、tests 与 fixtures。
- [事实] 该 skill 覆盖 Vercel 成本/性能优化、Observability Plus、metrics collection、budget summary、deep dive、gate investigations、report rendering、candidate reconciliation、scanner-driven gates、verification 与 claim extraction。
- [事实] 后续提交多次 harden public launch safety、frontmatter YAML、framework preflight、cache policy guard、Observability Plus access preflight、CLI token redaction、data gap reporting、project scope preflight、linked team scope、plan detection、workflow guidance 与 observation safety。
- [推断] 本 ref 正从 React/UI 最佳实践集合演进为“带数据采集、scope preflight、redaction、claim verification 和报告再生成”的垂直诊断系统。
- [推断] 对本仓库最可吸收的是复杂 verification / operational skill 的结构：`scope preflight`、`data gap reporting`、`claim verification`、fixtures/tests，而不是 Vercel-specific metrics 数据本体。

## 备注

- README 中的名字与实际目录/skill name 有少量漂移；web-design-guidelines 的规则需运行时远程抓取。

## 最近 14 天更新（2026-03-31 ~ 2026-04-14）
<!-- recent-updates:start -->
- [事实] 检查基线：`origin/main`
- [事实] 提交数：`1`
- [事实] 代表提交：
  - `2026-04-02` `Refine react-view-transition skill`
- [推断] 主要变化是继续打磨 `react-view-transition` skill。
<!-- recent-updates:end -->

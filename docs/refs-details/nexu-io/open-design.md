# nexu-io/open-design

- 上游仓库：`https://github.com/nexu-io/open-design`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/nexu-io/open-design`
- 主分类：**前端 UI / 设计系统**
- 能力标签：`本地优先设计工作台`, `Agent CLI 调度`, `Skills`, `DESIGN.md`, `SSE`, `Next.js`, `Express`
- 一句话总结：本地 daemon 调用用户机器上的编码 Agent CLI，把 brief、skill、设计系统和项目文件系统串成可预览、可编辑、可导出的设计 artifact 工作流。

## 能力概览

- [事实] Web 层提供项目入口、聊天、artifact 文件区、sandbox iframe 预览、comment mode 和 BYOK fallback。
- [事实] Daemon 层负责 Agent CLI 探测与 spawn、REST/SSE API、SQLite 元数据、项目文件读写、skills/design-systems 扫描、媒体生成和 API proxy。
- [事实] 仓库内置 `59` 个 `SKILL.md`、`137` 个 `DESIGN.md`、`94` 个 prompt-template 文件。本数值来自本地文件计数；README 中同时出现 `31`、`72`、`129` 等较旧或不同口径的数量。
- [事实] 支持 Claude Code、Codex、Devin、Cursor Agent、Gemini、OpenCode、Qwen、Copilot、Hermes、Kimi、Pi、Kiro、Mistral Vibe 等 CLI adapter。
- [事实] 媒体生成统一成 `image` / `video` / `audio` surface，provider 包括 OpenAI、Volcengine、xAI、HyperFrames、MiniMax、FishAudio 等。

## 资产盘点

- Monorepo：`pnpm@10.33.2` workspace，覆盖 `apps/*`、`packages/*`、`tools/*`、`e2e`。
- Web：`apps/web`，Next.js 16 App Router、React 18、TypeScript。
- Daemon：`apps/daemon`，Node 24、Express、`better-sqlite3`、SSE。
- Desktop：`apps/desktop`，Electron shell，通过 sidecar IPC 获取 Web URL。
- Contracts：`packages/contracts`，web/daemon 共享 DTO 和 SSE 类型。
- Sidecar/platform：`packages/sidecar-proto`、`packages/sidecar`、`packages/platform`，封装 sidecar 协议、IPC、进程 stamp 和命令解析。
- 工具层：`tools/dev` 和 `tools/pack`，分别负责本地开发生命周期和打包生命周期。

## 核心流程

1. 用户在 Web 入口选择 skill、设计系统和 brief。
2. Web 通过 daemon API 读取 agents、skills、design systems、projects、templates、prompt templates 和配置。
3. 创建项目后，daemon 在 `.od/projects/<projectId>/` 下准备真实文件工作区，并在 SQLite 记录项目、会话、消息、tabs、preview comments 等元数据。
4. Daemon 拼装系统提示词：discovery/question form、official designer prompt、`DESIGN.md`、craft references、`SKILL.md`、project metadata、template、deck/media contract。
5. Daemon 以项目目录为 cwd spawn 选定 Agent CLI，并通过 SSE 转发 stdout/stderr/结构化事件。
6. Web 解析流中的 `<artifact>...</artifact>`，写入项目文件，并在 sandbox iframe 中预览。
7. 用户可通过文件区继续编辑、下载 ZIP/PDF/HTML，或用 comment mode 生成局部修改提示。

## 关键设计

### Skills as files

- [事实] `skills/*/SKILL.md` 使用 Claude Code skill 约定，并扩展 `od:` frontmatter。
- [事实] 扩展字段包括 `mode`、`preview.type`、`design_system.requires`、`craft.requires`、`inputs`、`parameters`、`outputs`、`capabilities_required`。
- [推断] 这种“prompt + seed assets + references”的文件协议比代码插件更容易被人 review，也更容易迁移到不同 Agent runtime。

### Design Systems as Markdown

- [事实] `design-systems/*/DESIGN.md` 作为设计系统注入 prompt，而不是硬编码成 UI theme。
- [事实] daemon 会解析 title、category、summary、swatches、surface 和正文。
- [推断] 对本仓库的 skill 体系有直接启发：可把品牌/风格规则独立成可读、可复用、可版本化的 Markdown 资产。

### 本地 daemon 作为唯一特权进程

- [事实] Web 不直接碰文件系统或 spawn 进程；daemon 统一处理 agent 调度、文件读写、SQLite、媒体生成和 proxy。
- [推断] 这个边界能降低 Web 层复杂度，也让 Vercel Web + 本地 daemon 的部署形态更自然。

### Run service 和可恢复 SSE

- [事实] `runs.ts` 维护内存 run registry，状态包括 `queued`、`running`、`succeeded`、`failed`、`canceled`。
- [事实] 每个 run 保存最近事件，`GET /api/runs/:id/events` 支持通过 `Last-Event-ID` 或 `after` 续接。
- [推断] 这对长时间 agent 任务很有参考价值：UI 断线后可补发事件，而不是只能重跑。

## 亮点

- Agent runtime 解耦：项目不内置模型能力，而是调用用户已有 CLI。
- 文件化能力协议：`SKILL.md`、`DESIGN.md`、craft references 和 prompt templates 都是可审查资产。
- Artifact 落盘：聊天流只是交互层，真实产物进入项目文件夹，便于继续编辑和导出。
- Prompt stack 产品化：discovery form、方向选择、TodoWrite、critique、checklist 被组合成明确的设计生成纪律。
- 预览边界清晰：artifact 在 sandbox iframe 中运行，Web 和 daemon 权限分离。
- 多 topology：默认本地运行，也考虑 Web 部署到 Vercel 并连接本地 daemon 或 BYOK direct API 的降级形态。

## 风险与局限

- [事实] 多个核心 daemon 文件存在 `// @ts-nocheck`，包括 `agents.ts`、`runs.ts` 等已读文件。
- [推断] 大量关闭 TS 检查会降低接口演进和重构时的静态安全性。
- [事实] README 与本地文件计数存在数量漂移。
- [推断] 文档更新节奏可能跟不上仓库资产增长，使用时应以本地扫描结果为准。
- [事实] BYOK proxy 的 URL 校验拒绝非 HTTP(S)、localhost、loopback、link-local 和常见私网 IP 字面量。
- [推断] 已读片段未看到 DNS 解析后私网地址拦截；若允许自定义域名 baseUrl，仍需额外确认 SSRF 边界。
- [事实] 媒体模型中存在 `integrated: false` 的 provider/model。
- [推断] UI 可展示的模型列表不一定全部等于开箱可用能力，实际可用性取决于 provider 集成和凭据。

## 可借鉴点

- 把高频能力做成文件协议：`SKILL.md + assets + references + checklist`。
- 把设计系统做成 Markdown SSOT：人能 review，Agent 能直接读取。
- 在生成前先做 discovery form，避免让模型直接自由发挥。
- 让 artifact 必须落盘，聊天只是控制面。
- 用 run registry + SSE event buffer 支持长任务续接。
- 把本地 daemon 作为唯一特权边界，Web 只做交互和预览。
- 对不同 Agent CLI 统一抽象：detect、model list、build args、spawn、stream parser、capabilities。

## 2026-05-27 联网刷新调研

- [事实] 刷新后 range：`852a005b3219ce9cc4f8224ac5ebcc6ce1fcc6b1..a6a56099caf1266753da477a131ae21aea493251`。
- [事实] 上游在该 range 内新增 plugin runtime 主干：plugin install/apply/trust/snapshot/doctor/validate/pack/search/publish/verify/simulate/canon/diff/upgrade/events/stats/purge 等 CLI 或 daemon 能力，并加入 marketplace registry、snapshot GC、pipeline runner、GenUI event/cache、connector gate、trust mutation 与 tool-token gate。
- [事实] 上游新增 first-party atom/scenario plugin 资产，包含 `plugins/_official/atoms/*/SKILL.md`、`open-design.json`、scenario examples，以及 build-test、code-import、design-extract、diff-review、figma-extract、handoff、patch-edit、rewrite-plan、token-map 等 atom 实现与测试。
- [事实] 上游补充 deployment/security substrate：Docker/Helm、per-cloud Helm values、bound API token guard、S3 project storage、SQLite inventory/verify/vacuum、plugin event ring buffer 与 SSE tail。
- [事实] 最近提交还包括 official GSAP skill bundle、Community/Ambassadors 页面、agent report 清理、preview social sharing gating 和 file operations summary。
- [推断] 对本仓库的启发是：如果要吸收 plugin/agent-skill 生态，优先吸收 manifest validation、author-side lint、event observability、artifact provenance 和 first-party atom `SKILL.md` 协议，而不是复制 daemon、Web UI 或全套 marketplace。

## 关键文件

- `README.md`
- `package.json`
- `pnpm-workspace.yaml`
- `AGENTS.md`
- `docs/architecture.md`
- `docs/skills-protocol.md`
- `apps/web/src/App.tsx`
- `apps/web/src/components/ProjectView.tsx`
- `apps/web/src/artifacts/parser.ts`
- `apps/web/src/runtime/srcdoc.ts`
- `apps/daemon/src/server.ts`
- `apps/daemon/src/agents.ts`
- `apps/daemon/src/runs.ts`
- `apps/daemon/src/projects.ts`
- `apps/daemon/src/db.ts`
- `apps/daemon/src/skills.ts`
- `apps/daemon/src/design-systems.ts`
- `apps/daemon/src/media.ts`
- `packages/contracts/src/api/chat.ts`
- `packages/contracts/src/sse/chat.ts`
- `skills/web-prototype/SKILL.md`
- `skills/guizang-ppt/SKILL.md`
- `design-systems/default/DESIGN.md`

## 备注

- [事实] 本次只做阅读与文档沉淀，没有安装依赖或运行该项目自身测试。
- [事实] 该项目要求 Node `~24`；当前会话系统信息显示 `python3` 可用，但没有验证 Node/pnpm 版本。

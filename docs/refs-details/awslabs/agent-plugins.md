# awslabs/agent-plugins

- 上游仓库：`https://github.com/awslabs/agent-plugins`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/awslabs/agent-plugins`
- 主分类：**AWS Agent 插件与云开发技能集合**
- 能力标签：`AWS`, `Agent Plugins`, `MCP`, `云部署`, `Serverless`, `Amplify`, `数据库`, `SageMaker`, `迁移现代化`, `安全扫描`
- 一句话总结：AWS Labs 的 agent 插件市场仓库，把 AWS 架构、部署、Serverless、Amplify、数据库、SageMaker、迁移现代化等工作流打包为可安装的 skills、MCP servers、hooks 与 references。

## 能力概览

- 面向 Claude Code、Codex、Cursor 的 AWS 插件集合，README 明确用于帮助 agent 架构、部署和运维 AWS 工作负载。
- 插件包装模型包含 `skills`、`MCP servers`、`hooks`、`references`，并同时提供 Claude marketplace 与 Codex repo-local marketplace。
- AWS 能力覆盖 Amazon Location Service、AWS Amplify Gen 2、AWS Serverless、AWS Transform、Databases on AWS、Deploy on AWS、SageMaker AI、Codebase Documentor 等方向。
- Serverless 相关能力涉及 Lambda、API Gateway、EventBridge、Step Functions、SAM、CDK 和 Durable Functions。
- 数据库相关能力涉及 Aurora DSQL schema、查询、迁移、query plan 和 IAM auth。
- SageMaker 相关能力涉及模型定制、数据转换/评估、fine-tuning、模型部署、HyperPod 运维诊断。
- 安全与凭证考虑：README 要求审查生成代码、最小权限配置 AWS credentials、对生成 IaC 做安全扫描；多个 skill 明确要求 AWS CLI / AWS credentials，并在 destructive 或部署步骤前要求用户确认。
- `databases-on-aws` 的 `aurora-dsql` MCP 默认 `disabled: true`，写操作需要 `--allow-writes`。
- 仓库内配置了 Bandit、Semgrep、Gitleaks、Checkov、Grype 等扫描任务。
- [推断] 适合吸收为本仓库的 AWS 专项 skill/插件参考：其价值主要在 packaging 结构、MCP 配置样式、hook guardrail、reference 拆分方式；直接照搬需筛选，因为很多能力依赖 AWS 凭证、外部 MCP server、CLI、SSM 或云资源权限。

## 资产盘点

- 9 个 Codex marketplace 插件条目：`amazon-location-service`、`aws-amplify`、`aws-serverless`、`aws-transform`、`codebase-documentor-for-aws`、`databases-on-aws`、`deploy-on-aws`、`migration-to-aws`、`sagemaker-ai`。
- 8 个 Claude plugin manifest；`migration-to-aws` 只看到 Codex manifest。
- 28 个 `SKILL.md`。
- 8 个 `.mcp.json`。
- 3 个 hook 配置：
  - `deploy-on-aws`：编辑后验证 `.drawio`。
  - `aws-serverless`：编辑 `template.yaml/yml` 后运行 `sam validate --lint`。
  - `databases-on-aws`：`aurora-dsql transact` 后提示验证 schema 或 affected rows。
- scripts 覆盖 draw.io 后处理/验证、Aurora DSQL cluster 操作、SAM template 验证、SageMaker HyperPod/模型相关脚本。
- references 按 skill 拆分为安全、成本、默认选型、DSQL 迁移、API Gateway、Durable Functions、SageMaker notebook/诊断等资料。

## 关键文件

- `README.md`
- `AGENTS.md`
- `.agents/plugins/marketplace.json`
- `.claude-plugin/marketplace.json`
- `plugins/*/.codex-plugin/plugin.json`
- `plugins/*/.claude-plugin/plugin.json`
- `plugins/*/.mcp.json`
- `plugins/*/skills/*/SKILL.md`
- `plugins/*/hooks/hooks.json`
- `mise.toml`
- `.pre-commit-config.yaml`
- `docs/DESIGN_GUIDELINES.md`

## 备注

- README 提到 Agent Toolkit for AWS 是后继方向，此仓库继续可用并接受贡献，部分项目未来可能迁移到 Agent Toolkit。
- README 明确 Codex 已支持 repo-local marketplace 与 plugin manifests，但 Claude-specific automatic hooks 尚未全部接入 Codex manifests；`databases-on-aws` 的 prompt hook 是例外。
- `migration-to-aws` 的 Codex manifest 指向 `skills` 和 `.mcp.json`，但本地目录未发现这些资产；吸收前需单独核对上游状态。
- [推断] 更适合作为“结构与模式参考”而非整包吸收：AWS 凭证、云资源操作、MCP server、SSM、部署确认等边界需要在本仓库重新做安全门禁。

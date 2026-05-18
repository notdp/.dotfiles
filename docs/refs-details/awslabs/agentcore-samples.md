# awslabs/agentcore-samples

- 上游仓库：`https://github.com/awslabs/agentcore-samples`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/awslabs/agentcore-samples`
- 主分类：**AWS / Bedrock AgentCore 样例库**
- 能力标签：`AgentCore Runtime`, `AgentCore Gateway`, `AgentCore Identity`, `AgentCore Memory`, `Code Interpreter`, `Browser Tool`, `Observability`, `Evaluations`, `Policy/Cedar`, `MCP`, `AWS CDK`, `CloudFormation`, `Terraform`, `Strands Agents`, `LangGraph`, `CrewAI`, `LlamaIndex`, `OAuth/OIDC`, `Cognito`
- 一句话总结：Amazon Bedrock AgentCore Samples 是一个覆盖 AgentCore 入门、能力专题、端到端业务用例、第三方集成、IaC 部署和完整 Blueprint 的官方样例集合，重点展示如何在 AWS 上部署、治理、观测和评估生产级 agent。

## 能力概览

- Runtime：提供安全 serverless runtime，用于部署和扩展 agents/tools；支持多框架、多模型、多协议，并通过 `@app.entrypoint`、SDK、CLI、boto3/AWS SDK 调用。
- Gateway：把 Lambda、OpenAPI、Smithy API 转为 MCP-compatible tools，支持 Streamable HTTP、工具搜索、入站/出站鉴权、API key/IAM/OAuth 凭证。
- Identity：覆盖 inbound/outbound auth、OAuth 2LO/3LO、IAM、Cognito/Auth0/Okta/EntraID 等 IdP，用于 agent 与外部资源的委托访问。
- Memory：覆盖短期记忆、长期记忆、conversation storage、semantic/summary/user-preference/episodic/self-managed 策略、memory branching、安全模式。
- Tools：包含 Code Interpreter 与 Browser Tool，用于隔离代码执行、数据分析、Web 自动化、Live View、Session Replay、CloudTrail 审计。
- Observability：以 CloudWatch GenAI Observability 和 OpenTelemetry 为核心，覆盖 Runtime-hosted、自托管、Lambda 调用、第三方观测平台。
- Evaluations：支持 built-in/custom evaluators、on-demand/online evaluation，基于 OTEL traces 评分并返回 score、explanation、token usage。
- Policy：使用 Cedar 与 Policy Engine 对 Gateway tool call 做细粒度 allow/deny，支持 LOG_ONLY 与 ENFORCE 模式。
- IaC：提供 CloudFormation、CDK、Terraform 样例，覆盖 basic runtime、MCP server、multi-agent runtime、weather agent with tools/memory。
- [推断] 吸收价值高：适合作为 AgentCore 能力地图、AWS agent 运行时/网关/身份/记忆/观测/评估/策略样例索引；但不适合直接照搬运行，因大量样例会创建 AWS 云资源并产生费用。

## 资产盘点

- 顶层实际目录：
  - `00-getting-started/`
  - `01-tutorials/`
  - `02-use-cases/`
  - `03-integrations/`
  - `04-infrastructure-as-code/`
  - `05-blueprints/`
- 主要资产类型：
  - Jupyter notebooks
  - Python agents/scripts
  - TypeScript/JavaScript frontend、CDK、MCP server 代码
  - Java agent samples
  - Dockerfile/container samples
  - CloudFormation YAML、Terraform HCL、CDK Python/TypeScript
  - OpenAPI/FHIR specs、Cedar policy demos
- 代表性依赖：`bedrock-agentcore`、`bedrock-agentcore-starter-toolkit`、`strands-agents`、`boto3`、`langchain[aws]`、`langgraph`、`opentelemetry-instrumentation-langchain`、`mcp>=1.9.0`。

## 关键文件

- `README.md`
- `00-getting-started/README.md`
- `01-tutorials/README.md`
- `01-tutorials/01-AgentCore-runtime/README.md`
- `01-tutorials/02-AgentCore-gateway/README.md`
- `01-tutorials/03-AgentCore-identity/README.md`
- `01-tutorials/04-AgentCore-memory/README.md`
- `01-tutorials/06-AgentCore-observability/README.md`
- `01-tutorials/07-AgentCore-evaluations/README.md`
- `01-tutorials/08-AgentCore-policy/01-Getting-Started/README.md`
- `02-use-cases/README.md`
- `03-integrations/README.md`
- `04-infrastructure-as-code/README.md`
- `05-blueprints/customer-support-agent-with-agentcore/README.md`
- `MIGRATION.md`

## 备注

- 云副作用明确：样例会使用 AWS credentials，并可能创建 CloudFormation stacks、IAM roles/policies、S3 artifacts/buckets、Lambda、CloudWatch Logs、ECR repositories、Cognito、AgentCore Runtime/Gateway/Memory/Policy resources。
- 成本提示明确：IaC README 标注 basic runtime/MCP server 约 `$50-100/month`，multi-agent runtime 约 `$100-200/month`，weather agent 约 `$100-150/month`。
- 权限要求偏高：入门样例需要 CloudFormation、S3、IAM role management、Lambda、CloudWatch Logs、Bedrock AgentCore；blueprint 示例建议 `AdministratorAccess` 和 `SignInLocalDevelopmentAccess`。
- 根 README 与本地目录命名存在差异：README 描述 `getting-started/`、`features/`、`end-to-end/`、`legacy/`；本地实际顶层为编号目录 `00-*` 到 `05-*`，未在顶层看到 `legacy/`。
- [推断] 文档吸收优先级：优先吸收 `01-tutorials/README.md` 的能力分类、`04-infrastructure-as-code/README.md` 的云资源/成本边界、`05-blueprints/customer-support-agent-with-agentcore/README.md` 的端到端架构；具体 notebook 内容可作为后续专题深挖材料。

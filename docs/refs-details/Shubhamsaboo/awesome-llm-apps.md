# Shubhamsaboo/awesome-llm-apps

- 上游仓库：`https://github.com/Shubhamsaboo/awesome-llm-apps`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/Shubhamsaboo/awesome-llm-apps`
- 主分类：**LLM 应用模板 / Agent 示例库**
- 能力标签：`AI Agents`, `Multi-agent`, `RAG`, `MCP`, `Voice Agents`, `Agent Skills`, `Fine-tuning`, `OpenAI`, `Gemini`, `Claude`, `Qwen`, `Llama`, `Streamlit`, `FastAPI`, `Next.js`
- 一句话总结：一个可运行的 LLM 应用 cookbook，收录 Agent、RAG、MCP、语音、多智能体、技能与微调示例模板。

## 能力概览

- README 按 13 个主题组织示例，覆盖入门 Agent、高级 Agent、多智能体团队、游戏 Agent、语音 Agent、MCP Agent、RAG、Agent Skills、记忆应用、Chat with X、优化工具、微调和框架速成。
- README 明确定位为 `ready-to-run templates`，强调每个模板包含完整源码，面向 fork、定制与交付。
- 技术主题集中在 Python LLM app、Streamlit、Gradio、FastAPI、Google ADK/Gemini、OpenAI Agents SDK、Agno、LangChain、Qdrant、Cohere、Next.js 和 React。
- `awesome_agent_skills/` 包含 Agent Skills 格式示例，覆盖代码、研究、写作、计划、数据分析、生产力等方向。
- `self-improving-agent-skills/` 更贴近本仓库 skills 体系：用 Google ADK、Gemini、FastAPI 和 Next.js 演示 skill 评测、诊断、变更和复跑闭环。
- [推断] 对本仓库最有吸收价值的是 `awesome_agent_skills/` 的 skill 结构、规则拆分方式，以及 self-improving skill 的评测闭环思路；大量 app demo 更适合作为参考案例而非直接迁入。

## 资产盘点

- 顶层内容目录包括：`starter_ai_agents/`、`advanced_ai_agents/`、`rag_tutorials/`、`mcp_ai_agents/`、`voice_ai_agents/`、`advanced_llm_apps/`、`awesome_agent_skills/`、`ai_agent_framework_crash_course/`、`docs/`。
- `starter_ai_agents/` 下有 16 个入门 agent 示例目录。
- `rag_tutorials/` 下有 23 个 RAG 示例目录。
- `mcp_ai_agents/` 下有 6 个 MCP agent 示例目录。
- `voice_ai_agents/` 下有 4 个语音 agent 示例目录。
- `ai_agent_framework_crash_course/` 下有 Google ADK 与 OpenAI SDK 两套课程目录。
- `awesome_agent_skills/` 下有 20 个 skill/app 目录，以及 `README.md`。
- `docs/banner/` 存放 README banner 资源。

## 关键文件

- `README.md`
- `LICENSE`
- `awesome_agent_skills/README.md`
- `awesome_agent_skills/code-reviewer/SKILL.md`
- `awesome_agent_skills/code-reviewer/AGENTS.md`
- `awesome_agent_skills/code-reviewer/rules/*.md`
- `awesome_agent_skills/self-improving-agent-skills/README.md`
- `awesome_agent_skills/self-improving-agent-skills/backend/app.py`
- `awesome_agent_skills/self-improving-agent-skills/backend/adk_optimizer.py`
- `awesome_agent_skills/self-improving-agent-skills/frontend/package.json`

## 备注

- README 与目录结构都显示该仓库不是纯 curated list，而是包含大量本地源码模板。
- License 为 Apache-2.0。
- [推断] 文档吸收时应把主价值放在“可运行 LLM app 模板库 + Agent Skills 样例/自优化闭环”，避免逐项罗列所有 app。

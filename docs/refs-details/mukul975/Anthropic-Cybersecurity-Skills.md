# mukul975/Anthropic-Cybersecurity-Skills

- 上游仓库：`https://github.com/mukul975/Anthropic-Cybersecurity-Skills`
- 本地路径：`/Users/zhenninglang/.dotfiles/refs/mukul975/Anthropic-Cybersecurity-Skills`
- 当前引用提交：`0f429d0`（`2026-05-13`，`Update README.md`）
- 主分类：**安全 / 网络安全技能库**
- 能力标签：`Agent Skills`, `cybersecurity`, `DFIR`, `threat hunting`, `threat intelligence`, `cloud security`, `malware analysis`, `MITRE ATT&CK`, `NIST CSF`
- 一句话总结：大规模 AI agent 网络安全 skill 库，把防守、检测、响应、取证、云安全、红队和渗透测试等安全任务组织成 `SKILL.md` 工作流，并配套 framework mapping、references、assets 与脚本。

## 能力概览

- [事实] `README.md` 声明仓库是独立社区项目，不隶属于 Anthropic PBC。
- [事实] `README.md` 与 `index.json` 当前口径为 754 个 cybersecurity skills、26 个 security domains、5 个 framework mappings。
- [事实] 本地实测 `skills/*/SKILL.md` 为 754 个，另有 6 个 `SKILL.es.md`、1330 个 `references/*.md`、280 个 `assets/*.md`、1032 个 `scripts/` 目录内文件。
- [事实] `README.md` 的 26 个领域包括 Cloud Security、Threat Hunting、Threat Intelligence、Web Application Security、Network Security、Malware Analysis、Digital Forensics、Security Operations、SOC Operations、Container Security、OT/ICS Security、API Security、Incident Response、Red Teaming、Penetration Testing、DevSecOps、Zero Trust、Mobile Security、Ransomware Defense 等。
- [事实] 本地 frontmatter 统计显示全部 754 个 `SKILL.md` 的 `domain` 均为 `cybersecurity`，高频 `subdomain` 包括 `cloud-security`、`threat-hunting`、`threat-intelligence`、`network-security`、`web-application-security`、`malware-analysis`、`digital-forensics`。
- [推断] 它更适合作为安全领域 playbook 和 taxonomy reference，不适合作为本仓库默认可触发 skill 的整包来源。

## 关键文件

- `README.md`：仓库定位、安装方式、26 个安全领域、framework mapping 声明、skill anatomy 和示例 prompt。
- `index.json`：skill 索引，记录 `total_skills: 754`、仓库 URL、生成时间和每个 skill 的基本元数据。
- `skills/`：主 skill 目录，每个 skill 至少包含 `SKILL.md`，部分附带 `references/`、`scripts/`、`assets/`。
- `ATTACK_COVERAGE.md`：MITRE ATT&CK coverage map，记录 unique techniques、tactics 和 skill 映射。
- `mappings/`：ATT&CK Navigator layer、MITRE ATT&CK、NIST CSF、OWASP 相关 mapping 文档。
- `tools/validate-skill.py`：stdlib-only 的 `SKILL.md` frontmatter 校验脚本。
- `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`：Claude plugin / marketplace 元数据。
- `CONTRIBUTING.md`：新增 skill 的目录结构、frontmatter 字段、正文 section 和质量 checklist。
- `SECURITY.md`：漏洞报告范围与安全披露流程。

## Skill 结构观察

- [事实] `CONTRIBUTING.md` 要求新 skill 使用 `skills/<skill-name>/SKILL.md`，并包含 `name`、`description`、`domain`、`subdomain`、`tags`、`version`、`author`、`license` 等 frontmatter 字段。
- [事实] `README.md` 示例额外展示了 `atlas_techniques`、`d3fend_techniques`、`nist_ai_rmf`、`nist_csf` 等 mapping 字段。
- [事实] `CONTRIBUTING.md` 推荐正文包含 `When to Use`、`Prerequisites`、`Workflow`、`Key Concepts`、`Tools & Systems`、`Common Scenarios`、`Output Format`。
- [事实] `README.md` 展示的典型目录结构是：

```text
skills/performing-memory-forensics-with-volatility3/
├── SKILL.md
├── references/
│   ├── standards.md
│   └── workflows.md
├── scripts/
│   └── process.py
└── assets/
    └── template.md
```

- [推断] 对本仓库可复用的是“短入口 `SKILL.md` + 深入 `references/` + 输出 `assets/template.md` + 可审计脚本”的 progressive disclosure 组织方式。

## Framework mapping 观察

- [事实] `README.md` 声称覆盖 MITRE ATT&CK、NIST CSF 2.0、MITRE ATLAS、MITRE D3FEND、NIST AI RMF 五类框架。
- [事实] 本地 frontmatter 统计显示：`nist_csf` 出现在 754 个 skill，`d3fend_techniques` 出现在 139 个 skill，`nist_ai_rmf` 出现在 85 个 skill，`atlas_techniques` 出现在 81 个 skill。
- [事实] `ATTACK_COVERAGE.md` 记录 MITRE ATT&CK 覆盖 291 个 unique techniques、149 个 parent techniques、14 个 Enterprise ATT&CK tactics。
- [事实] `mappings/README.md` 记录的旧口径是 `Total skills scanned: 742`、Enterprise ATT&CK v14；`ATTACK_COVERAGE.md`、`README.md` 和 `mappings/mitre-attack/README.md` 中 ATT&CK 版本与统计口径不完全一致。
- [推断] 该仓库的 mapping 思路有参考价值，但 mapping 数据不宜作为权威 SSOT 直接导入本仓库。

## 安全与适配风险

- [事实] 仓库包含 dual-use/offensive skill，例如 exploit、C2 infrastructure、red team、phishing simulation、credential access、lateral movement 等主题。
- [事实] 部分 `scripts/` 可能执行网络请求、部署规则、写文件或访问外部系统；例如安全工具集成类脚本会读取 token、调用 API 或生成配置。
- [事实] 数量口径存在漂移：`README.md`、`index.json`、`.claude-plugin/marketplace.json` 写 754；`.claude-plugin/plugin.json` 写 753；`ATTACK_COVERAGE.md` 写 753+；`mappings/README.md` 写 742。
- [事实] `tools/validate-skill.py` 主要校验 frontmatter 基础字段、命名、描述长度、domain 和 subdomain，不校验 framework ID 有效性，也不校验正文必备 section。
- [推断] 如果直接并入本仓库的可触发 skills，会增加误触发 offensive 操作、外部 API 副作用和未授权安全测试的风险。

## 对本仓库的参考价值

1. **安全领域 taxonomy**：可借鉴其 security domain/subdomain 划分，用于本仓库 `guard-*`、`security-review`、`threat-model` 相关能力盘点。
2. **framework coverage 表达**：可参考 ATT&CK/NIST/OWASP mapping 的覆盖矩阵形式，但必须建立本仓库自己的可验证 mapping SSOT。
3. **结构化安全 playbook**：`When to Use`、`Prerequisites`、`Workflow`、`Verification`、`Output Format` 适合用于安全审查和事件响应类 skill 的固定骨架。
4. **references 分册模式**：长标准、流程、API、工具说明应下沉到 `references/`，避免把主 `SKILL.md` 写成大百科。
5. **模板化输出**：`assets/template.md` 适合作为 threat model、security finding、IR report、detection rule、evidence checklist 的格式参考。
6. **校验脚本思路**：可借鉴轻量 validator，但本仓库应补 framework ID、危险能力标记、授权边界、必备 section 和脚本副作用检查。

## 不建议照搬

- 不建议整包安装或复制 754 个 skill 到本仓库默认 `skills/`。
- 不建议把 exploit、C2、post-exploitation、phishing simulation 等 offensive workflow 做成自动触发能力。
- 不建议直接复用其 “every skill mapped to five frameworks” 叙述，除非本仓库有独立校验脚本证明。
- 不建议直接执行其 `scripts/`；如需参考，应先逐个审计网络、凭据、文件写入和外部系统副作用。
- 不建议把其数量、版本、coverage 统计写成本仓库权威事实；引用时应注明取自对应文件和提交。

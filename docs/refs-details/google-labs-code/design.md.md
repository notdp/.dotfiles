# google-labs-code/design.md

- 上游仓库: `https://github.com/google-labs-code/design.md`
- 本地路径: `/Users/zhenninglang/.dotfiles/refs/google-labs-code/design.md`
- Source SHA: `2a19f5dd97ab887971b417ebdf1e7e8fda0c7f79`（upstream HEAD）。**注意：本仓库以普通 vendored 文件形式存在（非 git submodule，不在 `.gitmodules`），2026-05-06 落地**，故无法用 `git submodule status` 核对血缘——见下文"血缘异常"。
- 主分类: **前端 UI / 设计系统**
- 能力标签: `DESIGN.md 格式规范`, `设计 token schema`, `确定性 linter`, `WCAG 对比度校验`, `token 引用解析+环检测`, `DTCG/Tailwind 互转`, `diff 回归门禁`, `few-shot 样例库`
- 一句话总结: DESIGN.md 是给 coding agent 的"视觉契约"格式（YAML token 层 + markdown 解释层），配套 `@google/design.md` 这个 agent-first CLI（lint/diff/export/spec）把美学约束变成可机器校验、可跨格式互转、可回归门禁的确定性产物。本仓库**已吸收格式与模板**，整条 CLI 自动化与 token 解析引擎是 **delta**。

## 血缘异常（需决策）

[事实] `git ls-files refs/google-labs-code/design.md/README.md` 返回 mode `100644`（普通文件），且 `.gitmodules` 无 `design.md` 条目——它不是 submodule，而是 2026-05-06 直接 copy 进仓库的 vendored 文件，与本仓库其余 refs 的"submodule pin commit"约定不一致。后果：无法自动判断它落后 upstream 多少。建议择机转为 submodule 统一血缘，或在此显式记录"vendored at upstream `2a19f5d`"。

## 核心机制

DESIGN.md 把"美学输入"拆成两层：YAML front matter 放机器可读 token（colors/typography/rounded/spacing/components），markdown body 放人类可读 rationale + Do/Don't；token 用 `{path.to.token}` 跨引用，**tokens 是规范值、prose 是上下文**（spec.md:8）。配套 CLI 把这份契约变成可执行工程产物：

1. **`lint`**：parser（remark）抽 front matter + H2 section → model 解析 token + 解引用 + 算 WCAG 亮度 → 7+ 条确定性规则产结构化 JSON findings（带 severity/path/message），errors>0 则 `exit 1`。
2. **`diff old new`**：token 级 added/removed/modified + `warnings/errors 变多即 regression`（exit 1）当 CI 门禁。
3. **`export --format css-tailwind|json-tailwind|dtcg`**：把同一份 token 喷成 Tailwind v4 `@theme` CSS / v3 `theme.extend` JSON / W3C DTCG `tokens.json`，token 成构建 SSOT。
4. **`spec [--rules-only]`**：把格式规范本身喷进 agent prompt；规范由 `spec-config.yaml`（SSOT）codegen 出 `docs/spec.md`，规范与 linter 同源不漂移。

## 关键设计

- **token 是规范值 / prose 是上下文的双层契约**：[事实] spec.md:8 `The tokens are the normative values; the prose provides context`。prose 可用描述性色名（Midnight Forest Green）对应系统 token 名（primary）。本仓库 `fe-ui-design-system` 已吸收双层结构，**但没吸收 "token 为 normative" 的校验闭环**。
- **确定性 linter 7+ 条规则各固定 severity**：[事实] broken-ref(error) / missing-primary(warning) / contrast-ratio(warning) / orphaned-tokens(warning) / section-order(warning) / missing-sections(info) / token-summary(info)。每条是纯函数 `RuleDescriptor{name,severity,description,run}`，runner 用 flatMap 聚合，可注入自定义规则。把"AI slop 禁用项"从 prompt 约束升级为可执行 lint。
- **WCAG 对比度内置进 token 校验**：[事实] `model/handler.ts` 解析 hex 时即算 WCAG 2.1 相对亮度（sRGB 线性化），`contrast-ratio.ts` 对每组件 backgroundColor/textColor 对算 `(L1+.05)/(L2+.05)`，低于 4.5:1 报 warning。把可访问性从交付前人工检查前移到契约校验。
- **链式 token 引用解析 + 环检测**：[事实] `resolveReference` 用 visited Set 防环 + `MAX_REFERENCE_DEPTH=10` 防深链，分 Phase 解析。让 `{colors.primary-60}` 成为可验证的图而非纯文本约定。
- **diff 作为回归门禁**：[事实] `commands/diff.ts`：`regression = after.errors>before.errors || after.warnings>before.warnings`，exit code = regression?1:0。把设计系统演进纳入 CI 可挡退化——这是本仓库 `/design-md` 完全没有的能力。
- **orphaned-tokens 内置 Material Design 3 家族语义**：[事实] `colorFamily()` 剥离 MD3 前后缀（on-/inverse-/-container/-fixed/-dim）归并家族根，`MD3_STANDARD_FAMILIES` 白名单永不报 orphan。**说明该 spec 隐含锚定 MD3 命名体系**——非 MD3 项目会误报。
- **容错优先 + 未知内容行为表**：[事实] parser/handler `Never throws — all errors returned as Result failures`；spec.md:344-356 给未知内容行为表（未知 section→保留不报错 / 未知 token→值合法即接受 / 重复 section→报错拒绝）。

## 资产盘点

| 资产 | 说明 | 规模 |
|---|---|---|
| `docs/spec.md` | DESIGN.md 格式权威规范（由 spec-config.yaml codegen）：token schema、8 个有序 section、未知内容行为表 | 356 行 |
| `packages/cli/src/linter/spec-config.yaml` | 格式规范单一来源：units/sections/typography/component_sub_tokens/color_roles/examples | 145 行 |
| `packages/cli/src/linter/linter/rules/` | 7+ 条确定性 lint 规则各自纯函数 + `.test.ts` | ~22 文件 |
| `packages/cli/src/linter/model/handler.ts` | token 解析引擎：hex→RGB+WCAG 亮度、链式引用解析+环检测、`contrastRatio()` | 413 行 |
| `packages/cli/src/commands/{lint,diff,export,spec}.ts` | 四个 CLI 命令 | — |
| `examples/{paws-and-paths,atmospheric-glass,totality-festival}/DESIGN.md` | 3 个完整真实样例（含 design_tokens.json + tailwind.config.js + README） | — |
| `packages/cli/src/linter/fixtures/*.md` | 9 个 lint fixture（HERITAGE/MERIDIAN/OUT_OF_ORDER/NO_FRONTMATTER…），天然反例语料 | 9 个 |

## 与本仓库映射 + 吸收裁决

详细裁决见 [`docs/refs-update-absorption-2026-06-25.md`](../../refs-update-absorption-2026-06-25.md)。摘要：

**已覆盖（不重复吸收）**：DESIGN.md 双层格式 + "token 规范值 / prose 上下文" + 按角色命名 token + Do/Don't 已被 `fe-ui-design-system` + `commands/design-md.md` 吸收（design-md.md:42 已直接引用本 spec.md）；DESIGN.md 工作流编排（init→use→critique→verify）已由 `commands/design-md.md` 覆盖。

**吸收候选（upstream 最大真实 delta = 整条 CLI 校验闭环）**：

| 候选 | classify | 落点 | Level | 裁决 |
|---|---|---|---:|---|
| DESIGN.md token-graph 语义 linter（broken-ref/section-order/orphaned-tokens 三条结构规则 + hex→WCAG 解析引擎底座） | script | new `scripts/lint_design_md.py` | L3 | **absorb**（最高优先；upstream 9 fixtures 是现成测试反例） |
| diff 回归门禁（`--diff old new`，warnings 变多即 regression） | script | `lint_design_md.py` 子命令 | L3 | **absorb**（依赖 lint 先落地） |
| 3 样例 + 9 fixtures 作为 few-shot 语料指针 | docs | 本文件 + `fe-ui-design-system` 加路径指针 | L1 | **absorb**（只放路径，不 inline） |
| 未知内容消费行为表 | guardrail | `commands/design-md.md` 边界段 | L2 | **absorb** |
| 多格式 export（DTCG/Tailwind 互转） | script | — | L1 | research-later（强依赖项目技术栈，无高频需求） |
| spec-config codegen（规范=校验器=prompt 同源） | method | 本文件记录 | L1 | observe（lint 规则 <10 条时引 codegen 是过度工程） |

## Premise collapse 与风险

- **只硬化客观规则**：WCAG 对比度数学、token 断引用、section 顺序、孤儿 token 可安全硬化；**绝不能把 token 命名/配色外推成审美正误**——orphaned-tokens 只报"自定义 token 未被引用"（机械事实），不能升格为"这个配色丑"。
- **MD3 白名单需可配置**：[未验证] orphaned-tokens 内置 MD3 家族白名单，若本仓库 DESIGN.md 不锚定 MD3 命名会对自定义 token 大量误报；吸收前需确认白名单可配置化。
- **schema 对齐前不可启用**：[未验证] 本仓库 `fe-ui-design-system` 产出的 DESIGN.md 是否严格遵循本 spec 的 `{path.to.token}` 语法与 8-section 顺序，尚未核对；若不一致，lint 会对自家产物大面积误报。
- **只移植算法最小子集**（80–120 行 Python：PyYAML + 引用解析 + hex→亮度），不全量搬 413 行 TS handler + remark parser + bun/turbo codegen（后者引入外部构建依赖）。
- **门禁不僵死**：diff regression 与 lint exit-code 若直接接进交付硬门，会把"有意收缩 token 集 / 合理的大字号低对比"误判为退化阻塞；必须保留 `--baseline` 显式更新、WCAG 大字号阈值标注"人工复核"，findings 默认"候选"非"绝对正误"。
- 许可：Apache-2.0（吸收 lint 算法为 clean-room 重写，非搬运）。

# Skill 近邻区分度 baseline（2026-06-25）

/ think-* + guard-* 簇 description 的近邻相似度一次性基线。背景见 [harness-governance-prd](./harness-governance-prd-2026-06-23.md) 的 A3（人工重写 19 条 description）。

## 为什么做这个

A3 手工重写了相邻 skill 的 description 让它们「可分」，但**没有任何自动量化器**证明真的拉开了 —— 只有「我重写了所以应该可分」的主观结论。本 baseline 用一次性 spike 量化回答：think-/guard- 簇里最容易混的 description 对，到底有多近？

## 方法（可丢弃 spike，未落成常驻工具）

- 语料：`coding-skills/{think-*,guard-*}/SKILL.md` 的 `description:` 字段（**不是** `catalog.json`，其 description 字段为空 0/65）。
- 向量：零依赖 TF-IDF（中英混合 tokenize = latin 词 + CJK 单字 + CJK bigram），两两余弦。
- 判据：已知易混对（research/survey/compare、map/context-map/ask-context/scope、check/close/verify/review/secure）是否聚在 Top；绝对分是否有「危险接近」的对。

> 决策：**不落 `scripts/skill_neighbor_eval.py` 常驻工具**（见下「结论」——已无火可救）。本文件即一次性产物；未来若怀疑某次 description 改动拉近了近邻，按上述方法手工复跑即可。

## 结果（N=25 skills，300 对）

Top-15 最相似对（★ = 已知易混）：

| rank | cos | pair |
|------|-----|------|
| 1 | 0.298 | ★ think-research ~ think-survey |
| 2 | 0.292 | ★ think-context-map ~ think-scope |
| 3 | 0.287 | ★ think-research ~ think-compare |
| 4 | 0.281 | ★ think-context-map ~ think-map |
| 5 | 0.268 | ★ guard-review ~ guard-verify |
| 6 | 0.229 | ★ think-survey ~ think-compare |
| 7 | 0.228 | think-map ~ think-scope |
| 8 | 0.224 | guard-secure ~ guard-threat-model |
| 9 | 0.220 | ★ think-ask-context ~ think-context-map |
| 13 | 0.163 | ★ guard-check ~ guard-verify |
| 15 | 0.152 | ★ guard-review ~ guard-secure |

全部 10 个已知易混对落在 Top-20 / 300（#1,2,3,4,5,6,9,13,15,20）。Bottom：`think-architecture ~ guard-gitops`、`think-plan ~ guard-mysql-review` ≈ 0.00。

## 结论

1. **方法有效**：TF-IDF 余弦干净地把真近邻排到顶、不相干排到底，可作为未来回归复查的排序器。
2. **无火**：最高相似仅 **0.298**，没有任何一对危险接近（如 >0.6 的近重复）。**A3 那轮重写已把 description 拉得足够开**。
3. **无新混淆对**：Top 候选几乎全是 AGENTS.md 第 67-74 行已手工消歧的对。唯一不在该清单的 `guard-secure ~ guard-threat-model`（#8）也**已在 description 层消歧**——guard-secure 明写「不用于建立项目级威胁模型 SSOT→改用 guard-threat-model」，且二者是 threat-model→secure 的**先后**关系（AGENTS.md 59-60）而非二选一。
4. **决策**：#3「语义评测」缺口比预估小，A3 已基本解决。不建常驻工具，零动作需要。本 baseline 作为未来回归对照。

## 复查触发条件（未来）

改了某条 think-/guard- 的 `description:` 且担心拉近近邻时，手工复跑本方法，对照本基线：若某对从 <0.30 跳到明显更高，说明该次改动稀释了区分度，回看是否需补互斥判别式。

# 风格契约 schema（style-contract）

> 承载某个账号/作者的**声音（voice）与偏好**，与 skill 解耦。写作 skill 读取它来个性化产出，
> 而不是把人格硬编进 SKILL.md。借鉴 baoyu-skills 的 style 文件六段式 + EXTEND.md 三级配置。

## 存放位置（三级，就近覆盖）

1. 创作项目根 `EXTEND.md` 或 `.writing/style.md`（项目级，最高优先级）
2. 用户级 `~/.config/writing/style.md`（跨项目默认）
3. 不存在时：skill 用保守默认 + 现场问 1–2 个问题补齐，不擅自假设。

## 字段 schema

```yaml
# style-contract
voice:
  persona: "一句话定位作者/账号（如：写给技术人的 AI/Agent 实践者）"
  tone: ["克制", "有观点", "口语但不油"]      # 语气关键词，3-5 个
  person: "第一人称『我』/ 中性 / 团队『我们』"  # 称谓人称
  rhythm: "长短句交替，允许单句成段"            # 节奏偏好
avoid:                                          # 负向约束（Avoid 段，压漂移最关键）
  - "夸张象征与宏大叙事"
  - "三段式排比"
  - "营销腔与空话（赋能/抓手/闭环）"
banned_words: ["赋能", "抓手", "闭环", "干货满满"]  # 该账号明确禁用词，叠加在 writing-constraints 之上
lexicon:                                         # 该账号特有口语词/术语（白名单）
  preferred: ["碎碎念", "顺手", "踩坑"]
signature:
  sign_off: "署名/结尾惯例（可空）"
  cta: "默认 CTA 措辞（可空）"
best_for: ["公众号长文", "技术随笔"]             # 适用体裁
corpus_ref: "assist-write-corpus 产出的语料库路径（可空）"
```

## 使用约定

- `writing-constraints.md` 是**全员下限**；style-contract 是**某账号的个性叠加**，只能加严不能放松硬约束（不能用 style-contract 解禁 em dash 等 [硬] 条款）。
- `banned_words` / `avoid` 与 writing-constraints 的 AI 套话表**并集**生效。
- skill 找不到 style-contract 时按保守默认，并提示用户可建一份以获得稳定声音。

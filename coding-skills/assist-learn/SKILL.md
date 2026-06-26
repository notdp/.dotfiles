---
name: assist-learn
description: 当完成一轮实现、排障或调研后，需要把经验提炼为可复用规则、模板或操作卡时使用；输出 learning note 并沉淀可复用模式。
argument-hint: <主题|变更|经验点>
---

# Assist Learn

把一次性的解决过程沉淀成可复用资产，而不是只停留在聊天记录里。

## 何时使用

- 刚完成一个功能、bug 修复或调研，想把经验留下来
- 同类问题未来还会重复出现，需要可复用 checklist / template / pattern
- 需要给自己或团队写 handoff note

## 默认流程

1. 先写清楚背景、触发条件和最终结果
2. 提炼“这次真正学到的模式”，不是流水账
3. 记录证据、边界和下次可复用的动作
4. 需要骨架时运行 `${HOME}/.dotfiles/coding-skills/assist-learn/scripts/scaffold_note.py`
5. 落点：写入当前项目的 `docs/learnings/<category>/<slug>.md`（canonical store），顶部 frontmatter（`title`/`date`/`problem_type`/`module`/`component`/`tags`）便于检索

## Read-side 回查（opt-in，开工前可选）

吸收自 compound-engineering 的复利闭环（`docs/refs-details/EveryInc/compound-engineering-plugin.md`）：写入的经验只有被回查才产生复利。开工前可主动搜历史经验，**这是 opt-in 工具，不自动注入每个流程**：

```bash
python3 ${HOME}/.dotfiles/coding-skills/assist-learn/scripts/learnings_search.py <关键词...>   # 默认搜 ./docs/learnings
```

返回 top 命中的路径 + frontmatter 摘要（不展开全文）；命中后再打开对应 note 读 Reusable Pattern。debug / plan / research 前判断"是否踩过同类问题"时尤其值得先跑一次。

## `/assist-consolidate`（显式 memory 巩固模式）

`/assist-consolidate` 是 assist-learn 的显式模式，不是独立 skill，也不是热路径 hook。它消费 `memory/.staging/raw_memories/*.json` 这类机械候选，把通过验证的候选提纯为 tracked `memory/user/*.md` 或当前项目 `docs/learnings/*.md`。

```bash
python3 ${HOME}/.dotfiles/coding-skills/assist-learn/scripts/assist_consolidate.py --root . --raw-dir memory/.staging/raw_memories --decision-file decisions.json
```

核心规则：

- 机械候选是不可信输入：必须有 evidence、implication、origin_session，并通过反自我毒化黑名单与 promote 判据后才可写入。
- promote 判据：候选进 user memory 需要跨 session 复现、`decision+why/evidence`、用户显式标记，或 vault 候选带 commit 与 verify 证据；不达标只 SKIP，不固化。
- structured decision 必填：生产路径不默认 ADD；`--decision-file` 可以是单候选 `{"action":"ADD"}`，批量时用 `{candidate_id:{"action":"ADD|UPDATE|SKIP|INVALIDATE"}}`，测试 fixture 不调用 live LLM。
- fail-closed redact：写 tracked `memory/user/*.md`、`memory/user/INDEX.md`、`docs/learnings/*.md` 前必须调用共享 redact gate；命中 secret-like 内容时拒写，不要求 hook 捕获兜底。
- 禁止裸物理 DELETE：`DELETE`/`INVALIDATE`/矛盾 UPDATE 只能做软失效；UPDATE 既有 note 时归档旧 note、写候选为新 note，并让旧 note 的 `superseded_by` 指向新 note id。
- 业务 repo gate：写 `docs/learnings/` 前区分 `internal/client/oss`；client/oss 默认拒写跨项目知识，除非有显式批准。

## 资产

- `references/learning-loop.md`
- `templates/learning-note.md`（含检索用 frontmatter）
- `${HOME}/.dotfiles/coding-skills/assist-learn/scripts/scaffold_note.py`
- `${HOME}/.dotfiles/coding-skills/assist-learn/scripts/learnings_search.py`（opt-in 历史经验检索）
- `${HOME}/.dotfiles/coding-skills/assist-learn/scripts/assist_consolidate.py`（显式 `/assist-consolidate` memory 巩固入口）

## 边界

- 工作失误、判断偏差、协作问题或流程事故的多轮复盘 → 先用 `/assist-retrospect`
- 复盘后需要把可迁移经验沉淀为模板 / 操作卡 → 回到 `/assist-learn`
- 不要从目标项目 cwd 运行 `${HOME}/.dotfiles/coding-skills/assist-learn/scripts/scaffold_note.py`；该脚本是本 skill 自带资产

## Gotchas

- 不要把时间线复述当成学习沉淀；重点是可复用模式
- 不要只写结论不写边界；适用条件不清的经验价值很低
- 不要把未验证猜测包装成经验规则
- 反自我毒化黑名单：不要把环境依赖型失败（缺二进制、缺凭证、PATH/权限未配置）、对工具的持久负面断言（如“某工具不能用”）、已解决的瞬时错误、一次性任务叙事写成长期 memory/learning 规则
- 可沉淀的是修复办法、证据和适用边界：记录“在什么环境下如何恢复/验证”，不要记录会长期误导 agent 的否定结论
- `/assist-consolidate` 的 ADD/UPDATE/SKIP 决策不等于事实已验证；只有满足 promote 判据且过 fail-closed redact 的内容才进入 tracked store

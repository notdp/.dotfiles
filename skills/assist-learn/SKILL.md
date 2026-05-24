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
4. 需要骨架时先解析本 skill 的安装目录，运行 `<skill_dir>/scripts/scaffold_note.py`

## 资产

- `references/learning-loop.md`
- `templates/learning-note.md`
- `scripts/scaffold_note.py`

## 边界

- 工作失误、判断偏差、协作问题或流程事故的多轮复盘 → 先用 `/assist-retrospect`
- 复盘后需要把可迁移经验沉淀为模板 / 操作卡 → 回到 `/assist-learn`
- 不要从目标项目 cwd 运行 `scripts/scaffold_note.py`；该脚本是本 skill 自带资产

## Gotchas

- 不要把时间线复述当成学习沉淀；重点是可复用模式
- 不要只写结论不写边界；适用条件不清的经验价值很低
- 不要把未验证猜测包装成经验规则

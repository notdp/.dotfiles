---
name: think-context-map
description: 当某次具体任务要改动多个文件或影响面不明、需要在实施前圈定改动范围时使用；产出单次任务的文件地图（Files to Modify + Dependencies + Test Files + Reference Patterns + Risk checklist）。不用于仓库全局地图（改用 think-map）、回答问题前的轻量信息需求清单（改用 think-ask-context）、还没和用户对齐要解决什么问题（先用 think-scope）。
---

# Context Map

在实施任何改动前，分析代码库并产出一份"单次任务的上下文地图"。

## Decision Principles

- `think-context-map` 优化的是单次改动的影响面控制，不是生成仓库百科。
- 地图必须支持一个可执行 plan：改哪些文件、同步影响谁、参考什么模式、跑哪些测试、最大风险是什么。
- 只列会改变实现或验证策略的上下文；无关文件即使相似也不要塞进表格。
- 当 Files to Modify、Dependencies、Test Files、Reference Patterns 和 Risk Assessment 足以支撑实施时停止，避免把调研扩成无边界搜索。

## 输入

{{task_description}}

## 指令

1. 在代码库中搜索与任务相关的文件
2. 识别直接依赖（imports / exports / 调用关系）
3. 找出相关测试
4. 查找类似模式的参考代码

## 输出格式

```markdown
## Context Map

### Files to Modify
| File | Purpose | Changes Needed |
|------|---------|----------------|
| path/to/file | <它的职责> | <要改什么> |

### Dependencies（可能需要同步改）
| File | Relationship |
|------|--------------|
| path/to/dep | imports X from modified file |

### Test Files
| Test | Coverage |
|------|----------|
| path/to/test | <覆盖了受影响的什么功能> |

### Reference Patterns（可参考的已有实现）
| File | Pattern |
|------|---------|
| path/to/similar | <可借鉴的模式> |

### Risk Assessment
- [ ] Breaking changes to public API
- [ ] Database migrations needed
- [ ] Configuration changes required
- [ ] 跨模块 / 跨子系统依赖
```

地图 review 通过前不要进入实施。

## 与其他 skill 的边界

- `think-map` 做整个仓库全局地图（技术栈、目录约定），范围是仓库
- 本 skill 做单次任务的文件地图，范围是任务
- `think-ask-context` 只声明信息需求不铺展依赖，比本 skill 更轻

## Gotchas

- 不要把不相关的文件塞进 Files to Modify 充数
- Dependencies 只列"可能需要同步改"的，不列所有 imports
- Risk Assessment 如果全部为空，考虑任务是否真的足够小、是否需要本 skill

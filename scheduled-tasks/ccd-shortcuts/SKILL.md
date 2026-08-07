---
name: ccd-shortcuts
description: 每天输出 Claude Code Desktop 快捷键全量表，并在表内标记出相对昨天的新增 / 改键
---

每天输出 Claude Code Desktop（`/Applications/Claude.app`）的**快捷键全量表**，翻译成中文，并在表内标记出相对上次的变化。

## 步骤

1. 运行提取脚本。它产出一份完整的 Markdown 全量表（三个 section），变化行已用 🆕 / ✏️ 标好：

```bash
python3 ~/.claude/scheduled-tasks/ccd-shortcuts/extract.py
```

2. **把表格重新输出给我，"命令 / 说明"那一列全部翻成中文。**

   - 标签是从 app bundle 里扒出来的英文（`Toggle sidebar`）或内部命令名（`cycleTranscriptMode`），**你直接翻，不要保留英文原文**。用户英文不好，看不懂英文表格等于白给。
   - 翻译要说人话、说清楚**实际效果**，不要字面直译。例：`cycleTranscriptMode` → "循环切换 transcript 视图"，不是"循环转录模式"；`Send in a forked session` → "发到 fork 出的新会话（仅本地会话）"。
   - 遇到含义拿不准的命令，去 bundle 里搜它的实现再翻，别猜。查法：在 `/Applications/Claude.app/Contents/Resources/ion-dist/assets/v1/*.js` 里搜该命令名——文件名带 hash 每次更新都变，**必须按内容搜，不要按文件名**；用 `python3 -c` 配合 `re`，`grep` 在这些超长单行压缩文件上会因复杂度超限而失败。
   - 三个 section 全都要，不要节选、不要只列变化、不要因为长就压成摘要。
   - 脚本输出末尾若有 `<!-- CHANGELOG ... -->` 注释块，不要显示给我，那是给你看的。

3. 表格**之后**追加一段中文说明：

   - **有变化时**（表头写着"共 N 处变动"，N > 0）：逐条讲清楚每个 🆕 / ✏️ / 移除项对应界面上什么操作、值不值得记。
   - **无变化时**（N = 0）：只写一行"相比上次无变化"，然后从全量表里挑 2–3 个我大概率还不知道、但实用的快捷键，各用一句话讲讲。不要每天重复推荐同样的几个。

4. **stderr 出现 WARN 或 ERROR** —— 说明 bundle 结构变了、正则失效，**不是快捷键被删了**。此时明确告诉我 `extract.py` 需要修，指出哪个 section（pane / registry / modal）解析不出来了，并给出你判断的新结构。绝对不要把解析失败汇报成"快捷键被移除"。

## 三个 section 的含义

- **pane** —— 面板/输入框硬编码键位表，这一列是内部命令名。**其中一部分不出现在 ⌘/ 弹窗里**（例如 `⌃O` 循环 transcript 视图），这类"隐藏快捷键"是重点，新出现时要特别指出。
- **registry** —— 全局命令注册表，带界面上的英文标签。
- **modal** —— ⌘/ 内置弹窗里实际渲染的行，即官方文档化的那批。

同一个键在不同 section 含义可能不同（例如 `⌘⇧I` 在 pane 层是模型菜单、在注册表里是 Import issue / 无痕对话），汇报时注意区分，别当成冲突。

快照存在 `~/.claude/scheduled-tasks/ccd-shortcuts/snapshot.json`，脚本每次运行后自动更新。
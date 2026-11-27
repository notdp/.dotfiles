---
name: ccd-shortcuts
description: 每周一 10:17 输出 Claude Code Desktop 快捷键全量表，并标记相对上次的新增 / 改键
---

每周输出 Claude Code Desktop（`/Applications/Claude.app`）的**快捷键全量表**，翻译成中文，并在表内标记出相对上次的变化。

## 步骤

1. 运行提取脚本。它产出一份完整的 Markdown 全量表（三个 section），变化行已用 🆕 / ✏️ 标好：

```bash
python3 ~/.claude/scheduled-tasks/ccd-shortcuts/extract.py
```

2. **把表格重新输出给我，"命令 / 说明"那一列全部翻成中文。**

   - 标签是从 app bundle 里扒出来的英文（`Toggle sidebar`）或内部命令名（`cycleTranscriptMode`），**你直接翻，不要保留英文原文**。用户英文不好，看不懂英文表格等于白给。
   - 翻译要说人话、说清楚**实际效果**，不要字面直译。例：`cycleTranscriptMode` → "循环切换 transcript 视图"，不是"循环转录模式"；`Send in a forked session` → "发到 fork 出的新会话（仅本地会话）"。
   - 遇到含义拿不准的命令，去 bundle 里搜它的实现再翻，别猜。用脚本自带的 `--grep`：

     ```bash
     python3 ~/.claude/scheduled-tasks/ccd-shortcuts/extract.py --grep 'cycleTranscriptMode'
     ```

     参数是 Python 正则，按内容搜全部已缓存 chunk，命中处前后各打印约 240 字符并标出所在 chunk 文件名。
     不要自己去 `/Applications/Claude.app` 里翻：6.x 起本地只剩一个占位页，界面代码是从 claude.ai 远程加载的，落在 Electron 的 HTTP 缓存里，且多数是 zstd 压缩，`grep` 和 `cat` 都搜不到。
   - 三个 section 全都要，不要节选、不要只列变化、不要因为长就压成摘要。
   - 脚本输出末尾若有 `<!-- CHANGELOG ... -->` 注释块，不要显示给我，那是给你看的。

3. 表格**之后**追加一段中文说明：

   - **有变化时**（表头写着"共 N 处变动"，N > 0）：逐条讲清楚每个 🆕 / ✏️ / 移除项对应界面上什么操作、值不值得记。
   - **无变化时**（N = 0）：只写一行"相比上次无变化"，然后从全量表里挑 2–3 个我大概率还不知道、但实用的快捷键，各用一句话讲讲。不要每天重复推荐同样的几个。

4. **stderr 出现 WARN 或 ERROR** —— 说明 bundle 结构变了、正则失效，**不是快捷键被删了**。此时明确告诉我 `extract.py` 需要修，指出哪个 section（pane / registry / modal）解析不出来了，并给出你判断的新结构。绝对不要把解析失败汇报成"快捷键被移除"。

   stderr 里还有三行 `source:`，写明每个 section 是从哪个 chunk 读出来的、那份缓存是什么时候落盘的。只在排查"这行怪数据哪来的"时看它；**日期不等于版本新旧**——内容没变的 chunk 跨版本不会被重新写入，日期旧不代表过时。

   当前已知待修（不是缺快捷键，是解析不全）：modal 一节 130 行里只认出 89 行，另有 2 行标签、5 行键位解析不出来。脚本会把上次快照里对应的行原样带过来，所以表是全的，但这几行的值可能滞后一轮。

## 三个 section 的含义

- **pane** —— 面板/输入框硬编码键位表，这一列是内部命令名。**其中一部分不出现在 ⌘/ 弹窗里**（例如 `⌃O` 循环 transcript 视图），这类"隐藏快捷键"是重点，新出现时要特别指出。
- **registry** —— 全局命令注册表，带界面上的英文标签。
- **modal** —— ⌘/ 内置弹窗里实际渲染的行，即官方文档化的那批。

同一个键在不同 section 含义可能不同（例如 `⌘⇧I` 在 pane 层是模型菜单、在注册表里是 Import issue / 无痕对话），汇报时注意区分，别当成冲突。

快照存在 `~/.claude/scheduled-tasks/ccd-shortcuts/snapshot.json`，脚本每次运行后自动更新。

数据来源是 Electron 的 HTTP 缓存（`~/Library/Application Support/Claude/Cache/Cache_Data`），也就是"这台机器最近加载过的 chunk"，不是完整 bundle。某个界面长期没打开，对应的 chunk 可能根本不在缓存里，那个 section 会报 `NOT FOUND`——这时打开对应界面（⌘/ 开弹窗）再跑一次。自检：`extract.py --demo`。
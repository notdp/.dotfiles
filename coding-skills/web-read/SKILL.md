---
name: web-read
description: 当对话中出现 URL、GitHub 页面或 PDF，需要读取并转换为干净 Markdown 时使用；优先走脚本化抓取链路，而不是每次临时拼工具。
argument-hint: <URL|PDF 链接>
---

# Web Read

把远程页面读取成可复用的 Markdown 输入，优先覆盖：

- 通用网页
- GitHub 页面
- PDF

## 目标

1. 把链接内容转成便于后续分析的文本
2. 尽量减少每次临时拼装抓取命令
3. 为后续 `assist-learn` / `think-research` 提供稳定输入

## 默认流程

1. 先判断链接是否属于 GitHub / PDF / 通用网页
2. 调用 `${HOME}/.dotfiles/coding-skills/web-read/scripts/fetch.sh`
3. 需要补充抓取策略时，参考 `references/read-methods.md`

## 使用约束

- 本 skill 处理远程 URL，不处理 repo 内本地文件
- 第一版不专门处理微信 / 飞书
- 如果链接需要登录态或复杂交互，改用 `agent-browser`
- 不要从目标项目 cwd 运行 `${HOME}/.dotfiles/coding-skills/web-read/scripts/fetch.sh`；该脚本是本 skill 自带资产

## 资产

- `references/read-methods.md`
- `${HOME}/.dotfiles/coding-skills/web-read/scripts/fetch.sh`

## Gotchas

- 不要把网页抓取和浏览器自动化混在一起；静态可读内容优先走脚本
- 不要直接把抓取结果当权威事实；后续结论仍需来源校验

---
name: guard-diff-scan
description: 当改动已完成但未 commit、需要确认没留调试遗留物时使用；扫描 git diff 中的 TODO/FIXME/调试语句。
argument-hint: <留空=当前工作树|--staged|路径>
---

# Diff Scan

在 commit 前扫一遍当前工作树的 diff，确认没有调试残留。

## 核心循环

为什么这样循环：调试残留通常藏在 diff 的新增行里，单靠人工浏览容易漏掉。先用脚本扫模式，再人工复核命中，可以把机械检测和语境判断分开，避免误删有意保留的示例或测试 fixture。

```
1. 优先跑 `${HOME}/.dotfiles/scripts/scan_diff_residue.py`（工作树 + 暂存区）
2. 按固定清单人工复核命中
3. 输出每条命中 + 建议处理
4. 全部确认后才 commit
```

脚本 exit code：`0` = 无命中，`1` = 有命中需人工处理，`2` = 扫描失败。

## 扫描清单

| 类型 | 触发模式 |
|------|----------|
| TODO/FIXME/XXX/HACK | `\b(TODO|FIXME|XXX|HACK)\b` |
| 调试打印 | `console\.log`、`print(`、`dbg!`、`pp `、`fmt.Println` |
| 调试断点 | `debugger;`、`breakpoint\(\)`、`pdb.set_trace` |
| 临时 DEBUG 前缀 | `\[DEBUG-[A-Za-z0-9_-]+\]` |
| 注释掉的代码块 | 连续 3+ 行以注释开头且含代码语法 |
| 硬编码 secret 疑似 | `password=`、`api_key=`、`token=` |
| 临时变量名 | `foo`、`bar`、`tmp1`、`test_xxx` 在生产代码里 |

## 工具化扫描

```bash
"${HOME}/.dotfiles/scripts/scan_diff_residue.py"
```

不要假设目标项目有 `${HOME}/.dotfiles/scripts/scan_diff_residue.py`；该 helper 来自 dotfiles，运行 cwd 才是目标仓库。

脚本扫描新增 diff 行和未追踪文件，并默认排除 `refs/**`、Markdown、`scripts/tests/**` 和扫描器自身，避免参考仓库快照与 fixture 产生噪音。脚本结果是第一层过滤，不替代人工判断：文档示例、测试 fixture、故意保留的 TODO 仍需逐条裁决。

## 输出格式

```markdown
## Diff Scan 结果

| 类型 | 文件 | 行 | 片段 | 建议 |
|------|------|----|------|------|
| TODO | src/auth.ts | 42 | `// TODO: handle retry` | 保留（有上下文）/ 删除 / 改写成 issue |
| console.log | src/cache.ts | 118 | `console.log('here', data)` | 删除 |

## 总结
- 命中 N 条
- 建议处理：X 条删除、Y 条保留、Z 条转 issue
- [ ] 用户确认通过，可以 commit
```

## 与其他 skill 的边界

- `guard-review` 做代码逻辑 review（是否有 bug、设计问题），范围大
- `guard-ship` 做交付前总预检（git status、敏感信息、分支），关注可交付性
- 本 skill 最窄：只扫 diff 中的文本遗留物，不做逻辑判断

## 编辑与 Git 礼仪（来自 codex 收编）

### 编辑约束

- 默认 ASCII；引入 Unicode 需要理由且文件已是该字符集
- 注释克制：不写"赋值给变量"这类废话；复杂块前可加 1 行 orientation
- 编辑用专用 patch 工具（Edit / MultiEdit / apply_patch），不用 `cat` 写文件
- 不用 Python 小脚本读写文件（shell 或 patch 工具能干就用）

### Dirty Worktree 礼仪

- 工作树可能不干净；NEVER 回滚不是你做的改动（除非用户明确要求）
- 提交 / 编辑时遇到不属于你的修改：在你触过的文件里先读懂、配合处理；在无关文件里 ignore
- 仅当那些改动让任务无法完成时才向用户问

### Git 红线

- 不用 `git reset --hard`、`git checkout --`，除非用户明确要求
- 模糊请求先问再动
- 优先非交互 git 命令；不进交互 console

## Gotchas

- TODO 不等于一定要删——有的 TODO 记录了真实后续工作，应转成 issue 或保留
- 测试文件里的 `console.log` / `print` 可能是有意的，不要一刀切
- 注释掉的代码块 vs 文档注释需要人工判断

## 未来增量

可继续把注释掉的代码块检测做成更强 AST / parser 版本；当前脚本先覆盖低误报文本模式。

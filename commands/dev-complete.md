---
description: dev-complete 单 pass 完备开发(spec→code→dual review→verify)
argument-hint: <直接用自然语言说你想做什么>
---

加载 `~/.dotfiles/coding-skills/dev-complete/SKILL.md` 并执行。harness: `~/.dotfiles/coding-skills/dev-complete/dc.py`。

子命令直通(用绝对路径)：

```
python3 ~/.dotfiles/coding-skills/dev-complete/dc.py <args>
```

- `scaffold --requirement <path> [--goal <g>]`：建 workspace，进入 scaffold 流程。
- `launch --workspace <ws> --role <coder|reviewer_a|reviewer_b>`：开 role pane。
- `verify --workspace <ws>`：跑 verify.sh。
- `complete --workspace <ws>`：门禁 gate。

先决条件：用户在 tmux 中、目标项目 git 仓库内。

无参数时读 `~/.dotfiles/coding-skills/dev-complete/SKILL.md` 后决定。

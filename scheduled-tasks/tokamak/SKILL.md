---
name: tokamak
description: 每 6 小时用 tokamak 实测一次 opus 和 haiku 的输出速度，记录历史并画趋势
---

实测一次 token 输出速度，存档并展示趋势。

第一步，两个模型各跑一次（每次 3 轮，自动追加结果到 ~/.claude/tokamak-history.jsonl 并打印速度、TTFT 与该模型上一次/前一天的对比）：

```bash
~/.dotfiles/bin/tokamak --model opus && ~/.dotfiles/bin/tokamak --model haiku
```

这里故意用 `opus` / `haiku` 别名而不是精确 id：要测的是"我当下实际在用的档位有多快"，模型换代就自动跟着测新的。脚本存进历史的 model 字段是 init 事件返回的已解析 id，所以换代后旧曲线停在原处、新 id 另起一条，不会把两代混成一条。

第二步，读 ~/.claude/tokamak-history.jsonl 全量历史，展示结果，输出方式按序：

1. 两行中文结论，opus 和 haiku 各一行：本次中位数 tok/s、TTFT（init→首字，不含 CLI 启动）、比该模型上一次/前一天快了还是慢了
2. 趋势图：有内联可视化工具（如 visualize/show_widget）就画图——时间-速度折线为主图，每个模型一条线（中位数做主线，该模型每条记录 speeds 里的单轮值做同色散点），TTFT 趋势画第二个小图、同样按模型分线（不要双 y 轴）；没有可视化工具就改用 markdown 表格，每个模型各列最近 5 条（时间、模型、中位数 tok/s、TTFT）

约束：直接跑脚本，不要手搓计时逻辑；不要改 --model 去测 fable（脚本也会拒绝）；跨模型的数不可比，别把 opus 和 haiku 混成一条线或算总体平均；某个模型报错就跳过它、照常报另一个，简短说明原因，不要反复重试烧 token。

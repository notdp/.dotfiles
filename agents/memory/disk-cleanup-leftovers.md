---
name: disk-cleanup-leftovers
description: 2026-09-07 磁盘清理时刻意没动的大目录清单（微信 26G、Telegram 8.5G、Cursor 9.4G、Claude vm_bundles 9G、孤儿 CoreSimulator 6.8G 等），下次清理可从这里开始
metadata:
  type: project
---

2026-09-07 清理时只删了 hive worktree 的 Rust target 和 VS Code 残留更新包。以下用户数据或需用户决定的目录没动：

- 微信 `~/Library/Containers/com.tencent.xinWeChat` 26G，建议在微信设置里清
- Telegram Group Container 8.5G
- Cursor Application Support 9.4G（globalStorage 4.1G、snapshots 2.7G）
- Claude Desktop `vm_bundles` 9G
- `~/Library/Developer/CoreSimulator` 6.8G，机器无 Xcode，是孤儿数据可删
- `~/.rustup` 7.6G，可能多 toolchain
- `~/.cache/codex-runtimes` 3.4G，含两个 `codex-runtime-install-*` 残留
- `~/.cache/whisper` 1.9G 模型
- `~/Developer` 下 node_modules 合计 30G
- hive 24 个 worktree 全部有未合并 commit，没删 worktree 本身

**Why:** 这些要么是用户数据，要么删了影响不清楚，用户没明确授权。

**How to apply:** 用户再说磁盘满时，直接列这个清单让用户挑，不用重扫。相关配置见 [[rust-build-cache-setup]]。

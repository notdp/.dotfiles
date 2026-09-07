---
name: rust-build-cache-setup
description: 机器上已配置 sccache 作为全局 rustc-wrapper，并有 launchd 每周日 23:00 跑 cargo-sweep 清 ~/Developer 下 7 天未用的 Rust 编译产物
metadata:
  type: project
---

2026-09-07 磁盘清理后配置的 Rust 编译缓存方案：

- `~/.cargo/config.toml` 设了 `[build] rustc-wrapper = "sccache"`（brew 装的 sccache 0.17.0），对所有 cargo 项目生效。
- `cargo-sweep` 装在 `~/.cargo/bin`，launchd 任务 `~/Library/LaunchAgents/com.notdp.cargo-sweep.plist` 每周日 23:00 跑 `cargo sweep --recursive --time 7 ~/Developer`，日志在 `~/Library/Logs/cargo-sweep/`。
- 机器上没装 Xcode，只有 CommandLineTools。

**Why:** hive 项目用 Claude Code Workflow 开了 24 个 worktree，每个 worktree 各自一份 Rust `target/`，累计 47G 把磁盘塞满（可用只剩 6.6G）。删掉 target 后释放到 40G。用户提到 Node 靠 pnpm store 没这问题，Rust 默认没有共享缓存。

**How to apply:** 再遇到磁盘满，先查 `~/Developer/hive/.claude/worktrees/*/target` 和各 worktree 是否还需要；Workflow 跑完的 worktree 应 `git worktree remove`。如果 sccache 出问题（增量编译 crate 不命中是正常现象），先看 `sccache --show-stats`。见 [[disk-cleanup-leftovers]]。

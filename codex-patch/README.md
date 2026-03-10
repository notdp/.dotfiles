# Codex tmux -CC Patch

为本地 Codex 源码仓库应用一个可重复使用的补丁，修复 `tmux -CC` 控制模式下的主题误判。
这套工具会记录一个 `manifest`，把“上次 patch 针对的官方 Codex 版本、源码 tag、构建产物路径”记下来。

## 适用范围

- 默认操作仓库：`~/Developer/codex`
- 默认官方版本来源：`/opt/homebrew/bin/codex --version`
- 默认 manifest：`state/manifest.json`
- 当前支持的补丁资产：
  - `assets/rust-v0.112.x-colorfgbg.patch`
  - `assets/tmux-cc-colorfgbg.patch`（开发版 `0.0.0/main`）

## 关键约束

- 不要直接 patch `/opt/homebrew/bin/codex` 或 npm/cask 安装出来的发布二进制。
- 这套工具走的是“官方版本检测 + 对应 release tag 打 patch + 本地构建”路线。
- 当前 `0.112.x` 的 patch 还会把本地 release 构建从 `fat LTO + codegen-units=1` 调成 `thin LTO + codegen-units=16`，优先缩短本地重编时间。
- `codex` shell 包装会先读 manifest；如果官方版本变了但 manifest 还没更新，会直接拦住并提示跑更新。
- 如果 `git apply --3way` 都失败，说明上游改动已经碰到目标代码了，这时要刷新补丁，而不是硬上。

## 使用流程

### 如果用户说“状态”“检查”“现在有没有打 patch”

直接运行：

```bash
python3 scripts/status.py
```

它会输出：

1. 当前仓库版本和分支
2. 当前官方 `codex` 版本
3. manifest 里记录的上次 patch 版本
4. 现在是否需要更新

### 如果用户说“打 patch”“应用 patch”“更新 codex 后重打”

直接运行：

```bash
python3 scripts/apply.py
```

默认会：

1. 检查仓库路径和目标文件
2. 用 `git apply --3way` 应用补丁
3. 构建 `codex-rs/target/release/codex`

### 如果用户只想构建

直接运行：

```bash
python3 scripts/build.py
```

### 如果用户说“更新 codex 后重打”“拉最新再重编”

直接运行：

```bash
python3 scripts/update.py
```

默认会：

1. 读取官方 `codex` 版本
2. `git fetch --tags`
3. 切到对应的 `patch/rust-vX.Y.Z` 本地分支
4. 重新应用匹配该版本的 patch
5. 重新构建本地 `codex`
6. 更新 `state/manifest.json`

### 如果用户说“恢复”“撤销 patch”

直接运行：

```bash
python3 scripts/restore.py
```

这会把两个目标文件恢复到仓库 `HEAD` 版本；如果用户在这两个文件上还有别的本地修改，要先提醒风险。

## 实现说明

- 补丁逻辑：在 `tmux -CC` 控制模式下，优先用 `COLORFGBG` 推导默认前景/背景色；其它终端仍保留原来的 OSC 10/11 查询路径。
- 这个修复只解决 `tmux -CC` 下的主题误判，不会全局禁用样式，也不会回退到 `NO_COLOR=1` 那种“能看但很丑”的方案。
- 如果用户想给别的仓库路径打 patch，脚本支持 `--repo /path/to/codex`。
- 如果 `update.py` 在 `git apply --check --3way` 这一步失败，说明上游代码已经漂移，需要刷新对应版本的 patch 资产，而不是继续硬套。

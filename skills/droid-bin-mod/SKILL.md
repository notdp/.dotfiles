---
name: droid-bin-mod
description: 修改 droid 二进制以禁用截断。当用户提到：修改/恢复/测试 droid、press Ctrl+O、output truncated、显示完整命令或输出时触发。
---

# Droid Binary Modifier

修改 Factory Droid CLI 二进制文件，禁用命令/输出截断，实现默认展开显示。

## 使用流程

### 如果用户说"测试"或"测试droid修改"

**直接执行以下命令验证修改效果，不要询问：**

```bash
# 测试 mod1+2 (命令截断) - 100字符命令应完整显示
echo "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" && echo done

# 测试 mod3 (输出行数) - 应显示99行而非4行
seq 1 100

# 测试 mod4 (diff行数) - 需要编辑文件看diff
seq 1 100 > /tmp/test100.txt
```

然后执行：把 `/tmp/test100.txt` 的第1-100行全部替换成 `A1` 到 `A100`，diff 应显示99行（原来限制20行）。

### 如果用户说"修改"或"恢复"

**询问用户需要哪些修改：**

```bash
┌────────────────────────────────────────────────────────────────────┐
│ EXECUTE  (echo "aaa..." command truncated. press Ctrl+O)  ← mod1+2 │
│ line 1                                                             │
│ ...                                                                │
│ line 4                                                    ← mod3   │
│ ... output truncated. press Ctrl+O                                 │
├────────────────────────────────────────────────────────────────────┤
│ EDIT  (README.md) +10 -5                                           │
│ ... (truncated after 20 lines)                            ← mod4   │
│ ... output truncated. press Ctrl+O                                 │
└────────────────────────────────────────────────────────────────────┘

mod1: "command truncated. press Ctrl+O" → hidden
mod2: command >50 chars truncated → >99 chars
mod3: output truncated at 4 lines → 99 lines
mod4: diff truncated at 20 lines → 99 lines

select: 1,2,3,4 / all / restore
```

用户选择后，执行对应修改。

## 版本适配说明

**混淆 JS 的应对策略**：变量名/函数名会变，但**字符串常量和代码结构不变**。

### 第一步：用不变的字符串定位

```bash
# 修改1+3b: 用 isTruncated 定位截断函数
strings ~/.local/bin/droid | grep "isTruncated"

# 修改2: 用 command.length 定位命令阈值
strings ~/.local/bin/droid | grep "command.length>"

# 修改3: 用 exec-preview 定位输出预览
strings ~/.local/bin/droid | grep "exec-preview"

# 修改4: 用上下文定位 diff 行数（在大段 JSX 渲染代码附近）
strings ~/.local/bin/droid | grep -E "var [A-Z]{2}=20,"
```

### 第二步：用模式匹配确认

定义 JS 变量名模式: `V = [A-Za-z_$][A-Za-z0-9_$]*` (适应任意混淆结果)

| 修改项      | 不变的定位字符串 | 匹配模式（正则）                        | v0.46.0 实例              |
| ----------- | ---------------- | --------------------------------------- | ------------------------- |
| 1 截断条件  | `isTruncated`    | `if\(!V&&!V\)return\{text:V,isTruncated:!1\}` | `if(!H&&!Q)return{text:A,isTruncated:!1}` |
| 2 命令阈值  | `command.length` | `command\.length>\d+`                   | `command.length>50`       |
| 3 输出预览  | `exec-preview`   | `slice\(0,\d\),V=V\.length` (marker前500字节) | `slice(0,4),D=q.length`   |
| 3b 字节补偿 | (全局唯一)       | `V=80,V=3\)` (截断函数参数)             | `R=80,T=3)`               |
| 4 diff 行数 | (后跟变量声明)   | `var V=20,V,` (后跟逗号+变量)           | `var LD=20,UDR,`          |

### 字节补偿池

修改 3 `slice(0,4)→slice(0,99)` 多 1 字节，需要从截断函数参数补回。

截断函数被修改 1 短路后，参数值无所谓，可用来平衡字节：

| 补偿项 | 位置              | v0.46.0 | 可调范围               |
| ------ | ----------------- | ------- | ---------------------- |
| 参数 1 | 截断函数第 2 参数 | `=80,`  | 80→8 (-1), 80→800 (+1) |
| 参数 2 | 截断函数第 3 参数 | `=3)`   | 3→33 (+1)              |

## 修改原理

### 修改 1: 截断函数条件 (核心)

**原始代码**:

```javascript
function JZ9(A, R=80, T=3) {       // R=宽度限制80字符, T=行数限制3行
  if (!A) return {text: A||"", isTruncated: !1};
  let B = A.split("\n"),
      H = B.length > T,            // H: 是否超过行数限制
      Q = A.length > R;            // Q: 是否超过宽度限制
  if (!H && !Q)                    // 如果都不超限
    return {text: A, isTruncated: !1};   // ← 返回原文，不截断
  // ... 截断逻辑 ...
  return {text: J, isTruncated: !0};     // ← 返回截断后的文本
}
```

**修改**: `if(!H&&!Q)` → `if(!0||!Q)`

```plain
原: if(!H && !Q)  → 只有当 H=false 且 Q=false 时才返回原文
改: if(!0 || !Q)  → !0 是 true，所以 true || 任何 = true，永远返回原文
```

**效果**:

- 永远走早期返回分支，返回原文 + `isTruncated:!1`（不显示 Ctrl+O 提示）
- 后面的截断逻辑永远不执行
- 因此原来的"截断参数 R=80,T=3"和"截断返回 isTruncated:!0"修改都不需要了

### 修改 2: 命令显示阈值

**位置**: 命令文本显示

**修改**: `command.length>50` → `command.length>99`

- 原来超 50 字符就截断
- 现在超 99 字符才截断

### 修改 3: 输出预览行数

**位置**: 命令执行结果显示区域

**修改**: `slice(0,4)` → `slice(0,99)`

- 原来只显示前 4 行输出
- 现在显示前 99 行

**字节长度补偿**: `slice(0,4)` → `slice(0,99)` 多 1 字节，从截断函数参数补：

```plain
slice(0,4)  → slice(0,99)   +1字节
R=80        → R=8           -1字节  (截断函数被修改1短路，参数值无所谓)
总计: 0字节
```

### 修改 4: diff/edit 显示行数

**位置**: Edit 工具的 diff 输出

**修改**: `var LD=20` → `var LD=99`

- 原来 diff 最多显示 20 行
- 现在显示 99 行

## 修改汇总

| #   | 修改项    | 原始         | 修改后         | 字节 | 说明                 |
| --- | --------- | ------------ | -------------- | ---- | -------------------- |
| 1   | 截断条件  | `if(!H&&!Q)` | `if(!0\|\|!Q)` | 0    | 核心：永远返回原文   |
| 2   | 命令阈值  | `length>50`  | `length>99`    | 0    | 命令文本显示长度     |
| 3   | 输出预览  | `slice(0,4)` | `slice(0,99)`  | +1   | 输出内容显示行数     |
| 3b  | 字节补偿  | `X=80,Y=3)`  | `X=8,Y=3)`     | -1   | 截断函数参数(被短路) |
| 4   | diff 行数 | `LD=20`      | `LD=99`        | 0    | Edit diff 显示行数   |

## 修改脚本

脚本位置: `~/.factory/skills/droid-bin-mod/scripts/`

### mods/ - 功能修改

```bash
mods/mod1_truncate_condition.py  # 截断条件短路 (0 bytes)
mods/mod2_command_length.py      # 命令阈值 50→99 (0 bytes)
mods/mod3_output_lines.py        # 输出行数 4→99 (+1 byte，需补偿)
mods/mod4_diff_lines.py          # diff行数 20→99 (0 bytes)
```

### compensations/ - 字节补偿

mod3 会 +1 byte，必须用补偿脚本平衡，否则二进制损坏。

```bash
compensations/comp_r80_to_r8.py    # R=80→R=8 (-1 byte) ← 常用
compensations/comp_r80_to_r800.py  # R=80→R=800 (+1 byte)
compensations/comp_t3_to_t33.py    # T=3→T=33 (+1 byte)
```

### 执行示例

```bash
# 1. 移除签名
codesign --remove-signature ~/.local/bin/droid

# 2. 执行修改
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod1_truncate_condition.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod2_command_length.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod3_output_lines.py
python3 ~/.factory/skills/droid-bin-mod/scripts/compensations/comp_r80_to_r8.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod4_diff_lines.py

# 3. 重新签名
codesign -s - ~/.local/bin/droid
```

### 工具脚本

```bash
python3 ~/.factory/skills/droid-bin-mod/scripts/status.py   # 检查状态
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py  # 恢复原版
```

脚本使用正则匹配变量名，适应混淆后变量名变化。

## 前提条件

- macOS 系统（需要 codesign 命令）
- Python 3
- droid 二进制位于 `~/.local/bin/droid`

## 修改流程

```bash
# 1. 备份 (带版本号)
cp ~/.local/bin/droid ~/.local/bin/droid.backup.$(~/.local/bin/droid --version)

# 2. 移除签名
codesign --remove-signature ~/.local/bin/droid

# 3. 手动修改二进制 (参考上面的修改原理)

# 4. 重新签名
codesign -s - ~/.local/bin/droid

# 5. 验证
~/.local/bin/droid --version
```

## 测试修改效果

修改完成后，告诉用户：

```plain
新开一个 droid 窗口，输入"测试droid修改"
```

### 测试命令（供 droid 执行）

```bash
# 测试修改1+2 (命令截断)
echo "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" && echo done

# 测试修改3 (输出行数)
seq 1 100

# 测试修改4 (diff行数) - 先创建文件
seq 1 100 > /tmp/test100.txt
# 然后让 droid 编辑前30行看 diff
```

### 检查点

- 修改 1: 命令框不再显示 "command truncated. press Ctrl+O for detailed view"
- 修改 2: 100 字符的命令完整显示
- 修改 3: 输出显示 99 行（原来只显示 4 行）
- 修改 4: diff 显示超过 20 行（原来只显示 20 行）

## 恢复原版

**必须用脚本恢复**（直接 cp 会因 macOS 元数据问题导致 SIGKILL）：

```bash
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py --list  # 查看备份
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py         # 恢复最新
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py 0.46.0  # 恢复指定版本
```

## 禁用自动更新

```bash
# 添加到 ~/.zshrc
export DROID_DISABLE_AUTO_UPDATE=1
```

## 安全说明

- 此修改仅影响本地 UI 渲染
- Factory 服务器不验证客户端二进制完整性
- 不发送二进制哈希、签名、机器指纹
- 只验证 API Key 有效性

## 版本升级后脚本失败的排查

如果 droid 更新后脚本报错"未找到"，按以下步骤排查：

### 1. 检查特征数字是否变化

```bash
# 这些数字有语义含义，通常不会变
strings ~/.local/bin/droid | grep -E "=80,|=3\)|>50|=20,"
```

- `80` - 截断宽度限制
- `3` - 截断行数限制  
- `50` - 命令长度阈值
- `20` - diff 显示行数

### 2. 检查字符串常量是否存在

```bash
strings ~/.local/bin/droid | grep -E "isTruncated|command.length|exec-preview"
```

### 3. 更新脚本正则

如果变量名模式变化（如单字母→多字母），修改 `common.py` 中的 `V` 模式：

```python
# 当前模式 (适应大多数混淆器)
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'
```

### 4. 调整 marker 距离

如果 mod3 找不到，可能 `exec-preview` 和 `slice(0,X)` 的距离变了：

```python
# 在 mod3_output_lines.py 中调整 max_dist
near_marker=b'exec-preview', max_dist=1000  # 默认500
```

### 5. 重新备份

```bash
cp ~/.local/bin/droid ~/.local/bin/droid.backup.$(~/.local/bin/droid --version)
```

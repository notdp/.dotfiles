---
name: droid-binary-modifier
description: 修改 Factory Droid CLI 二进制文件以禁用命令/输出截断。当用户想要：(1) 禁用 droid 命令截断显示，(2) 让 droid 显示完整命令而不是 "press Ctrl+O for detailed view"，(3) 增加输出预览行数，(4) 修改 droid 二进制的 UI 显示参数时使用此 skill。
---

# Droid Binary Modifier

修改 Factory Droid CLI 二进制文件，禁用命令/输出截断，实现默认展开显示。

## 快速使用

```bash
python3 ~/.factory/skills/droid-binary-modifier/scripts/modify_droid.py
```

## 版本适配说明

**重要**: droid 更新后，混淆后的变量名和函数名会变化。脚本中的模式可能需要更新。

### 如何找到新版本中的对应位置

1. **命令截断函数** - 搜索 `command truncated`:

   ```bash
   strings ~/.local/bin/droid | grep -B5 "command truncated"
   ```

   找到类似 `function XXX(A,R=80,T=3)` 的函数定义

2. **输出预览行数** - 搜索上下文特征:

   ```bash
   strings ~/.local/bin/droid | grep "exec-preview"
   ```

   附近会有 `slice(0,N)` 其中 N 是预览行数

3. **命令显示截断** - 搜索特征:

   ```bash
   strings ~/.local/bin/droid | grep "command.length>"
   ```

4. **截断提示文字** - 确认位置:

   ```bash
   strings ~/.local/bin/droid | grep "press Ctrl+O"
   ```

## 修改原理

### 目标 1: 命令截断函数 (核心)

**搜索特征**: `function XXX(A,R=80,T=3)` 其中 XXX 是混淆后的函数名

**原始代码逻辑**:

```javascript
function JZ9(A,R=80,T=3){  // R=宽度限制, T=行数限制
  if(!A) return {text:A||"",isTruncated:!1};
  let B=A.split("\n"),H=B.length>T,Q=A.length>R;
  if(!H&&!Q) return {text:A,isTruncated:!1};  // 不截断
  // ... 截断逻辑 ...
  return {text:J,isTruncated:!0};  // 返回截断结果
}
```

**修改方法**:

1. `if(!H&&!Q)` → `if(!0||!Q)` - 条件永真，永远返回原文
2. `isTruncated:!0` → `isTruncated:!1` - 不触发截断提示

### 目标 2: 输出预览行数

**搜索特征**: `slice(0,4)` 附近有 `exec-preview` 或 `flexDirection:"column"`

**修改**: `slice(0,4)` → `slice(0,99)` (保持字符串长度，用 `lengt` 替换 `length`)

### 目标 3: 命令显示阈值

**搜索特征**: `command.length>50` 和 `slice(0,47)`

**修改**:

- `command.length>50` → `command.length>99`
- `slice(0,47)` → `slice(0,96)`

## 修改内容汇总 (v0.46.0)

| 修改项   | 原始模式                                  | 修改后                      | 搜索特征              |
| -------- | ----------------------------------------- | --------------------------- | --------------------- |
| 截断条件 | `if(!H&&!Q)return{text:A,isTruncated:!1}` | `if(!0\|\|!Q)...`           | `function XXX(A,R=80` |
| 截断返回 | `isTruncated:!0` (函数末尾)               | `isTruncated:!1`            | 同上函数内            |
| 截断参数 | `R=80,T=3`                                | `R=99,T=9`                  | 同上函数定义          |
| 输出预览 | `C=q.slice(0,4),D=q.length`               | `C=q.slice(0,99),D=q.lengt` | `exec-preview`        |
| 命令阈值 | `command.length>50`                       | `command.length>99`         | `command.length>`     |
| 命令截取 | `slice(0,47)`                             | `slice(0,96)`               | 同上附近              |

## 手动修改步骤

如果脚本不工作（版本不兼容），手动修改：

```python
with open('~/.local/bin/droid', 'rb') as f:
    data = f.read()

# 1. 找到截断函数 (搜索特征)
pos = data.find(b'function ')  # 找到后看上下文确认

# 2. 替换 (保持字节长度一致!)
data = data.replace(b'原始模式', b'修改后')

# 3. 写回
with open('~/.local/bin/droid', 'wb') as f:
    f.write(data)
```

## 前提条件

- macOS 系统（需要 codesign 命令）
- Python 3
- droid 二进制位于 `~/.local/bin/droid`

## 修改流程

```bash
# 1. 备份
cp ~/.local/bin/droid ~/.local/bin/droid.backup

# 2. 移除签名
codesign --remove-signature ~/.local/bin/droid

# 3. 修改 (使用脚本或手动)
python3 scripts/modify_droid.py

# 4. 重新签名
codesign -s - ~/.local/bin/droid

# 5. 验证
~/.local/bin/droid --version
```

## 恢复原版

```bash
cp ~/.local/bin/droid.backup ~/.local/bin/droid
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

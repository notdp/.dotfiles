---
name: droid-bin-mod
description: 修改 droid CLI 二进制文件以禁用截断和解锁功能。当用户说"修改droid"、"恢复droid"、"测试droid修改"、press Ctrl+O、output truncated、显示完整命令或输出时触发。注意：这是修改 ~/.local/bin/droid 二进制，不是 .factory/droids 配置文件。
---

# Droid Binary Modifier

修改 Factory Droid CLI 二进制文件，禁用命令/输出截断，实现默认展开显示。

## 使用流程

### 如果用户说"测试"或"测试droid修改"

**直接执行以下命令验证修改效果，不要询问：**

```bash
# 测试 mod1+2 (命令截断) - 100字符命令应完整显示
echo "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" && echo done

# 测试 mod3 (输出行数+提示) - 99行无提示，100行有提示
seq 1 99   # 应显示99行，无 "press Ctrl+O" 提示
seq 1 100  # 应显示99行，有 "press Ctrl+O" 提示

# 测试 mod4 (diff行数) - 需要编辑文件看diff
seq 1 100 > /tmp/test100.txt
```

然后执行：把 `/tmp/test100.txt` 的第1-100行全部替换成 `A1` 到 `A100`，diff 应显示99行（原来限制20行）。

### 如果用户说"修改"或"恢复"

**询问用户需要哪些修改：**

```
mod1: 命令框 "command truncated. press Ctrl+O" 提示 → 隐藏
mod2: 命令超 50 字符截断 → 超 99 字符才截断
mod3: 命令输出截断行数 4 行 → 99 行 (含 exec hint 提示)
mod4: Edit diff 截断行数 20 行 → 99 行
mod5: Ctrl+N 只在 custom model 间切换 (不弹 selector popup)
mod6: Mission 模型不强切 → Orchestrator 保持 custom model
mod7: Custom model 支持完整 effort 级别 (anthropic: max, openai: xhigh)
mod8: Summarizer OpenAI → Chat Completions API fallback
mod9: 禁用自动更新 → checkForUpdates() 返回 null (可选)

select: 1-9 / all / restore
```

用户选择后，执行对应修改。

## 修改汇总

| #   | 修改项       | 原始             | 修改后           | 字节 | 说明                                    |
| --- | ------------ | ---------------- | ---------------- | ---- | --------------------------------------- |
| 1   | 截断条件     | `if(!H&&!Q)`     | `if(!0\|\|!Q)`   | 0    | 短路截断函数，隐藏命令框 "press Ctrl+O" |
| 2   | 命令阈值     | `length>50`      | `length>99`      | 0    | 命令超 99 字符才截断                    |
| 3   | 输出行数     | `D=B?8:4`        | `D=99\|\|4`      | 0    | 输出显示 99 行，超过才显示提示          |
| 4   | diff 行数    | `VAR=20`         | `VAR=99`         | 0    | Edit diff 显示 99 行                   |
| 5   | Ctrl+N cycle | popup toggle     | c8A() 内联 cycle | -2   | Ctrl+N 直接在 custom model 间切换       |
| 6   | mission 模型 | `V.includes(X)`  | `!0` + 空格填充  | 0    | 改条件而非数据，不强切+不警告           |
| 7   | effort 级别  | `["off","low","medium","high"]` | 按 provider 区分 | +132 | 两处: 各+66 |
| 8   | summarizer   | Responses API    | Chat Completions | +32  | 两条 OpenAI compress 路径都改走正确 API |
| 9   | 禁用更新     | `let H,{remoteConfig:$}=...` | `return null;/*..*/` | 0 | checkForUpdates() 直接返回 null (可选) |
| 11  | unicode escape | `default:A+=M` | `M=="u"?fromCharCode:A+=M` | +120 | YcM/NcM parser 修复 \uXXXX 解析 (可选) |
| 12  | unicode proxy  | wU$ 无预处理 | `H=H.replace(uXXXX)` | +49 | wU$ 入口补回裸 uXXXX 反斜杠 (可选) |
| 补偿 | 死代码+字符串 | 多处            | 注释/缩短填充    | -162 | 统一补偿 mod5+7+8; mod11/12 自带补偿  |

## 修改脚本

脚本位置: `~/.factory/skills/droid-bin-mod/scripts/`

### mods/ - 功能修改

```
mods/mod1_truncate_condition.py    # 截断条件短路 (0 bytes)
mods/mod2_command_length.py        # 命令阈值 50→99 (0 bytes)
mods/mod3_output_lines.py          # 输出行数 8→99 (0 bytes, 含 exec hint)
mods/mod4_diff_lines.py            # diff行数 20→99 (0 bytes)
mods/mod5_custom_model_cycle.py    # Ctrl+N custom model cycle (-2 bytes)
mods/mod6_mission_model.py         # Mission 模型不强切 (0 bytes)
mods/mod7_custom_effort_levels.py  # effort 级别扩展 (+132 bytes)
mods/mod8_summarizer_openai_fix.py # summarizer/compress OpenAI fix (+32 bytes)
mods/mod9_disable_auto_update.py   # 禁用自动更新 (0 bytes, 可选)
mods/mod11_unicode_escape_fix.py    # YcM/NcM unicode escape fix (+120 bytes, 可选)
mods/mod12_unicode_proxy_fix.py     # wU$ unicode proxy fix (+49 bytes, 可选)
```

### compensations/ - 字节补偿

```bash
compensations/comp_universal.py          # 无参数: 显示当前可用补偿空间
compensations/comp_universal.py <bytes>  # 缩减指定字节数
```

补偿区域来源:
- FFH 死代码 (mod1 短路): ~71B
- mod6 else 分支: ~43B
- mod6 空格填充: ~25B
- help text 字符串缩短: ~192B

### 执行示例

```bash
# 1. macOS: 移除签名
codesign --remove-signature ~/.local/bin/droid

# 2. 执行修改
python3 mods/mod1_truncate_condition.py
python3 mods/mod2_command_length.py
python3 mods/mod3_output_lines.py
python3 mods/mod4_diff_lines.py
python3 mods/mod5_custom_model_cycle.py
python3 mods/mod6_mission_model.py
python3 mods/mod7_custom_effort_levels.py
python3 mods/mod8_summarizer_openai_fix.py
python3 mods/mod9_disable_auto_update.py    # 可选
python3 mods/mod11_unicode_escape_fix.py   # 可选: BYOK unicode fix
python3 mods/mod12_unicode_proxy_fix.py    # 可选: proxy unicode fix

# 3. 补偿 (mod7:+132 + mod8:+32 + mod5:-2 = +162)
python3 compensations/comp_universal.py 162

# 4. macOS: 重新签名
codesign -s - ~/.local/bin/droid
```

### 工具脚本

```bash
python3 status.py                   # 检查状态
python3 restore.py --list           # 查看备份
python3 restore.py                  # 恢复最新
python3 restore.py 0.96.0           # 恢复指定版本
```

## 修改原理

### mod1: 截断函数条件 (核心)

**修改**: `if(!H&&!Q)` → `if(!0||!Q)`
- `!0` 是 `true`，`true || anything` = `true`，永远返回原文 + `isTruncated:!1`

### mod2: 命令显示阈值

**修改**: `command.length>50` → `command.length>99`

### mod3: 输出预览行数和提示条件

**修改**: `D=B?8:4` → `D=99||4`
- `99||4` 永远等于 99，显示前 99 行，超过 99 行才显示提示

### mod4: diff/edit 显示行数

**修改**: `var VAR=20` → `var VAR=99`

### mod5: Ctrl+N custom model 直接切换

**原版**: `ul` callback 弹出 model selector popup，列表从 `ur()` 获取（只有内置模型）
**修改**: 替换为内联 cycle 逻辑
```javascript
ul=K9.useCallback(()=>{
  let RR=c8A();                    // custom model IDs
  if(RR.length<=1)return;
  let oR=VT().getModel(),
      gA=RR[(RR.indexOf(oR)+1)%RR.length];
  if(gA)Yk(gA)                    // handler 切换模型
},[lw])
```
- `c8A()` = `GR().getCustomModels().map(T=>T.id)` 的封装
- `Yk` = model select handler (带 session sync)

### mod6: Mission 模型白名单恒通过

两处 `Y9H.includes(X)` → `!0` + 空格填充等长
- enter-mission: custom model 保留，不强切
- vO 回调: 任意模型不再触发警告

配合 `settings.json` 中 `missionModelSettings` 设置 Worker/Validator 模型。

### mod7: Custom model 完整 effort 级别

两处 `supportedReasoningEfforts` 列表，按 provider 区分：
- Anthropic: `["off","low","medium","high","max"]`
- OpenAI: `["none","low","medium","high","xhigh"]`

### mod8: Summarizer OpenAI fix

OpenAI custom model 的 compress/summarizer 两条路径都从 Responses API 重定向到 Chat Completions API：
- 路径1: `provider==="openai"` 加 `&&!1` 短路 Responses API 路径，并把 generic-chat-completion-api 条件扩展匹配 `openai`
- 路径2: 另一条 `provider==="openai"` 直连 `responses.create(...).output_text||""` 的分支同样加 `&&!1`，自然落到后面的 `chat.completions.create(...)`

### mod9: 禁用自动更新 (可选)

`checkForUpdates()` 函数体首行替换为 `return null;` + 注释填充等长

## 前提条件

- macOS 或 Linux
- Python 3
- droid 二进制位于 `~/.local/bin/droid`

## 修改流程

```bash
# 1. 备份 (带版本号)
cp ~/.local/bin/droid ~/.local/bin/droid.backup.$(~/.local/bin/droid --version)

# 2. macOS: 移除签名
codesign --remove-signature ~/.local/bin/droid

# 3. 执行修改脚本

# 4. macOS: 重新签名
codesign -s - ~/.local/bin/droid

# 5. 验证
~/.local/bin/droid --version
```

## 恢复原版

```bash
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py --list  # 查看备份
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py         # 恢复最新
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py 0.96.0  # 恢复指定版本
```

## 安全说明

- 此修改仅影响本地 UI 渲染
- Factory 服务器不验证客户端二进制完整性
- 只验证 API Key 有效性

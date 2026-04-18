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
mod1:  命令框 "command truncated. press Ctrl+O" 提示 → 隐藏
mod2:  命令超 50 字符截断 → 超 99 字符才截断
mod3:  命令输出截断行数 8 行 → 99 行 (含 exec hint 提示)
mod4:  Edit diff 截断行数 20 行 → 99 行
mod5:  Ctrl+N 只在 custom model 间切换 (不弹 selector popup)
mod6:  Mission 模型不强切 → Orchestrator 保持 custom model
mod7:  Custom model 支持完整 effort 级别 (anthropic: max, openai: xhigh)
mod8:  Summarizer OpenAI → Chat Completions API fallback
mod9:  禁用自动更新 → checkForUpdates() 返回 null (可选)
mod10: tag strip 找不到闭标签时不再截断后续内容 (可选)
mod11: BYOK unicode escape 修复 \uXXXX 解析 bug (可选)
mod12: proxy unicode 修复 裸 uXXXX → \uXXXX (可选, 依赖 mod11)

select: 1-12 / all / restore
```

用户选择后，执行对应修改。

## 修改汇总

| #   | 修改项       | 原始             | 修改后           | 字节 | 说明                                    |
| --- | ------------ | ---------------- | ---------------- | ---- | --------------------------------------- |
| 1   | 截断条件     | `if(!H&&!Q)`     | `if(!0\|\|!Q)`   | 0    | 短路截断函数，隐藏命令框 "press Ctrl+O" |
| 2   | 命令阈值     | `length>50`      | `length>99`      | 0    | 命令超 99 字符才截断                    |
| 3   | 输出行数     | `maxLines:R?Y1A:8` | `maxLines:R?Y1A:99` | +3   | 输出显示 99 行（0.104.0+ 使用 bXH/maxLines） |
| 4   | diff 行数    | `VAR=20`         | `VAR=99`         | 0    | Edit diff 显示 99 行                   |
| 5   | Ctrl+N cycle | popup toggle     | 动态探测 UR()/vT() 内联 cycle | +80  | Ctrl+N 直接在 custom model 间切换（支持 spec mode） |
| 6   | mission 模型 | `V.includes(X)`  | `!0` + 空格填充  | 0    | 改条件而非数据，不强切+不警告           |
| 7   | effort 级别  | `["off","low","medium","high"]` | 按 provider 区分 | +132 | 两处: 各+66 |
| 8   | summarizer   | Responses API    | Chat Completions | +8   | lxH() &&!1 短路两条 Responses 路径    |
| 9   | 禁用更新     | `let H,{remoteConfig:$}=...` | `return null;/*..*/` | 0 | checkForUpdates() 直接返回 null (可选) |
| 10  | tag strip    | `A=A.slice(0,B)` | `A=A.slice(0  )` | 0 | ym9 找不到闭标签时不再截断 (可选) |
| 11  | unicode escape | `default:A+=M` | `M=="u"?fromCharCode:A+=M` | +136 | YcM/NcM parser 修复 \uXXXX 解析 (可选, BYOK) |
| 12  | unicode proxy  | wU$/r_T 无预处理 | `H=H.replace(uXXXX)` | +49 | 函数入口补回裸 uXXXX 反斜杠 (可选, proxy) |
| 补偿 | 死代码+字符串 | 多处            | 注释/缩短填充    | -408 | 统一由 comp_universal.py 补偿 mod3+5+7+8+11+12 |

## 修改脚本

脚本位置: `~/.factory/skills/droid-bin-mod/scripts/`

### mods/ - 功能修改

```
mods/mod1_truncate_condition.py    # 截断条件短路 (0 bytes)
mods/mod2_command_length.py        # 命令阈值 50→99 (0 bytes)
mods/mod3_output_lines.py          # 输出行数 8→99 (+1 byte × 3处 = +3 bytes, 0.104.0+)
mods/mod4_diff_lines.py            # diff行数 20→99 (0 bytes)
mods/mod5_custom_model_cycle.py    # Ctrl+N custom model cycle (+80 bytes, 动态探测函数名)
mods/mod6_mission_model.py         # Mission 模型不强切 (0 bytes)
mods/mod7_custom_effort_levels.py  # effort 级别扩展 (+132 bytes)
mods/mod8_summarizer_openai_fix.py # summarizer/compress OpenAI fix (+8 bytes)
mods/mod9_disable_auto_update.py   # 禁用自动更新 (0 bytes, 可选)
mods/mod10_tag_strip_fix.py        # ym9 tag strip 找不到闭标签时不截断 (0 bytes, 可选)
mods/mod11_unicode_escape_fix.py   # YcM/NcM unicode escape fix (+136 bytes, 可选 BYOK)
mods/mod12_unicode_proxy_fix.py    # wU$/r_T unicode proxy fix (+49 bytes, 可选 proxy)
```

### compensations/ - 字节补偿

```bash
compensations/comp_universal.py          # 无参数: 显示当前可用补偿空间
compensations/comp_universal.py <bytes>  # 缩减指定字节数
```

补偿区域来源（总容量约 583 bytes）:
- 截断函数死代码 (mod1 短路): ~71B
- mod8-else 死分支: ~38B
- mod8 空格填充 (2 处): ~23B
- mod6 注释: ~19B
- help text 字符串缩短 (9 条): ~432B
  - worker/explorer description: ~240B (最大两条)
  - slash command help text: ~192B

### 执行示例

```bash
# 1. 备份 + macOS: 移除签名
cp ~/.local/bin/droid ~/.local/bin/droid.backup.$(~/.local/bin/droid --version)
codesign --remove-signature ~/.local/bin/droid

# 2. 执行修改（按顺序）
python3 mods/mod1_truncate_condition.py
python3 mods/mod2_command_length.py
python3 mods/mod3_output_lines.py
python3 mods/mod4_diff_lines.py
python3 mods/mod5_custom_model_cycle.py
python3 mods/mod6_mission_model.py
python3 mods/mod7_custom_effort_levels.py
python3 mods/mod8_summarizer_openai_fix.py
python3 mods/mod9_disable_auto_update.py    # 可选
python3 mods/mod10_tag_strip_fix.py         # 可选: ym9 tag strip fix
python3 mods/mod11_unicode_escape_fix.py    # 可选: BYOK unicode fix (自补偿)
python3 mods/mod12_unicode_proxy_fix.py     # 可选: proxy unicode fix (自补偿, 依赖 mod11)

# 3. 补偿 (所有 mod 统一走 comp_universal.py)
#    全部 mod1-12: mod3:+3 + mod5:+80 + mod7:+132 + mod8:+8 + mod11:+136 + mod12:+49 = +408
#    仅 mod1-10 (不含 mod11/12): mod3:+3 + mod5:+80 + mod7:+132 + mod8:+8 = +223
python3 compensations/comp_universal.py 408

# 4. macOS: 重新签名
codesign -s - ~/.local/bin/droid

# 5. 验证
~/.local/bin/droid --version
python3 status.py
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

脚本自动探测版本格式：

- **v0.104.0+**: `maxLines:R?Y1A:8` → `maxLines:R?Y1A:99`（3 处，各 +1 byte）
  - 新版本使用 `bXH(text, {maxLines: ...})` 渲染 bash 输出，折叠视图从 8 行改为 99 行
- **v0.96-0.99**: `D=B?8:4` → `D=99||4`（0 bytes）
  - `99||4` 永远等于 99，显示前 99 行，超过 99 行才显示提示

### mod4: diff/edit 显示行数

**修改**: `var VAR=20` → `var VAR=99`

### mod5: Ctrl+N custom model 直接切换

**原版**: Ctrl+N callback 弹出 model selector popup
**修改**: 替换为内联 cycle 逻辑，**动态探测 minified 函数名**（关键）：

```javascript
IM=I9.useCallback(()=>{
  let RR=UR().getCustomModels().map((gA)=>gA.id);   // UR 动态探测
  if(RR.length<=1)return;
  let oR=vT().hasSpecModeModel()                    // vT 动态探测
        ? vT().getSpecModeModel()
        : vT().getModel(),
      gA=RR[(RR.indexOf(oR)+1)%RR.length];
  if(gA)t2(gA)                                      // t2 = model select handler
},[fJ])
```

**关键设计：动态探测，不硬编码函数名**
- `find_settings_service_getter()`: 查找所有 `XXX().getCustomModels()` 调用，验证 `function XXX(){return YYY}` 形式的单例 getter，取频次最高的 → 0.104.0 探测结果 `UR()`
- `find_session_service_getter()`: 查找同时调用 `getModel()` 和 `hasSpecModeModel()` 的函数 → 0.104.0 探测结果 `vT()`

历史教训: 旧版 mod5 硬编码 `c8A()` 和 `GR()`，在 0.104.0 中分别对应不同的东西（IamClient class / lazy-init namespace），导致 Ctrl+N 失效。动态探测确保跨版本兼容。

**支持状态**:
- 原版 selector callback → 直接 cycle
- 旧错误 patch（peekNextCycleModel 版）→ 修复为直接 cycle
- 已 patch → 幂等跳过
- 旧稳定函数补丁（`customModels.map` 注入）→ 自动回滚再重新 patch

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

OpenAI custom model 的 compress/summarizer 两条路径都从 Responses API 重定向到 Chat Completions API。

v0.96.0: 使用 `provider==="openai"` 直接判断 (+32 bytes)
v0.99.0: 重构为 `lxH(provider)` 函数调用，`lxH` 定义为 `return H==="openai"||H==="xai"`

**修改**: 两处 `if(lxH(...))` 加 `&&!1` 短路，使其落到后面的 `chat.completions.create(...)` (+8 bytes)
- 路径1: BYOK custom model: `if(lxH(h.provider))` → `if(lxH(h.provider)&&!1)`
- 路径2: proxy 路径: `if(lxH(W))` → `if(lxH(W)&&!1)`

脚本动态查找 lxH 等效函数名，兼容不同版本的 minified 名称。

### mod9: 禁用自动更新 (可选)

`checkForUpdates()` 函数体首行替换为 `return null;` + 注释填充等长

### mod10: tag strip 找不到闭标签时不截断 (可选)

**Bug**: `<system-reminder>` / `<system-notification>` 的 tag 剥离函数在找不到闭标签时（例如 model 输出字面量开标签），`if(VAR<0){VAR=VAR.slice(0,VAR);break}` 会从开标签位置截断**所有后续内容**。

**修复**: `slice(0,B)` → `slice(0  )`（0 bytes，`slice(0)` 返回原字符串即 no-op）

v0.104.0 中每个 tag 一处，共 2 处 patch。脚本通用变量名匹配，不硬编码。

### mod11: BYOK unicode escape 修复 (可选)

**Bug**: YcM/NcM 的 JSON 字符串解析器在 switch default case 中处理 `\uXXXX` 时只取 backslash 后一个字符：`\u5de5 → u5de5`（丢反斜杠）。BYOK 路径（直连 Anthropic/OpenAI）中工具调用里的中文/emoji 参数会损坏。

**修复**: 两处 `default:A+=V;break}}else A+=H[Y];Y++` → `V=="u"?(A+=String.fromCharCode(parseInt(H.slice(Y+1,Y+5),16)),Y+=4):A+=V;break}}else A+=H[...`（+68 bytes × 2 = +136 bytes）

### mod12: proxy unicode 裸 uXXXX 预处理 (可选)

**Bug**: 上游 proxy（如 claude-code-relay、OneAPI）在 `partial_json` 中传递中文时会使用错误格式 `u5de5`（无反斜杠）而非 `\u5de5`。工具调用走 `input_json_delta.partial_json`，触发 bug，参数损坏。

**修复**: 在 `wU$/r_T` 函数入口（动态探测函数名）插入预处理 `H=H.replace(/(?<!\\\\)u([0-9a-fA-F]{4})/g,'\\\\u$1')`，将裸 `uXXXX` 转回 `\uXXXX`。（+49 bytes）

覆盖 `JSON.parse` 和 `YcM` 两条路径。droid 诊断 "heredoc 传中文问题" 是错的，实际是 proxy JSON 序列化 bug。

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

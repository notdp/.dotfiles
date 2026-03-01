---
name: droid-bin-mod
description: 修改 droid 二进制以禁用截断和解锁功能。当用户提到：修改/恢复/测试 droid、press Ctrl+O、output truncated、显示完整命令或输出、mission 门控时触发。
---

# Droid Binary Modifier

修改 Factory Droid CLI 二进制文件，禁用命令/输出截断，实现默认展开显示。

## 使用流程

### 如果用户说"测试"或"测试droid修改"

**直接执行以下命令验证修改效果，不要询问：**

```bash
# 测试 mod1+2 (命令截断) - 100字符命令应完整显示
echo "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" && echo done

# 测试 mod3+5 (输出行数+提示) - 99行无提示，100行有提示
seq 1 99   # 应显示99行，无 "press Ctrl+O" 提示
seq 1 100  # 应显示99行，有 "press Ctrl+O" 提示

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
│ ... output truncated. press Ctrl+O for detailed view      ← mod5   │
├────────────────────────────────────────────────────────────────────┤
│ EDIT  (README.md) +10 -5                                           │
│ ... (truncated after 20 lines)                            ← mod4   │
│ ... output truncated. press Ctrl+O for detailed view               │
└────────────────────────────────────────────────────────────────────┘

mod1: 命令框 "command truncated. press Ctrl+O" 提示 → 隐藏
mod2: 命令超 50 字符截断 → 超 99 字符才截断
mod3: 命令输出截断行数 4 行 → 99 行
mod4: Edit diff 截断行数 20 行 → 99 行
mod5: 输出区 "output truncated. press Ctrl+O" 提示 >4 行 → >99 行
mod6: Ctrl+N 只在 custom model 间切换 (/model 菜单不受影响)
mod7: Mission 门控破解 → /enter-mission 可用 (BYOK)
mod8: Mission 模型不强切 → Orchestrator 保持 custom model
mod9: Custom model 支持完整 effort 级别 (anthropic: max, openai: xhigh)

注：mod1 影响命令框提示，mod5 影响输出区提示，两者位置不同
注：mod7+mod8 配合 settings.json 中 missionModelSettings 设置 Worker/Validator 模型
注：mod9 修复 custom model Tab 切换只有 off/low/medium/high 的限制

select: 1,2,3,4,5,6,7,8,9 / all / restore
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
| 4 diff 行数 | (后跟变量声明)   | `var V=20,V,` (后跟逗号+变量)           | `var LD=20,UDR,`          |
| 5 输出提示  | `exec-preview`   | `,V>4&&V\.jsxDEV` (marker附近)          | `,D>4&&q1.jsxDEV`         |

### 0.49+ 版本变化

mod3 和 mod5 现在使用同一个变量控制：`aGR=4`
- `slice(0,aGR)` - 截取前 aGR 行显示
- `D>aGR&&` - 超过 aGR 行才显示提示

修改 `aGR=4` → `aGR=99` 一次性解决 mod3 和 mod5，+1 byte 变化（4→99 多一位数字），需要补偿。

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

### 修改 3+5: 输出预览行数和提示条件

**位置**: 命令执行结果显示区域

**修改**: `aGR=4` → `aGR=99`

- 变量 `aGR` 同时控制：
  - `slice(0,aGR)` - 显示前多少行
  - `D>aGR&&` - 超过多少行显示提示
- 修改变量定义，一次性解决两个问题
- +1 byte 变化（4→99 多一位数字），需要补偿

### 修改 4: diff/edit 显示行数

**位置**: Edit 工具的 diff 输出

**修改**: `var LD=20` → `var LD=99`

- 原来 diff 最多显示 20 行
- 现在显示 99 行

## 修改汇总

| #   | 修改项       | 原始         | 修改后         | 字节 | 说明                                      |
| --- | ------------ | ------------ | -------------- | ---- | ----------------------------------------- |
| 1   | 截断条件     | `if(!H&&!Q)` | `if(!0\|\|!Q)` | 0    | 短路截断函数，隐藏命令框 "press Ctrl+O"   |
| 2   | 命令阈值     | `length>50`  | `length>99`    | 0    | 命令超 99 字符才截断                      |
| 3+5 | 输出行数     | `aGR=4`      | `aGR=99`       | +1   | 输出显示 99 行，超过才显示提示            |
| 4   | diff 行数    | `LD=20`      | `LD=99`        | 0    | Edit diff 显示 99 行                      |
| 6   | model cycle  | peek/cycle 函数 | 覆盖H+移除检查  | 0    | Ctrl+N 只切换 custom model                |
| 7   | mission 门控 | `enable_extra_mode`,`!1` | `enable_extra_mod0`,`!0` | 0 | /enter-mission 可用 |
| 8   | mission 模型 | `Y9H.includes(X)` | `!0` + 空格填充 | 0  | 改条件而非数据，不强切+不警告         |
| 9   | effort 级别  | `["off","low","medium","high"]` | 按 provider 区分 | +66 | anthropic 加 max，openai 加 xhigh |
| 补偿 | 死代码区域   | 多处死代码   | 注释/缩短填充   | -67  | 统一补偿 mod3(+1) + mod9(+66)        |

**注**：
- mod1: 命令框提示（command truncated）
- mod3+5: 输出区行数和提示（output truncated）由同一变量控制
- mod6: 修改 `peekNextCycleModel`, `peekNextCycleSpecModeModel`, `cycleSpecModeModel` 三个函数
  （`cycleModel` 是委托函数，无需修改）
- mod7: 改 `EnableAGIMode` 定义处的 statsigName + defaultValue
- mod8: 两处 `Y9H.includes(X)` → `!0`（改条件，不改数据结构）
- mod9: wR() 中 custom model 分支，根据 T.provider 返回正确的 effort 列表

### 修改 7: Mission 门控破解

**位置**: `EnableAGIMode` 定义处

**原始代码**:
```javascript
EnableAGIMode:{displayName:"Enable Extra Mode",statsigName:"enable_extra_mode",defaultValue:!1}
```

**修改**:
1. `statsigName:"enable_extra_mode"` → `"enable_extra_mod0"` (末尾 `e`→`0`)
2. `defaultValue:!1` → `defaultValue:!0`

**原理**: Statsig 查不到 `"enable_extra_mod0"` → 返回 `undefined` → `??` fallback 到 `!0`(true) → 门控通过。
一处定义影响所有引用: `/enter-mission`、`/mission`、`/missions`、UI filter。

**稳定锚点**: `EnableAGIMode`, `statsigName:"enable_extra_mode"`, `defaultValue:!1` — 均为字符串常量。

### 修改 8: Mission 模型白名单恒通过

**位置**: 两处 `Y9H.includes()` 调用

**原始代码**:
```javascript
// enter-mission: 检查模型是否在白名单
if(Y9H.includes(I)){if(!h9H.includes(D))B.setReasoningEffort(B7H)}
else B.setModel(VCA,B7H),B.setReasoningEffort(B7H)

// vO 回调: 模型切换时检查是否弹警告
if(!(Y9H.includes(kA)&&h9H.includes(bR)))K("system",$7H,...)
```

**修改**: 将两处 `Y9H.includes(X)` 替换为 `!0` + 空格填充等长

```javascript
// enter-mission: 永远走 if 分支，不强切模型
if(!0             ){if(!h9H.includes(D))B.setReasoningEffort(B7H)}
else B.setModel(VCA,B7H),B.setReasoningEffort(B7H)  // 永远不执行

// vO 回调: 等价于 if(!h9H.includes(bR))，只检查 effort
if(!(!0              &&h9H.includes(bR)))K("system",$7H,...)
```

**原理**: 直接改条件表达式，不改数据结构（旧方案将 Y9H 数组替换为对象，存在运行时类型风险）。
- enter-mission: custom model 保留，只在 reasoning effort 不对时修正
- vO: 任意模型不再触发警告，只在 effort 不是 high/xhigh 时警告

**配合 mod7**: 应用 mod7+mod8 后，检查 `~/.factory/settings.json` 配置完整性，
确保 custom model 和 missionModelSettings 都正确配置。

**交互流程**:
1. 读取 settings.json 的 `customModels`，检查每个 custom model 是否有 `reasoningEffort` 字段：
   - 如果缺少，提示用户：`custom model "XXX" 缺少 reasoningEffort 字段，建议设为 "high"，否则进入 mission 时会显示模型警告。是否自动添加？`
   - 用户确认后写入（或用户手动指定值）
   - 原因：droid 用 `customModels[].reasoningEffort` 作为模型的 `defaultReasoningEffort`，缺失时 fallback 到 `"none"`，导致 mission 模式 vO 回调警告触发
2. 检查已有的 `missionModelSettings`
3. 列出可选模型，显示当前配置，让用户选择:
```
当前 missionModelSettings:
  Worker:    Claude Opus 4.6 [custom:Claude-Opus-4.6-0] (high)
  Validator: GPT-5.3 Codex [custom:GPT-5.3-Codex-1] (high)

可选模型:
  0: Claude Opus 4.6  (custom:Claude-Opus-4.6-0)
  1: GPT-5.3 Codex    (custom:GPT-5.3-Codex-1)

选择 Worker 模型 [0]:
选择 Validator 模型 [1]:
```
4. 默认推荐: Worker 用 `sessionDefaultSettings.model`，Validator 用第二个 custom model（如有）
5. 写入 settings.json 顶层 `missionModelSettings` 字段，格式如下：

```json
{
  "missionModelSettings": {
    "workerModel": "custom:Claude-Opus-4.6-0",
    "workerReasoningEffort": "high",
    "validationWorkerModel": "custom:GPT-5.3-Codex-1",
    "validationWorkerReasoningEffort": "high"
  }
}
```

**注意**：值必须是字符串（model ID），不是对象。Key 名是 `validationWorkerModel`，不是 `validatorModel`。

**稳定锚点**: 上下文关键字 `getReasoningEffort` + `h9H.includes` + `if(!(` 结构。
变量名 `Y9H`、`h9H`、参数名 `I`/`kA` 均为混淆产物，版本间会变，脚本用正则 + 上下文定位。

### 修改 6: Ctrl+N 只在 custom model 间切换

**目标函数**: `peekNextCycleModel`, `peekNextCycleSpecModeModel`, `cycleSpecModeModel` (3 个)

> `cycleModel` 是委托函数（调用 `peekNextCycleModel`），无 `validateModelAccess`，无需修改。

**原始代码** (以 peekNextCycleModel 为例):

```javascript
peekNextCycleModel(H){
  if(H.length===0)return null;
  ...
  if(!this.validateModelAccess(D).allowed)continue;
  ...
}
```

**修改**:
1. 函数入口覆盖参数: `H=this.customModels.map(m=>m.id);` (+N bytes)
2. 移除 `validateModelAccess` 检查，替换为等长注释 (-N bytes)

```javascript
peekNextCycleModel(H){
  H=this.customModels.map(m=>m.id);
  if(H.length===0)return null;
  ...
  /*            */
  ...
}
```

**效果**: Ctrl+N 只在 settings.json 中配置的 custom model 间切换，`/model` 菜单不受影响

**稳定锚点**（不受混淆影响）:
- `peekNextCycleModel` / `peekNextCycleSpecModeModel` / `cycleSpecModeModel` — 方法名
- `this.validateModelAccess` / `.allowed` — 方法和属性名
- `this.customModels` — 属性名

### 修改 9: Custom model 完整 effort 级别

**位置**: `wR()` 函数中 custom model 分支

**问题**: wR() 对 custom model 硬编码 `supportedReasoningEfforts` 为 `["off","low","medium","high"]`，
缺少 anthropic 的 `"max"` 和 openai 的 `"xhigh"`，导致 Tab 切换无法到达这些级别。

**原始代码**:
```javascript
supportedReasoningEfforts:L?["off","low","medium","high"]:["none"]
```

**修改**:
```javascript
supportedReasoningEfforts:L?T.provider=="openai"?["none","low","medium","high","xhigh"]:["off","low","medium","high","max"]:["none"]
```

**效果**:
- Anthropic custom model: `off → low → medium → high → max → off ...`
- OpenAI custom model: `none → low → medium → high → xhigh → none ...`

**字节**: +66 bytes，由 `comp_universal.py` 统一补偿。

**稳定锚点**: `supportedReasoningEfforts`、`T.provider`、`["off","low","medium","high"]` — 均为字符串常量。

**配合 mod9**: 应用 mod9 后，检查 `~/.factory/settings.json` 中 `extraArgs` 的 effort 相关参数。
mod9 解锁了完整 effort 级别后，extraArgs 中的 effort 参数已冗余，且会导致副作用。

**交互流程**:
1. 运行 `status.py` 检查配置
2. 如果发现 extraArgs 中有 effort 相关参数，询问用户是否移除，并说明：
   - Anthropic: `extraArgs.thinking` 和 `extraArgs.output_config.effort` 已不需要
   - OpenAI: 必须移除整个 `extraArgs.reasoning` 对象（包括 `reasoning.summary`），`text.verbosity` 可保留
   - **不移除的后果**:
     - `extraArgs` 在 `responses.create()` 中通过 JS 浅展开 (`...extraArgs`) 排在 `requestParams` 之后
     - `extraArgs.reasoning` 会整个覆盖 `requestParams.reasoning`（含 `effort` 字段），导致 effort 丢失
     - 例如: `{...{reasoning: {effort:"high", summary:"auto"}}, ...{reasoning: {summary:"detailed"}}}` = `{reasoning: {summary:"detailed"}}` — effort 没了
     - 结果：Tab 切换 Thinking Level 完全无效，所有级别发出的请求体一样
3. 用户确认后修改 settings.json：
   - Anthropic: 移除 `thinking` + `output_config.effort`；如果 extraArgs 变为空对象 `{}`，删除整个 `extraArgs` 字段
   - OpenAI: 移除整个 `reasoning` 键（不能只移除 `reasoning.effort` 而保留 `reasoning.summary`，因为浅展开会覆盖整个对象）；`text.verbosity` 可保留

## 修改脚本

脚本位置: `~/.factory/skills/droid-bin-mod/scripts/`

### mods/ - 功能修改

```bash
mods/mod1_truncate_condition.py  # 截断条件短路 (0 bytes)
mods/mod2_command_length.py      # 命令阈值 50→99 (0 bytes)
mods/mod3_output_lines.py        # 输出行数 aGR=4→99 (+1 byte, 同时解决 mod5)
mods/mod4_diff_lines.py          # diff行数 20→99 (0 bytes)
mods/mod5_exec_hint.py           # 由 mod3 自动处理
mods/mod6_custom_model_cycle.py  # Ctrl+N 只切换 custom model (0 bytes)
mods/mod7_mission_gate.py        # Mission 门控破解 (0 bytes)
mods/mod8_mission_model.py             # Mission 模型不强切 (0 bytes)
mods/mod9_custom_effort_levels.py      # custom model effort 级别 (+66 bytes)
```

mod3 产生 +1 byte，mod9 产生 +66 bytes，合计 +67 bytes。
由 `comp_universal.py 67` 统一补偿。

### compensations/ - 字节补偿

```bash
compensations/comp_universal.py          # 通用补偿，利用所有 mod 的死代码区域 (~249B 可用)
compensations/comp_universal.py          # 无参数: 显示当前可用补偿空间
compensations/comp_universal.py <bytes>  # 缩减指定字节数
compensations/comp_substring.py <bytes>  # 旧方案：仅修改 FFH 函数的 substring
compensations/comp_r80_to_r8.py          # 旧方案：R=80→R=8 (-1 byte)
```

用法：`python3 comp_universal.py 67` 补偿 mod3(+1) + mod9(+66) 的 +67 bytes。

补偿区域来源 (由各 mod 短路/替换产生的死代码):
- FFH 死代码 (mod1 短路): ~151B — 截断函数被短路后的不可达代码，替换为 `;return{text:H,isTruncated:!1}`
- mod8 else 分支: ~44B — enter-mission 永不执行的 else
- mod8 空格填充: ~25B — !0 替换后的空格
- mod6 注释: ~36B — validateModelAccess 注释掉的检查

### 执行示例（跨平台）

```bash
# 1. macOS: 移除签名
[[ "$OSTYPE" == "darwin"* ]] && codesign --remove-signature ~/.local/bin/droid

# 2. 执行修改
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod1_truncate_condition.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod2_command_length.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod3_output_lines.py       # +1 byte
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod4_diff_lines.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod6_custom_model_cycle.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod7_mission_gate.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod8_mission_model.py
python3 ~/.factory/skills/droid-bin-mod/scripts/mods/mod9_custom_effort_levels.py  # +66 bytes
python3 ~/.factory/skills/droid-bin-mod/scripts/compensations/comp_universal.py 67  # 补偿 mod3(+1) + mod9(+66)

# 3. macOS: 重新签名
[[ "$OSTYPE" == "darwin"* ]] && codesign -s - ~/.local/bin/droid
```

**说明**：`[[ "$OSTYPE" == "darwin"* ]]` 自动检测平台，macOS 执行签名操作，Linux 跳过。

### 工具脚本

```bash
python3 ~/.factory/skills/droid-bin-mod/scripts/status.py   # 检查状态
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py  # 恢复原版
```

脚本使用正则匹配变量名，适应混淆后变量名变化。

## 前提条件

- macOS 或 Linux 系统
- Python 3
- droid 二进制位于 `~/.local/bin/droid`

**平台差异**：
- macOS: 需要 codesign 移除/重签签名
- Linux: 无需签名操作，直接修改即可
- Windows: 未测试，不支持

## 修改流程（跨平台）

```bash
# 1. 备份 (带版本号)
cp ~/.local/bin/droid ~/.local/bin/droid.backup.$(~/.local/bin/droid --version)

# 2. macOS: 移除签名
[[ "$OSTYPE" == "darwin"* ]] && codesign --remove-signature ~/.local/bin/droid

# 3. 执行修改脚本 (参考上面的修改原理)

# 4. macOS: 重新签名
[[ "$OSTYPE" == "darwin"* ]] && codesign -s - ~/.local/bin/droid

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

# 测试修改3+5 (输出行数+提示)
seq 1 99   # 99行无提示
seq 1 100  # 100行有提示

# 测试修改4 (diff行数) - 先创建文件
seq 1 100 > /tmp/test100.txt
# 然后让 droid 编辑前30行看 diff
```

### 检查点

- 修改 1: 命令框不再显示 "command truncated. press Ctrl+O for detailed view"
- 修改 2: 100 字符的命令完整显示
- 修改 3+5: `seq 1 99` 显示 99 行无提示，`seq 1 100` 显示 99 行有提示
- 修改 4: diff 显示超过 20 行（原来只显示 20 行）

## 恢复原版

**推荐用脚本恢复**（macOS 上直接 cp 会因元数据问题导致 SIGKILL，Linux 可直接 cp）：

```bash
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py --list  # 查看备份
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py         # 恢复最新
python3 ~/.factory/skills/droid-bin-mod/scripts/restore.py 0.46.0  # 恢复指定版本
```

## 禁用自动更新

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
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

### 6. mod6/7/8/9 排查

**mod6** (custom model cycle):
```bash
# 检查方法名是否存在
strings ~/.local/bin/droid | grep -E "peekNextCycleModel|cycleSpecModeModel|validateModelAccess"
```

**mod7** (mission 门控):
```bash
# 检查 EnableAGIMode 定义
strings ~/.local/bin/droid | grep "enable_extra_mode"
```

**mod8** (mission 模型):
```bash
# 检查 includes + getReasoningEffort 上下文
strings ~/.local/bin/droid | grep -E "getReasoningEffort|\.includes\("
```

**mod9** (effort 级别):
```bash
# 检查 effort 列表
strings ~/.local/bin/droid | grep "supportedReasoningEfforts"
strings ~/.local/bin/droid | grep -E '\["off","low","medium","high"\]'
```

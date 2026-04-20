---
name: droid-bin-mod
description: 修改 droid 二进制以禁用截断和解锁功能。当用户提到：修改/恢复/测试 droid、press Ctrl+O、output truncated、显示完整命令或输出、mission 门控时触发。
---

# Droid Binary Modifier

修改 Factory Droid CLI 二进制文件，禁用命令/输出截断、解锁 custom model 与 effort 级别、适配 Opus 4.7 adaptive thinking。

## 使用流程

### 如果用户说"测试"或"测试droid修改"

**直接执行以下命令验证修改效果，不要询问：**

```bash
# 测试 mod1+2 (命令截断) - 100 字符命令应完整显示
echo "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" && echo done

# 测试 mod3 (输出行数+提示) - 99 行无提示，100 行有提示
seq 1 99
seq 1 100

# 测试 mod4 (diff 行数) - 先造文件
seq 1 100 > /tmp/test100.txt
```

然后执行：把 `/tmp/test100.txt` 的第 1-100 行全部替换成 `A1` 到 `A100`，diff 应显示 99 行。

### 如果用户说"修改"或"恢复"

**询问用户需要哪些修改：**

```bash
┌────────────────────────────────────────────────────────────────────┐
│ EXECUTE  (echo "aaa..." command truncated. press Ctrl+O)  ← mod1+2 │
│ line 1                                                             │
│ ...                                                                │
│ line 4                                                    ← mod3   │
│ ... output truncated. press Ctrl+O for detailed view      ← mod3   │
├────────────────────────────────────────────────────────────────────┤
│ EDIT  (README.md) +10 -5                                           │
│ ... (truncated after 20 lines)                            ← mod4   │
└────────────────────────────────────────────────────────────────────┘

mod1:  隐藏命令框 "command truncated. press Ctrl+O" 提示
mod2:  命令超 50 字符截断 → 超 99 字符才截断
mod3:  命令输出截断行数 4 → 99（同时取消输出区 Ctrl+O 提示）
mod4:  Edit diff 截断行数 20 → 99
mod5:  Ctrl+N 只在 custom model 间切换（/model 菜单不受影响）
mod6:  Mission 模型不强切 → Orchestrator 保持 custom model
mod7:  Custom model 支持完整 effort 级别（anthropic: xhigh,max / openai: xhigh）
mod8:  禁用内置模型 → /model 菜单只显示 BYOK custom model
mod9:  禁用自动更新 → checkForUpdates() 返回 null
mod10: 适配 Opus 4.7 adaptive thinking → P7I 跳过历史剥离，跨轮保留 thinking 配置

select: 1-10 / all / restore
```

用户选择后，执行对应修改。

## 版本适配说明

**混淆 JS 的应对策略**：变量名/函数名会变，但**字符串常量和代码结构不变**。脚本用正则 + 上下文定位，不依赖具体变量名。

### 第一步：用不变的字符串定位

```bash
strings ~/.local/bin/droid | grep "isTruncated"              # mod1
strings ~/.local/bin/droid | grep "command.length>"          # mod2
strings ~/.local/bin/droid | grep "exec-preview"             # mod3
strings ~/.local/bin/droid | grep -E "var [A-Z]{2}=20,"      # mod4
strings ~/.local/bin/droid | grep "peekNextCycleModel"       # mod5
strings ~/.local/bin/droid | grep "getReasoningEffort"       # mod6
strings ~/.local/bin/droid | grep "supportedReasoningEfforts" # mod7
strings ~/.local/bin/droid | grep "isCustomModel"            # mod8
strings ~/.local/bin/droid | grep "async checkForUpdates"    # mod9
strings ~/.local/bin/droid | grep -E "thinking.{0,20}I7I"    # mod10
```

### 第二步：用模式匹配确认

定义 JS 变量名模式: `V = [A-Za-z_$][A-Za-z0-9_$]*`

## 修改原理

### 修改 1: 截断函数条件

**目标**: 命令/输出永不截断，不显示 "press Ctrl+O" 提示。

**位置**: 截断函数（含 `isTruncated` 返回字段）。

**原始代码**:

```javascript
function JZ9(A, R=80, T=3) {
  if (!A) return {text: A||"", isTruncated: !1};
  let B = A.split("\n"),
      H = B.length > T,
      Q = A.length > R;
  if (!H && !Q) return {text: A, isTruncated: !1};  // 早期返回
  // ... 截断逻辑 ...
  return {text: J, isTruncated: !0};
}
```

**修改**: `if(!H&&!Q)` → `if(!0||!Q)`（永远走早期返回，后续截断代码成死代码）。

**字节**: 0 bytes。

**稳定锚点**: `isTruncated` 字符串常量。

### 修改 2: 命令显示阈值

**目标**: 命令文本超过 50 字符就截断 → 改为超过 99 字符才截断。

**位置**: 命令文本显示。

**修改**: `command.length>50` → `command.length>99`。

**字节**: 0 bytes。

**稳定锚点**: `command.length>` 字符串常量。

### 修改 3: 输出预览行数和提示条件

**目标**: 命令执行结果只显示前 4 行并提示 Ctrl+O → 改为 99 行才提示。

**位置**: 命令执行结果显示区域，变量 `aGR` 同时控制 `slice(0,aGR)`（显示行数）和 `D>aGR&&`（显示提示条件）。

**修改**: `aGR=4` → `aGR=99`（一次改动同时解决行数 + 提示）。

**字节**: 视版本 +1~+4 bytes（数字位数变化），由 `comp_universal.py` 补偿。

**稳定锚点**: `exec-preview` 字符串常量 + 附近的 `slice(0,X)` 模式。

### 修改 4: diff/edit 显示行数

**目标**: Edit 工具 diff 最多显示 20 行 → 改为 99 行。

**位置**: diff 渲染代码段。

**修改**: `var LD=20` → `var LD=99`。

**字节**: 0 bytes。

**稳定锚点**: `var V=20,V,` 结构（后跟变量声明）。

### 修改 5: Ctrl+N 只在 custom model 间切换

**目标**: Ctrl+N 切换模型时只在 settings.json 中配置的 custom model 间循环，不再包含 droid 内置模型。

**目标函数**: `peekNextCycleModel`、`peekNextCycleSpecModeModel`、`cycleSpecModeModel` 三个（`cycleModel` 是委托函数，无需改）。

**原始代码** (以 `peekNextCycleModel` 为例):

```javascript
peekNextCycleModel(H){
  if(H.length===0)return null;
  ...
  if(!this.validateModelAccess(D).allowed)continue;
  ...
}
```

**修改**:
1. 函数入口覆盖参数: `H=this.customModels.map(m=>m.id);`
2. 移除 `validateModelAccess` 检查，替换为等长注释

```javascript
peekNextCycleModel(H){
  H=this.customModels.map(m=>m.id);
  if(H.length===0)return null;
  ...
  /*            */
  ...
}
```

**字节**: 0 bytes（入口加法 + 检查删减等长抵消）。

**稳定锚点**: 方法名 `peekNextCycleModel` 等 + `this.validateModelAccess`、`.allowed`、`this.customModels` 属性名。

### 修改 6: Mission 模型白名单恒通过

**目标**: 进入 mission 模式不强切 Orchestrator 模型，custom model 可保留。

**位置**: 两处 `Y9H.includes()` 调用（enter-mission 分支 + vO 警告回调）。

**原始代码**:

```javascript
// enter-mission
if(Y9H.includes(I)){if(!h9H.includes(D))B.setReasoningEffort(B7H)}
else B.setModel(VCA,B7H),B.setReasoningEffort(B7H)

// vO 警告回调
if(!(Y9H.includes(kA)&&h9H.includes(bR)))K("system",$7H,...)
```

**修改**: 两处 `Y9H.includes(X)` 替换为 `!0` + 空格等长填充。

```javascript
if(!0             ){if(!h9H.includes(D))B.setReasoningEffort(B7H)}
else B.setModel(VCA,B7H),B.setReasoningEffort(B7H)          // 永远不执行（死代码）

if(!(!0              &&h9H.includes(bR)))K("system",$7H,...)
```

**字节**: 0 bytes。

**稳定锚点**: `getReasoningEffort` + `h9H.includes` + `if(!(` 结构关键字上下文。

**配合 settings.json**: 应用 mod6 后检查 `customModels[].reasoningEffort` 和顶层 `missionModelSettings`：

```json
{
  "missionModelSettings": {
    "workerModel": "custom:Claude-Opus-4.7-0",
    "workerReasoningEffort": "high",
    "validationWorkerModel": "custom:GPT-5.3-Codex-1",
    "validationWorkerReasoningEffort": "high"
  }
}
```

值必须是字符串（model ID），key 名是 `validationWorkerModel`（不是 `validatorModel`）。`customModels[].reasoningEffort` 缺失会 fallback 到 `"none"`，触发 vO 警告。

### 修改 7: Custom model 完整 effort 级别

**目标**: custom model 的 Tab 切换除 `off/low/medium/high` 外解锁更高级别（anthropic `max`、openai `xhigh`）。

**位置**: `wR()` 函数中 custom model 分支。

**原始代码**:

```javascript
supportedReasoningEfforts:L?["off","low","medium","high"]:["none"]
```

**修改**: 根据 `T.provider` 返回不同 effort 列表：

```javascript
supportedReasoningEfforts:L?T.provider=="openai"?["none","low","medium","high","xhigh"]:["off","low","medium","high","max"]:["none"]
```

**效果**:
- Anthropic custom model: `off → low → medium → high → max → off ...`
- OpenAI custom model: `none → low → medium → high → xhigh → none ...`

**字节**: +74 bytes/处，通常命中 2 处共 +148 bytes，由 `comp_universal.py` 统一补偿。

**稳定锚点**: `supportedReasoningEfforts`、`T.provider`、`["off","low","medium","high"]` 字符串常量。

**配合 settings.json**: mod7 解锁 effort 后，settings.json 的 `extraArgs` 中 effort 相关参数需清理，否则 JS 浅展开（`...extraArgs`）会覆盖请求体里的 effort，让 Tab 切换失效。
- Anthropic: 移除 `extraArgs.thinking` 与 `extraArgs.output_config.effort`
- OpenAI: 移除整个 `extraArgs.reasoning` 对象（不能只移除 `reasoning.effort` 而保留 `reasoning.summary`，因为浅展开覆盖整个键）；`text.verbosity` 可保留

### 修改 8: 禁用 droid 官方内置模型

**目标**: `/model` 菜单和 Ctrl+N 只能选 BYOK custom model，内置模型返回 `allowed: false`。

**位置**: `validateModelAccess` 函数的最终 return。

**原始代码**:

```javascript
validateModelAccess(H) {
  if (H.startsWith("custom:")) { return {allowed: !0, isCustomModel: !0} }
  if (!kcH(H, $)) return {allowed: !1, reason: bwH, isCustomModel: !1};
  return {allowed: !0, isCustomModel: !1}   // ← 内置模型通过
}
```

**修改**: `return{allowed:!0,isCustomModel:!1}` → `return{allowed:!1,isCustomModel:!1}`。

**效果**:
- 非 `custom:` 前缀模型全部拒绝
- `getModel` fallback 逻辑自动切到第一个可用 custom model
- `hasAnyAvailableModel` 仍返回 true

**字节**: 0 bytes。

**稳定锚点**: `isCustomModel:!1};return{allowed:` + `isCustomModel:!1}}` 字符串常量。

### 修改 9: 禁用自动更新

**目标**: 阻止 droid 启动时自动下载新版本覆盖已 patch 的二进制。

**位置**: `Zp.checkForUpdates()` 方法。

**原始代码**:

```javascript
async checkForUpdates(){let H,{remoteConfig:$}=this.config;if($.apiUrl)H=...}
```

**修改**: 函数体开头插入 `return null;`，用注释填充到等长：

```javascript
async checkForUpdates(){return null;/*                   */if($.apiUrl)H=...}
```

**效果**: 调用方 `$WD()` 收到 null 走 `if(!E)return "no-update"` 分支，跳过整个下载/安装流程。

**字节**: 0 bytes。

**稳定锚点**: 方法名 `async checkForUpdates(`。

**建议**: 配合 `sudo chattr +i ~/.local/bin/droid`（Linux）或同等手段双保险锁定文件。

### 修改 10: 适配 Opus 4.7 adaptive thinking

**目标**: 让 `{type:"adaptive", display:"summarized"}` 的 thinking 配置跨轮保留，使 Opus 4.7 的自适应思考预算在工具循环中持续生效。

**位置**: `P7I` 函数内的历史检测分支。

**问题**: `summarized` 模式下 assistant 响应首块通常直接是 `tool_use`（非 `type:"thinking"`）。droid 的 P7I 原逻辑检测到"历史中存在 assistant 消息但不以 thinking 开头"（`I7I` 返回 true），会剥掉当前请求的 thinking 配置并从历史中删除所有 thinking 块。结果：第二轮起 thinking 永久关闭，服务端无法继续 adaptive 分配。

**原始代码**:

```javascript
if(T.thinking){
  if(I7I(B)||D7I(B)){
    if(E7I(G))T={outputConfig:T.outputConfig,betaFlags:T.betaFlags};
    else T={betaFlags:[]};
    if(E.messages&&Array.isArray(E.messages))E.messages=f7I(E.messages)
  }
}
```

**修改**: `I7I(B)||D7I(B)` → `!1            `（`!1` + 12 空格，同长替换）。

**效果**: 内层条件永远为假，历史检测分支不执行，thinking 配置跨轮保留。

**字节**: 0 bytes。

**稳定锚点**: `V.thinking){if(V(V)||V(V))` 结构（`||` + `.thinking` 属性名）。

**副作用**: 对 `type:"enabled"` 模式也跳过历史剥离。若历史里存在不一致 thinking 块且模式切到 `enabled`，理论上可能触发 Anthropic 一致性报错（实测未见）。更保守的做法是仅对 `adaptive` 类型跳过（+26 字节版本，需 comp_universal 补偿）。

**验证**: 运行 `droid exec --skip-permissions-unsafe "run pwd, echo, date separately"` 后检查 CLIProxyAPI 日志，期望连续多轮请求均携带 `"thinking":{"type":"adaptive","display":"summarized"}`。

## 修改汇总

| #   | 名称           | 原始                                   | 修改后                          | 字节    | 效果                                         |
| --- | -------------- | -------------------------------------- | ------------------------------- | ------- | -------------------------------------------- |
| 1   | 截断条件       | `if(!H&&!Q)`                           | `if(!0\|\|!Q)`                  | 0       | 截断函数短路，命令/输出永不截断              |
| 2   | 命令阈值       | `length>50`                            | `length>99`                     | 0       | 命令超 99 字符才截断                         |
| 3   | 输出行数+提示  | `aGR=4`                                | `aGR=99`                        | +1~+4   | 输出 99 行后才显示 Ctrl+O 提示               |
| 4   | diff 行数      | `LD=20`                                | `LD=99`                         | 0       | Edit diff 显示 99 行                         |
| 5   | model cycle    | peek/cycle 函数                        | 覆盖参数 + 移除 access 检查     | 0       | Ctrl+N 只切换 custom model                   |
| 6   | mission 模型   | `Y9H.includes(X)` ×2                   | `!0` + 空格填充                 | 0       | mission 不强切 + 不弹警告                    |
| 7   | effort 级别    | `["off","low","medium","high"]`        | 按 provider 返回完整列表         | +148    | Tab 可达 anthropic `max` / openai `xhigh`    |
| 8   | 禁用内置模型   | `allowed:!0`                           | `allowed:!1`                    | 0       | validateModelAccess 非 custom 全部拒绝       |
| 9   | 禁用自动更新   | `let H,{remoteConfig:$}=this.config;`  | `return null;/*..*/`            | 0       | checkForUpdates() 直接返回 null              |
| 10  | adaptive thinking | `if(I7I(B)\|\|D7I(B))`              | `if(!1            )`            | 0       | P7I 跳过历史剥离，adaptive 跨轮保留          |

**字节补偿**: mod3 和 mod7 产生的增量（通常合计 +149~+152 bytes）由 `comp_universal.py N` 从各 mod 短路/替换产生的死代码区域中回收，总可用空间约 249 bytes。

## 修改脚本

脚本位置: `~/.claude/skills/droid-bin-mod/scripts/`

### mods/ — 功能修改

```
mod1_truncate_condition.py          # 截断条件短路 (0 bytes)
mod2_command_length.py              # 命令阈值 50→99 (0 bytes)
mod3_output_lines.py                # 输出行数 4→99 (+1~+4 bytes)
mod4_diff_lines.py                  # diff 行数 20→99 (0 bytes)
mod5_custom_model_cycle.py          # Ctrl+N 只切换 custom model (0 bytes)
mod6_mission_model.py               # Mission 模型不强切 (0 bytes)
mod7_custom_effort_levels.py        # effort 级别扩展 (+148 bytes)
mod8_disable_builtin_models.py      # 禁用内置模型 (0 bytes)
mod9_disable_auto_update.py         # 禁用自动更新 (0 bytes)
mod10_adaptive_thinking.py          # Opus 4.7 adaptive thinking 多轮保留 (0 bytes)
```

### compensations/ — 字节补偿

```
comp_universal.py           # 通用补偿：从各 mod 死代码区域回收字节
comp_universal.py           # 无参数：显示当前可用补偿空间
comp_universal.py <bytes>   # 缩减指定字节数
```

补偿区域来源（由 mod 短路/替换产生的死代码）:
- 截断函数死代码（mod1 短路后）: ~151B
- mod6 else 分支 + 空格填充: ~69B
- mod5 注释区域: ~36B

### 工具脚本

```
status.py    # 检查当前 mod 应用状态
restore.py   # 恢复指定版本备份
```

## 执行流程

```bash
# 1. 备份（带版本号）
cp ~/.local/bin/droid ~/.local/bin/droid.backup.$(~/.local/bin/droid --version)

# 2. macOS: 移除签名（Linux 跳过）
[[ "$OSTYPE" == "darwin"* ]] && codesign --remove-signature ~/.local/bin/droid

# 3. 执行 mod 脚本
SCRIPT_DIR=~/.claude/skills/droid-bin-mod/scripts
python3 $SCRIPT_DIR/mods/mod1_truncate_condition.py
python3 $SCRIPT_DIR/mods/mod2_command_length.py
python3 $SCRIPT_DIR/mods/mod3_output_lines.py
python3 $SCRIPT_DIR/mods/mod4_diff_lines.py
python3 $SCRIPT_DIR/mods/mod5_custom_model_cycle.py
python3 $SCRIPT_DIR/mods/mod6_mission_model.py
python3 $SCRIPT_DIR/mods/mod7_custom_effort_levels.py
python3 $SCRIPT_DIR/mods/mod8_disable_builtin_models.py
python3 $SCRIPT_DIR/mods/mod9_disable_auto_update.py
python3 $SCRIPT_DIR/mods/mod10_adaptive_thinking.py

# 4. 字节补偿（mod3 + mod7 的实际增量）
python3 $SCRIPT_DIR/compensations/comp_universal.py 152

# 5. macOS: 重新签名
[[ "$OSTYPE" == "darwin"* ]] && codesign -s - ~/.local/bin/droid

# 6. 验证版本正常启动
~/.local/bin/droid --version
```

## 前提条件

- macOS 或 Linux
- Python 3
- droid 二进制位于 `~/.local/bin/droid`
- macOS 需要 codesign 工具；Linux 无需签名

## 恢复原版

macOS 直接 `cp` 恢复会因元数据问题导致 SIGKILL，推荐用 `restore.py`（Linux 也可用）：

```bash
python3 ~/.claude/skills/droid-bin-mod/scripts/restore.py --list    # 查看所有备份
python3 ~/.claude/skills/droid-bin-mod/scripts/restore.py           # 恢复最新
python3 ~/.claude/skills/droid-bin-mod/scripts/restore.py 0.104.0   # 恢复指定版本
```

## 安全说明

- 修改只影响本地 UI 渲染与客户端决策逻辑
- Factory 服务器不校验客户端二进制完整性、不收集二进制哈希/机器指纹
- 仅 API Key 在服务端校验

## 版本升级后脚本失败的排查

升级 droid 后脚本报 "未找到" 的排查步骤：

### 1. 检查特征数字是否仍存在

```bash
strings ~/.local/bin/droid | grep -E "=80,|=3\)|>50|=20,"
```

语义化数字（80 宽度、3 行数、50 命令阈值、20 diff 行数）通常不会变。

### 2. 检查字符串锚点是否仍存在

```bash
strings ~/.local/bin/droid | grep -E "isTruncated|command.length|exec-preview|supportedReasoningEfforts|isCustomModel|async checkForUpdates"
```

### 3. 更新变量名模式

混淆器可能改变量命名风格。修改 `common.py` 中 `V` 正则：

```python
V = rb'[A-Za-z_$][A-Za-z0-9_$]*'
```

### 4. 调整 marker 距离

mod3 等定位依赖 marker 附近距离，混淆重排时可能超出默认 500 字节，脚本里调 `max_dist=1000`。

### 5. mod5-10 专项检查

```bash
# mod5 方法名
strings ~/.local/bin/droid | grep -E "peekNextCycleModel|cycleSpecModeModel|validateModelAccess"
# mod6 mission 白名单上下文
strings ~/.local/bin/droid | grep -E "getReasoningEffort|\.includes\("
# mod7 effort 列表
strings ~/.local/bin/droid | grep -E '\["off","low","medium","high"\]'
# mod8 validateModelAccess 结果
strings ~/.local/bin/droid | grep -c 'isCustomModel:!1};return{allowed:'
# mod9 checkForUpdates patch 检测
strings ~/.local/bin/droid | grep "checkForUpdates(){return null"
# mod10 thinking 剥离分支
strings ~/.local/bin/droid | grep -E "thinking\)\{if\("
```

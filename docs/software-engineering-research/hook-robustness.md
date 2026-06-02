# Hook 健壮性约定

> 来源吸收：`docs/refs-absorption-plan-2026-06-02.md` A10，源 OthmanAdi/planning-with-files（`resolve-plan-dir.sh` 的多解析器链 + fail-open hook）。
> 目标：让本仓库 `scripts/hook_*.py` / `scripts/hooks/` 的健壮性约定成文，新 hook 作者按 hook 类别选对失败语义，不写出会崩 agent loop 的实现。

## 失败语义按 hook 类别分（核心约束）

hook 失败时是放行还是阻断，取决于它的职责。**不要统一用一种**。

| hook 类别 | 代表 | 失败语义 | 理由 |
|---|---|---|---|
| 注入 / 提示类 | `context_capsule.py`、stop 自检提示 | **fail-open** | 注入失败不该挡住用户正常操作；输入解析异常应吞掉返回空注入，不崩 loop |
| 安全 / 校验门 | `boundary_gate.py`、`command_guard.py` | **fail-closed** | 该阻断的动作在 hook 失败时必须仍阻断或显式报错；故障导向安全，不能因异常静默放行 |

判断口诀：**这个 hook 是"提供信息"还是"把关风险"**。提供信息 → fail-open；把关风险 → fail-closed。

## fail-open 写法

- 解析 stdin / JSON 失败时吞掉异常，返回空结果（如本仓库 `load_hook_input` 吞 `JSONDecodeError`），让主流程继续。
- 任何注入类 hook 的顶层都应有兜底，确保异常不冒泡成非零退出打断 agent。

## fail-closed 写法

- 校验/门禁 hook 解析失败时**不要**默认放行；要么阻断该动作，要么以明确错误退出，让上层看到"门禁未生效"而不是误以为通过。
- 校验逻辑里的 `except` 不要静默 `pass`；至少记录并保持阻断态。

## 可移植解析链（跨 OS）

hook/脚本里探测路径、时间、mtime 等不要绑死单一工具（BSD vs GNU `stat`/`date` 行为不同，Alpine 无某些工具）。按可用性回退：

```
stat 变体 → date 变体 → python3 → perl
```

planning-files 的 `resolve-plan-dir.sh` 用这条链兜底，使同一 hook 在 macOS/Linux/Alpine 行为一致。本仓库 hook 以 Python 标准库为主时此问题较小，但任何 shell 探测逻辑都应按此回退，不假设 GNU coreutils。

## 自查清单

- [ ] 明确本 hook 是注入/提示类还是安全/校验门
- [ ] 注入类：解析异常 fail-open，不崩 loop
- [ ] 校验类：解析异常 fail-closed，不静默放行
- [ ] shell 探测路径/时间：按 stat→date→python3→perl 回退，不假设 GNU
- [ ] 没有把 `except` 写成静默 `pass`（错误不静默传递）

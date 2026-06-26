# dev-long-run — worker 感知闭环 + 安全自动干预 (observe / await-all)

Status: spec draft (2026-06-26) · 待审批
Author: 郎振宁 (with assistant)
依赖 / 上游: `overview.md`（L22 await 协议 + anti-抓屏判完成锁；散文见 `overview.md:388/426`、L26 metrics/stuck、non-goal `overview.md:81`）、`parallel.md`（搁置的 `await-all` 草图 `parallel.md:88`）、`scripts/hooks/command_guard.py`（危险/不可逆操作判定器，复用 + 加固）

> 本文是「协调者感知 worker 不够闭环」这一问题的设计 SSOT。范围已与用户在 2026-06-26 对齐（见 §1 / §3 决策表），未经审批不进入实现。

---

## 1. 背景 / 问题

dev-long-run 的协调者 = 用户正在对话的 LLM 本身（`SKILL.md:9`「没有独立 orchestrator pane」），不是后台进程。它对 worker 的感知**只发生在它主动调 `lr.py await` 并阻塞等待的那段时间内**，而 `await` 一次只盯一个 pane（`lr.py:1119-1171`，全系统唯一的轮询循环）。完成信号是 worker 写的 `<role>.status` 文件，**抓屏判完成被明令禁止**（`overview.md:426`：spike 证明抓屏判定假阳+假阴）。

这套设计在三个实战场景下漏掉了 worker 的真实状态（根因经源码核对，见下表）：

| # | 实战失败 | 根因类别 | 今天为什么漏（file:line 证据） |
|---|---|---|---|
| 1 | omzsh 强制更新框吞了下发，worker 根本没启动，协调者傻等 | **下发确认协议缺口** | `launch_role` 贴完 intro 立刻 `_register` 为 `running`（`lr.py:808`），无任何回读确认 agent 起来了；`wait_kilo_ready` 超时也只 WARN 后照发（`lr.py:654`）。更新框画面在变 → `update_idle` 不计 strike → 只能等满 600s TIMEOUT，被误当「卡死」而非「从未启动」。设计层面甚至无法区分「没启动」与「启动了但没写 status」（`overview.md:41`）。 |
| 2 | 网络/模型报错，worker 已经挂了，协调者还在等 | **分类缺口** | `WORKER_STATES=(coding,done,blocked,compact)`（`lr.py:230`）**无 `error` 态**；`_FAIL_LINE_RE`（`lr.py:444`）只用于 verify 输出，**从不扫 pane 屏幕**。pane 没死（非 DEAD）+ 没写 status（非 done）+ 报错在重绘（画面变 → `update_idle` 清零 `lr.py:266`，非 IDLE）→ 烧满 600s。报错 worker 与「慢但正常」worker **结构上不可区分**。 |
| 3 | worker 卡在人工 y/n 确认，协调者看不到 | **分类缺口 + 主动误判** | `IDLE_READY_MARKERS=("? for shortcuts","Ask anything","bypass permissions")`（`lr.py:254`）是**就绪框**标记，不是**确认框**标记。典型 `[y/N]` 不含这些 → 不计 idle → 烧满超时；若确认框恰含 `bypass permissions` 且画面冻结 → 被**误判成 IDLE=「干完忘写 status」**（`lr.py:1154`），实则是 BLOCKED 等输入。无任何自动答（`consume_claude_trust` 只在 launch 时跑一次）。 |

**归一**：#1 是下发协议；#2/#3 是同一个**分类缺口**（没有对活 pane 内容的语义读取）；三者共享一个**节奏缺口**（感知是 per-await、单 pane、按需触发）。
**额外发现**：`cmd_await`——把感知变成可行动信号的唯一代码——**零测试**（`test_lr.py` grep 无 await/TIMEOUT/IDLE/DEAD 引用），最高风险代码无回归网。

---

## 2. 目标 / 非目标

### Goals
- G1 协调者能**主动、低延迟**感知**所有** worker pane 的状态，而不仅是被动等单个 done 信号。
- G2 把 worker 状态分类细化到可行动：`working / ready_idle / awaiting_input / errored / dispatch_blocked / done / blocked / compact / unknown`。
- G3 type(a) 幂等补救（重发被吞 prompt、模型报错有界退避重试、补 status）**回合内自动**。
- G4 type(b) worker 弹出的确认，在**三道安全底座**下**激进自动答**（LLM 判可逆即自动），不可逆/逃逸沙箱的一律上报。
- G5 #1 下发失败用**确定性 post-dispatch 校验**单独、提前修掉（最便宜的独立赢）。
- G6 关闭 `cmd_await` 零测试缺口；新逻辑全部纯函数 + 单测。

### Non-goals（沿用既有设计，刻意不动）
- NG1 **不做后台 daemon / 完全无人值守的全自动闭环**（`overview.md:81`）。"自动" = LLM 调命令后**协议里的确定性分支在回合内处理**，不是常驻进程。
- NG2 **抓屏内容永不用于判定 `done`**（`overview.md:388/426` 红线不动）；完成仍只认 `<role>.status` 文件。
- NG3 **不引入第二个 pane 状态 SSOT**：复用 `SESSIONS.md` 注册表 + `state.json` + `metrics.jsonl`，不新开常驻状态库。
- NG4 不改既有退出码/门禁契约（L22/L23）；新可观测产物只增不改 SSOT、不参与门禁（沿用 L26 边界）。

---

## 3. 已锁定决策（续 overview.md 的 L29 → L30+）

| # | 决策 |
|---|---|
| L30 | **观测命令 `observe` / `await-all`**。`lr.py observe --workspace <ws>`：一次性枚举 `SESSIONS.md` 所有 running pane，对每个 `capture_pane` + 分类，输出结构化 JSON 摘要数组（只读、无循环，LLM 随时可调）。`lr.py await-all --workspace <ws>`：把 `cmd_await` 从单 pane 泛化到 N pane 的有界循环——每拍 observe 全部，**任一 pane 进入可行动态（done/blocked/dead/errored/awaiting_input/dispatch_blocked）或全部 done 或超时即返回**，返回摘要 + 触发 pane。这就是用户要的「定时感知」，但循环在 python 调用内、由 LLM 触发（贴合 NG1）。沿用 L22 纪律：完成判定只认 status token。 |
| L31 | **读屏 carve-out 红线**。允许 `capture_pane` 内容用于**异常检测**（errored / awaiting_input / dispatch_blocked 的分类）；**绝不**用于声明 `done`。spec 与代码注释双处写死此线，防漂移回判完成。分类器对 `done` 永远返回「不判」，done 只能来自 status 文件。 |
| L32 | **type(a) 幂等补救自动**。`dispatch_blocked`（已知 shell 阻塞，如 omzsh 更新框）→ 自动按安全键解除（更新框答 N=拒绝更新，可逆）+ 重发 intro；worker 漏写 status 的 `ready_idle` → 自动 `lr.py send` 重发「写 status」指令再 await 一轮；`errored` 且属可重试类（网络/API 限流）→ **有界退避重试**（最大次数 `MAX_RETRY`，且不在「已做了一半破坏性操作后」盲重试）。这些补救动作本身幂等/可逆。 |
| L33 | **type(b) 自动答 = 白名单极性（正向证明才自动）**。【2026-06-26 红队翻转：原「非 deny 即可自动」的黑名单极性被**实证证伪**——把真 `command_guard` 跑 ~90 条命令，对 `sudo rm -rf /` / 拆分 `rm -r -f /` / `git -C / reset --hard` / `git clean -fd`(warn 非 deny) / `truncate`·`dd`·`dropdb`·`redis FLUSHALL` / 裸 `DROP DATABASE` / ANSI 被截断的抓屏文本，均返回 `None` 或 `warn` 而非 `deny`，**静默放行**。黑名单永远补不全，故翻为白名单。】worker 弹出的确认（`awaiting_input`）→ **默认上报**；**仅当下列全部成立才自动答**：(a) 动作正向落在**只读/沙箱内可恢复白名单**（正向枚举：读文件/`ls`/`cat`/`git status`/`git diff`/worktree 内改文件…，**不是**「不在黑名单」）；(b) `command_guard.classify(action)` 返回 `None`（任何 `warn`/`deny` → 上报）；(c) worktree 容器**已证明**包含（L34，证不出→上报）；(d) prompt 形态在闭集且安全键已知（L39c）；(e) 人未在该 pane（L39b）；(f) LLM 判可逆。任一不成立 / 抽取低置信 / 分类 unknown → **fail-closed 上报**。`classify==None` **不是**「安全」，只是「判定器没话说」——安全由白名单 (a) 给。误判代价不对称（可逆误判=多问一次；危险误判=不可逆损失），故底座是白名单。 |
| L34 | **worktree-aware 容器门（证明包含，否则上报）**。安全边界 = 该 run 的**单个 worktree 目录**（`state.json.worktree_path`，一个 run 一个，planner/coder/reviewer 共享，非每 worker 一个）。`escapes_worktree` **fail-closed**：对动作每个操作数 canonicalize（展开 `~`；遇**未展开 `$VAR` / 命令替换** → 上报；`realpath` 收 `..`、解 symlink），要求**严格是 `realpath(worktree_path)` 的子孙**才算容器内；**无路径操作数 = 无法证明包含 = 上报**（不是默认放行——这是原 §4.4 的 spec 内矛盾，红队 E3）。另检网络/远端/DB 逃逸：`-h/--host`、远端句柄、DB 名、k8s/systemd/cron/registry/deploy 动词 → 逃逸上报（让 redis `-h staging`/`dropdb`/`make deploy` 这类「目标不是路径」也被挡）。**in-place 模式**（worktree=主仓 feature 分支，L16 已拒 main/master）沙箱更弱 → `in_place=True` 作 python 硬入参，该模式下沙箱内的删除/`reset` 也降级上报，只放纯读类。 |
| L35 | **复用并加固 `command_guard.py`**，作可逆判定的一道 gate（**不是**唯一安全来源——白名单 L33a 才是）。重构抽公共 `classify(command: str) -> Decision`（`warn`/`deny`/`None`），hook 与 observe 层共用。**加固（S2，红队 E2 实证现状有洞）**：(i) unwrap `sudo/timeout/nice/nohup/command/time/doas/ionice/stdbuf/setsid` 递归判内层 + 任何提权 → **无条件上报**；(ii) rm flags 跨**前导 option token 取并集**判 r&f（`rm -r -f /` 也中）；(iii) 读子命令前**跳过 git 全局选项**（`-C/-c/--no-pager/--git-dir/--work-tree`），非 cwd 的 `-C/--work-tree` 视为逃逸；(iv) 加**内容型 DDL/DML 扫描**（DROP/TRUNCATE/ALTER/DELETE FROM + 表/库 token，前缀无关）；(v) 补 deny 规则：`truncate/dd/shred/mkfs/wipefs`、`:>`/`>` 覆盖重定向、`dropdb`/`redis FLUSH*`/`crontab -r`/`curl\|sh`。全部加回归测试（S2 现绿 ≠ 已覆盖——实证零覆盖）。 |
| L36 | **审计护栏 + 影子档**。每次自动答/自动补救 append 到 `metrics.jsonl`（既有 append-only 流，已 git-exclude）：`{event:"auto_intervene", pane, role, screen_class, extracted_action, guard_decision, worktree_scope, answer, ts}`。事后可审计、可复盘定位误判。首次启用支持 `--shadow`：只**记录**「本会自动答 X」不真答，跑几轮看命中率再放真自动。 |
| L37 | **关闭 `cmd_await` / 分类器测试缺口**。新分类器、抽取器、决策函数、worktree 逃逸判定全为纯函数 + 单测；补 `cmd_await`/`await-all` 的退出码与 idle 算术的集成测试（构造 pane/status fixture 断言）。 |
| L38 | **#1 下发确认作为独立先行 phase**。`launch_role` send 后做确定性 post-dispatch 校验（capture_pane 确认 agent ready marker 出现 / intro 回显 / status 文件开始写），超时未确认 → `dispatch_blocked`。此为确定性小修，与 L30-L34 的启发式分类层解耦，**先行落地**（cheapest win，不被大改拖延）。 |
| L39 | **自动干预的三道工程约束（红队 E5/E6/E7）**。(a) **预算**：per-pane·per-phase 自动干预预算 `MAX_AUTO_INTERVENE`（总次数）+ 同 `extracted_action` 签名 `MAX_REPEAT`（从 `metrics.jsonl` 读 L36 记录），超限停自动、上报「疑似干预环」——**一串各自可逆的步骤合起来可能不可逆**（`MAX_RETRY` 只管 errored，管不到跨态 ping-pong）。(b) **人在 pane**：按键前查 tmux client 是否 attach / pane 近期有无人工活动，有人在 → 降级上报（overview「用户不进 pane」前提有泄漏：debug/inspect 路径存在）。(c) **闭集 prompt 形态**：自动答仅限二元 `[y/N]`（且 N=拒绝）、omzsh 已知框；数字菜单 / 箭头选择 / 自由文本 / yes-to-all → 一律上报（**证不出哪个键安全**）。 |

---

## 4. 架构细节

### 4.1 状态分类器 `classify_screen(screen, prev_screen, backend, status_state, age_s) -> screen_class`（纯函数）

**两帧最小（红队 E4）**：任何「可行动态」（errored / awaiting_input / dispatch_blocked / ready_idle）都要求**屏幕跨一个 poll 间隔冻结**（`screen == prev_screen`）才成立；画面还在变 = `working`，绝不据单帧动手。`prev_screen` 进签名（原签名漏了，S3 强制）。

优先级（高→低，短路）：
1. `done`/`blocked`/`compact` ← **仅** status 文件（L31：抓屏不参与）。
2. `dispatch_blocked` ← launch 后 `age_s` 内 status 文件从未出现 **且** 屏幕匹配 shell 阻塞模式（per-backend 表：omzsh `Would you like to update`、`Press [Y]`、shell 提示符无 agent ready marker、`command not found`）。
3. `errored` ← 错误模式命中**屏幕尾部 tail** **且帧冻结**（`_FAIL_LINE_RE` 复用到 pane + API/网络标记 `rate limit`/`network error`/`ECONNRESET`/`API error`）。在 tail+冻结锚定，防把 coder 正在分析的日志里的 `Error:`/测试输出里的 `FAILED` 误判为 errored（红队 E4 FP）。
4. `awaiting_input` ← 确认框模式命中**尾部** **且帧冻结** **且** status≠done。再**子分类 prompt 形态**：`binary_yn`（`[y/N]`，N=拒绝）/ `omzsh_update` / `numbered`（`[1] Yes [2] No`）/ `arrow_select` / `free_text` / `yes_to_all`——只有 `binary_yn`+`omzsh_update` 进 L39c 闭集，其余即便可逆也上报（证不出安全键）。
5. `ready_idle` ← **先剥常驻 footer chrome**（`bypass permissions`、`? for shortcuts` 这类页脚）再判 `pane_looks_idle` + 帧冻结；并 gate 在「无任何确认框/数字选项 glyph」之上——否则带 Claude footer 的真 `[y/N]` 会被误判 ready_idle，BLOCKED pane 卡死（这正是 spec 要修的 #3，红队 E4）。
6. `working` ← 画面在变 / spinner / 出 token。
7. `unknown` ← 都不匹配 → **fail-closed**，按需上报。

> per-backend 标记表与 `IDLE_READY_MARKERS` 同构：每个 backend（kilo/claude/droid/codex）一组正则，集中维护、可单测。**维护责任人 = harness-ops**（TUI 变了要更新表）。

### 4.2 决策函数（**白名单极性**；对「我列的不一定全」的回应——定义判定函数而非枚举场景）

```
for pane in observe(workspace):           # L30 枚举所有 running pane
  cls = classify_screen(pane.screen, pane.prev_screen, pane.backend,
                        pane.status_state, pane.age_s)            # 两帧最小 §4.1
  switch cls:
    done|blocked|compact: 按 L22 既有退出码处理
    working|ready_idle:   继续等（ready_idle 超 idle_timeout 才按 type(a) 补 status）
    dispatch_blocked:     # type(a)
        if 屏幕逐字匹配已注册安全 shell 框（omzsh 框 verbatim 白名单, P3）:
            自动按已知安全键 + 重发 intro                       # L32
        else: 上报
    errored:              # type(a)
        if 可重试类 且 retry < MAX_RETRY 且 非破坏性操作中途: 退避重试   # L32
        else: 上报
    awaiting_input:       # type(b) —— 白名单极性, 默认上报
        if intervene_budget_exceeded(pane): 上报「疑似干预环」    # L39a
        if human_attached_or_recent(pane): 上报                  # L39b
        if prompt_shape ∉ {binary_yn, omzsh_update}: 上报         # L39c 闭集
        action, confidence = extract_pending_action(pane.screen) # 不可靠层
        if confidence == low: 上报                               # fail-closed
        # —— 下列全部成立才自动答（正向证明, L33）——
        if  in_readonly_or_sandbox_allowlist(action)             # (a) 正向白名单
        and command_guard.classify(action) is None              # (b) 任何 warn/deny → 上报
        and not escapes_worktree(action, state.worktree_path, state.in_place)  # (c) 证明包含 L34
        and LLM_judges_reversible(action):                      # (f) LLM 兜底
            自动答(安全键); append_metric("auto_intervene", ...)  # L36
        else: 上报                                               # 证不出 → 上报
    unknown:              上报                                    # fail-closed
  if 任一 pane 进入可行动态: append_metric(...) ; await-all 返回
```

> 关键：自动答是**合取门**（全部 ✓ 才动），不是「没踩黑名单就动」。`classify==None` 只是必要条件之一，安全由正向白名单 (a) 担保。

### 4.3 `extract_pending_action(screen) -> (action, confidence)`（**实施前必做 spike，见 §5**）
把确认框屏幕里「正在被请求批准的命令/操作」抽成命令串喂给 `command_guard`。可靠性是 type(b) 承重风险——**不假装解决**，靠 fail-closed 兜。

**`confidence == high` 的具体定义（红队 E8：不定义则 fail-closed 不可执行）**：① 命令落在屏幕**单一锚定区域**（一个 tool-approval 框内），非跨多行拼接；② `split_tokens(action)` 能 round-trip（非空、无 shlex ValueError）；③ 无截断标记 / 无残留 ANSI / 无替换字符 `�`；④ 是**单条命令**非多步链（含 `&&`/`;`/`|` 多动词 → 降 `low`）；⑤ 确认框只请求**一个**动作（多动作框 → `low`）。任一不满足 = `low` → 上报。
- 抽取器**自评 confidence**，P5 不得把它 stub 成 `high`/`True`（测试断言）。
- 注意：很多 TUI 确认框展示的是**自然语言摘要/计划**而非字面命令——这类 `split_tokens` 出来不是 argv → `low` → 上报（红队 E_extract）。喂自然语言给为 argv 设计的 `command_guard` 会产生垃圾 None，故必须先过 confidence 闸。

### 4.4 worktree 容器门 `escapes_worktree(action, worktree_path, in_place) -> bool`（**fail-closed：证明包含否则算逃逸**）
复用 `command_guard` 的 remote-ref / wide-path / push-target，但**判定基准翻转**（红队 E3：原版只在「检测到」逃逸时上报、无路径操作数时默认放行 = spec 内矛盾）：
- 对每个操作数 canonicalize：展开 `~`；遇**未展开 `$VAR` / 命令替换 / glob 通配** → **算逃逸**（证不出）；`realpath` 收 `..`、解 symlink；要求**严格是 `realpath(worktree_path)` 的子孙**。
- **无任何路径操作数 = 无法证明包含 = 算逃逸**（`reset --hard`/`dropdb`/`make deploy` 无路径参数 → 上报）。
- 网络/远端/DB 句柄逃逸：`-h/--host`、远端 ref、DB 名、k8s/systemd/cron/registry/deploy 动词 → 逃逸。
- **in-place 模式**（worktree = 主仓 feature 分支，`state.json.in_place=True` 硬入参）：沙箱弱 → 沙箱内的删除/`reset`/写 也算逃逸，**只放纯读类**。`in_place` 进 python 决策函数硬入参 + 参数化测试（红队 E8，原 spec 此条仅散文）。

### 4.5 协议变更（`prompts/loop_orchestrator.md`）
- 把「检测 worker 完成一律用 `lr.py await --pane`」升级为「用 `lr.py await-all` 同时盯所有在跑 worker；返回的 `screen_class` 按决策表分支」。
- 新增 type(a)/type(b) 处理 playbook（对应 §4.2），明确「自动 vs 上报」边界与 fail-closed 默认。
- 保留 L22 红线措辞：完成只认 status，不抓屏判 done。

---

## 5. 实施前必做 spike（承重前提，未 spike 不进实现）

| Spike | 验证什么 | 失败的后果 |
|---|---|---|
| S1 跨 backend 确认框 fixture | 采集 kilo/claude/droid/codex 真实的「确认框 / 报错屏 / shell 阻塞框」截屏；确认 §4.1 per-backend 正则稳定分类、`extract_pending_action` 能抽出命令串；**并把 §4.3 `confidence==high` 五条作为出口标准固化**（含「confident-wrong」对抗样本：多动作框、危险 token 不在首行、行被 wrap）；混入**自然语言摘要框**确认其落 `low`→上报 | 抽取不可靠 → type(b) 退化为「全上报」（仍安全，但 G4 激进自动答落空，需告知用户预期降级） |
| S2 `command_guard.classify` **重构 + 加固** | 抽公共入口不破坏现有 hook（`test_*command_guard*` 全绿）；**并完成 L35(i)-(v) 加固**（unwrap wrapper、rm 跨 token flags、git 全局选项、DDL/DML 内容扫描、补 truncate/dd/dropdb/FLUSHALL/crontab/重定向），对红队 ~90 条样本断言正确 deny；提权一律上报 | 破坏既有命令护栏（线上每次 Bash 都过它）→ 高 blast radius；加固漏项 → 白名单极性下仍安全（None≠放行），但会过度上报 |
| S3 `await-all` 退出/聚合语义 | 多 pane 同时到达不同态时的返回优先级、超时聚合；**强制 `prev_screen` 入分类签名（两帧最小）**；**与 `parallel.md:88` 搁置草图的退出码契约不冲突**（命名归属：`observe-await` / `--mode any\|all`，红队 P3） | 竞态/漏报某 pane；命名撞车 |

已 spike 成事实（本 spec 前置）：worker 跑在 run 级隔离 worktree（`lr.py:90/985`，`--new`）或 in-place 当前 worktree（`lr.py:105`）；`command_guard` 是可复用纯函数判定器（`command_guard.py:240-423`）。

---

## 6. Boundary facts

- Risk types: operational-side-effect（自动答 worker 确认 / 自动按键 = 对 pane 的副作用，可能触发不可逆动作）、context-surface（改 `loop_orchestrator.md` = 进 model context）、shared-path（`command_guard` 重构影响线上每次 Bash 的命令护栏 hook）、observability-routing（新增 `metrics.jsonl` 事件类型）
- Callers: `command_guard.classify` 新增被 observe 层 + 既有 `command_guard` hook 调用；`await-all` 被 loop orchestrator 调用
- Contract cases: **自动答 = 合取门全 ✓ 才动**（accept-自动：读文件/`ls`/`git status`/worktree 内改 + `classify==None` + 容器已证 + `binary_yn` + 人不在 pane + LLM 可逆；reject-必上报：任何 `warn`/`deny`、`sudo`/提权、拆分 flag、git 全局选项越权、无路径操作数、未展开 `$VAR`、自然语言摘要框、数字菜单/自由文本、预算超限、人在 pane）；**must-escalate 类硬 bar = 0 误自动答**（§7）
- Data source: pane 屏幕 capture（仅异常检测，L31）、`state.json`、`SESSIONS.md`、`<role>.status`
- Metric route: `metrics.jsonl` 新增 `event:"auto_intervene"`（append-only，不参与门禁，沿用 L26 边界）
- Schema contract: `observe` 输出 JSON 数组 `{pane, role, screen_class, status_state, alive, evidence_tail}`；`await-all` 退出码沿用 L22 + 聚合语义（S3 定）
- User approval: 2026-06-26 对齐——执行主体=强化 LLM 协调者无 daemon；读屏 carve-out=仅异常检测；type(a)=自动；type(b) 初选「激进自动答 + 完整 deny 底座 + worktree 感知」→ **红队实证 deny 黑名单静默放行后，用户同日改选「翻转为白名单极性（证不出就上报）」**（引述见 §3 L30-L39）

Boundary decisions（spec 内做出的、需复述的边界变化）:
- read-screen carve-out: 放开抓屏用于异常检测，但红线禁用于判 done（L31，evidence: 用户批准 carve-out + 保留 anti-抓屏判完成）
- auto-intervention 极性: type(b) 自动答 = **白名单合取门**（正向证明才动），非「非 deny 即自动」（L33，evidence: 红队 E1/E2 实证黑名单底座漏 sudo/warn-tier/无规则类 + 用户 2026-06-26 改选白名单）
- command_guard 加固: 扩 deny 判定（unwrap/flags/DDL/补类），影响线上每次 Bash 的命令护栏 hook（L35，evidence: 红队 E2 + S2 等价性测试守护）

---

## 7. 风险 / 验证 / 回退

### 风险
- R1（最高）**危险动作被误自动答**：原缓解「deny 底座是确定性兜底（只需认出危险 token）」**已被红队证伪**（guard 对 sudo/拆分 flag/无规则类/裸 SQL 返回 None/warn）。新缓解 = **白名单极性**（正向证明才动，L33）+ guard 加固（L35）+ fail-closed 抽取（§4.3）+ 影子档先验。安全不再压在「认出危险」，而压在「证明安全 + 证不出就上报」。
- R2 **误杀慢但正常的 pane**：长 build/大测试画面静止像卡死。缓解 = type(a) 默认只「上报」不「重启」（重启不在自动白名单）；errored 仅对可重试类、有界次数；两帧最小 + 冻结锚定（§4.1）防把变动画面判 errored。
- R3 **per-backend 正则随 TUI 演化失效**：缓解 = 集中表 + 单测 + harness-ops 维护责任；失配 → unknown → 上报（fail-closed，不会误自动）。
- R4 **`command_guard` 重构/加固回归**：缓解 = S2 先跑既有测试全绿、再以红队 ~90 样本断言加固正确，才改调用方。
- R5 **干预环（各自可逆，合起来不可逆）**：缓解 = L39a 预算 + metrics 签名去重。

### 验证（**安全系统必须测它要拒的输入，不只 happy path** —— 红队 E_verify）
- 单测：分类器各 `screen_class`（含 FP/FN 对抗样本、两帧冻结）、决策函数各分支、`escapes_worktree`（含 `in_place` 参数化、未展开 `$VAR`、symlink、无路径操作数）、`extract` confidence 五条、`command_guard.classify` 等价性 + 加固样本。
- **负向/拒绝测试（硬 bar）**：跨所有 backend，凡 `command_guard` `deny`/`warn`、提权、逃逸、非闭集 prompt 形态、low-confidence → **断言绝不自动答**。注入合成危险确认框（`sudo rm -rf /`、`git -C / reset --hard`、`DROP DATABASE`…）使 must-escalate 分母非平凡。
- 集成：构造 pane/status fixture 跑 `await-all` 断言退出码 + 触发 pane（关闭 L37 缺口）。
- 影子档实跑：真实 run `--shadow` 跑若干轮，对**有标注 ground-truth 集**测两个分离指标——(1) **must-escalate 类误自动答率，硬 bar = 0**（任何一例即阻断上线）；(2) 过度上报率（soft，可调）。达 (1) 才开真自动。
- acceptance：三个原始失败模式各造可复现场景（含 #3 的**危险变体**：一个必须被上报的破坏性确认框）+ 验证 <设定延迟 内感知并正确分流（自动 vs 上报）。

### 回退
- `observe`/`await-all` 是新增命令，不改既有 `await`；协议可一键切回「只用单 pane `await`」。
- type(b) 自动答可整体关（`--shadow` 或 config flag），退化为「快速上报」仍解 #3「看不到」痛点。
- `command_guard` 重构若回归，revert 调用方、保留 hook 原样。

---

## 8. Phasing（实现顺序，未审批不启动）

- **P0** S1/S2/S3 spike → 事实化承重前提。
- **P1（独立先行，L38）** `launch_role` post-dispatch 确定性校验 + `dispatch_blocked` 检测 + omzsh 更新框已知模式自动解除。修掉 #1，最便宜、确定性、不依赖启发式分类。
- **P2** `observe` 命令 + `classify_screen` 分类器 + per-backend 表 + 单测。修掉 #2/#3 的「感知/分类」缺口（先只上报，不自动答）。
- **P3** `await-all` 泛化 + 协议接入 `loop_orchestrator.md` + 关闭 `cmd_await` 测试缺口（L37）。
- **P4** type(a) 幂等自动补救（重发/退避重试/补 status）。
- **P5a** `command_guard.classify` 重构 + **加固 L35(i)-(v)**，behind S2 等价性 + 红队 ~90 样本断言。仅扩 guard，不接自动答。
- **P5b** `extract_pending_action`（含 §4.3 confidence 五条）+ 白名单 L33(a) + 容器门 L34 + 闭集形态 L39c + 预算 L39a + 人在 pane L39b 全部接好，**SHADOW-ONLY**（只记不答），与 type(a) 同跑 soak。
- **P5c** 翻真自动，**gated 在「must-escalate 类误自动答率 = 0」硬 bar**（§7，任何一例阻断）。
> 红队 E8：原 P5 把最险代码放最后一次性上，拆成 a/b/c 让加固先落、shadow 先泡、硬 bar 守住翻真自动。

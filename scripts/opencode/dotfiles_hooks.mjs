import { spawnSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const COMMAND_GUARD = resolve(REPO_ROOT, "scripts", "hooks", "command_guard.py");
const STOP_CHECK = resolve(REPO_ROOT, "scripts", "hooks", "stop_check.py");
const CONTEXT_CAPSULE = resolve(REPO_ROOT, "scripts", "hooks", "context_capsule.py");
const MEMORY_CAPTURE = resolve(REPO_ROOT, "scripts", "hooks", "memory_capture.py");
// 与 scripts/hooks/memory_flags.py 的 ENABLED_VALUES 保持一致。
const MEMORY_ENABLED_VALUES = new Set(["1", "true", "yes", "on"]);
const CAPSULE_MARKER = "<!-- dotfiles-context-capsule -->";
const MEMORY_MARKER_OPEN = "<dotfiles-memory>";
const MEMORY_MARKER_CLOSE = "</dotfiles-memory>";
const NOTIFY_TMUX_TITLE = resolve(REPO_ROOT, "scripts", "notify-tmux-title.sh");
const IDLE_NOTICE_DEBOUNCE_MS = 2000;
const COMPLETION_TITLE = "OpenCode task complete";
const COMPLETION_MESSAGE = "OpenCode task complete.";
const idleNotices = new Map();

function runPythonHook(script, input, cwd, args = []) {
  const options = {
    input: JSON.stringify(input),
    encoding: "utf8",
  };
  options.env = { ...process.env };
  if (cwd) {
    options.cwd = cwd;
    options.env.FACTORY_PROJECT_DIR = cwd;
  }
  const result = spawnSync("python3", [script, ...args], options);
  // hookError 标记运行时失败(spawn/非0/坏 JSON), 供 command guard 走 fail-closed;
  // 注入类调用方(capsule/memory/stop)只读 systemMessage/additionalContext, 忽略它, 仍 fail-open。
  if (result.error) {
    return { systemMessage: `${script} failed: ${result.error.message}`, hookError: true };
  }
  if (result.status !== 0) {
    return { systemMessage: `${script} exited with ${result.status}: ${result.stderr.trim()}`, hookError: true };
  }
  try {
    return JSON.parse(result.stdout || "{}");
  } catch {
    return { systemMessage: `${script} returned invalid JSON: ${result.stdout.trim()}`, hookError: true };
  }
}

function runCommandGuard(command) {
  return runPythonHook(COMMAND_GUARD, { tool_input: { command } });
}

// 把 context_capsule.py 匹配到的 capsule 文本注入到用户消息里。
// 注意: 不能往 output.parts push 新 part —— runtime 要求 part 带完整 schema
// (id/messageID/sessionID), 缺字段会让 session 崩(已实测 UnknownError)。
// 改为追加到既有 user text part 的 text 字段, 不动 part 结构; 标记防重复注入。
// 这是 kilo/opencode 侧 capsule 注入的等价物(Claude/Droid/Codex 走 UserPromptSubmit hook)。
function injectContextCapsules(output) {
  try {
    const parts = output?.parts;
    if (!Array.isArray(parts)) {
      return;
    }
    const textPart = parts.find(
      (part) => part && part.type === "text" && typeof part.text === "string" && part.text.trim(),
    );
    if (!textPart) {
      return;
    }
    const needsCapsuleSegment = !textPart.text.includes(CAPSULE_MARKER);
    const needsMemorySegment = !hasCompleteMemorySegment(textPart.text);
    if (!needsCapsuleSegment && !needsMemorySegment) {
      return;
    }
    const decision = runPythonHook(CONTEXT_CAPSULE, { prompt: textPart.text.trim() }, undefined, ["--event", "prompt"]);
    const context = decision?.hookSpecificOutput?.additionalContext;
    if (typeof context === "string" && context.trim()) {
      const segments = selectMissingContextSegments(context, needsCapsuleSegment, needsMemorySegment);
      if (segments.length > 0) {
        textPart.text = `${textPart.text}\n\n${segments.join("\n\n")}`;
      }
    }
  } catch (error) {
    // hook 铁律: 注入失败绝不能崩主流程, fail-open。
    if (process.env.DOTFILES_CAPSULE_LOG) {
      appendFileSync(process.env.DOTFILES_CAPSULE_LOG, `inject error: ${error?.stack || error}\n`, "utf8");
    }
  }
}

function selectMissingContextSegments(context, needsCapsuleSegment, needsMemorySegment) {
  const memorySegment = extractMemorySegment(context);
  const capsuleSegment = removeMemorySegment(context).trim();
  const segments = [];
  if (needsCapsuleSegment && capsuleSegment) {
    segments.push(`${CAPSULE_MARKER}\n${capsuleSegment}`);
  }
  if (needsMemorySegment && memorySegment) {
    segments.push(memorySegment);
  }
  return segments;
}

function extractMemorySegment(context) {
  const start = context.indexOf(MEMORY_MARKER_OPEN);
  const end = context.indexOf(MEMORY_MARKER_CLOSE);
  if (start === -1 || end === -1 || end < start) {
    return "";
  }
  return context.slice(start, end + MEMORY_MARKER_CLOSE.length).trim();
}

function hasCompleteMemorySegment(text) {
  const start = text.indexOf(MEMORY_MARKER_OPEN);
  const end = text.indexOf(MEMORY_MARKER_CLOSE);
  return start !== -1 && end !== -1 && end > start;
}

function removeMemorySegment(context) {
  const start = context.indexOf(MEMORY_MARKER_OPEN);
  const end = context.indexOf(MEMORY_MARKER_CLOSE);
  if (start === -1 || end === -1 || end < start) {
    return context;
  }
  return `${context.slice(0, start)}${context.slice(end + MEMORY_MARKER_CLOSE.length)}`;
}

function isShellLikeName(value) {
  const name = String(value || "").toLowerCase();
  return ["bash", "shell", "execute", "terminal", "command"].some((part) => name.includes(part));
}

function firstString(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function maybeCommandFromToolHook(input, output) {
  if (!isShellLikeName(input?.tool)) {
    return "";
  }
  const args = output?.args || input?.args || {};
  return firstString(args.command, args.cmd, args.script, input?.command);
}

function maybeCommandFromPermission(input) {
  const metadata = input?.metadata || {};
  const command = firstString(metadata.command, metadata.cmd, metadata.script);
  if (command) {
    return command;
  }
  if (!isShellLikeName(input?.type) && !isShellLikeName(input?.title)) {
    return "";
  }
  if (typeof input?.pattern === "string") {
    return input.pattern.trim();
  }
  return firstString(input?.title);
}

function applyCommandGuard(command, output) {
  const decision = runCommandGuard(command);
  // Guard OUTAGE (it could not RUN — python3 missing / crash / bad JSON): fail OPEN.
  // command_guard 是 advisory / defense-in-depth(见 command_guard.py 顶注),不是硬边界;
  // 它自己挂掉时不该把 agent 整个锁死(那比它防的风险更糟,且 agent 无法跑命令去自救)。
  // 但要 LOUD 告警,让"护栏当前形同关闭"被立刻看见并修复。注入类 hook 也是这套 fail-open 哲学。
  if (decision.hookError) {
    const warn = `⚠️ command guard 未能运行(${decision.systemMessage || "unknown error"})——本条命令未经检查即放行。命令护栏当前形同关闭，请尽快修复。`;
    try { process.stderr.write(warn + "\n"); } catch {}
    appendGuardReason(output, warn);
    return;
  }
  const hookOutput = decision.hookSpecificOutput || {};
  // Guard RAN and decided DENY: a real detection — fail CLOSED (block).
  if (hookOutput.permissionDecision === "deny") {
    const reason = hookOutput.permissionDecisionReason || "Command denied by dotfiles command guard.";
    appendGuardReason(output, reason);
    throw new Error(reason);
  }
  if (decision.systemMessage) {
    appendGuardReason(output, decision.systemMessage);
  }
}

function applyPermissionGuard(command, output) {
  const decision = runCommandGuard(command);
  // Guard outage: fail OPEN (don't block the permission flow), but warn loudly.
  if (decision.hookError) {
    try { process.stderr.write(`⚠️ command guard 未能运行；本次 permission 未经检查即放行。\n`); } catch {}
    return;
  }
  // Guard ran and said deny: block.
  if (decision.hookSpecificOutput?.permissionDecision === "deny") {
    output.status = "deny";
  }
}

function runStopCheck(directory) {
  return runPythonHook(STOP_CHECK, {}, directory);
}

function isMemoryEnabled() {
  return MEMORY_ENABLED_VALUES.has(String(process.env.DOTFILES_MEMORY_ENABLED || "").trim().toLowerCase());
}

// session.idle 时把本轮 kilo/opencode 会话喂给 memory_capture(SQLite 读取 → raw 候选)。
// hook 铁律: flag 门控(默认关=dormant)、fail-open(绝不崩主流程)、非阻塞语义
// (失败只吞掉, 不抛)。kilo/opencode 共用本 .mjs 分不清平台, 故传 sessionID 让
// python 侧按 session 在两库里自动定位(capture_sqlite_for_session)。
function runMemoryCapture(workspace, sessionID) {
  if (!isMemoryEnabled() || !sessionID) {
    return;
  }
  try {
    runPythonHook(MEMORY_CAPTURE, {}, workspace, ["--root", workspace, "--sqlite-session", sessionID]);
  } catch (error) {
    if (process.env.DOTFILES_MEMORY_CAPTURE_LOG) {
      appendFileSync(process.env.DOTFILES_MEMORY_CAPTURE_LOG, `capture error: ${error?.stack || error}\n`, "utf8");
    }
  }
}

// 把 guard 的拒绝/告警理由附到既有 text part 上 —— 不 push 无完整 schema 的新 part
// (runtime 会 UnknownError，见 injectContextCapsules 注释)。无可附着的 text part 时不强行加，
// 拦截结果由抛出的 Error / output.status 承载。
function appendGuardReason(output, text) {
  const parts = output?.parts;
  if (!Array.isArray(parts)) {
    return;
  }
  const textPart = parts.find(
    (part) => part && part.type === "text" && typeof part.text === "string",
  );
  if (textPart) {
    textPart.text = textPart.text ? `${textPart.text}\n\n${text}` : text;
  }
}

function idleSessionID(event) {
  return event?.properties?.sessionID || "";
}

function isIdleEvent(event) {
  if (event?.type === "session.idle") {
    return true;
  }
  return event?.type === "session.status" && event?.properties?.status?.type === "idle";
}

function shouldNotifyIdle(sessionID, message) {
  const key = `${sessionID}:${message}`;
  const now = Date.now();
  const last = idleNotices.get(key) || 0;
  if (now - last < IDLE_NOTICE_DEBOUNCE_MS) {
    return false;
  }
  idleNotices.set(key, now);
  return true;
}

function notifyWithPaneName({ title, message, variant }) {
  const event = variant === "success" ? "stop" : "notification";
  const result = spawnSync("bash", [NOTIFY_TMUX_TITLE, "--app", "opencode", "--event", event], {
    encoding: "utf8",
    env: process.env,
  });
  if (process.env.DOTFILES_OPENCODE_NOTIFY_LOG) {
    appendFileSync(
      process.env.DOTFILES_OPENCODE_NOTIFY_LOG,
      `${JSON.stringify({ title, message, variant, event, stdout: result.stdout.trim(), stderr: result.stderr.trim(), status: result.status })}\n`,
      "utf8",
    );
  }
}

async function showIdleNotification(client, directory, notification) {
  notifyWithPaneName(notification);
  await client?.tui?.showToast?.({
    query: { directory },
    body: {
      title: notification.title,
      message: notification.message,
      variant: notification.variant,
      duration: 10000,
    },
  });
}

async function notifyForCompletion(client, workspace, sessionID) {
  const result = runStopCheck(workspace);
  const notification = result.systemMessage
    ? { title: "Dotfiles stop check", message: result.systemMessage, variant: "warning" }
    : { title: COMPLETION_TITLE, message: COMPLETION_MESSAGE, variant: "success" };
  if (!shouldNotifyIdle(sessionID, notification.message)) {
    return;
  }
  await showIdleNotification(client, workspace, notification);
}

export const DotfilesHooksPlugin = async ({ client, directory } = {}) => {
  const workspace = directory || process.cwd();
  return {
    event: async ({ event }) => {
      if (!isIdleEvent(event)) {
        return;
      }
      const sessionID = idleSessionID(event);
      await notifyForCompletion(client, workspace, sessionID);
      runMemoryCapture(workspace, sessionID);
    },
    // NOTE: 完成播报只绑 `session.idle`/`session.status{idle}`(每轮结束一次)。
    // 不要重新挂 `experimental.text.complete` —— 它按 partID 每段文本输出 fire 一次,
    // 在 kilo(一轮多段输出)下会变成"每次输出都 say"(2s/5s 去重窗口拦不住跨段间隔)。
    // 收到新用户消息时按 prompt 注入匹配的 context capsule(scope/planning/debug/...)。
    "chat.message": async (_input, output) => {
      injectContextCapsules(output);
    },
    "command.execute.before": async (input, output) => {
      const command = [input.command, input.arguments].filter(Boolean).join(" ").trim();
      applyCommandGuard(command, output);
    },
    "tool.execute.before": async (input, output) => {
      const command = maybeCommandFromToolHook(input, output);
      if (command) {
        applyCommandGuard(command, output);
      }
    },
    "permission.ask": async (input, output) => {
      const command = maybeCommandFromPermission(input);
      if (command) {
        applyPermissionGuard(command, output);
      }
    },
  };
};

export const server = DotfilesHooksPlugin;
export default DotfilesHooksPlugin;

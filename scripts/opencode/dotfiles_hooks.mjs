import { spawnSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const COMMAND_GUARD = resolve(REPO_ROOT, "scripts", "hooks", "command_guard.py");
const STOP_CHECK = resolve(REPO_ROOT, "scripts", "hooks", "stop_check.py");
const NOTIFY_TMUX_TITLE = resolve(REPO_ROOT, "scripts", "notify-tmux-title.sh");
const IDLE_NOTICE_DEBOUNCE_MS = 2000;
const COMPLETION_TITLE = "OpenCode task complete";
const COMPLETION_MESSAGE = "OpenCode task complete.";
const idleNotices = new Map();

function runPythonHook(script, input, cwd) {
  const options = {
    input: JSON.stringify(input),
    encoding: "utf8",
  };
  if (cwd) {
    options.cwd = cwd;
    options.env = { ...process.env, FACTORY_PROJECT_DIR: cwd };
  }
  const result = spawnSync("python3", [script], options);
  if (result.error) {
    return { systemMessage: `${script} failed: ${result.error.message}` };
  }
  if (result.status !== 0) {
    return { systemMessage: `${script} exited with ${result.status}: ${result.stderr.trim()}` };
  }
  try {
    return JSON.parse(result.stdout || "{}");
  } catch {
    return { systemMessage: `${script} returned invalid JSON: ${result.stdout.trim()}` };
  }
}

function runCommandGuard(command) {
  return runPythonHook(COMMAND_GUARD, { tool_input: { command } });
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
  const hookOutput = decision.hookSpecificOutput || {};
  if (hookOutput.permissionDecision === "deny") {
    const reason = hookOutput.permissionDecisionReason || "Command denied by dotfiles command guard.";
    appendTextPart(output, reason);
    throw new Error(reason);
  }
  if (decision.systemMessage) {
    appendTextPart(output, decision.systemMessage);
  }
}

function applyPermissionGuard(command, output) {
  const decision = runCommandGuard(command);
  const hookOutput = decision.hookSpecificOutput || {};
  if (hookOutput.permissionDecision === "deny") {
    output.status = "deny";
  }
}

function runStopCheck(directory) {
  return runPythonHook(STOP_CHECK, {}, directory);
}

function appendTextPart(output, text) {
  if (!Array.isArray(output.parts)) {
    output.parts = [];
  }
  output.parts.push({ type: "text", text, synthetic: true });
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
      await notifyForCompletion(client, workspace, idleSessionID(event));
    },
    // NOTE: 完成播报只绑 `session.idle`/`session.status{idle}`(每轮结束一次)。
    // 不要重新挂 `experimental.text.complete` —— 它按 partID 每段文本输出 fire 一次,
    // 在 kilo(一轮多段输出)下会变成"每次输出都 say"(2s/5s 去重窗口拦不住跨段间隔)。
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

import { spawnSync } from "node:child_process";
import { appendFileSync } from "node:fs";

const COMMAND_GUARD = "/Users/zhenninglang/.dotfiles/scripts/hooks/command_guard.py";
const STOP_CHECK = "/Users/zhenninglang/.dotfiles/scripts/hooks/stop_check.py";
const NOTIFY_TMUX_TITLE = "/Users/zhenninglang/.dotfiles/scripts/notify-tmux-title.sh";
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
    "experimental.text.complete": async (input) => {
      await notifyForCompletion(client, workspace, input?.sessionID || "");
    },
    "command.execute.before": async (input, output) => {
      const command = [input.command, input.arguments].filter(Boolean).join(" ").trim();
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
    },
  };
};

export const server = DotfilesHooksPlugin;
export default DotfilesHooksPlugin;

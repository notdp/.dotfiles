import { spawnSync } from "node:child_process";

const COMMAND_GUARD = "/Users/zhenninglang/.dotfiles/scripts/hooks/command_guard.py";

function runCommandGuard(command) {
  const result = spawnSync("python3", [COMMAND_GUARD], {
    input: JSON.stringify({ tool_input: { command } }),
    encoding: "utf8",
  });
  if (result.error) {
    return { systemMessage: `Command guard failed: ${result.error.message}` };
  }
  if (result.status !== 0) {
    return { systemMessage: `Command guard exited with ${result.status}: ${result.stderr.trim()}` };
  }
  try {
    return JSON.parse(result.stdout || "{}");
  } catch {
    return { systemMessage: `Command guard returned invalid JSON: ${result.stdout.trim()}` };
  }
}

function appendTextPart(output, text) {
  if (!Array.isArray(output.parts)) {
    output.parts = [];
  }
  output.parts.push({ type: "text", text, synthetic: true });
}

export const DotfilesHooksPlugin = async () => ({
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
});

export const server = DotfilesHooksPlugin;
export default DotfilesHooksPlugin;

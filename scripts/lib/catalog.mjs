export const UNIVERSAL_AGENTS = [
  'Amp', 'Codex', 'Gemini CLI', 'GitHub Copilot', 'Kimi Code CLI', 'OpenCode',
];

export const UNIVERSAL = {
  commands: '~/.agents/commands',
};

export const AGENTS = [
  { name: 'AdaL',         commands: '~/.adal/commands' },
  { name: 'Antigravity',  commands: '~/.agent/commands' },
  { name: 'Augment',      commands: '~/.augment/commands' },
  { name: 'Claude Code',  commands: '~/.claude/commands',                  instructions: '~/.claude/CLAUDE.md' },
  { name: 'Cline',        commands: '~/.cline/commands' },
  { name: 'CodeBuddy',    commands: '~/.codebuddy/commands' },
  { name: 'Codex',        commands: '~/.codex/prompts',                    instructions: '~/.codex/AGENTS.md' },
  { name: 'Command Code', commands: '~/.commandcode/commands' },
  { name: 'Continue',     commands: '~/.continue/commands' },
  { name: 'Crush',        commands: '~/.crush/commands' },
  { name: 'Cursor',       commands: '~/.cursor/commands' },
  { name: 'Droid',        commands: '~/.factory/commands',                 instructions: '~/.factory/AGENTS.md' },
  { name: 'Gemini CLI',   commands: '~/.gemini/antigravity/global_workflows' },
  { name: 'Goose',        commands: '~/.goose/commands' },
  { name: 'iFlow CLI',    commands: '~/.iflow/commands' },
  { name: 'Junie',        commands: '~/.junie/commands' },
  { name: 'Kilo Code',    commands: '~/.kilocode/commands' },
  { name: 'Kiro CLI',     commands: '~/.kiro/commands' },
  { name: 'Kode',         commands: '~/.kode/commands' },
  { name: 'MCPJam',       commands: '~/.mcpjam/commands' },
  { name: 'Mistral Vibe', commands: '~/.vibe/commands' },
  { name: 'Mux',          commands: '~/.mux/commands' },
  { name: 'Neovate',      commands: '~/.neovate/commands' },
  { name: 'OpenClaw',     commands: '~/commands' },
  { name: 'OpenHands',    commands: '~/.openhands/commands' },
  { name: 'Pi',           commands: '~/.pi/commands' },
  { name: 'Pochi',        commands: '~/.pochi/commands' },
  { name: 'Qoder',        commands: '~/.qoder/commands' },
  { name: 'Qwen Code',    commands: '~/.qwen/commands' },
  { name: 'Roo Code',     commands: '~/.roo/commands' },
  { name: 'Trae',         commands: '~/.trae/commands' },
  { name: 'Windsurf',     commands: '~/.windsurf/commands' },
  { name: 'Zencoder',     commands: '~/.zencoder/commands' },
];

export function allCommandPaths() {
  return [UNIVERSAL.commands, ...AGENTS.map(a => a.commands)];
}

export function allAgentPaths() {
  return AGENTS.filter(a => a.instructions).map(a => a.instructions);
}

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// Infer the dotfiles dir from whatever is already linked. Votes on link
// *targets*, not the agent-side paths: a commands link always points at
// <dotfiles>/commands and an instructions link at <dotfiles>/agents/AGENTS.md,
// regardless of what the agent calls its own directory (prompts,
// global_workflows, ...).
export function detectDotfilesDir() {
  const HOME = os.homedir();
  const expand = (s) => (s === '~' ? HOME : s.startsWith('~/') ? path.join(HOME, s.slice(2)) : s);
  const votes = {};

  const tally = (paths, strip) => {
    for (const p of paths) {
      try {
        const full = expand(p);
        if (!fs.lstatSync(full).isSymbolicLink()) continue;
        const target = fs.readlinkSync(full);
        if (!strip.test(target)) continue;
        const dir = target.replace(strip, '');
        votes[dir] = (votes[dir] || 0) + 1;
      } catch {}
    }
  };

  tally(allCommandPaths(), /\/commands$/);
  tally(allAgentPaths(), /\/agents\/AGENTS\.md$/);

  let best = null;
  let max = 0;
  for (const [dir, count] of Object.entries(votes)) {
    if (count > max) { best = dir; max = count; }
  }
  return best;
}

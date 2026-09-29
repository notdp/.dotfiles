#!/usr/bin/env node

import { intro, outro, confirm, spinner, note, log } from '@clack/prompts';
import { allCommandPaths, allAgentPaths, detectDotfilesDir } from './lib/catalog.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const HOME = os.homedir();
const expand = (s) => (s === '~' ? HOME : s.startsWith('~/') ? path.join(HOME, s.slice(2)) : s);
const shorten = (s) => s.replace(HOME, '~');

const DOTFILES_DIR = detectDotfilesDir() || expand('~/.dotfiles');
const COMMANDS_DIR = path.join(DOTFILES_DIR, 'commands');
const AGENTS_FILE = path.join(DOTFILES_DIR, 'agents', 'AGENTS.md');

function findLatestBackup(fullPath) {
  const dir = path.dirname(fullPath);
  const base = path.basename(fullPath);
  try {
    const entries = fs.readdirSync(dir)
      .filter(e => e.startsWith(`${base}.bak-`))
      .map(e => ({ name: e, stat: fs.statSync(path.join(dir, e)) }))
      .sort((a, b) => b.stat.mtimeMs - a.stat.mtimeMs);
    return entries.length ? path.join(dir, entries[0].name) : null;
  } catch { return null; }
}

function removeLink(rawPath, expectedTarget) {
  const full = expand(rawPath);
  try {
    const stat = fs.lstatSync(full);
    if (stat.isSymbolicLink()) {
      const target = fs.readlinkSync(full);
      if (target === expectedTarget) {
        fs.unlinkSync(full);
        return { status: 'removed', path: rawPath };
      }
      return { status: 'skipped', path: rawPath, reason: `points to ${shorten(target)}` };
    }
    return { status: 'skipped', path: rawPath, reason: 'exists but not a symlink' };
  } catch (err) {
    if (err.code === 'ENOENT') return { status: 'missing', path: rawPath };
    throw err;
  }
}

function restoreBackup(rawPath) {
  const full = expand(rawPath);
  const backup = findLatestBackup(full);
  if (backup) {
    fs.renameSync(backup, full);
    return shorten(backup);
  }
  return null;
}

async function main() {
  intro('.dotfiles uninstaller');
  log.info(`Detected source: ${shorten(DOTFILES_DIR)}`);

  const targets = [
    ...allCommandPaths().map(p => ({ path: p, target: COMMANDS_DIR, type: 'command' })),
    ...allAgentPaths().map(p => ({ path: p, target: AGENTS_FILE, type: 'agent' })),
  ];

  const linked = targets.filter(t => {
    try {
      const full = expand(t.path);
      const stat = fs.lstatSync(full);
      return stat.isSymbolicLink() && fs.readlinkSync(full) === t.target;
    } catch { return false; }
  });

  if (linked.length === 0) {
    log.info('No dotfiles symlinks found.');
    outro('Nothing to uninstall.');
    return;
  }

  const cmdLinks = linked.filter(t => t.type === 'command');
  const agentLinks = linked.filter(t => t.type === 'agent');
  const summaryLines = [];
  if (cmdLinks.length) {
    summaryLines.push(`Commands (${cmdLinks.length}):`);
    cmdLinks.forEach(t => summaryLines.push(`  → ${t.path}`));
  }
  if (agentLinks.length) {
    if (summaryLines.length) summaryLines.push('');
    summaryLines.push(`Instructions (${agentLinks.length}):`);
    agentLinks.forEach(t => summaryLines.push(`  → ${t.path}`));
  }
  note(summaryLines.join('\n'), `Found ${linked.length} symlink(s)`);

  const proceed = await confirm({ message: 'Remove these symlinks?' });
  if (!proceed || typeof proceed === 'symbol') {
    outro('Cancelled.');
    process.exit(0);
  }

  const s = spinner();
  s.start('Removing symlinks...');

  const results = { removed: 0, restored: 0, skipped: [], errors: [] };

  for (const t of linked) {
    try {
      const r = removeLink(t.path, t.target);
      if (r.status === 'removed') {
        results.removed++;
        const backup = restoreBackup(t.path);
        if (backup) results.restored++;
      } else if (r.status === 'skipped') {
        results.skipped.push(`${r.path}: ${r.reason}`);
      }
    } catch (err) {
      results.errors.push(`${t.path}: ${err.message}`);
    }
  }

  s.stop('Done!');

  const lines = [];
  if (results.removed) lines.push(`✓ ${results.removed} symlink(s) removed`);
  if (results.restored) lines.push(`✓ ${results.restored} backup(s) restored`);
  if (results.skipped.length) {
    lines.push(`- ${results.skipped.length} skipped:`);
    results.skipped.forEach(s => lines.push(`  ${s}`));
  }
  if (results.errors.length) {
    lines.push(`✗ ${results.errors.length} error(s):`);
    results.errors.forEach(e => lines.push(`  ${e}`));
  }

  if (lines.length) note(lines.join('\n'), 'Results');

  if (fs.existsSync(DOTFILES_DIR)) {
    const removeSrc = await confirm({
      message: `Also remove ${shorten(DOTFILES_DIR)}?`,
    });
    if (removeSrc && typeof removeSrc !== 'symbol') {
      fs.rmSync(DOTFILES_DIR, { recursive: true, force: true });
      log.info(`Removed ${shorten(DOTFILES_DIR)}`);
    }
  }

  outro('Uninstall complete!');
}

main().catch(err => {
  log.error(`Error: ${err.message}`);
  process.exit(1);
});

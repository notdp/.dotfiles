#!/usr/bin/env node

import { intro, outro, confirm, spinner, note, log } from '@clack/prompts';
import { allCommandPaths, detectDotfilesDir } from './lib/catalog.mjs';
import pc from 'picocolors';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const HOME = os.homedir();
const expand = (s) => (s === '~' ? HOME : s.startsWith('~/') ? path.join(HOME, s.slice(2)) : s);
const shorten = (s) => s.replace(HOME, '~');

const DOTFILES_DIR = detectDotfilesDir() || expand('~/.dotfiles');
const COMMANDS_DIR = path.join(DOTFILES_DIR, 'commands');
const AGENTS_FILE = path.join(DOTFILES_DIR, 'agents', 'AGENTS.md');

function findFixable() {
  const targets = allCommandPaths().map(p => ({ path: p, target: COMMANDS_DIR, type: 'command' }));

  return targets.filter(t => {
    const full = expand(t.path);
    try {
      const stat = fs.lstatSync(full);
      return !stat.isSymbolicLink() && stat.isDirectory();
    } catch { return false; }
  });
}

function mergeAndLink(rawPath, target) {
  const full = expand(rawPath);
  const bak = `${full}.bak-${Date.now()}`;

  // rsync contents into dotfiles target (don't overwrite existing)
  try {
    execSync(`rsync -a --ignore-existing "${full}/" "${target}/"`, { stdio: 'pipe' });
  } catch {
    try { execSync(`cp -an "${full}/." "${target}/"`, { stdio: 'pipe' }); }
    catch {}
  }

  // backup original dir
  fs.renameSync(full, bak);

  // create symlink
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.symlinkSync(target, full);

  return bak;
}

async function main() {
  intro('.dotfiles fix');

  const fixable = findFixable();

  if (fixable.length === 0) {
    log.info('No standalone directories found. Everything is already linked.');
    outro('Nothing to fix.');
    return;
  }

  const maxLen = Math.max(...fixable.map(f => f.path.length));
  const lines = fixable.map(f =>
    `${f.path.padEnd(maxLen)} ${pc.dim('→ merge into')} ${shorten(f.target)}`
  );
  note(lines.join('\n'), `Found ${fixable.length} standalone dir(s)`);

  log.info(`Contents will be merged into ${pc.cyan(shorten(DOTFILES_DIR))}, originals backed up.`);

  const proceed = await confirm({ message: 'Proceed?' });
  if (!proceed || typeof proceed === 'symbol') {
    outro('Cancelled.');
    process.exit(0);
  }

  const s = spinner();
  s.start('Merging and linking...');

  const results = [];
  for (const f of fixable) {
    try {
      const bak = mergeAndLink(f.path, f.target);
      results.push({ path: f.path, bak: shorten(bak), ok: true });
    } catch (err) {
      results.push({ path: f.path, error: err.message, ok: false });
    }
  }

  s.stop('Done!');

  const resultLines = [];
  for (const r of results) {
    if (r.ok) {
      resultLines.push(`${pc.green('✓')} ${r.path} ${pc.dim(`(backup: ${r.bak})`)}`);
    } else {
      resultLines.push(`${pc.red('✗')} ${r.path}: ${r.error}`);
    }
  }
  note(resultLines.join('\n'), 'Results');

  outro('Fix complete! Run `npx . status` to verify.');
}

main().catch(err => {
  log.error(`Error: ${err.message}`);
  process.exit(1);
});

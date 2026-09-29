#!/usr/bin/env node

import {
  intro, outro, cancel, confirm, text, select,
  isCancel, spinner, note, log,
} from '@clack/prompts';
import { paginatedGroupMultiselect, styledMultiselect } from './lib/paginated-group-multiselect.mjs';
import { execFileSync, execFile as execFileCb } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFileCb);

const HOME = os.homedir();
const expand = (s) => (s === '~' ? HOME : s.startsWith('~/') ? path.join(HOME, s.slice(2)) : s);
const shorten = (s) => s.replace(HOME, '~');
const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const PACKAGE_ROOT = path.resolve(SCRIPT_DIR, '..');

import { UNIVERSAL_AGENTS, UNIVERSAL, AGENTS } from './lib/catalog.mjs';

const IGNORE_DIRS = new Set(['.system', '.git', '.github', '.ruff_cache', 'node_modules']);

// ── Path helpers ─────────────────────────────────────────────

function toProjectPath(p) {
  if (p === '~') return '.';
  if (p.startsWith('~/')) return p.slice(2);
  return p;
}

function agentLabel(agent, isGlobal) {
  const base = agent.commands.replace(/\/[^/]+$/, '').replace(/^~\//, '');
  const display = isGlobal ? base : toProjectPath(base);
  return `${agent.name} (${display})`;
}

// ── Helpers ──────────────────────────────────────────────────

function isLinkedTo(linkPath, target) {
  try { return fs.readlinkSync(expand(linkPath)) === target; }
  catch { return false; }
}

const mergeWarnings = [];

function createLink(linkPath, target) {
  const full = expand(linkPath);
  if (isLinkedTo(linkPath, target)) return 'exists';

  try {
    const stat = fs.lstatSync(full);
    if (stat.isSymbolicLink()) {
      fs.unlinkSync(full);
    } else if (stat.isDirectory()) {
      const bak = `${full}.bak-${Date.now()}`;
      fs.renameSync(full, bak);
      try { execFileSync('rsync', ['-a', '--ignore-existing', `${bak}/`, `${target}/`], { stdio: 'pipe' }); }
      catch { try { execFileSync('cp', ['-an', `${bak}/.`, `${target}/`], { stdio: 'pipe' }); } catch {} }
      mergeWarnings.push(`Merged ${shorten(full)} into ${shorten(target)}, backup: ${shorten(bak)}`);
    } else if (stat.isFile()) {
      fs.renameSync(full, `${full}.bak-${Date.now()}`);
    }
  } catch (err) {
    if (err.code !== 'ENOENT') throw err;
  }

  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.symlinkSync(target, full);
  return 'created';
}

function createCopy(destPath, source) {
  const full = expand(destPath);
  fs.mkdirSync(path.dirname(full), { recursive: true });

  const srcStat = fs.statSync(source);
  if (srcStat.isDirectory()) {
    fs.mkdirSync(full, { recursive: true });
    try { execFileSync('rsync', ['-a', `${source}/`, `${full}/`], { stdio: 'pipe' }); }
    catch { execFileSync('cp', ['-r', `${source}/.`, `${full}/`], { stdio: 'pipe' }); }
  } else {
    fs.copyFileSync(source, full);
  }
  return 'created';
}

function ensureFrontMatter(dir) {
  if (!fs.existsSync(dir)) return;
  for (const file of fs.readdirSync(dir).filter(f => f.endsWith('.md'))) {
    const fp = path.join(dir, file);
    const content = fs.readFileSync(fp, 'utf-8');
    if (content.startsWith('---')) continue;
    fs.writeFileSync(fp, `---\ndescription:\n---\n\n${content}`);
  }
}

// ── Initialization helpers ───────────────────────────────────

function scanDir(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter(d => d.isDirectory() && !d.name.startsWith('.') && !IGNORE_DIRS.has(d.name))
    .map(d => d.name);
}

function needsInit(dotfilesDir) {
  const commandsDir = path.join(dotfilesDir, 'commands');
  if (!fs.existsSync(dotfilesDir)) return true;
  const hasCommands = fs.existsSync(commandsDir) && fs.readdirSync(commandsDir).some(f => f.endsWith('.md') && f !== '.gitkeep');
  return !hasCommands;
}

function scanCommands(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(f => f.endsWith('.md') && f !== '.gitkeep')
    .map(f => f.replace(/\.md$/, ''));
}

// ── Main ─────────────────────────────────────────────────────

async function main() {
  intro('.dotfiles installer');

  let createdDir = null;
  const createdLinks = [];

  function rollback() {
    for (const link of createdLinks) {
      try { fs.unlinkSync(expand(link)); } catch {}
    }
    if (createdDir && fs.existsSync(createdDir)) {
      fs.rmSync(createdDir, { recursive: true, force: true });
    }
  }

  function bail() {
    rollback();
    cancel('Cancelled.');
    process.exit(0);
  }

  // ── Step 1: Installation scope ──
  const scope = await select({
    message: 'Installation scope',
    options: [
      { value: 'global', label: 'Global', hint: 'Install in home directory (available across all projects)' },
      { value: 'project', label: 'Project', hint: 'Install in current directory (committed with your project)' },
    ],
  });
  if (isCancel(scope)) bail();

  const isGlobal = scope === 'global';

  // ── Step 2: Installation method ──
  const method = await select({
    message: 'Installation method',
    options: [
      { value: 'symlink', label: 'Symlink (Recommended)', hint: 'Single source of truth, easy updates' },
      { value: 'copy', label: 'Copy to all agents', hint: 'Independent copies for each agent' },
    ],
  });
  if (isCancel(method)) bail();

  // ── Step 3: Dotfiles directory ──
  const dirInput = await text({
    message: 'Dotfiles directory?',
    placeholder: isGlobal ? '~/.dotfiles' : '.agents',
    defaultValue: isGlobal ? '~/.dotfiles' : '.agents',
  });
  if (isCancel(dirInput)) bail();

  const DOTFILES_DIR = isGlobal
    ? expand(dirInput.trim())
    : path.resolve(dirInput.trim());

  const COMMANDS_DIR = path.join(DOTFILES_DIR, 'commands');
  const AGENTS_FILE = path.join(DOTFILES_DIR, 'agents', 'AGENTS.md');

  // ── Step 4: Initialize if needed ──
  const isSameDir = path.resolve(PACKAGE_ROOT) === path.resolve(DOTFILES_DIR);

  async function copyFromPackage() {
    const s = spinner();
    s.start('Copying content from package...');
    const existed = fs.existsSync(DOTFILES_DIR);
    fs.mkdirSync(DOTFILES_DIR, { recursive: true });
    if (!existed) createdDir = DOTFILES_DIR;
    for (const dir of ['commands', 'agents']) {
      const src = path.join(PACKAGE_ROOT, dir);
      const dst = path.join(DOTFILES_DIR, dir);
      if (fs.existsSync(src)) {
        fs.mkdirSync(dst, { recursive: true });
        try { execFileSync('rsync', ['-a', '--ignore-existing', `${src}/`, `${dst}/`], { stdio: 'pipe' }); }
        catch { execFileSync('cp', ['-r', `${src}/.`, `${dst}/`], { stdio: 'pipe' }); }
      }
    }
    s.stop('Content copied.');

    const availableCommands = scanCommands(COMMANDS_DIR);
    if (availableCommands.length > 0) {
      const selectedCommands = await styledMultiselect({
        message: 'Select commands to install',
        options: availableCommands.map(c => ({ value: c, label: c })),
        initialValues: availableCommands,
        required: false,
      });
      if (isCancel(selectedCommands)) bail();
      const keepCommands = new Set((selectedCommands || []).map(c => `${c}.md`));
      for (const f of fs.readdirSync(COMMANDS_DIR)) {
        if (f.endsWith('.md') && f !== '.gitkeep' && !keepCommands.has(f)) fs.unlinkSync(path.join(COMMANDS_DIR, f));
      }
    }
  }

  if (!isSameDir && needsInit(DOTFILES_DIR)) {
    if (isGlobal) {
      const initMode = await select({
        message: 'How to set up dotfiles?',
        options: [
          { value: 'new', label: 'Create new', hint: 'Start with pre-made commands' },
          { value: 'import', label: 'Import existing', hint: 'Clone your git repository' },
        ],
      });
      if (isCancel(initMode)) bail();

      if (initMode === 'new') {
        await copyFromPackage();
      } else {
        const repoUrl = await text({
          message: 'Git repository URL?',
          placeholder: 'user/.dotfiles',
        });
        if (isCancel(repoUrl)) bail();
        const s = spinner();
        s.start('Cloning repository...');
        try {
          await execFileAsync('gh', ['repo', 'clone', repoUrl.trim(), DOTFILES_DIR]);
          createdDir = DOTFILES_DIR;
          s.stop('Repository cloned.');
        } catch (err) {
          s.stop('Clone failed.');
          if (fs.existsSync(DOTFILES_DIR)) {
            fs.rmSync(DOTFILES_DIR, { recursive: true, force: true });
          }
          log.error(`gh repo clone failed: ${err.message}`);
          process.exit(1);
        }
      }
    } else {
      await copyFromPackage();
    }
  } else if (!isSameDir) {
    log.warn(`${shorten(DOTFILES_DIR)} already has content, skipping initialization.`);
  }

  // Ensure directories exist (skip for git repos — user manages their own structure)
  const isGitRepo = fs.existsSync(path.join(DOTFILES_DIR, '.git'));
  if (!isGitRepo) {
    fs.mkdirSync(COMMANDS_DIR, { recursive: true });
    fs.mkdirSync(path.dirname(AGENTS_FILE), { recursive: true });
  }

  if (!isGitRepo && isGlobal && !fs.existsSync(AGENTS_FILE)) {
    log.info('First install — merging existing agent instruction files...');
    let content = '';
    for (const a of AGENTS) {
      if (!a.instructions) continue;
      const file = expand(a.instructions);
      try {
        const stat = fs.lstatSync(file);
        if (stat.isFile() && !stat.isSymbolicLink()) {
          content += `\n# === from ${a.instructions} ===\n`;
          content += fs.readFileSync(file, 'utf-8');
        }
      } catch {}
    }
    fs.writeFileSync(AGENTS_FILE, content);
  }

  // ── Step 5: Select agents ──
  const universalLabel = isGlobal ? '.agents' : toProjectPath('.agents');
  const lockedGroups = {
    [`Universal (${universalLabel})`]: UNIVERSAL_AGENTS.map(name => ({ label: name })),
  };

  const agentOptions = AGENTS.map(a => ({
    value: a.name,
    label: agentLabel(a, isGlobal),
  }));

  function isAgentLinked(agent) {
    return isLinkedTo(agent.commands, COMMANDS_DIR);
  }

  const selectedAgents = await paginatedGroupMultiselect({
    message: 'Select agents to configure',
    options: { 'Other agents': agentOptions },
    lockedGroups,
    initialValues: AGENTS.filter(isAgentLinked).map(a => a.name),
    required: false,
    maxItems: 10,
  });
  if (isCancel(selectedAgents)) bail();

  const chosen = new Set(selectedAgents || []);
  const chosenAgents = AGENTS.filter(a => chosen.has(a.name));

  // Collect all paths to install
  const commandPaths = [
    isGlobal ? UNIVERSAL.commands : toProjectPath(UNIVERSAL.commands),
    ...chosenAgents.map(a => isGlobal ? a.commands : toProjectPath(a.commands)),
  ];
  const instructionPaths = chosenAgents
    .filter(a => a.instructions)
    .map(a => isGlobal ? a.instructions : toProjectPath(a.instructions));

  const total = commandPaths.length + instructionPaths.length;
  if (total === 0) { outro('Nothing selected.'); return; }

  // ── Summary ──
  const methodLabel = method === 'symlink' ? 'Symlink' : 'Copy';
  const summaryLines = [];
  if (commandPaths.length) {
    if (summaryLines.length) summaryLines.push('');
    summaryLines.push(`Commands (${commandPaths.length}):`);
    commandPaths.forEach(c => summaryLines.push(`  → ${c}`));
  }
  if (instructionPaths.length) {
    if (summaryLines.length) summaryLines.push('');
    summaryLines.push(`Instructions (${instructionPaths.length}):`);
    instructionPaths.forEach(i => summaryLines.push(`  → ${i}`));
  }
  summaryLines.push('');
  summaryLines.push(`Scope: ${isGlobal ? 'Global' : 'Project'}  │  Method: ${methodLabel}`);
  summaryLines.push(`Source: ${shorten(DOTFILES_DIR)}`);

  note(summaryLines.join('\n'), 'Installation Summary');

  const proceed = await confirm({ message: 'Proceed with installation?' });
  if (!proceed || typeof proceed === 'symbol') bail();

  // ── Execute ──
  const s = spinner();
  s.start(method === 'symlink' ? 'Creating symlinks...' : 'Copying files...');

  const stats = { created: 0, exists: 0, errors: [] };

  function doInstall(items, target) {
    for (const item of items) {
      try {
        const r = method === 'symlink'
          ? createLink(item, target)
          : createCopy(item, target);
        if (r === 'created') createdLinks.push(item);
        stats[r === 'created' ? 'created' : 'exists']++;
      } catch (err) {
        stats.errors.push(`${item}: ${err.message}`);
      }
    }
  }

  doInstall(commandPaths, COMMANDS_DIR);
  doInstall(instructionPaths, AGENTS_FILE);
  if (!isGitRepo) ensureFrontMatter(COMMANDS_DIR);

  s.stop('Done!');

  for (const w of mergeWarnings) log.warn(w);

  const resultLines = [];
  const verb = method === 'symlink' ? 'symlink(s)' : 'copie(s)';
  if (stats.created) resultLines.push(`✓ ${stats.created} new ${verb} created`);
  if (stats.exists) resultLines.push(`✓ ${stats.exists} already linked`);
  if (stats.errors.length) {
    resultLines.push(`✗ ${stats.errors.length} error(s):`);
    stats.errors.forEach(e => resultLines.push(`  ${e}`));
  }

  if (resultLines.length) note(resultLines.join('\n'), 'Results');

  // Installation succeeded, disable rollback
  createdDir = null;
  createdLinks.length = 0;

  // ── Optional: git init ──
  if (!isGitRepo && isGlobal) {
    const wantGit = await confirm({ message: 'Set up as git repository?' });
    if (wantGit && !isCancel(wantGit)) {
      const repoUrl = await text({
        message: 'Remote repository URL?',
        placeholder: 'https://github.com/user/.dotfiles.git',
      });
      if (!isCancel(repoUrl) && repoUrl?.trim()) {
        try {
          execFileSync('git', ['init'], { cwd: DOTFILES_DIR, stdio: 'pipe' });
          execFileSync('git', ['remote', 'add', 'origin', repoUrl.trim()], { cwd: DOTFILES_DIR, stdio: 'pipe' });
          log.info(`Git initialized with remote: ${repoUrl.trim()}`);
        } catch (err) {
          log.warn(`Git setup failed: ${err.message}`);
        }
      }
    }
  }

  outro('Installation complete!');
}

main().catch(err => {
  cancel(`Error: ${err.message}`);
  process.exit(1);
});

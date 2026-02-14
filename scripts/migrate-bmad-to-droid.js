#!/usr/bin/env node
/**
 * BMAD to Droid 迁移脚本
 * 
 * 源目录: .claude/commands/bmad/ (BMAD 精简入口版本)
 * 输出:
 * - Droids (droids/): bmad-bmm-pm.md (包含 model + tools)
 * - Commands (commands/): bmad-bmm-quick-spec.md (斜杠命令)
 * 
 * 命名规则: bmad-{namespace}-{name}
 */
const fs = require('fs');
const path = require('path');

// 脚本在 scripts/ 目录下，项目根目录是父目录
const PROJECT_ROOT = path.resolve(__dirname, '..');
const BMAD_SRC = path.join(PROJECT_ROOT, '.claude', 'commands', 'bmad');
const DROIDS_DIR = path.join(PROJECT_ROOT, 'droids');
const COMMANDS_DIR = path.join(PROJECT_ROOT, 'commands');

// Droids 默认 tools
const DEFAULT_TOOLS = '["Read", "Edit", "Execute", "Grep", "Glob", "LS", "WebSearch"]';

// 确保目标目录存在
fs.mkdirSync(DROIDS_DIR, { recursive: true });
fs.mkdirSync(COMMANDS_DIR, { recursive: true });

console.log('=== BMAD to Droid Migration ===');
console.log(`Source: ${BMAD_SRC}`);
console.log(`Droids: ${DROIDS_DIR}`);
console.log(`Commands: ${COMMANDS_DIR}`);
console.log('');

let droidsCount = 0;
let commandsCount = 0;

// 递归遍历目录
function* walkDir(dir) {
    if (!fs.existsSync(dir)) return;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            yield* walkDir(fullPath);
        } else if (entry.isFile() && entry.name.endsWith('.md')) {
            yield fullPath;
        }
    }
}

// 检测文件类型 (agents, workflows, tasks)
function detectType(relPath) {
    const normalizedPath = relPath.replace(/\\/g, '/');
    if (normalizedPath.includes('/agents/')) return 'agents';
    if (normalizedPath.includes('/workflows/')) return 'workflows';
    if (normalizedPath.includes('/tasks/')) return 'tasks';
    return null;
}

// 提取 frontmatter 字段
function extractFrontmatter(content) {
    const result = { description: '', name: '', body: content };
    
    if (!content.startsWith('---')) return result;
    
    const endIndex = content.indexOf('---', 3);
    if (endIndex === -1) return result;
    
    const frontmatter = content.slice(3, endIndex);
    result.body = content.slice(endIndex + 3).trim();
    
    // 提取 description
    const descMatch = frontmatter.match(/description:\s*['"]?([^'"\n]+)['"]?/);
    if (descMatch) result.description = descMatch[1].trim();
    
    // 提取 name
    const nameMatch = frontmatter.match(/name:\s*['"]?([^'"\n]+)['"]?/);
    if (nameMatch) result.name = nameMatch[1].trim();
    
    return result;
}

// 处理单个文件
function processFile(srcFile) {
    const relPath = path.relative(BMAD_SRC, srcFile);
    const normalizedPath = relPath.replace(/\\/g, '/');
    const parts = normalizedPath.split('/');
    
    // 提取命名空间 (bmm 或 core)
    const namespace = parts[0];
    const filename = path.basename(srcFile, '.md');
    const fileType = detectType(normalizedPath);
    
    if (!fileType) {
        console.log(`  [SKIP] Unknown type: ${relPath}`);
        return;
    }
    
    const content = fs.readFileSync(srcFile, 'utf-8');
    const { description, body } = extractFrontmatter(content);
    const defaultDesc = `BMAD ${fileType}: ${filename}`;
    const finalDesc = description || defaultDesc;
    
    // 生成名称: bmad__{namespace}__{type}__{filename}
    // 用 __ 分隔层级，保留原文件名中的 -
    // agents -> droid (不含 type)
    // workflows/tasks -> command (含 type: workflow/task)
    
    // 1. 生成 Droid 文件 (仅 agents)
    if (fileType === 'agents') {
        const droidName = `bmad__${namespace}__${filename}`;
        const droidFile = path.join(DROIDS_DIR, `${droidName}.md`);
        const droidContent = `---
name: ${droidName}
description: ${finalDesc}
model: inherit
tools: ${DEFAULT_TOOLS}
---

${body}
`;
        fs.writeFileSync(droidFile, droidContent, 'utf-8');
        console.log(`  [DROID] ${relPath} -> ${droidName}.md`);
        droidsCount++;
    }
    
    // 2. 生成 Command 文件 (workflows 和 tasks)
    // 文件名包含类型: bmad__{namespace}__workflow__{name} 或 bmad__{namespace}__task__{name}
    if (fileType === 'workflows' || fileType === 'tasks') {
        const typeLabel = fileType === 'workflows' ? 'workflow' : 'task';
        const commandName = `bmad__${namespace}__${typeLabel}__${filename}`;
        const commandFile = path.join(COMMANDS_DIR, `${commandName}.md`);
        const commandContent = `---
description: ${finalDesc}
---

${body}
`;
        fs.writeFileSync(commandFile, commandContent, 'utf-8');
        console.log(`  [COMMAND] ${relPath} -> ${commandName}.md`);
        commandsCount++;
    }
}

// 检查源目录是否存在
if (!fs.existsSync(BMAD_SRC)) {
    console.error(`Error: Source directory not found: ${BMAD_SRC}`);
    console.error('Please ensure BMAD is installed in .claude/commands/bmad/');
    process.exit(1);
}

// 执行迁移
console.log('Processing files...');
for (const file of walkDir(BMAD_SRC)) {
    processFile(file);
}

console.log('');
console.log('=== Migration Complete ===');
console.log(`Droids migrated: ${droidsCount}`);
console.log(`Commands migrated: ${commandsCount}`);
console.log(`Total files created: ${droidsCount + commandsCount}`);
console.log('');
console.log('Usage:');
console.log('  Droids: @bmad__bmm__pm');
console.log('  Commands: /bmad__bmm__workflow__quick-spec');

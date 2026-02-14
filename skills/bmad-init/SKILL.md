---
name: bmad-init
description: Initialize BMAD for a project by copying _bmad source files and configuring project settings. Use when starting a new project with BMAD workflows or when the user mentions "bmad init", "initialize bmad", or "setup bmad".
---

# BMAD Project Initialization

Initialize BMAD (BMad Method) by copying source files to the current project and configuring project-specific settings.

## What this skill does

1. Copies `_bmad/` directory from `~/.dotfiles/_bmad/` to the project root
2. Updates config files with project-specific settings
3. Creates `_bmad-output/` directory structure for workflow outputs
4. Optionally updates `.gitignore`

## Execution Steps

### Step 1: Get Current Directory and Check Environment

```bash
pwd
```

Store result as `{project-root}`.

Check if BMAD source exists:
```bash
ls -d ~/.dotfiles/_bmad 2>/dev/null
```

If source doesn't exist:
- Display error: "BMAD source not found at ~/.dotfiles/_bmad. Please install .dotfiles first."
- Exit skill

### Step 2: Check Existing Installation

```bash
ls -d _bmad 2>/dev/null
```

If `_bmad/` already exists:
- Display: "BMAD already installed in this project."
- Ask: "[U]pdate config / [R]einstall (overwrite) / [C]ancel?"
- If Update: Skip to Step 4
- If Reinstall: Continue to Step 3
- If Cancel: Exit skill

### Step 3: Copy BMAD Source Files

Copy the entire `_bmad` directory to the project:

```bash
cp -r ~/.dotfiles/_bmad ./_bmad
```

Display progress:
```
📦 Copying BMAD source files...
   ~/.dotfiles/_bmad → ./_bmad
```

### Step 4: Collect User Configuration (Interactive)

Get the project directory name as default:
```bash
basename "$(pwd)"
```

Ask user for each setting:

```
📋 BMAD Project Configuration

Project name [{basename}]: 
Your name [User]: 
Communication language [Chinese]: 
Document output language [Chinese]: 
Skill level (beginner/intermediate/expert) [intermediate]: 
```

### Step 5: Update Config Files (In-place Edit)

**CRITICAL:** Do NOT regenerate config files. Use `sed` to modify only specific fields in the copied files.
All path variables like `{project-root}` must remain as literal strings - they are resolved at BMAD runtime.

Edit `./_bmad/bmm/config.yaml` - only modify these fields:
```bash
sed -i 's/^project_name:.*/project_name: {project_name}/' ./_bmad/bmm/config.yaml
sed -i 's/^user_skill_level:.*/user_skill_level: {user_skill_level}/' ./_bmad/bmm/config.yaml
sed -i 's/^user_name:.*/user_name: {user_name}/' ./_bmad/bmm/config.yaml
sed -i 's/^communication_language:.*/communication_language: {communication_language}/' ./_bmad/bmm/config.yaml
sed -i 's/^document_output_language:.*/document_output_language: {document_output_language}/' ./_bmad/bmm/config.yaml
```

Edit `./_bmad/core/config.yaml` - only modify these fields:
```bash
sed -i 's/^user_name:.*/user_name: {user_name}/' ./_bmad/core/config.yaml
sed -i 's/^communication_language:.*/communication_language: {communication_language}/' ./_bmad/core/config.yaml
sed -i 's/^document_output_language:.*/document_output_language: {document_output_language}/' ./_bmad/core/config.yaml
```

Where `{project_name}`, `{user_name}`, etc. are the values collected from the user in Step 4.

### Step 6: Create Output Directories

```bash
mkdir -p _bmad-output/planning-artifacts _bmad-output/implementation-artifacts
```

### Step 7: Update .gitignore (Optional)

Ask user: "Add _bmad-output/ to .gitignore? [Y/n]"

If yes, check if `.gitignore` exists and append:
```
# BMAD output files
_bmad-output/
```

Ask user: "Add _bmad/ to .gitignore? (Choose No to version control BMAD config) [y/N]"

If yes, append:
```
# BMAD source files (can be regenerated with bmad-init)
_bmad/
```

### Step 8: Summary

```
✅ BMAD initialized for: {project_name}

📁 Created:
   _bmad/                        (BMAD source files)
   ├── bmm/config.yaml           (project config)
   └── core/config.yaml          (core config)
   _bmad-output/
   ├── planning-artifacts/
   └── implementation-artifacts/

🚀 Available workflows:
   /bmad__bmm__workflow__create-product-brief  - Create product brief
   /bmad__bmm__workflow__prd                   - Create PRD
   /bmad__bmm__workflow__create-architecture   - Create architecture
   /bmad__bmm__workflow__workflow-status       - Check workflow status

💡 Tips:
   - Config files are in ./_bmad/bmm/config.yaml
   - Outputs go to ./_bmad-output/
   - Run bmad-init again to update config
```

## Config Reference

| Field | Description | Default |
|-------|-------------|---------|
| `project_name` | Project identifier | directory name |
| `user_name` | Your name | "User" |
| `user_skill_level` | beginner/intermediate/expert | "intermediate" |
| `communication_language` | AI speaks in | "Chinese" |
| `document_output_language` | Docs written in | "Chinese" |
| `output_folder` | Base output path | "{project-root}/_bmad-output" |
| `tea_use_mcp_enhancements` | TEA MCP features | false |
| `tea_use_playwright_utils` | TEA Playwright | false |

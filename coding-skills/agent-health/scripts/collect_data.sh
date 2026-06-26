#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$PWD}"

if [[ ! -d "$repo_root" ]]; then
  echo "repo root does not exist: $repo_root" >&2
  exit 2
fi

agents_file="$repo_root/agents/AGENTS.md"
# SSOT is coding-skills/ (this repo); fall back to skills/ for older/other layouts.
if [[ -d "$repo_root/coding-skills" ]]; then
  catalog_file="$repo_root/coding-skills/catalog.json"
  skills_dir="$repo_root/coding-skills"
else
  catalog_file="$repo_root/skills/catalog.json"
  skills_dir="$repo_root/skills"
fi

hook_candidates=(
  "$repo_root/hooks"
  "$repo_root/hooks.json"
  "$repo_root/.factory/settings.json"
  "$repo_root/.factory/hooks.json"
  "$repo_root/.droid/hooks.json"
)

mcp_candidates=(
  "$repo_root/.mcp.json"
  "$repo_root/mcp.json"
  "$repo_root/.factory/mcp.json"
  "$repo_root/.droid/mcp.json"
)

skills_count="0"
if [[ -d "$skills_dir" ]]; then
  skills_count="$(
    find "$skills_dir" -mindepth 2 -maxdepth 2 -name SKILL.md ! -path "*/.system/*" | wc -l | tr -d ' '
  )"
fi

find_first_existing() {
  for candidate in "$@"; do
    if [[ -e "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

find_hook_config() {
  for candidate in "${hook_candidates[@]}"; do
    if [[ ! -e "$candidate" ]]; then
      continue
    fi
    if [[ "$candidate" == */settings.json ]] && ! grep -q '"hooks"' "$candidate"; then
      continue
    fi
    printf '%s\n' "$candidate"
    return 0
  done
  return 1
}

status="PASS"
issues=()

if [[ ! -f "$agents_file" ]]; then
  status="FAIL"
  issues+=("[FAIL] Missing agents/AGENTS.md")
fi

if [[ ! -f "$catalog_file" ]]; then
  [[ "$status" == "PASS" ]] && status="WARN"
  issues+=("[WARN] Missing catalog.json ($catalog_file)")
fi

hook_path="$(find_hook_config || true)"
if [[ -z "$hook_path" ]]; then
  [[ "$status" == "PASS" ]] && status="WARN"
  issues+=("[WARN] Missing hook configuration")
fi

mcp_path="$(find_first_existing "${mcp_candidates[@]}" || true)"
if [[ -z "$mcp_path" ]]; then
  [[ "$status" == "PASS" ]] && status="WARN"
  issues+=("[WARN] Missing MCP configuration")
fi

echo "=== SUMMARY ==="
echo "STATUS: $status"
echo "ROOT: $repo_root"
echo "SKILLS: $skills_count"
if [[ -f "$agents_file" ]]; then
  echo "AGENTS: present"
else
  echo "AGENTS: missing"
fi
if [[ -f "$catalog_file" ]]; then
  echo "CATALOG: present"
else
  echo "CATALOG: missing"
fi
if [[ -n "$hook_path" ]]; then
  echo "HOOKS: present"
else
  echo "HOOKS: missing"
fi
if [[ -n "$mcp_path" ]]; then
  echo "MCP: present"
else
  echo "MCP: missing"
fi
echo

echo "=== ISSUES ==="
if [[ "${#issues[@]}" -eq 0 ]]; then
  echo "(none)"
else
  printf '%s\n' "${issues[@]}"
fi
echo

echo "=== EVIDENCE ==="
if [[ -f "$agents_file" ]]; then
  echo "AGENTS_FILE: $agents_file"
fi
if [[ -f "$catalog_file" ]]; then
  echo "CATALOG_FILE: $catalog_file"
fi
echo "SKILLS_COUNT: $skills_count"
if [[ -n "$hook_path" ]]; then
  echo "HOOK_PATH: $hook_path"
fi
if [[ -n "$mcp_path" ]]; then
  echo "MCP_PATH: $mcp_path"
fi

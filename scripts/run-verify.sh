#!/usr/bin/env bash
# run-verify.sh — 自动探测并运行项目 test / typecheck / build / lint 命令
# 用法：bash scripts/run-verify.sh [repo_root]
# 输出：Markdown 表格（Check | Command | Result | Evidence）
# 行为：尽力而为，任何检查失败不中断其它；exit code 0=全绿，1=有失败，2=无任何可检测目标

set -u  # 不用 -e，单项失败不能阻断其它

REPO="${1:-$(pwd)}"
cd "$REPO" || { echo "ERROR: cannot cd to $REPO"; exit 2; }

# 结果收集 —— 每行：check|command|result|evidence
RESULTS=()
FAIL_COUNT=0
RAN_COUNT=0

run_check() {
  local name="$1"; local cmd="$2"
  RAN_COUNT=$((RAN_COUNT+1))
  local tmp
  tmp=$(mktemp)
  local start
  start=$(date +%s)
  if eval "$cmd" >"$tmp" 2>&1; then
    local dur=$(($(date +%s)-start))
    local last
    last=$(tail -n 1 "$tmp" | tr -d '|' | cut -c 1-80)
    RESULTS+=("${name}|\`${cmd}\`|pass (${dur}s)|${last:-ok}")
  else
    local exit_code="$?"
    local dur=$(($(date +%s)-start))
    local last
    last=$(tail -n 3 "$tmp" | tr -d '|' | tr '\n' ' ' | cut -c 1-120)
    local summary
    if [[ -f scripts/compact_validator_error.py ]] && command -v python3 >/dev/null 2>&1; then
      summary=$(python3 scripts/compact_validator_error.py --command "$cmd" --check "$name" --exit-code "$exit_code" <"$tmp" | tr -d '|' | tr '\n' ' ' | cut -c 1-220)
    fi
    RESULTS+=("${name}|\`${cmd}\`|fail (${dur}s)|${summary:-${last:-fail}}")
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
  rm -f "$tmp"
}

# 按项目类型探测
if [[ -f package.json ]]; then
  if grep -q '"test"' package.json 2>/dev/null; then
    run_check "tests (npm)" "npm test --silent"
  fi
  if grep -q '"lint"' package.json 2>/dev/null; then
    run_check "lint (npm)" "npm run lint --silent"
  fi
  if grep -q '"typecheck"' package.json 2>/dev/null; then
    run_check "typecheck (npm)" "npm run typecheck --silent"
  fi
  if grep -q '"build"' package.json 2>/dev/null; then
    run_check "build (npm)" "npm run build --silent"
  fi
fi

if [[ -f pyproject.toml ]] || [[ -d tests ]] && ls tests/test_*.py >/dev/null 2>&1; then
  if command -v pytest >/dev/null 2>&1; then
    run_check "tests (pytest)" "pytest -q"
  elif [[ -f pyproject.toml ]] && command -v python3 >/dev/null 2>&1; then
    run_check "tests (unittest)" "python3 -m unittest discover -q"
  fi
fi

if [[ -d scripts/tests ]] && ls scripts/tests/test_*.py >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  run_check "tests (scripts unittest)" "python3 -m unittest discover -s scripts/tests -p \"test_*.py\""
fi

if [[ -f Cargo.toml ]]; then
  run_check "tests (cargo)" "cargo test --quiet"
fi

if [[ -f Makefile ]] && grep -qE '^test:' Makefile; then
  run_check "tests (make)" "make test"
fi

if [[ -f go.mod ]]; then
  run_check "tests (go)" "go test ./..."
fi

# 本仓库特定：skills 校验
if [[ -f scripts/verify_skills.py ]]; then
  run_check "verify_skills" "python3 scripts/verify_skills.py"
fi

# 本仓库特定：subagents 校验
if [[ -f scripts/verify_agents.py ]]; then
  run_check "verify_agents" "python3 scripts/verify_agents.py"
fi

# 本仓库特定：opencode/kilo plugin 契约测试(node)
if [[ -f scripts/tests/test_dotfiles_hooks.mjs ]] && command -v node >/dev/null 2>&1; then
  run_check "tests (plugin mjs)" "node scripts/tests/test_dotfiles_hooks.mjs"
fi

# 输出
echo "## 验证结果"
echo ""
if [[ $RAN_COUNT -eq 0 ]]; then
  echo "未探测到任何可执行的 test/build/lint 命令。"
  echo ""
  echo "- [ ] 请手动声明验证方式并填写下方表格"
  exit 2
fi

echo "| Check | Command | Result | Evidence |"
echo "|-------|---------|--------|----------|"
for line in "${RESULTS[@]}"; do
  # shellcheck disable=SC2001
  echo "| $(echo "$line" | sed 's/|/ | /g') |"
done
echo ""
echo "## 总结"
echo "- 运行: $RAN_COUNT 项"
echo "- 失败: $FAIL_COUNT 项"
if [[ $FAIL_COUNT -eq 0 ]]; then
  echo "- 状态: ✅ 全绿"
  exit 0
else
  echo "- 状态: ❌ 有失败，详见 Evidence 列"
  exit 1
fi

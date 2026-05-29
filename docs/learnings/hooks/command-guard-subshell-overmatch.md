---
title: command_guard subshell 提取会误匹配引号/heredoc 内的字面量
date: 2026-05-29
problem_type: pattern
module: scripts/hooks/command_guard.py
component: extract_command_substitutions
tags: [hook, command-guard, false-positive, subshell, heredoc, commit]
---

# Learning Note: command_guard subshell 提取会误匹配引号/heredoc 内的字面量

Date: 2026-05-29

## Context

- Problem: 给 command_guard 加了 `extract_command_substitutions`，递归评估 `$(...)`/反引号内命令以封堵绕过。随后一次 `git commit -F - <<'EOF' ... EOF`，commit message 正文里含字面量 `$(git push origin main)` 作示例，被 hook 解析并 deny，commit 失败。
- Scope: command_guard PreToolUse hook 对 Bash 命令字符串的扫描。
- Trigger: 命令字符串里出现替代语法字面量（即使在单引号/heredoc 内、不会被 shell 执行）。

## Outcome

- Final approach: 改写 commit message 去掉该字面量后提交成功；未削弱 hook（deny 侧 fail-safe，宁可误报不漏放）。
- Validation: `git commit` 成功，HEAD 前进；F3 相关 27 个 command_guard 测试仍绿。
- Constraints: 该误匹配是 deny 方向（安全侧），但会拦住含替代语法字面量的合法命令。

## Reusable Pattern

- Signal: 在 hook 里对原始命令字符串做语法提取，但不解析引号上下文。
- Decision rule: tokenize 前扫原始串的提取逻辑，无法区分"引号/heredoc 内字面量"与"真实可执行替代"；默认会过度匹配。
- Steps: (1) 给这类 guard 写测试时显式覆盖"引号内字面量不应被当真实命令"; (2) 写 commit message / 文档时避免内联 `$(危险命令)` 字面量; (3) 若要消除误报，需引号上下文感知解析（成本较高，按需做）。

## Evidence

- Commands: `git commit -q -F - <<'EOF' ... $(git push origin main) ... EOF` → permissionDecision deny
- Files: `scripts/hooks/command_guard.py`（`extract_command_substitutions`），commit `e6e1812`
- Tests / checks: `scripts/tests/test_hook_command_guard.py`（subshell 用例）

## Follow-ups

- Remaining risks: 含替代语法字面量的合法命令会被 deny（false positive，安全侧）。
- Next actions: 待定——是否给 `extract_command_substitutions` 加引号上下文感知（区分单引号字面量 vs 真实替换），列为 backlog。

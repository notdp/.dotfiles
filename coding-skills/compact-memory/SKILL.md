---
name: compact-memory
description: 当需要把多条同主题 episodic memory 反思压缩成带来源引用的 semantic memory，或评估 lexical 召回是否足够、是否需要 embedding 增强时使用；只做 on-demand，不接 daemon/hook。
argument-hint: <topic|decision-file|holdout>
---

# /compact-memory

Use this skill when repeated episodic user memory notes should be compacted into one higher-level semantic memory. This is on-demand reflection only: no daemon, no hook auto-compaction, and no live LLM call inside the deterministic write script.

## Contract

- Start with local lexical recall over `memory/user/*.md`.
- Produce a structured decision file before writing. The deterministic script only validates and applies that decision.
- Every generated insight must cite source notes using `(because of <id>)`.
- `<2` matching source notes means no promotion to semantic memory.
- This phase implements the count threshold only. Cumulative `importance` threshold and cooldown-window trigger are explicitly not implemented because `/compact-memory` is a manual on-demand command and cooldown semantics are weak without an automatic scheduler.
- Use dual-track storage: source episodic notes stay on disk for audit.
- Mark explicitly refuted source notes as `stale`; do not physically delete them and do not silently rewrite their bodies.
- Apply char-budget rejection before tracked writes. Do not truncate note text or INDEX content silently.
- Treat embedding as conditional embedding work: only add sidecars after holdout evidence shows lexical recall is insufficient and the sidecar branch is fully verified.

## Flow

1. Lexical recall: collect active episodic source notes by `--topic` and/or decision `source_ids`.
2. Reflection decision: an LLM or human writes a JSON decision with `action`, `title`, `insight`, and `source_ids`; tests use fixtures.
3. Deterministic write: run `coding-skills/compact-memory/scripts/compact_memory.py` to validate citations, reject unsafe writes, rebuild `INDEX.md`, and optionally mark explicitly refuted sources `stale`.

## Decision Shape

```json
{
  "id": "reflect-lexical",
  "action": "ADD",
  "title": "Prefer lexical recall before embeddings",
  "insight": "Use lexical recall before adding embeddings (because of lexical-a) (because of lexical-b).",
  "source_ids": ["lexical-a", "lexical-b"],
  "keywords": ["lexical", "recall"],
  "stale_sources": {"old-note": "refuted by newer evidence"}
}
```

## Skip Cases

- One-off task narration.
- Environment-dependent transient failures.
- Fewer than two matching episodic notes.
- Missing or unknown `(because of <id>)` citations.
- Over-budget semantic note or projected INDEX.
- Duplicate active semantic memory for the same title or same source set.

## Embedding Evaluation

Use `--evaluate-recall --holdout <jsonl> --top-k <n> --threshold <float>` to record whether lexical recall is sufficient. The evaluator uses the same index/frontmatter scoring surface as prompt-time recall, not full-body optimistic matching. If the result is `lexical_sufficient`, do not create `.npy` sidecars. If it is `embedding_required`, stop for a verified embedding implementation rather than adding untested infra.

# Mneme

> **Mneme is memory that survives the session.**
>
> It gives agents memory that persists, compounds, and can be trusted.

Mneme is a memory quality layer for OpenClaw.
It does not replace OpenClaw memory. It repairs, audits, and improves it.

## Goal

**Make an agent's memory work, then make it better.**

Mneme starts with **Six**.

For v1, that means starting with one agent — Six — and fixing the basic failure modes first:

- broken recall
- stale or missing indexes
- important facts trapped in daily notes
- duplicate or conflicting memory
- memory that exists, but is hard to use

## What Mneme does

Mneme v1 does four things:

1. **Restore recall**
   - detect broken memory config
   - detect missing embedding backends
   - detect stale or missing indexes
   - verify that memory search actually works

2. **Recover important memory**
   - read `MEMORY.md`
   - read daily memory files
   - extract durable facts worth keeping

3. **Compile memory into usable structure**
   - people
   - projects
   - systems
   - decisions
   - incidents
   - todos
   - timeline

4. **Audit memory quality**
   - duplicates
   - contradictions
   - stale facts
   - facts trapped in daily notes that should be promoted

## What Mneme is not

Mneme v1 is not:

- a new vector database
- a replacement for OpenClaw builtin, QMD, or Honcho memory
- cross-agent shared memory yet
- silent autonomous rewriting of memory
- a vague "AI memory" claim with no provenance

## Why this exists

OpenClaw already has real memory primitives: Markdown memory files, indexing, hybrid search, QMD, and Honcho.

So Mneme should not try to replace the official memory system.
It should make that system more reliable and more usable.

The first job is simple:

**fix recall, recover durable knowledge, and keep memory healthy over time.**

## V1 plan

### 1. Restore recall
Get memory search healthy and verified.

### 2. Recover durable memory
Promote important facts out of existing notes.

### 3. Compile memory
Turn scattered notes into usable indexes.

### 4. Keep memory healthy
Surface stale, duplicate, and conflicting facts.

## Success

Mneme v1 is successful if:

- Six can answer prior-context questions reliably
- answers come from memory, not bluffing
- important facts survive session resets
- memory becomes easier to inspect and maintain
- broken recall is caught before the user notices

## First tool

Mneme now includes its first live check:

- [`scripts/mneme_memory_check.py`](./scripts/mneme_memory_check.py) — verify memory config, index health, embeddings readiness, and live recall
- [`scripts/mneme_ingest_memory.py`](./scripts/mneme_ingest_memory.py) — ingest OpenClaw memory files into raw Mneme evidence JSONL
- [`scripts/mneme_compile_memory.py`](./scripts/mneme_compile_memory.py) — generate a first-pass compiled memory pack from OpenClaw-style notes
- [`scripts/mneme_secret_scrub.py`](./scripts/mneme_secret_scrub.py) — scan memory files for likely secrets and redact obvious raw tokens/passwords
- [`scripts/mneme_memory_drift.py`](./scripts/mneme_memory_drift.py) — detect likely contradictions and stale facts in memory files
- [`scripts/mneme_run.py`](./scripts/mneme_run.py) — run the Mneme maintenance flow in one command
- [`scripts/mneme_llm_compile.py`](./scripts/mneme_llm_compile.py) — prepare/validate LLM-assisted compile passes against raw evidence

## Docs

- [Mneme v1 Spec](./docs/spec-v1.md)
- [Evidence model](./docs/evidence-model.md)
- [Ingest](./docs/ingest.md)
- [Milestone 1 checklist](./docs/milestone-1-checklist.md)
- [Memory check](./docs/memory-check.md)
- [Compiler](./docs/compiler.md)
- [Compiler format](./docs/compiler-format.md)
- [Secret scrub](./docs/secret-scrub.md)
- [Memory drift](./docs/memory-drift.md)
- [Runner](./docs/runner.md)
- [LLM compiler](./docs/llm-compiler.md)
- [Automation](./docs/automation.md)
- [Roadmap](./ROADMAP.md)
- [Brand copy](./docs/brand-copy.md)

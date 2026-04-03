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

## Docs

- [Mneme v1 Spec](./docs/spec-v1.md)
- [Milestone 1 checklist](./docs/milestone-1-checklist.md)
- [Memory check](./docs/memory-check.md)
- [Roadmap](./ROADMAP.md)
- [Brand copy](./docs/brand-copy.md)

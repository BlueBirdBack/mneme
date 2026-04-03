# OpenClaw Memory References

Mneme is not a replacement for OpenClaw memory.
It is a layer that repairs, audits, compiles, and extends it.

This doc records the official OpenClaw memory references that shaped Mneme.

## Official OpenClaw docs

### 1. Memory overview
- https://docs.openclaw.ai/concepts/memory

What it contributes:
- the overall memory model
- how OpenClaw thinks about durable memory vs session context
- the baseline architecture Mneme should build on, not fight

How Mneme relates:
- Mneme treats this as the top-level contract
- Mneme's job is to improve memory quality and workflow around this base

### 2. Builtin memory
- https://docs.openclaw.ai/concepts/memory-builtin

What it contributes:
- file-backed memory behavior
- builtin indexing/search assumptions
- local-first memory primitives

How Mneme relates:
- Mneme relies on builtin memory as the practical substrate for `MEMORY.md` and daily notes
- Mneme should detect and repair failures in this layer rather than reinventing it blindly

### 3. QMD memory
- https://docs.openclaw.ai/concepts/memory-qmd

What it contributes:
- richer indexing and retrieval behavior
- transcript/doc indexing patterns
- more advanced local retrieval options

How Mneme relates:
- Mneme can treat QMD-style indexing as an upstream capability
- Mneme's evidence/compile layers should stay compatible with stronger retrieval backends like this

### 4. Honcho memory
- https://docs.openclaw.ai/concepts/memory-honcho

What it contributes:
- cross-session persistence
- user/agent modeling
- multi-agent memory direction

How Mneme relates:
- Mneme starts with one agent's memory first
- Honcho-style ideas matter later when promoted local knowledge becomes shared memory

### 5. Memory search
- https://docs.openclaw.ai/concepts/memory-search

What it contributes:
- the retrieval/search layer itself
- hybrid search behavior
- the operational side of recall quality

How Mneme relates:
- the first real Mneme trigger was exactly here: memory search was unavailable
- Mneme now includes checks to catch broken recall before the user does

## External inspiration

### Karpathy on memory systems
- https://x.com/karpathy/status/2039805659525644595

Why it matters:
- strong direction for evidence-backed memory systems
- raw evidence -> compiled notes/wiki -> retrieval -> maintenance
- reinforces that useful memory is a system, not just a bigger context window

How Mneme relates:
- Mneme follows the same general shape:
  - raw evidence
  - compiled memory
  - retrieval/validation
  - maintenance/hygiene
- but Mneme is grounded specifically in OpenClaw's memory model and runtime

## Practical rule

When Mneme changes memory behavior, the official OpenClaw docs remain the source of truth for:
- what the base system does
- what belongs in the runtime/config layer
- what Mneme should extend rather than duplicate

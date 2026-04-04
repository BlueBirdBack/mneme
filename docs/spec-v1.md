# Mneme v1 Spec

## One-line definition
Mneme is a memory quality layer for OpenClaw.
It repairs, audits, and improves memory instead of replacing it.

## Goal
Make Six's memory work, then make it better.

## Problem
OpenClaw already provides memory files, indexing, and search.
The gap is not the lack of a memory system.
The gap is memory quality.

Common failures:
- recall is broken or misconfigured
- indexes are stale or missing
- durable facts are buried in daily notes
- memory contains duplicates or contradictions
- the right fact exists somewhere, but is hard to retrieve and trust

## Scope
Mneme v1 does four things.

### 1. Restore recall
Mneme checks whether OpenClaw memory is actually working.

Checks:
- backend in use
- provider configuration
- embedding availability
- index health and freshness
- retrieval quality
- citation availability

Outputs:
- memory health report
- clear failure reasons
- recommended fixes

### 2. Recover important memory
Mneme reads existing memory sources and finds durable facts worth keeping.

Initial sources:
- `MEMORY.md`
- `memory/*.md`

Later sources:
- session transcripts
- selected extra docs and project notes

Outputs:
- candidate durable facts
- promotion suggestions
- duplicate/conflict warnings

### 3. Compile memory into usable structure
Mneme turns chronological notes into structured memory artifacts.

Initial compiled artifacts:
- `compiled/people.md`
- `compiled/projects.md`
- `compiled/systems.md`
- `compiled/decisions.md`
- `compiled/incidents.md`
- `compiled/timeline.md`

Planned next artifact:
- `compiled/todos.md`

Requirement:
important claims must stay traceable to source notes.

### 4. Audit memory quality
Mneme keeps memory from rotting.

Checks:
- duplicates
- contradictions
- stale facts
- missing provenance
- facts trapped in daily notes that should be durable

Outputs:
- memory hygiene report
- promotion suggestions
- repair suggestions

## Non-goals
Not in v1:
- replacing builtin memory, QMD, or Honcho
- building a new general-purpose vector backend
- cross-agent shared memory by default
- silent memory rewriting without audit trail
- claiming certainty without provenance

## Architecture
Keep it simple.

### Sources
Mneme reads OpenClaw memory sources first.
It does not invent a second hidden source of truth.

### Checks
Mneme runs health checks against the live memory setup.

### Compiler
Mneme compiles raw notes into structured artifacts.

### Audit
Mneme detects quality problems and proposes repairs.

### Promotion
Mneme suggests what should become durable memory.
It should not silently overwrite truth.

## Milestones

### Milestone 1: Recall works
Success means:
- memory search is healthy
- provider is valid
- index exists and is current
- recall returns useful results

### Milestone 2: Durable memory recovery
Success means:
- important facts are extracted from current notes
- obvious duplicates are merged or flagged
- missing durable facts are identified

### Milestone 3: Compiled memory exists
Success means:
- people, project, system, decision, incident, and timeline views exist
- they are easier to use than raw note grep
- todo views are clearly marked as planned until implemented

### Milestone 4: Memory hygiene exists
Success means:
- stale and contradictory memory is surfaced automatically
- memory quality improves over time

## First implementation target
The first live target is Six.

Immediate real-world problem:
- memory search is configured to use `local`
- local embeddings are unavailable
- semantic recall is broken

That is exactly the kind of failure Mneme v1 should detect and fix first.

## Definition of success
Mneme v1 succeeds if Six can reliably recover prior context from memory, with enough structure and provenance to trust the answer.

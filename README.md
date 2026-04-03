# Mneme

> **Mneme is memory that survives the session.**
>
> It gives agents memory that persists, compounds, and can be trusted.

Mneme turns raw evidence into durable, source-backed memory for agents.

## What it is

Mneme is a memory engine for agents. It collects raw evidence from sessions, notes, documents, code, and other sources, then compiles that evidence into structured memory that can be retrieved, cited, maintained, and shared.

The first job is not “shared memory for everyone.” The first job is simpler and harder:

**restore an agent’s memory, make it trustworthy, and make it compound over time.**

Shared memory comes later, after the system can reliably distinguish evidence from inference, current truth from stale notes, and personal context from promoted knowledge.

## Why it exists

Agent memory is usually weak in exactly the ways that matter most:

- important facts get trapped inside old sessions
- decisions become hard to recover
- notes drift away from source truth
- context accumulates, but knowledge does not

Mneme exists to fix that.

## Principles

- **Evidence first** — memory should be grounded in source material
- **Durable by default** — useful work should survive the session
- **Retrieval over wishful remembering** — important facts should be found, not guessed
- **Citations where it counts** — memory should be inspectable and verifiable
- **Maintenance matters** — stale, duplicate, and conflicting memory must be detectable
- **Promotion is earned** — shared memory should come from verified local memory, not vibes

## Initial scope

Version 1 is focused on personal agent memory:

1. ingest raw evidence
2. compile it into structured memory
3. retrieve it with citations and confidence markers
4. detect contradictions, duplicates, and stale facts
5. support deliberate promotion into shared memory later

## Non-goals for v1

- universal cross-agent truth by default
- hidden autonomous memory rewriting without auditability
- replacing source documents with opaque summaries
- pretending confidence is the same as correctness

## Status

Early repo. The shape is clear; the machinery comes next.

See [ROADMAP.md](./ROADMAP.md) for the first milestones and [docs/brand-copy.md](./docs/brand-copy.md) for positioning copy.

# Mneme Agent-Connected Workflow

Mneme now has a real agent-driven compile path.

This is the layer above the deterministic roundtrip tooling.

## What is "agent-connected"?

It means a real agent session does the grouping/summarization step instead of a human hand-writing candidate JSON.

The flow is:
1. ingest raw evidence
2. prepare category bundles
3. send one bundle to an agent
4. receive candidate JSON back
5. validate it against real evidence ids
6. materialize it into compiled outputs

## What lives in the repo

The repo provides the deterministic shell:
- `scripts/mneme_ingest_memory.py`
- `scripts/mneme_llm_compile.py`
- `scripts/mneme_materialize_candidates.py`
- `scripts/mneme_llm_roundtrip.py`

These handle:
- ingest
- bundle prep
- validation
- final output materialization

## What does **not** live in the repo

The actual agent dispatch currently depends on the OpenClaw runtime/tooling layer.
That part is environment-specific.

So the current split is:
- **repo** = stable pipeline pieces
- **runtime** = send bundle to agent, receive candidate JSON

## Proven result

The first real agent-connected pass was run for the `projects` category.

Outcome:
- a real `projects` bundle was sent to a sub-agent
- the sub-agent returned candidate JSON
- Mneme validated the evidence refs successfully
- Mneme materialized the result into compiled outputs

This proved the loop:

**raw evidence -> agent judgment -> validation -> compiled memory**

## Recommended next step

Add a runtime wrapper that can:
- pick a category bundle
- dispatch it to an agent automatically
- capture the JSON response
- call validate/materialize automatically
- write a short review report

That is the path from "agent-assisted" to "agent-driven" Mneme.
